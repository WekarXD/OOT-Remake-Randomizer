"""Great Fairy fountains as item locations (design
docs/superpowers/specs/2026-11-15-great-fairies-design.md; proven by test batch 26).

Each fountain hands over its reward with one `Dm_SY_GetInEvent` call (the full skip
can copy it). With the rewards shuffled, every fountain is patched:
- the grant gives the placed item; the special entries (Din, Wisdom, Courage add their
  own gauge or defense animation) are pointed at the generic one when it changed;
- the Power fairy's spin attack guide is skipped when she gives something else;
- the revisit check reads `HavePlayedEvent.<fountain event>` instead of
  `IsGet.<own reward>`, so a revisit only heals even if that reward was found elsewhere;
- the fairies are free (as in OoTR): every pay question and rupee check goes to its
  "yes" case and every payment is skipped, so the first visit always grants;
- `TriForcePoint` summons every fairy without Din's Fire.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .formats.bfevfl import (SUBFLOW, SWITCH, EventFlow, patch_pointers, set_string_param,
                             set_subflow_entry)
from .songs import _rename_flag, bypass

GRANT_FLOW = 'Dm_SY_GetInEvent'
GENERIC_GRANT = 'GetInEvent_Demo_NotLookatObjectEntry'
GUIDE_FLOW = 'ActionGuide'
TRIFORCE_FLOW = 'TriForcePoint'
DIN_GATE = 'IsGet.Item_DinFire'
BOOL_QUERY = 'EventQueryIsGameDataBool'
PAY_QUERIES = ('EventQueryTalkChoice2', 'EventQueryHasRuppe')
PAYMENT = 'EventTriggerIncreaseRupee'
# What a fountain never gives, until a test batch proves it (docs/TODO.md):
# - a token: untested from a GetInEvent grant (as from a song scene);
# - Item_BulletBag_Small, TBox_DekuSeedBundle: they hang GetInEvent (batch 25), and
#   Item_ScrubBusinessSeed is Deku seeds too (final review);
# - the Bow, the Slingshot and the Bomb Bag: GetInEvent handed over the Slingshot
#   without its ammo (batch 25), and the logic would count a useless weapon (review).
FOUNTAIN_FORBIDDEN = frozenset({
    'Obj_Token_Gold', 'Item_BulletBag_Small', 'TBox_DekuSeedBundle', 'Item_ScrubBusinessSeed',
    'Item_Range_Bow', 'Item_Range_SlingShot', 'Item_BombBag_Small'})


class FairyPatchError(ValueError):
    pass


@dataclass(frozen=True)
class Fountain:
    name: str  # flow suffix
    location: str  # OoTR location
    reward: str  # what it gives in the game

    @property
    def flow(self) -> str:
        return 'Dm_FairyFountain_' + self.name


# The remake swaps the castle's and the mountain's rewards against the N64 (each flow's
# camera warps to its own fountain; batch 26).
FOUNTAINS: tuple[Fountain, ...] = (
    Fountain('Power', 'HC Great Fairy Reward', 'Item_FairyBless_MP'),
    Fountain('Din', 'DMT Great Fairy Reward', 'Item_DinFire'),
    Fountain('Wisdom', 'DMC Great Fairy Reward', 'Item_FairyBless_MPDouble'),
    Fountain('Frore', 'ZF Great Fairy Reward', 'Item_FaroreWind'),
    Fountain('Nayru', 'Colossus Great Fairy Reward', 'Item_NayruLove'),
    Fountain('Courage', 'OGC Great Fairy Reward', 'Item_FairyBless_DefenseDouble'),
)
FOUNTAIN_BY_LOCATION: dict[str, Fountain] = {f.location: f for f in FOUNTAINS}
FAIRY_REWARDS: frozenset[str] = frozenset(f.reward for f in FOUNTAINS)


def _switch_case_targets(flow: EventFlow, index: int) -> dict[int, int]:
    """{case value: target event} of switch `index` (a bool query: 0 is true)."""
    ev = flow.events[index]
    cases_p = flow._u64(flow._events_p + 0x30 * index + 0x18)
    return {flow._u32(cases_p + 8 * k): ev.cases[k] for k in range(len(ev.cases))}


def _retarget(data: bytes, old: int, new: int) -> bytes:
    """Every pointer to event `old` goes to `new`."""
    flow = EventFlow(data)
    return patch_pointers(data, {off: new for off in flow.link_slots.values()
                                 if flow._u16(off) == old})


def _to_yes(data: bytes, index: int) -> bytes:
    targets = _switch_case_targets(EventFlow(data), index)
    if 0 not in targets:
        raise FairyPatchError(f'Switch {index} has no "yes" case.')
    return _retarget(data, index, targets[0])


def make_free(data: bytes) -> bytes:
    """The flow without charging: every pay question (`TalkChoice2`) and rupee check
    (`HasRuppe`, including the copies the full skip inlines, which skip the question)
    goes to its "yes" case, and every payment (`IncreaseRupee`) is skipped. Batch 26:
    patching only the question left the skip's direct path, and patching only the
    checks let "No" reach `DontPay1`."""
    flow = EventFlow(data)
    for i in [i for i, ev in enumerate(flow.events) if ev.query in PAY_QUERIES]:
        data = _to_yes(data, i)
    flow = EventFlow(data)
    return bypass(data, [i for i, ev in enumerate(flow.events) if ev.action == PAYMENT])


def patch_fountain(data: bytes, fountain: Fountain, item: str) -> bytes:
    """The fountain's flow giving `item`, free, healing only on a revisit."""
    flow = EventFlow(data)
    grants = [i for i, ev in enumerate(flow.events)
              if ev.kind == SUBFLOW and ev.sub_flow == GRANT_FLOW
              and flow.action_params(i).get('ActorName') == fountain.reward]
    if not grants:
        raise FairyPatchError(f'{fountain.flow}: no grant of {fountain.reward}.')
    changed = item != fountain.reward
    for i in grants:
        data = set_string_param(data, i, 'ActorName', item)
        if changed and flow.events[i].sub_entry != GENERIC_GRANT:
            data = set_subflow_entry(data, i, GENERIC_GRANT)
    if changed:
        flow = EventFlow(data)
        data = bypass(data, [i for i, ev in enumerate(flow.events)
                             if ev.kind == SUBFLOW and ev.sub_flow == GUIDE_FLOW])
    data, n = _rename_flag(data, BOOL_QUERY, 'IsGet.' + fountain.reward,
                           'HavePlayedEvent.' + fountain.flow)
    if n != 1:
        raise FairyPatchError(f'{fountain.flow}: {n} own-reward checks, expected one.')
    return make_free(data)


def patch_triforce(data: bytes) -> bytes:
    """`TriForcePoint` summoning every fairy without Din's Fire."""
    flow = EventFlow(data)
    gates = [i for i, ev in enumerate(flow.events)
             if ev.kind == SWITCH and ev.query == BOOL_QUERY and len(ev.cases) == 2
             and flow.action_params(i).get('GameDataName') == DIN_GATE]
    if len(gates) != 1:
        raise FairyPatchError(f'{TRIFORCE_FLOW}: {len(gates)} Din gates, expected one.')
    return _to_yes(data, gates[0])


def fairy_flow_patches(read: Callable[[str], bytes],
                       fairies: dict[str, str]) -> dict[str, bytes]:
    """{flow name: patched bytes} for `fairies` (OoTR fountain location -> what it
    gives, all six), or {} when the rewards are not shuffled. `read(name)` gives the
    current version of a flow (the full skip's, if it wrote one)."""
    if not fairies:
        return {}
    if set(fairies) != set(FOUNTAIN_BY_LOCATION):
        raise FairyPatchError(f'Expected the six fountains, got {sorted(fairies)}.')
    out = {f.flow: patch_fountain(read(f.flow), f, fairies[f.location]) for f in FOUNTAINS}
    out[TRIFORCE_FLOW] = patch_triforce(read(TRIFORCE_FLOW))
    return out
