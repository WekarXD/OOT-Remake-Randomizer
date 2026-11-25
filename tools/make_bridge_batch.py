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
Usage: python -I tools/make_bridge_batch.py <nup> <out_mod_dir> <34a|34b|34c|34d|34f>
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
    owned: tuple[str, ...] = ()  # medallions given at the start
    active: tuple[str, ...] = ganon.TRIALS  # trials left to clear
    steps: tuple[tuple[str, str], ...] = ()  # quest steps set by the start preset


VARIANTS = {
    '34a': Variant(3, MEDALS),
    '34b': Variant(3, MEDALS[:2]),
    '34c': Variant(0, (), ()),
    '34d': Variant(0, (), ('Forest',)),
    '34f': Variant(None, steps=ganon.BRIDGE_STEPS),
}


def _check_after_gifts(data: bytes, n: int) -> bytes:
    """The hook flow with the bridge check after its last gift (or before everything
    with 0 medallions, as on leaving home)."""
    if n == 0:
        return ganon.with_start_steps(data)
    flow = EventFlow(data)
    gifts = [e.index for e in flow.events
             if e.kind == SUBFLOW and e.sub_entry == 'GetInEvent'
             and flow.action_params(e.index).get('ActorName', '').startswith('Item_Medal_')]
    return ganon.with_bridge_check(data, max(gifts), n)


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
                                 challenge_steps=variant.steps, adult=True))
    if variant.medallions is not None:
        hook = FLOW_DIR + HOOK_FLOW + FLOW_EXT
        batch.files[hook] = _check_after_gifts(batch.read(hook), variant.medallions)
    return batch.compressed()


def main() -> None:
    if len(sys.argv) != 4 or sys.argv[3] not in VARIANTS:
        raise SystemExit(__doc__)
    nup_path, out, name = sys.argv[1:4]
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, VARIANTS[name]))


if __name__ == '__main__':
    main()
