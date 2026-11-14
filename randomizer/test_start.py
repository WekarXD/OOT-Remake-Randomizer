"""Start presets for test seeds (never used by normal generation).

On a new game, the scene where Link first leaves his house (`HOOK_FLOW`) is
replaced by a chain: the flags that scene sets (so it does not replay), the
preset's flags, one item gift per item and a teleport. Built with
`formats.evfl_append`. See docs/superpowers/specs/2026-11-13-test-teleport-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from randomizer.formats.bfevfl import EventFlow, patch_pointers
from randomizer.formats.evfl_append import (ActionSpec, SubflowSpec, append_events,
                                            set_entry_subflows)

HOOK_FLOW = 'Dm_Kokiri_0045'
HOOK_ENTRY = 'EntryPoint0'
# Flags the hook scene sets itself (events 39 and 45).
HOOK_FLAGS = ('KokiriForest_LinkHouseDoor_Open', 'Dm_Kokiri_0050_After_Near_End')


@dataclass(frozen=True)
class StartPreset:
    banc: str  # destination map, e.g. 'HyruleField_Child'
    start_pos: str  # named start position in that map
    items: tuple[str, ...] = ()  # actors to give, e.g. 'Item_Ocarina_Fairy'
    flags: tuple[tuple[str, bool], ...] = ()  # (GameDataName, value)


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
