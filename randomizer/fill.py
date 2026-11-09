"""Reparto determinista de objetos clave entre cofres (assumed fill).

`place` devuelve, para cada Hash de cofre, el `Drop__DropActor` que tendrá.
Solo se tocan los sitios elegibles (cofre asociado a una ubicación de OoTR,
sin parche de evento, fuera de la tienda y sin objeto de mazmorra). Los
objetos clave de esos sitios se colocan con *assumed fill*: al colocar cada
uno se dan por tenidos todos los que faltan por colocar y se elige al azar
entre los sitios libres alcanzables. El resto del contenido de los sitios
elegibles se baraja entre los sitios que quedan libres. El resultado se
valida con `World.can_beat`; si falla se reintenta con otro RNG.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from dataclasses import dataclass

from randomizer import RANDO_VERSION
from randomizer.game import ChestActor
from randomizer.items import (DUNGEON_ITEM_PREFIXES, ITEM_LEVEL, KEY_ITEMS, LABELS_ES,
                              NON_EXCLUDABLE)
from randomizer.locations import LocationEntry
from randomizer.logic.world import World

MODES = ('vanilla', 'any_chest')
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


class FillError(Exception):
    pass


def _settings_key(settings: Settings) -> str:
    data = dataclasses.asdict(settings)
    del data['seed']
    del data['spoiler']  # solo afecta a los archivos de salida, no a la colocación
    del data['skip_cutscenes']  # idem: no cambia la colocación
    data['excluded_items'] = sorted(settings.excluded_items)
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


def _fixed(world_base: dict[str, str], loc_map: dict[int, LocationEntry],
           placed: dict[int, str]) -> dict[str, str]:
    """`fixed` de la lógica: base vanilla con los sitios elegibles a relleno
    (`world_base`) y los objetos clave ya colocados encima."""
    fixed = dict(world_base)
    for h in sorted(placed):
        drop = placed[h]
        if drop in KEY_ITEMS:
            fixed[loc_map[h].location] = drop
    return fixed


def _attempt(rng: random.Random, original: dict[int, str], eligible: list[int],
             moving: list[int], loc_map: dict[int, LocationEntry], world: World,
             base: dict[str, str], no_key: frozenset[int] = frozenset()
             ) -> dict[int, str] | None:
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
        reach = world.reachable_locations(_fixed(base, loc_map, placed),
                                          owned=to_place[i + 1:])
        candidates = [h for h in free if h not in placed and h not in no_key
                      and loc_map[h].location in reach]
        if not candidates:
            return None
        placed[rng.choice(candidates)] = item

    rest = [original[h] for h in free if h not in moving]
    rng.shuffle(rest)
    open_sites = [h for h in free if h not in placed]
    for h, drop in zip(open_sites, rest, strict=True):
        placed[h] = drop

    if not world.can_beat(_fixed(base, loc_map, placed)):
        return None
    result = dict(original)
    result.update(placed)
    return result


def place(chests: list[ChestActor], loc_map: dict[int, LocationEntry],
          world: World, settings: Settings) -> dict[int, str]:
    """Mapa Hash -> Drop__DropActor para todos los cofres de `chests`."""
    if settings.key_items_mode not in MODES:
        raise FillError(f'Modo de objetos clave desconocido: {settings.key_items_mode!r}')
    bad = settings.excluded_items & NON_EXCLUDABLE
    if bad:
        label = ', '.join(LABELS_ES.get(a, a) for a in sorted(bad))
        raise FillError(f'No se puede excluir {label}: la lógica necesita moverlo '
                        'para que la partida sea completable.')
    original = _original_drops(chests)
    if settings.key_items_mode == 'vanilla':
        return dict(original)

    eligible = _eligible(chests, loc_map, original)
    moving = [h for h in eligible if original[h] in KEY_ITEMS
              and original[h] not in settings.excluded_items]
    no_key = frozenset(c.hash for c in chests
                       if c.banc.split('/')[1:2] and c.banc.split('/')[1] in NO_KEY_TARGET_ZONES)
    base = world.vanilla_fixed()
    for h in eligible:
        base[loc_map[h].location] = FILLER

    for attempt in range(MAX_ATTEMPTS + 1):
        result = _attempt(_rng(settings, attempt), original, eligible, moving,
                          loc_map, world, base, no_key)
        if result is not None:
            return result
    raise FillError('No se ha podido generar una semilla completable con estos ajustes')
