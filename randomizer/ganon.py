"""Rainbow Bridge medallions and Ganon's Trials (OoTR's `bridge`, `bridge_medallions`,
`trials`, `trials_random`). See docs/superpowers/specs/2026-11-22-bridge-and-trials-design.md.

- Bridge: the bridge scene's AINB creates its trigger once `Defeat_Ganon` is past `Ready`
  and `Step01` (Zelda's Light Arrows scene sets `Step01` in the vanilla game). Rewriting
  those BoolExps in GameDataList does nothing in game (test batch 34c); moving the quest
  does (34f). So, with `bridge == 'medallions'`, every dungeon-reward scene checks the
  pouch for the medallions right after its grant and moves the quest when there are
  enough; with 0 medallions the first scene after leaving home moves it.
- Trials: the skipped trials' flags are set at the start of the bridge scene, which plays
  once before Link can enter the castle.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

from randomizer.fill import MAX_TRIALS, Settings, _rng
from randomizer.formats.bfevfl import SUBFLOW, EventFlow, patch_pointers, set_string_param
from randomizer.formats.evfl_append import (ActionSpec, SwitchSpec, add_actions, add_queries,
                                            append_events)
from randomizer.gifts import GIFTS

TRIALS = ('Forest', 'Fire', 'Water', 'Shadow', 'Spirit', 'Light')  # OoTR's order
MEDALLION_ACTORS = tuple(f'Item_Medal_{t}' for t in TRIALS)

# The quest steps the bridge's AINB waits for.
BRIDGE_STEPS = (('Defeat_Ganon', 'Ready'), ('Defeat_Ganon', 'Step01'))
# The dungeon-reward scenes (the sites of Shuffle Dungeon Rewards) and what they grant.
_REWARDS = tuple(g for g in GIFTS if g.setting == 'shuffle_dungeon_rewards')
REWARD_FLOWS = tuple(g.flow for g in _REWARDS)
REWARD_ACTORS = frozenset(g.content for g in _REWARDS)
GRANT_ENTRY = 'GetPouchContentByActorName'
# The scene where Link first leaves his house (test_start.HOOK_FLOW): 0 medallions.
START_FLOW, START_ENTRY = 'Dm_Kokiri_0045', 'EntryPoint0'
_POUCH_QUERY = ('PouchSystemActor', 'EventQueryIsExistInPouch')
_STEP_ACTION = ('ChallengeSystemActor', 'EventExecuteProgressChallengeStep')

TRIALS_FLOW = 'Defeat_Ganon'
RAINBOW_ENTRY = 'GanonCastle_Adult_Field_Rainbow'
BARRIER_REMOVE = 'InsideGanonCastle_Dungeon_BarrierRemove_'
BARRIER_COUNT = 'InsideGanonCastle_Dungeon_Barrier_Count'
ALL_CLEAR = 'InsideGanonCastle_IsAllBarrierClear'
BARRIER_MOVIE = 'HavePlayedEvent.Dm_InsideGanonCastle_0090'
LACS_FLOW = 'AllSage'

# The trials' RNG stream (fill attempts use 0.., the reward shuffle -1).
_TRIALS_STREAM = -2


def active_trials(settings: Settings) -> tuple[str, ...]:
    """The trials the player must clear, in `TRIALS` order: a seeded sample of
    `settings.trials` (or of a random count with `trials_random`)."""
    if not settings.trials_random and settings.trials == MAX_TRIALS:
        return TRIALS
    rng = _rng(settings, _TRIALS_STREAM)
    count = rng.randint(0, MAX_TRIALS) if settings.trials_random else settings.trials
    chosen = set(rng.sample(TRIALS, count))
    return tuple(t for t in TRIALS if t in chosen)


def world_settings(settings: Settings) -> dict:
    """The OoTR World settings these options set."""
    active = active_trials(settings)
    return {'bridge': settings.bridge, 'bridge_medallions': settings.bridge_medallions,
            'trials': len(active),
            'skipped_trials': {t: t not in active for t in TRIALS}}


def _set_bool(name: str) -> ActionSpec:
    return ActionSpec('GameDataActor', 'EventTriggerSetGameDataBool',
                      {'GameDataName': name, 'Index': -1, 'Value': True})


def rainbow_patch(data: bytes, active: Sequence[str]) -> bytes:
    """`TRIALS_FLOW` with the bridge scene first marking the skipped trials as cleared."""
    specs = [_set_bool(BARRIER_REMOVE + t) for t in TRIALS if t not in active]
    specs.append(ActionSpec('GameDataActor', 'EventTriggerSetGameDataInt',
                            {'GameDataName': BARRIER_COUNT, 'Index': -1,
                             'Value': len(active)}))
    if not active:  # the central barrier, as `BarrierRemove_All` leaves it
        specs += [_set_bool(ALL_CLEAR), _set_bool(BARRIER_MOVIE)]
    start = EventFlow(data).entry_points[RAINBOW_ENTRY]
    out = add_actions(data, [(s.actor, s.action) for s in specs])
    out, idx = append_events(out, specs)
    flow = EventFlow(out)
    links = {flow.link_slots[('entry', RAINBOW_ENTRY)]: idx[0],
             flow.link_slots[('next', idx[-1])]: start}
    links.update((flow.link_slots[('next', a)], b) for a, b in zip(idx, idx[1:]))
    return patch_pointers(out, links)


def lacs_patch(data: bytes) -> bytes:
    """`LACS_FLOW` with Zelda's `Defeat_Ganon Step01` turned into a second `AllSage
    Complete`: the bridge no longer needs it, and after the bridge it could move the
    quest back."""
    flow = EventFlow(data)
    hits = [e.index for e in flow.events
            if e.action == 'EventExecuteProgressChallengeStep'
            and flow.action_params(e.index).get('ChallengeName') == 'Defeat_Ganon'
            and flow.action_params(e.index).get('StepName') == 'Step01']
    if not hits:
        raise ValueError(f'{LACS_FLOW} has no Defeat_Ganon Step01 call')
    for i in hits:
        data = set_string_param(data, i, 'ChallengeName', 'AllSage')
        data = set_string_param(data, i, 'StepName', 'Complete')
    return data


def _step_specs() -> list[ActionSpec]:
    return [ActionSpec(*_STEP_ACTION, {
        'ChallengeName': challenge, 'IsIgnoreCompletedChallenge': False,
        'IsIgnoreChallengeProgressUI': True, 'IsWaitEnd': True, 'StepName': step})
        for challenge, step in BRIDGE_STEPS]


def reward_grants(flow: EventFlow) -> list[int]:
    """The events of a reward scene that grant its reward."""
    return [e.index for e in flow.events
            if e.kind == SUBFLOW and e.sub_entry == GRANT_ENTRY
            and flow.action_params(e.index).get('ActorName') in REWARD_ACTORS]


def with_bridge_check(data: bytes, after: int, n: int) -> bytes:
    """The flow with, right after event `after`, a check of the pouch for `n` of the six
    medallions that moves `Defeat_Ganon` to `BRIDGE_STEPS`, then the original next event.
    The check is a decision diagram: node (i, k) asks for medallion i while k are still
    needed among medallions i..5."""
    total = len(MEDALLION_ACTORS)
    if not 0 <= n <= total:
        raise ValueError(f'cannot require {n} of {total} medallions')
    nodes: list[tuple[int, int]] = []
    todo = [(0, n)]
    while todo:
        i, k = todo.pop()
        if (i, k) in nodes or k == 0 or k > total - i:
            continue
        nodes.append((i, k))
        todo += [(i + 1, k - 1), (i + 1, k)]
    specs = [SwitchSpec(*_POUCH_QUERY, {'Actor': MEDALLION_ACTORS[i], 'Num': 1})
             for i, _ in nodes] + _step_specs()
    cont = EventFlow(data).events[after].next
    out = add_queries(add_actions(data, [_STEP_ACTION]), [_POUCH_QUERY])
    out, idx = append_events(out, specs)
    at = dict(zip(nodes, idx))
    chain = idx[len(nodes):]

    def target(i: int, k: int) -> int:
        return chain[0] if k == 0 else cont if k > total - i else at[(i, k)]

    flow = EventFlow(out)
    links = {flow.link_slots[('next', after)]: target(0, n)}
    for (i, k), e in at.items():
        links[flow.link_slots[('case', e, 0)]] = target(i + 1, k - 1)  # has it
        links[flow.link_slots[('case', e, 1)]] = target(i + 1, k)
    links.update((flow.link_slots[('next', a)], b) for a, b in zip(chain, chain[1:]))
    links[flow.link_slots[('next', chain[-1])]] = cont
    return patch_pointers(out, links)


def with_start_steps(data: bytes) -> bytes:
    """`START_FLOW` moving `Defeat_Ganon` to `BRIDGE_STEPS` before its own events."""
    start = EventFlow(data).entry_points[START_ENTRY]
    out = add_actions(data, [_STEP_ACTION])
    out, idx = append_events(out, _step_specs())
    flow = EventFlow(out)
    links = {flow.link_slots[('entry', START_ENTRY)]: idx[0],
             flow.link_slots[('next', idx[-1])]: start}
    links.update((flow.link_slots[('next', a)], b) for a, b in zip(idx, idx[1:]))
    return patch_pointers(out, links)


def flow_patches(read: Callable[[str], bytes], settings: Settings) -> dict[str, bytes]:
    """{flow: bytes} for `generate._with_flow_patches`."""
    out: dict[str, bytes] = {}
    active = active_trials(settings)
    if active != TRIALS:
        out[TRIALS_FLOW] = rainbow_patch(read(TRIALS_FLOW), active)
    if settings.bridge != 'medallions':
        return out
    out[LACS_FLOW] = lacs_patch(read(LACS_FLOW))
    for name in REWARD_FLOWS:
        data = read(name)
        grants = reward_grants(EventFlow(data))
        if not grants:
            raise ValueError(f'{name} has no reward grant')
        for g in grants:  # the indices stay: new events are appended
            data = with_bridge_check(data, g, settings.bridge_medallions)
        out[name] = data
    if settings.bridge_medallions == 0:
        out[START_FLOW] = with_start_steps(read(START_FLOW))
    return out
