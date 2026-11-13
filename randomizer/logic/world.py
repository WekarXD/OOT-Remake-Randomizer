"""Reachability search over OoTR's glitchless logic.

`World(settings)` compiles once all the rules of the vendored World/*.json
(no MQ) and answers, for a placement `fixed` (OoTR location -> OoTR item or
remake actor), which locations are reachable and whether the game can be
beaten. It mimics OoTR's `Search.py`: child and adult start at `Root`, each
age expands its regions through the exits whose rule is met, and locations
and events are collected with a shared `State` until a fixed point is reached.

Simplifications (all conservative: the logic may consider something
unreachable that is reachable, never the reverse):

- Time of day: `at_day`, `at_night` and `at_dampe_time` hold for an age if
  that age reaches some region with `"time_passes": true` (OoTR without
  entrance shuffle always treats them as true). `provides_time` is not used.
- `has_all_notes_for_song` requires all five ocarina buttons (does not apply
  in vanilla: `shuffle_individual_ocarina_notes = false`).
- Progressive items with a level (hookshot, strength): the remake's direct
  model, the maximum level is kept; the generic OoTR item counts as level 1
  (see `rules.State.collect`).
- `vanilla_settings.json`: `open_door_of_time` is `"stones_oot_sot"` and not
  `false`, because in this OoTR commit the setting is a string; it is the
  value that reproduces the original game (3 stones + Ocarina of Time + Song
  of Time) and the most restrictive. The file also includes values that OoTR
  computes in `World` and that override the setting (`keysanity`,
  `shuffle_silver_rupees`, `entrance_shuffle`, `skipped_trials`,
  `selected_adult_trade_item`, `disable_trade_revert`...).
- Starting state like OoTR's `ItemPool.py`: with these settings, the five
  ocarina buttons and a gifted Fire Temple key (OoTR gives it because it
  assumes the player does not spend it on the lower door with the vanilla key
  design; vanilla has that softlock risk, OoTR ignores it).
- Key logic: OoTR's (worst door-opening order). With keys and key items in
  their vanilla spots, OoTR does NOT consider the game beatable (the Water
  Temple asks for 5 keys before the Longshot and there are only 4; the Spirit
  Temple asks for 3 as a child for the Silver Gauntlets and there are 2),
  although the real game is. It is stricter, so it is left as is.
- Bombs (batch 19): in the remake they cannot be thrown until the Goron's
  Bracelet is owned, so `REMAKE_HELPERS` turns `Bomb_Bag` into "Bomb Bag and
  strength". It also gates Bombchus, which the rules tie to the Bomb Bag.
- Items with no effect in any rule are not collected during the search (they
  do not change the result); `reachable_locations` evaluates all the
  locations at the end with the fixed-point state.
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


# Remake-specific rules that tighten OoTR's, keyed by
# (region, kind, spot). `{orig}` is OoTR's original rule.
# - Deku Tree: to climb to the floor of the compass room you have to kill the
#   vine Skulltulas with a ranged weapon (batch 17). The basement is
#   opened by jumping from that floor onto the web.
_DEKU_UPPER = 'can_use(Slingshot) or can_use(Bow) or can_use(Hookshot)'
REMAKE_RULES: dict[tuple[str, str, str], str] = {
    ('Deku Tree Lobby', 'locations', 'Deku Tree Compass Chest'): _DEKU_UPPER,
    ('Deku Tree Lobby', 'locations', 'Deku Tree Compass Room Side Chest'): _DEKU_UPPER,
    ('Deku Tree Lobby', 'locations', 'Deku Tree GS Compass Room'):
        f'({{orig}}) and ({_DEKU_UPPER})',
    ('Deku Tree Lobby', 'exits', 'Deku Tree Basement'):
        f'deku_tree_shortcuts or (({{orig}}) and here({_DEKU_UPPER}))',
}


# Remake helpers that replace OoTR's, applied over LogicHelpers.json. Helpers
# take precedence over item names, so `Bomb_Bag` here gates every rule that
# asks for the bag (`Bombs`, `has_bombchus`, the World files...). The item is
# named as a string so the helper does not expand itself.
REMAKE_HELPERS: dict[str, str] = {
    'Bomb_Bag': "'Bomb Bag' and Progressive_Strength_Upgrade",
}


def load_helpers() -> dict[str, str]:
    """OoTR's helpers with `REMAKE_HELPERS` applied over them."""
    return {**ootr_data.load_helpers(), **REMAKE_HELPERS}


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
        compiler = Compiler(load_helpers(), settings)
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
                    # Like OoTR: unconditional exit to the savewarp destination.
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
        # (region, location, rule) of all the locations in the world.
        self._all_locations = [(r.name, loc, fn) for r in self.regions.values()
                               for loc, fn in r.locations]
        self._events = [(r.name, ev, fn) for r in self.regions.values()
                        for ev, fn in r.events]
        if not any(loc == self.win_location for _, loc, _ in self._all_locations):
            raise RuleError(f'win location {self.win_location!r} not in world')
        self.starting_items = self._starting_items(settings)

    @staticmethod
    def _starting_items(settings: dict) -> list[str]:
        """Items that OoTR puts in the starting state (ItemPool.py) with these settings."""
        start = []
        if not settings['shuffle_individual_ocarina_notes']:
            start += list(OCARINA_BUTTONS)
        if settings['scarecrow_behavior'] == 'free':
            start.append('Scarecrow Song')
        if not settings['keysanity']:
            # OoTR cannot model the vanilla key of the Fire Temple's lower door
            # and gifts a key (assuming it is not spent on that door).
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
        """Reachable locations. `owned`: extra items assumed to be owned
        from the start (for the *assumed fill*)."""
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
