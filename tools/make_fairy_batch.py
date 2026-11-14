"""Great Fairy test batch 26 (spike), one variant per fountain, on the full skip.

Each variant teleports Link onto the fountain's Triforce point with an ocarina and
Zelda's Lullaby, and patches the fountains the way the shuffle would:
- the fountain's grant (Dm_SY_GetInEvent call) gives another item; the special grant
  entries (Din, Wisdom, Courage: their own gauge/defense animation) are pointed at the
  generic one;
- the fairies are free, as in OoTR: every rupee check passes and nothing is charged
  (so the first visit always grants, and a refused payment cannot lose the item);
- the revisit check reads HavePlayedEvent.<fountain event> instead of IsGet.<own
  reward> (as the windmill), so a revisit only heals;
- TriForcePoint no longer needs Din's Fire to summon the other fairies;
- the Power fairy's spin attack guide is skipped when she gives something else.

26a: Death Mountain Trail (Din) gives Farore's Wind; Link already has the double magic and
     no rupees.
26b: Hyrule Castle (Power) gives the Boomerang; no magic, no Din's Fire.
26c: Death Mountain Crater (Wisdom), adult, gives Nayru's Love; no magic.
Usage: python -I tools/make_fairy_batch.py <nup> <out_mod_dir> [26a|26b|26c]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import FLOW_DIR, FLOW_EXT, Batch, add_start, write_mod  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.formats.bfevfl import (SUBFLOW, SWITCH, EventFlow, patch_pointers,  # noqa: E402
                                       set_string_param, set_subflow_entry)
from randomizer.songs import _rename_flag, bypass  # noqa: E402
from randomizer.test_start import NewStartPos, StartPreset  # noqa: E402

GRANT_FLOW = 'Dm_SY_GetInEvent'
GENERIC_GRANT = 'GetInEvent_Demo_NotLookatObjectEntry'
TRIFORCE_FLOW = 'TriForcePoint'
DIN_GATE = 'IsGet.Item_DinFire'
BOOL_QUERY = 'EventQueryIsGameDataBool'
# fountain -> (vanilla reward, map, Triforce point, fountain basin centre)
FOUNTAINS = {
    # The remake swaps these two against the N64: Din's fountain is at the top of Death
    # Mountain and Power's by Hyrule Castle (each flow's camera warps there; batch 26
    # attempts 1-3 sent 26a to the castle, which is Power's, still charging).
    'Din': ('Item_DinFire', 'DeathMountainTrail_Child',
            (-34.0, 211.2, -189.2), (-34.7, 210.1, -191.1)),
    'Power': ('Item_FairyBless_MP', 'HyruleCastle',
              (118.5, 108.8, -76.8), (120.5, 107.7, -77.4)),
    'Wisdom': ('Item_FairyBless_MPDouble', 'DeathMountainCrater_Adult',
               (-76.6, 122.2, 46.6), (-78.4, 121.1, 47.6)),
}
SONGS = ('Item_Ocarina_Fairy', 'Item_Melody_ZeldaLullaby')
# variant -> (fountain, item it gives, extra start items, adult)
VARIANTS = {
    '26a': ('Din', 'Item_FaroreWind', ('Item_FairyBless_MPDouble',), False),
    '26b': ('Power', 'Item_Boomerang', (), False),
    '26c': ('Wisdom', 'Item_NayruLove', ('Obj_Armor_Goron',), True),
}


def _switch_case_targets(flow: EventFlow, index: int) -> dict[int, int]:
    """{case value: target event} of switch `index`."""
    ev = flow.events[index]
    cases_p = flow._u64(flow._events_p + 0x30 * index + 0x18)
    return {flow._u32(cases_p + 8 * k): ev.cases[k] for k in range(len(ev.cases))}


def _retarget(data: bytes, old: int, new: int) -> bytes:
    """Every pointer to event `old` goes to `new`."""
    flow = EventFlow(data)
    return patch_pointers(data, {off: new for off in flow.link_slots.values()
                                 if flow._u16(off) == old})


def _one(hits: list[int], what: str) -> int:
    if len(hits) != 1:
        raise SystemExit(f'FAIL: {len(hits)} {what}, expected one')
    return hits[0]


def _some(hits: list[int], what: str) -> list[int]:
    """`hits`, which must not be empty (the full skip copies some events: Din's grant
    is both at 308 and in the shortened path at 615)."""
    if not hits:
        raise SystemExit(f'FAIL: no {what}')
    return hits


def patch_fountain(data: bytes, name: str, item: str) -> bytes:
    reward = FOUNTAINS[name][0]
    flow = EventFlow(data)
    for grant in _some([i for i, ev in enumerate(flow.events)
                        if ev.kind == SUBFLOW and ev.sub_flow == GRANT_FLOW
                        and flow.action_params(i).get('ActorName') == reward],
                       f'{name} grants'):
        data = set_string_param(data, grant, 'ActorName', item)
        if item != reward and flow.events[grant].sub_entry != GENERIC_GRANT:
            data = set_subflow_entry(data, grant, GENERIC_GRANT)
    if item != reward:  # the Power fairy's spin attack guide
        guides = [i for i, ev in enumerate(flow.events)
                  if ev.kind == SUBFLOW and ev.sub_flow == 'ActionGuide']
        data = bypass(data, guides)
    data, n = _rename_flag(data, BOOL_QUERY, 'IsGet.' + reward,
                           'HavePlayedEvent.Dm_FairyFountain_' + name)
    _some(list(range(n)), f'own-reward checks in {name}')
    return make_free(data)


def make_free(data: bytes) -> bytes:
    """The flow without charging: every pay question (`TalkChoice2`) goes to its "yes"
    case, every rupee check (`HasRuppe`, including the copies the full skip inlines,
    which skip the question) to its "enough" case, and every payment (`IncreaseRupee`,
    also inlined from `Pay`) is skipped. Batch 26 attempt 1 patched only the question
    (the skip's direct path still checked the rupees); attempt 2 only the checks ("No"
    still led to DontPay1, whose line also says Link has too few rupees)."""
    flow = EventFlow(data)
    for check in [i for i, ev in enumerate(flow.events)
                  if ev.query in ('EventQueryTalkChoice2', 'EventQueryHasRuppe')]:
        data = _retarget(data, check, _switch_case_targets(EventFlow(data), check)[0])
    flow = EventFlow(data)
    return bypass(data, [i for i, ev in enumerate(flow.events)
                         if ev.action == 'EventTriggerIncreaseRupee'])


def patch_triforce(data: bytes) -> bytes:
    """TriForcePoint summons every fairy without Din's Fire."""
    flow = EventFlow(data)
    gate = _one([i for i, ev in enumerate(flow.events)
                 if ev.kind == SWITCH and ev.query == BOOL_QUERY and len(ev.cases) == 2
                 and flow.action_params(i).get('GameDataName') == DIN_GATE], 'Din gates')
    return _retarget(data, gate, _switch_case_targets(flow, gate)[0])


def _preset(fountain: str, extra: tuple[str, ...], adult: bool) -> StartPreset:
    _, banc, point, basin = FOUNTAINS[fountain]
    yaw = math.atan2(basin[0] - point[0], basin[2] - point[2])  # facing the basin
    pos = NewStartPos(f'RandoTest_Fairy{fountain}', (point[0], point[1] + 0.2, point[2]),
                      (0.0, yaw, 0.0))
    return StartPreset(banc, pos.name, items=SONGS + extra, new_pos=pos, adult=adult)


def build(nup: NupArchive, variant: str) -> dict[str, bytes]:
    fountain, item, extra, adult = VARIANTS[variant]
    game = GameData(nup)
    batch = Batch(nup)
    skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
    batch.files.update(batch.unpack(skip))
    path = FLOW_DIR + 'Dm_FairyFountain_' + fountain + FLOW_EXT
    batch.files[path] = patch_fountain(batch.read(path), fountain, item)
    if fountain != 'Din':  # the other fountains call Din's shared Pay entries
        path = FLOW_DIR + 'Dm_FairyFountain_Din' + FLOW_EXT
        batch.files[path] = make_free(batch.read(path))
    path = FLOW_DIR + TRIFORCE_FLOW + FLOW_EXT
    batch.files[path] = patch_triforce(batch.read(path))
    add_start(batch, _preset(fountain, extra, adult))
    return batch.compressed()


def main() -> None:
    nup_path, out = sys.argv[1:3]
    variant = sys.argv[3] if len(sys.argv) > 3 else '26a'
    if variant not in VARIANTS:
        raise SystemExit(f'Unknown variant {variant!r}: use one of {", ".join(VARIANTS)}.')
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, variant))


if __name__ == '__main__':
    main()
