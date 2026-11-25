"""Test batch 34: Rainbow Bridge medallions and Ganon's Trials
(docs/superpowers/specs/2026-11-22-bridge-and-trials-design.md), on the full skip.

Every variant puts adult Link at Ganon's Castle's entrance, facing the gap of the bridge.
Attempt 1 rewrote the bridge's BoolExps in GameDataList: no bridge, even with 0 medallions
(34c), while moving `Defeat_Ganon` to Step01 opened it (34f). Attempt 2 checks the pouch
after each reward grant (`ganon.with_bridge_check`). Here the preset's own gifts stand in
for the reward scene: the check runs right after them, as it does after a reward grant.
34a: bridge needs 3 medallions (the deepest check), Link gets 3: the bridge appears.
34b: bridge needs 3 medallions, Link gets 2: no bridge.
34c: bridge needs 0 medallions (the quest moves on leaving home) and there are 0 trials:
     the bridge appears; inside, the central barrier is already gone.
34d: bridge needs 0 medallions and only the Forest trial is left: inside, the Forest
     room's barrier is up and the other five are cleared.
34f: the game's own condition met by the preset (Defeat_Ganon at Step01): the bridge
     appears (passed on 2026-11-25; kept as the control).
Batch 36, the other bridge modes (34a-34d passed on 2026-11-25):
36a: tokens, 10 needed, the counter at 10: the check before each map change (the
     preset's teleport runs it) moves the quest: the bridge appears.
36b: tokens, 10 needed, the counter at 9: no bridge.
36c: hearts, 5 needed, max life 20 quarters (5 hearts): the bridge appears.
36d: Spiritual Stones, 2 needed, Link gets 2: the bridge appears (the reward check, as
     in 34a, with the stones).
36e: tokens, 3 needed, the preset gives 3 real tokens.
36f: hearts, 5 needed, the preset gives 2 Heart Containers (3 + 2 = 5).
Usage: python -I tools/make_bridge_batch.py <nup> <out_mod_dir> <34a|34b|34c|34d|34f|36a..36f>
"""
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import FLOW_DIR, FLOW_EXT, Batch, add_start, write_mod  # noqa: E402
from randomizer import ganon  # noqa: E402
from randomizer.formats.bfevfl import SUBFLOW, EventFlow  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.test_start import HOOK_FLOW, StartPreset  # noqa: E402

MEDALS = ('Item_Medal_Forest', 'Item_Medal_Fire', 'Item_Medal_Water')


@dataclass(frozen=True)
class Variant:
    medallions: int | None  # required for the bridge; None: the vanilla bridge
    owned: tuple[str, ...] = ()  # rewards given at the start
    active: tuple[str, ...] = ganon.TRIALS  # trials left to clear
    steps: tuple[tuple[str, str], ...] = ()  # quest steps set by the start preset
    mode: str = 'medallions'  # the bridge mode; `medallions` is its count
    ints: tuple[tuple[str, int], ...] = ()  # (GameDataName, value) set by the start preset


VARIANTS = {
    '34a': Variant(3, MEDALS),
    '34b': Variant(3, MEDALS[:2]),
    '34c': Variant(0, (), ()),
    '34d': Variant(0, (), ('Forest',)),
    '34f': Variant(None, steps=ganon.BRIDGE_STEPS),
    '36a': Variant(10, mode='tokens', ints=((ganon.TOKEN_COUNT, 10),)),
    '36b': Variant(10, mode='tokens', ints=((ganon.TOKEN_COUNT, 9),)),
    '36c': Variant(5, mode='hearts', ints=((ganon.MAX_LIFE, 20),)),
    '36d': Variant(2, ganon.STONE_ACTORS[:2], mode='stones'),
    # 36a-36c set the counters directly: the bridge followed the token count, but no
    # token showed in the inventory and the max life write did not stick (2026-11-25).
    # These give the real items instead, as in play.
    '36e': Variant(3, ('Obj_Token_Gold',) * 3, mode='tokens'),
    '36f': Variant(5, ('Obj_Heart_Container',) * 2, mode='hearts'),
}


def _check_after_gifts(data: bytes, n: int, actors: tuple[str, ...]) -> bytes:
    """The hook flow with the bridge check after its last reward gift (or before
    everything with a count of 0, as on leaving home)."""
    if n == 0:
        return ganon.with_start_steps(data)
    flow = EventFlow(data)
    gifts = [e.index for e in flow.events
             if e.kind == SUBFLOW and e.sub_entry == 'GetInEvent'
             and flow.action_params(e.index).get('ActorName', '') in actors]
    return ganon.with_bridge_check(data, max(gifts), n, actors)


def build(nup: NupArchive, variant: Variant) -> dict[str, bytes]:
    game = GameData(nup)
    batch = Batch(nup)
    batch.files.update(batch.unpack(files_with_fallback(game, FULL_SKIP_PHASE)[0]))
    if variant.medallions is not None:
        lacs = game.flow_path(ganon.LACS_FLOW)
        batch.files[lacs] = ganon.lacs_patch(batch.read(lacs))
    if variant.active != ganon.TRIALS:
        trials = game.flow_path(ganon.TRIALS_FLOW)
        batch.files[trials] = ganon.rainbow_patch(batch.read(trials), variant.active)
    add_start(batch, StartPreset('GanonCastle', 'GanonCastleEntrance', items=variant.owned,
                                 challenge_steps=variant.steps, adult=True,
                                 ints=variant.ints))
    if variant.mode in ganon.BRIDGE_ITEMS and variant.medallions is not None:
        hook = FLOW_DIR + HOOK_FLOW + FLOW_EXT
        batch.files[hook] = _check_after_gifts(batch.read(hook), variant.medallions,
                                               ganon.BRIDGE_ITEMS[variant.mode])
    elif variant.mode in ('tokens', 'hearts'):
        go = game.flow_path(ganon.MAP_CHANGE_FLOW)
        name, value = ((ganon.TOKEN_COUNT, variant.medallions) if variant.mode == 'tokens'
                       else (ganon.MAX_LIFE, variant.medallions * ganon.QUARTERS_PER_HEART))
        batch.files[go] = ganon.with_count_check(batch.read(go), name, value)
    return batch.compressed()


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[3] not in VARIANTS:
        raise SystemExit(__doc__)
    nup_path, out, name = sys.argv[1:4]
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, VARIANTS[name]))


if __name__ == '__main__':
    main()
