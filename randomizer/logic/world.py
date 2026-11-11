"""Búsqueda de alcanzabilidad sobre la lógica glitchless de OoTR.

`World(settings)` compila una vez todas las reglas de los World/*.json
vendorizados (sin MQ) y responde, para un reparto `fixed` (ubicación OoTR ->
objeto OoTR o actor del remake), qué ubicaciones se alcanzan y si se puede
ganar. Imita `Search.py` de OoTR: niño y adulto empiezan en `Root`, cada edad
expande sus regiones por las salidas cuya regla cumple, y las ubicaciones y
eventos se recogen con un `State` compartido hasta llegar a un punto fijo.

Simplificaciones (todas conservadoras: la lógica puede creer inalcanzable algo
que sí lo es, nunca al revés):

- Hora del día: `at_day`, `at_night` y `at_dampe_time` valen para una edad si
  esa edad alcanza alguna región con `"time_passes": true` (OoTR sin barajar
  entradas los da por buenos siempre). `provides_time` no se usa.
- `has_all_notes_for_song` exige los cinco botones de ocarina (no aplica en
  vanilla: `shuffle_individual_ocarina_notes = false`).
- Objetos progresivos con nivel (gancho, fuerza): modelo directo del remake,
  se guarda el nivel máximo; el objeto OoTR genérico cuenta como nivel 1 (ver
  `rules.State.collect`).
- `vanilla_settings.json`: `open_door_of_time` vale `"stones_oot_sot"` y no
  `false`, porque en este commit de OoTR el ajuste es una cadena; es el valor
  que reproduce el juego original (3 piedras + Ocarina del Tiempo + Canción
  del Tiempo) y el más restrictivo. El fichero incluye también valores que en
  OoTR calcula `World` y que tapan al ajuste (`keysanity`,
  `shuffle_silver_rupees`, `entrance_shuffle`, `skipped_trials`,
  `selected_adult_trade_item`, `disable_trade_revert`...).
- Estado inicial como `ItemPool.py` de OoTR: con estos ajustes, los cinco
  botones de ocarina y una llave del Templo del Fuego regalada (OoTR la da
  porque asume que el jugador no la gasta en la puerta baja con el diseño
  vanilla de llaves; vanilla tiene ese riesgo de bloqueo, OoTR lo ignora).
- Lógica de llaves: la de OoTR (peor orden de apertura de puertas). Con
  llaves y objetos clave en su sitio vanilla, OoTR NO da el juego por
  ganable (Templo del Agua pide 5 llaves antes del Gancho largo y solo hay 4;
  el Espíritu pide 3 de niño para los Guanteletes de plata y hay 2), aunque
  el juego real sí lo es. Es más estricto, así que se deja tal cual.
- Los objetos sin efecto en ninguna regla no se recogen durante la búsqueda
  (no cambian el resultado); `reachable_locations` evalúa todas las
  ubicaciones al final con el estado del punto fijo.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path

from randomizer import items as remake_items
from randomizer.logic import ootr_data
from randomizer.logic.rules import (
    ALIASES, ITEM_TABLE, AGES, OCARINA_BUTTONS, Compiler, RuleError, State, _true)

SETTINGS_PATH = Path(__file__).resolve().parent / 'vanilla_settings.json'

Rule = Callable[[State, str], bool]


# Reglas propias del remake que endurecen las de OoTR, por
# (región, tipo, sitio). `{orig}` es la regla original de OoTR.
# - Árbol Deku: para subir al piso de la sala de la brújula hay que matar las
#   Skulltulas de las enredaderas con un arma a distancia (lote 17). El sótano
#   se abre saltando desde ese piso sobre la telaraña.
_DEKU_UPPER = 'can_use(Slingshot) or can_use(Bow) or can_use(Hookshot)'
REMAKE_RULES: dict[tuple[str, str, str], str] = {
    ('Deku Tree Lobby', 'locations', 'Deku Tree Compass Chest'): _DEKU_UPPER,
    ('Deku Tree Lobby', 'locations', 'Deku Tree Compass Room Side Chest'): _DEKU_UPPER,
    ('Deku Tree Lobby', 'locations', 'Deku Tree GS Compass Room'):
        f'({{orig}}) and ({_DEKU_UPPER})',
    ('Deku Tree Lobby', 'exits', 'Deku Tree Basement'):
        f'deku_tree_shortcuts or (({{orig}}) and here({_DEKU_UPPER}))',
}


def _remake_rule(region: str, kind: str, spot: str, rule: str) -> str:
    override = REMAKE_RULES.get((region, kind, spot))
    return rule if override is None else override.replace('{orig}', rule)


def load_vanilla_settings() -> dict:
    data = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
    data.pop('_comment', None)
    return data


class _Region:
    __slots__ = ('name', 'exits', 'locations', 'events', 'time_passes')

    def __init__(self, name: str, time_passes: bool) -> None:
        self.name = name
        self.time_passes = time_passes
        self.exits: list[tuple[str, Rule]] = []
        self.locations: list[tuple[str, Rule]] = []
        self.events: list[tuple[str, Rule]] = []


class World:
    def __init__(self, settings: dict) -> None:
        self.settings = settings
        compiler = Compiler(ootr_data.load_helpers(), settings)
        self.regions: dict[str, _Region] = {}
        for regions in ootr_data.load_world_files().values():
            for data in regions:
                name = data['region_name']
                if name in self.regions:
                    raise RuleError(f'duplicate region {name!r}')
                region = _Region(name, bool(data.get('time_passes')))
                for kind in ('exits', 'locations', 'events'):
                    target = getattr(region, kind)
                    for spot, rule in (data.get(kind) or {}).items():
                        rule = _remake_rule(name, kind, spot, rule)
                        target.append((spot, compiler.compile(rule, region=name)))
                if 'savewarp' in data:
                    # Como OoTR: salida sin condición hacia el destino del savewarp.
                    region.exits.append((data['savewarp'].split(' -> ')[1], _true))
                self.regions[name] = region
        compiler.compile_pending_subrules()
        for region_name, event, fn in compiler.subrules:
            if region_name not in self.regions:
                raise RuleError(f'at() to unknown region {region_name!r}')
            self.regions[region_name].events.append((event, fn))
        for region in self.regions.values():
            for target, _ in region.exits:
                if target not in self.regions:
                    raise RuleError(f'exit {region.name} -> {target}: unknown region')

        self.locations = ootr_data.load_locations()
        self.win_location = next(
            n for n, v in self.locations.items() if v['vanilla_item'] == 'Triforce')
        self._referenced = frozenset(compiler.referenced)
        self._relevant_cache: dict[str, bool] = {}
        # (región, ubicación, regla) de todas las ubicaciones del mundo.
        self._all_locations = [(r.name, loc, fn) for r in self.regions.values()
                               for loc, fn in r.locations]
        self._events = [(r.name, ev, fn) for r in self.regions.values()
                        for ev, fn in r.events]
        if not any(loc == self.win_location for _, loc, _ in self._all_locations):
            raise RuleError(f'win location {self.win_location!r} not in world')
        self.starting_items = self._starting_items(settings)

    @staticmethod
    def _starting_items(settings: dict) -> list[str]:
        """Objetos que OoTR mete en el estado inicial (ItemPool.py) con estos ajustes."""
        start = []
        if not settings['shuffle_individual_ocarina_notes']:
            start += list(OCARINA_BUTTONS)
        if settings['scarecrow_behavior'] == 'free':
            start.append('Scarecrow Song')
        if not settings['keysanity']:
            # OoTR no sabe modelar la llave vanilla de la puerta baja del Templo
            # del Fuego y regala una llave (asume que no se gasta en esa puerta).
            start.append('Small Key (Fire Temple)')
        return start

    # ---- API -------------------------------------------------------------
    def vanilla_fixed(self) -> dict[str, str]:
        fixed = {name: v['vanilla_item'] for name, v in self.locations.items()
                 if v['vanilla_item']}
        for actor, location in remake_items.KEY_ITEM_HOME.items():
            fixed[location] = actor
        return fixed

    def reachable_locations(self, fixed: dict[str, str],
                            owned: Iterable[str] = ()) -> set[str]:
        """Ubicaciones alcanzables. `owned`: objetos extra que se dan por
        tenidos desde el principio (para el *assumed fill*)."""
        state, reached, _ = self._search(fixed, stop_at_win=False, owned=owned)
        return {loc for region, loc, fn in self._all_locations
                if self._ok(fn, state, reached, region)}

    def can_beat(self, fixed: dict[str, str], owned: Iterable[str] = ()) -> bool:
        return self._search(fixed, stop_at_win=True, owned=owned)[2]

    # ---- internals -------------------------------------------------------
    def _relevant(self, item: str) -> bool:
        cached = self._relevant_cache.get(item)
        if cached is not None:
            return cached
        if item in remake_items.KEY_ITEMS:
            result = True
        elif item not in ITEM_TABLE:
            raise KeyError(f'unknown item {item!r}')
        else:
            alias = ALIASES.get(item)
            result = item in self._referenced or bool(alias and alias[0] in self._referenced)
        self._relevant_cache[item] = result
        return result

    @staticmethod
    def _ok(fn: Rule, state: State, reached: dict[str, set[str]], region: str) -> bool:
        return ((region in reached['adult'] and fn(state, 'adult'))
                or (region in reached['child'] and fn(state, 'child')))

    def _search(self, fixed: dict[str, str], stop_at_win: bool,
                owned: Iterable[str] = ()):
        state = State()
        for item in self.starting_items:
            state.collect(item)
        for item in owned:
            state.collect(item)
        reached = {age: {'Root'} for age in AGES}
        queues = {age: list(self.regions['Root'].exits) for age in AGES}
        pending: list[tuple[str, str | None, Rule, str]] = []
        for region, loc, fn in self._all_locations:
            item = fixed.get(loc)
            if loc == self.win_location:
                pending.append((region, loc, fn, item or ''))
            elif item is not None and self._relevant(item):
                pending.append((region, loc, fn, item))
        for region, event, fn in self._events:
            pending.append((region, None, fn, event))

        won = False
        while True:
            for age in AGES:
                self._expand(age, state, reached[age], queues)
            progress = False
            remaining = []
            for entry in pending:
                region, loc, fn, item = entry
                if self._ok(fn, state, reached, region):
                    progress = True
                    if loc is None:
                        state.events.add(item)
                    else:
                        if loc == self.win_location:
                            won = True
                            if stop_at_win:
                                return state, reached, True
                        if item:
                            state.collect(item)
                else:
                    remaining.append(entry)
            pending = remaining
            if not progress:
                return state, reached, won

    def _expand(self, age: str, state: State, regs: set[str],
                queues: dict[str, list[tuple[str, Rule]]]) -> None:
        queue = queues[age]
        failed: list[tuple[str, Rule]] = []
        i = 0
        while i < len(queue):
            target, fn = queue[i]
            i += 1
            if target in regs:
                continue
            if fn(state, age):
                regs.add(target)
                region = self.regions[target]
                if region.time_passes and age not in state.tod:
                    state.tod.add(age)
                    queue.extend(failed)
                    failed = []
                queue.extend(region.exits)
            else:
                failed.append((target, fn))
        queues[age] = failed
