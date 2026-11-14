"""Start presets for test seeds (never used by normal generation).

On a new game, the scene where Link first leaves his house (`HOOK_FLOW`) is
replaced by a chain: the flags that scene sets (so it does not replay), the
preset's flags, one item gift per item and a teleport. Built with
`formats.evfl_append`. See docs/superpowers/specs/2026-11-13-test-teleport-design.md.

The game also needs to know which flows an event calls before it starts it:
the entry's own subflow list (`set_entry_subflows`) and the event's
`SubFlowList` row in `ANALYZED_INFO`. Without the first Link freezes at the
first call; without the second the event does not start (batch 21).
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from randomizer.formats import byml

from randomizer.formats.bfevfl import EventFlow, patch_pointers
from randomizer.formats.evfl_append import (ActionSpec, SubflowSpec, append_events,
                                            set_entry_subflows)

HOOK_FLOW = 'Dm_Kokiri_0045'
HOOK_ENTRY = 'EntryPoint0'
# Flags the hook scene sets itself (events 39 and 45).
HOOK_FLAGS = ('KokiriForest_LinkHouseDoor_Open', 'Dm_Kokiri_0050_After_Near_End')
ANALYZED_INFO = 'RSDB/GameAnalyzedEventInfo.Product.111.rstbl.byml.zs'
# Named start positions per map ({banc: {name: {'Rot': [x, y, z], 'Trans': [x, y, z]}}});
# the teleport's NextStartPos must be one of them.
START_POS = 'Banc/BancBasedResource/StartPos.byml.zs'


@dataclass(frozen=True)
class NewStartPos:
    """A start position to add to `START_POS` for a preset whose map has none
    where the test must begin."""
    name: str
    trans: tuple[float, float, float]
    rot: tuple[float, float, float]


@dataclass(frozen=True)
class StartPreset:
    banc: str  # destination map, e.g. 'HyruleField_Child'
    start_pos: str  # named start position in that map
    items: tuple[str, ...] = ()  # actors to give, e.g. 'Item_Ocarina_Fairy'
    flags: tuple[tuple[str, bool], ...] = ()  # (GameDataName, value)
    new_pos: NewStartPos | None = None  # added to `banc`; start_pos must name it


def _flag(name: str, value: bool) -> ActionSpec:
    return ActionSpec('GameDataActor', 'EventTriggerSetGameDataBool',
                      {'GameDataName': name, 'Index': -1, 'Value': value})


def _chain(preset: StartPreset) -> list[ActionSpec | SubflowSpec]:
    specs: list[ActionSpec | SubflowSpec] = [_flag(f, True) for f in HOOK_FLAGS]
    specs += [_flag(name, value) for name, value in preset.flags]
    specs += [SubflowSpec('Dm_SY_GetInEvent', 'GetInEvent', {'ActorName': item})
              for item in preset.items]
    specs.append(SubflowSpec('Dm_SY_BancChangeGo', 'EntryPoint0', {
        'NextBanc': preset.banc, 'NextStartPos': preset.start_pos, 'BootEventName': '',
        'IsCheckAir': False, 'NextStartPosAir': preset.start_pos}))
    return specs


def chain_calls(preset: StartPreset) -> list[tuple[str, str]]:
    """(flow, entry) of each subflow call of the preset chain, in order."""
    return [(s.flow, s.entry) for s in _chain(preset) if isinstance(s, SubflowSpec)]


def subflow_closure(load: Callable[[str], EventFlow | None],
                    calls: Iterable[tuple[str, str]], skip: str = '') -> list[str]:
    """Sorted names of every flow reached from `calls` ((flow, entry) pairs),
    following each entry's subflow list recursively; `load(name)` gives a flow
    (None if missing) and `skip` is left out (the event's own flow). This is the
    event's `SubFlowList` in `ANALYZED_INFO`."""
    flows: dict[str, EventFlow | None] = {}
    seen: set[tuple[str, str]] = set()
    stack = list(calls)
    while stack:
        name, entry = stack.pop()
        if (name, entry) in seen:
            continue
        seen.add((name, entry))
        if name not in flows:
            flows[name] = load(name)
        flow = flows[name]
        if flow is None or entry not in flow.entry_points:
            continue
        for i in flow.entry_subflows(entry):
            ev = flow.events[i]
            stack.append((ev.sub_flow or name, ev.sub_entry))
    return sorted({name for name, _ in seen} - {skip})


def with_subflow_list(info: bytes, event: str, names: Sequence[str]) -> bytes:
    """`ANALYZED_INFO` (decompressed) with event's `SubFlowList` set to `names`
    (sorted, as in the game). Raises KeyError if the event has no row."""
    ver, rows = byml.load(info)
    if not any(r['__RowId'] == event for r in rows):
        raise KeyError(event)
    rows = [{**r, 'SubFlowList': sorted(names)} if r['__RowId'] == event else r for r in rows]
    return byml.dump(rows, ver)


def with_start_pos(data: bytes, banc: str, pos: NewStartPos) -> bytes:
    """`START_POS` (decompressed) with `pos` added to map `banc`. Raises KeyError
    for an unknown map and ValueError if the name already exists there."""
    ver, root = byml.load(data)
    if banc not in root:
        raise KeyError(banc)
    if pos.name in root[banc]:
        raise ValueError(f'{banc} already has a start position {pos.name!r}.')
    entry = {'Rot': list(pos.rot), 'Trans': list(pos.trans)}
    return byml.dump({**root, banc: {**root[banc], pos.name: entry}}, ver)


def apply_start(flow_bytes: bytes, preset: StartPreset) -> bytes:
    """`HOOK_FLOW` with its entry pointing to the preset chain (the original events
    stay, unreachable from the entry) and listing the chain's subflow calls."""
    specs = _chain(preset)
    data, idx = append_events(flow_bytes, specs)
    flow = EventFlow(data)
    links = {flow.link_slots[('entry', HOOK_ENTRY)]: idx[0]}
    for a, b in zip(idx, idx[1:]):
        links[flow.link_slots[('next', a)]] = b
    data = patch_pointers(data, links)
    calls = [i for i, s in zip(idx, specs) if isinstance(s, SubflowSpec)]
    return set_entry_subflows(data, HOOK_ENTRY, calls)
