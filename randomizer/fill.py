"""Reparto determinista de objetos clave entre cofres (assumed fill).

`place` devuelve, para cada Hash de cofre, el `Drop__DropActor` que tendrá.
Solo se tocan los sitios elegibles (cofre asociado a una ubicación de OoTR,
sin parche de evento, fuera de la tienda y sin objeto de mazmorra). Los
objetos clave de esos sitios se colocan con *assumed fill*: al colocar cada
uno se dan por tenidos todos los que faltan por colocar y se elige al azar
entre los sitios libres alcanzables. El resto del contenido de los sitios
elegibles se baraja entre los sitios que quedan libres. El resultado se
valida con `World.can_beat`; si falla se reintenta con otro RNG.

Con `tokensanity` distinto de `'off'`, las Skulltulas doradas que entran según
el modo (`gs_sites`) son sitios elegibles más, cuyo contenido original es la
ficha (`TOKEN`). Las fichas entran en el reparto como el resto del contenido.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from dataclasses import dataclass

from randomizer import RANDO_VERSION
from randomizer.game import ChestActor, SkulltulaActor
from randomizer.items import (DUNGEON_ITEM_PREFIXES, ITEM_LEVEL, KEY_ITEMS, LABELS_ES,
                              NON_EXCLUDABLE)
from randomizer.locations import GsEntry, LocationEntry
from randomizer.logic.world import World

MODES = ('vanilla', 'any_chest')
TOKENSANITY = ('off', 'dungeons', 'overworld', 'all')
TOKEN = 'Obj_Token_Gold'
OOTR_TOKEN = 'Gold Skulltula Token'
MAX_ATTEMPTS = 100
FILLER = 'Rupees (5)'
# Zonas (segmento de la ruta del Banc tras 'Banc/') donde no se colocan objetos
# clave. Sus cofres siguen siendo origen de objetos y destino de relleno, pero
# en el remake el número de llaves pequeñas y de puertas de estas mazmorras
# difiere del N64 (Templo del Agua 4 llaves en vez de 6, Centro de
# Entrenamiento Gerudo, Pozo) y la llave gratis del Templo del Fuego es una
# suposición de OoTR; la lógica no es fiable ahí.
NO_KEY_TARGET_ZONES = frozenset({'WaterTemple', 'GerudoTrainingGround',
                                 'BottomOfTheWell', 'FireTemple'})


@dataclass(frozen=True)
class Settings:
    seed: str
    key_items_mode: str = 'any_chest'  # 'vanilla' | 'any_chest'
    excluded_items: frozenset[str] = frozenset()
    spoiler: bool = True
    skip_cutscenes: bool = False
    tokensanity: str = 'off'  # ver TOKENSANITY


class FillError(Exception):
    pass


def _settings_key(settings: Settings) -> str:
    data = dataclasses.asdict(settings)
    del data['seed']
    del data['spoiler']  # solo afecta a los archivos de salida, no a la colocación
    del data['skip_cutscenes']  # idem: no cambia la colocación
    data['excluded_items'] = sorted(settings.excluded_items)
    if settings.tokensanity == 'off':
        del data['tokensanity']  # la clave queda como antes de existir la opción
    return json.dumps(data, sort_keys=True)


def _rng(settings: Settings, attempt: int) -> random.Random:
    text = f'{RANDO_VERSION}|{settings.seed}|{_settings_key(settings)}|{attempt}'
    digest = hashlib.sha256(text.encode()).digest()
    return random.Random(int.from_bytes(digest[:8], 'big'))


def _original_drops(chests: list[ChestActor]) -> dict[int, str]:
    out: dict[int, str] = {}
    for c in chests:
        prev = out.setdefault(c.hash, c.drop)
        if prev != c.drop:
            raise FillError(f'El cofre {c.hash} tiene contenidos distintos en sus copias')
    return out


def _eligible(chests: list[ChestActor], loc_map: dict[int, LocationEntry],
              original: dict[int, str]) -> list[int]:
    shop = {c.hash for c in chests if 'HrlCity_Shop' in c.gyaml}
    out = []
    for h in sorted(original):
        entry = loc_map.get(h)
        if entry is None or entry.status == 'unmapped' or entry.needs_event_patch:
            continue
        if h in shop or original[h].startswith(DUNGEON_ITEM_PREFIXES):
            continue
        out.append(h)
    return out


def gs_sites(skulltulas: list[SkulltulaActor], gs_map: dict[int, GsEntry] | None,
             mode: str) -> list[int]:
    """Hash de las Skulltulas que son sitios con este modo de tokensanity,
    sin duplicados y ordenados. Las que no están en `gs_map` no entran."""
    if mode not in TOKENSANITY:
        raise FillError(f'Modo de tokensanity desconocido: {mode!r}')
    if mode == 'off' or not gs_map:
        return []
    out = set()
    for s in skulltulas:
        entry = gs_map.get(s.hash)
        if entry is not None and (mode == 'all' or entry.dungeon == (mode == 'dungeons')):
            out.add(s.hash)
    return sorted(out)


def _fixed(world_base: dict[str, str], site_loc: dict[int, str],
           placed: dict[int, str]) -> dict[str, str]:
    """`fixed` de la lógica: base vanilla con los sitios elegibles a relleno
    (`world_base`) y los objetos clave y las fichas ya colocados encima."""
    fixed = dict(world_base)
    for h in sorted(placed):
        drop = placed[h]
        if drop in KEY_ITEMS:
            fixed[site_loc[h]] = drop
        elif drop == TOKEN:
            fixed[site_loc[h]] = OOTR_TOKEN
    return fixed


def _attempt(rng: random.Random, original: dict[int, str], eligible: list[int],
             moving: list[int], site_loc: dict[int, str], world: World,
             base: dict[str, str], no_key: frozenset[int] = frozenset(),
             gs: frozenset[int] = frozenset(),
             gs_forbidden: frozenset[str] = frozenset()) -> dict[int, str] | None:
    # Sitios elegibles que se quedan fijos: los de objetos clave excluidos.
    pinned = {h: original[h] for h in eligible
              if original[h] in KEY_ITEMS and h not in moving}
    free = [h for h in eligible if h not in pinned]

    to_place = [original[h] for h in moving]
    rng.shuffle(to_place)
    # Estable: progresivos de nivel más alto primero, el resto en orden barajado.
    to_place.sort(key=lambda a: -ITEM_LEVEL[a][1] if a in ITEM_LEVEL else 0)

    placed: dict[int, str] = dict(pinned)
    for i, item in enumerate(to_place):
        reach = world.reachable_locations(_fixed(base, site_loc, placed),
                                          owned=to_place[i + 1:])
        candidates = [h for h in free if h not in placed and h not in no_key
                      and site_loc[h] in reach
                      and not (h in gs and item in gs_forbidden)]
        if not candidates:
            return None
        placed[rng.choice(candidates)] = item

    rest = [original[h] for h in free if h not in moving]
    rng.shuffle(rest)
    open_sites = [h for h in free if h not in placed]
    # Las Skulltulas libres se llenan primero, con los primeros contenidos
    # barajados que se pueden soltar; lo que queda va a los cofres libres.
    open_gs = [h for h in open_sites if h in gs]
    allowed = [i for i, drop in enumerate(rest) if drop not in gs_forbidden][:len(open_gs)]
    if len(allowed) < len(open_gs):
        raise FillError('No hay suficientes objetos que se puedan soltar en las Skulltulas')
    for h, i in zip(open_gs, allowed, strict=True):
        placed[h] = rest[i]
    taken = set(allowed)
    rest = [drop for i, drop in enumerate(rest) if i not in taken]
    open_chests = [h for h in open_sites if h not in gs]
    for h, drop in zip(open_chests, rest, strict=True):
        placed[h] = drop

    if not world.can_beat(_fixed(base, site_loc, placed)):
        return None
    result = dict(original)
    result.update(placed)
    return result


def place(chests: list[ChestActor], loc_map: dict[int, LocationEntry],
          world: World, settings: Settings,
          skulltulas: list[SkulltulaActor] = (),
          gs_map: dict[int, GsEntry] | None = None,
          gs_forbidden: frozenset[str] = frozenset()) -> dict[int, str]:
    """Mapa Hash -> Drop__DropActor para todos los cofres de `chests` y las
    Skulltulas que entran con `settings.tokensanity` (ver `gs_sites`).
    `gs_forbidden`: contenidos que no pueden ir a una Skulltula."""
    if settings.key_items_mode not in MODES:
        raise FillError(f'Modo de objetos clave desconocido: {settings.key_items_mode!r}')
    bad = settings.excluded_items & NON_EXCLUDABLE
    if bad:
        label = ', '.join(LABELS_ES.get(a, a) for a in sorted(bad))
        raise FillError(f'No se puede excluir {label}: la lógica necesita moverlo '
                        'para que la partida sea completable.')
    gs = gs_sites(skulltulas, gs_map, settings.tokensanity)
    original = _original_drops(chests)
    for h in gs:
        if h in original:
            raise FillError(f'El Hash {h} es a la vez cofre y Skulltula')
        original[h] = TOKEN
    if settings.key_items_mode == 'vanilla':
        return dict(original)

    chest_sites = _eligible(chests, loc_map, original)
    eligible = sorted(chest_sites + gs)
    site_loc = {h: loc_map[h].location for h in chest_sites}
    site_loc.update((h, gs_map[h].location) for h in gs)
    moving = [h for h in eligible if original[h] in KEY_ITEMS
              and original[h] not in settings.excluded_items]
    bancs = [(c.hash, c.banc) for c in chests] + [(s.hash, s.banc) for s in skulltulas]
    no_key = frozenset(h for h, banc in bancs
                       if banc.split('/')[1:2] and banc.split('/')[1] in NO_KEY_TARGET_ZONES)
    no_key |= frozenset(h for h in gs
                        if gs_map[h].no_key or gs_map[h].status == 'guessed')
    base = world.vanilla_fixed()
    for h in eligible:
        base[site_loc[h]] = FILLER

    for attempt in range(MAX_ATTEMPTS + 1):
        result = _attempt(_rng(settings, attempt), original, eligible, moving,
                          site_loc, world, base, no_key, frozenset(gs), gs_forbidden)
        if result is not None:
            return result
    raise FillError('No se ha podido generar una semilla completable con estos ajustes')
