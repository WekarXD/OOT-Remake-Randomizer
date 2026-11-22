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

from randomizer.analyzed_info import ANALYZED_INFO, subflow_closure  # noqa: F401 (re-exported)
from randomizer.formats import byml

from randomizer.formats.bfevfl import EventFlow, patch_pointers
from randomizer.formats.evfl_append import (ActionSpec, SubflowSpec, add_actions, append_events,
                                            set_entry_subflows)

HOOK_FLOW = 'Dm_Kokiri_0045'
HOOK_ENTRY = 'EntryPoint0'
# Flags the hook scene sets itself (events 39 and 45).
HOOK_FLAGS = ('KokiriForest_LinkHouseDoor_Open', 'Dm_Kokiri_0050_After_Near_End')
# (GameDataName, value) for leaving the forest, which the teleport skips (batch 20):
# - Saria's farewell on the bridge (KokiriForest_ArriveLostWood -> Dm_Kokiri_0150/0155):
#   otherwise walking back to the bridge triggers it with Saria absent and the screen
#   stays black. HyruleField_ChangeENV is the flag it sets.
# - the exit guard (Npc_Kokiri_007_Child): his air wall on the bridge path is present
#   while this flag is on; he clears it himself after the Deku Tree.
FOREST_EXIT_FLAGS = (('HavePlayedEvent.KokiriForest_ArriveLostWood', True),
                     ('HavePlayedEvent.Dm_Kokiri_0150', True),
                     ('HavePlayedEvent.Dm_Kokiri_0155', True),
                     ('HyruleField_ChangeENV', True),
                     ('KokiriForest_Npc_Kokiri_007_Child_Blocker_00', False))
# Becoming an adult, as the game does when the Master Sword is drawn again
# (Market_Child_Field_ChildToAdult): swap the equipment, leave the childhood, then
# change to an *_Adult map.
ERA_CHANGE = ('ReplaceEquipmentForEraChange', 'ReplaceEquipmentForEraChange')
CHILDHOOD_FLAG = 'Sequence_IsChildhood'
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
    # (ChallengeName, StepName) quest steps to progress, in order (e.g. the castle
    # quest must be at Step04 for Zelda's meeting to trigger).
    challenge_steps: tuple[tuple[str, str], ...] = ()
    adult: bool = False  # arrive as an adult; `banc` is an *_Adult map or a dungeon
    # Event started on arrival. A dungeon's map entrance passes its arrival event
    # (e.g. 'Dm_SY_BancChangeArrive_InsideTheDekuTree_01').
    boot_event: str = ''
    rupees: int = 0  # rupees to add (as the fountains' payment does, with a sign)
    ints: tuple[tuple[str, int], ...] = ()  # (GameDataName, value), e.g. a token count


def _flag(name: str, value: bool) -> ActionSpec:
    return ActionSpec('GameDataActor', 'EventTriggerSetGameDataBool',
                      {'GameDataName': name, 'Index': -1, 'Value': value})


def _chain(preset: StartPreset) -> list[ActionSpec | SubflowSpec]:
    specs: list[ActionSpec | SubflowSpec] = [_flag(f, True) for f in HOOK_FLAGS]
    specs += [_flag(name, value) for name, value in FOREST_EXIT_FLAGS + preset.flags]
    specs += [ActionSpec('GameDataActor', 'EventTriggerSetGameDataInt',
                         {'GameDataName': name, 'Index': -1, 'Value': value})
              for name, value in preset.ints]
    specs += [ActionSpec('ChallengeSystemActor', 'EventExecuteProgressChallengeStep', {
        'ChallengeName': challenge, 'IsIgnoreCompletedChallenge': False,
        'IsIgnoreChallengeProgressUI': True, 'IsWaitEnd': True, 'StepName': step})
        for challenge, step in preset.challenge_steps]
    specs += [SubflowSpec('Dm_SY_GetInEvent', 'GetInEvent', {'ActorName': item})
              for item in preset.items]
    if preset.rupees:
        specs.append(ActionSpec('PouchSystemActor', 'EventTriggerIncreaseRupee',
                                {'Value': preset.rupees}))
    if preset.adult:
        # A dungeon has one map for both eras; only a child map conflicts (batch 33).
        if preset.banc.endswith('_Child'):
            raise ValueError(f'An adult preset needs an *_Adult map, not {preset.banc!r}.')
        # The era change reads the childhood flag, so it runs before the flag changes.
        specs += [SubflowSpec(*ERA_CHANGE, {}), _flag(CHILDHOOD_FLAG, False)]
    specs.append(SubflowSpec('Dm_SY_BancChangeGo', 'EntryPoint0', {
        'NextBanc': preset.banc, 'NextStartPos': preset.start_pos,
        'BootEventName': preset.boot_event,
        'IsCheckAir': False, 'NextStartPosAir': preset.start_pos}))
    return specs


def chain_calls(preset: StartPreset) -> list[tuple[str, str]]:
    """(flow, entry) of each subflow call of the preset chain, in order."""
    return [(s.flow, s.entry) for s in _chain(preset) if isinstance(s, SubflowSpec)]




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
    data = add_actions(flow_bytes, [(s.actor, s.action) for s in specs
                                    if isinstance(s, ActionSpec)])
    data, idx = append_events(data, specs)
    flow = EventFlow(data)
    links = {flow.link_slots[('entry', HOOK_ENTRY)]: idx[0]}
    for a, b in zip(idx, idx[1:]):
        links[flow.link_slots[('next', a)]] = b
    data = patch_pointers(data, links)
    calls = [i for i, s in zip(idx, specs) if isinstance(s, SubflowSpec)]
    return set_entry_subflows(data, HOOK_ENTRY, calls)
