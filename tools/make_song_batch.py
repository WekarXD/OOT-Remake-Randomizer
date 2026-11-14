"""Song test batches (Shuffle Songs), one variant per teleport destination.

22 (default): the two song scenes that check their own song (Song Locations).

On top of the full skip, the crater's Sheik gives Song of Storms and the windmill man
gives the Bolero of Fire. Leaving Link's house for the first time makes Link an adult
and teleports him to the crater's warp pad, with the fire quest at the step where
Sheik appears. Getting Storm there first is what used to stop the windmill scene.
24a: without the full skip (to check the lesson bypass), Impa gives a Deku Shield.
24b: on the full skip, the crater's Sheik gives the Hookshot (checks the crater bypass).
24c: as 24b, but without the lesson's example and repeat (experiment: only its fixed end).
Usage: python -I tools/make_song_batch.py <nup> <out_mod_dir> [22|24a|24b|24c]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import FLOW_DIR, FLOW_EXT, Batch, add_start, write_mod  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.formats.bfevfl import SUBFLOW, EventFlow  # noqa: E402
from randomizer.songs import LESSON_FLOW, SONGS, bypass, song_flow_patches  # noqa: E402
from randomizer.test_start import NewStartPos, StartPreset  # noqa: E402

# SageOfFire's steps in order (RSDB/Challenge); the crater's logic starts Sheik's scene
# at MeetSheik (Logic/DeathMountainCrater_Adult_Prefab_a0e2 and e63c).
FIRE_STEPS = ('Ready', 'StopDaruniaJr', 'TalkDaruniaJr', 'MoveStatue', 'EnterCrater',
              'MeetSheik')
PRESET = StartPreset(
    'DeathMountainCrater_Adult', 'FireBolero',
    # The Hookshot is the way out of the warp pad's ledge (batch 22, attempt 1).
    items=('Item_Ocarina_Time', 'Obj_Armor_Goron', 'Item_Hookshot'),
    challenge_steps=tuple(('SageOfFire', s) for s in FIRE_STEPS)
    + (('SubEvent_GetStormSong', 'Ready'),),
    adult=True)
VANILLA = {s.location: s.actor for s in SONGS}
PLACEMENT = VANILLA | {
    'Sheik in Crater': 'Item_Melody_StormSong',
    'Song from Windmill': 'Item_Melody_FireBolero',
}
# The castle courtyard on Impa's anchor, with the castle quest at Step04 so Zelda's
# meeting can start (batches 20 and 23a).
COURTYARD = NewStartPos('RandoTest_MeetImpa',
                        (5.134531497955322, 126.82830810546875, -236.39134216308594),
                        (0.0, 3.141592653589793, 0.0))
CASTLE = StartPreset('HyruleCastle', COURTYARD.name, items=('Item_Ocarina_Fairy',),
                     new_pos=COURTYARD,
                     challenge_steps=tuple(('Goto_HyruleCastle', f'Step0{i}') for i in (1, 2, 3, 4)))
# The crater preset without the Hookshot: in 24b Sheik gives it, and it is the way out.
CRATER_NO_HOOKSHOT = StartPreset(
    PRESET.banc, PRESET.start_pos, items=('Item_Ocarina_Time', 'Obj_Armor_Goron'),
    challenge_steps=PRESET.challenge_steps, adult=True)
# name -> (preset, song placement, built on the full skip)
VARIANTS = {
    '22': (PRESET, PLACEMENT, True),
    '24a': (CASTLE, VANILLA | {'Song from Impa': 'TBox_Shield_Deku'}, False),
    '24b': (CRATER_NO_HOOKSHOT, VANILLA | {'Sheik in Crater': 'Item_Hookshot'}, True),
    '24c': (CRATER_NO_HOOKSHOT, VANILLA | {'Sheik in Crater': 'Item_Hookshot'}, True),
}
# Variants whose patched song scenes also skip the lesson's example and repeat.
NO_REPEAT = {'24c'}
EXAMPLE_AND_REPEAT = ('LearningOcarinaPlayExample', 'LearningOcarinaFollowExample')


def _without_repeat(data: bytes) -> bytes:
    flow = EventFlow(data)
    return bypass(data, [i for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW
                         and ev.sub_flow == LESSON_FLOW and ev.sub_entry in EXAMPLE_AND_REPEAT])


def build(nup: NupArchive, variant: str = '22') -> dict[str, bytes]:
    preset, placement, full_skip = VARIANTS[variant]
    game = GameData(nup)
    batch = Batch(nup)
    if full_skip:
        skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
        batch.files.update(batch.unpack(skip))

    def read(name: str) -> bytes:
        return batch.read(FLOW_DIR + name + FLOW_EXT)

    for name, data in song_flow_patches(read, placement).items():
        if variant in NO_REPEAT and name.startswith('Dm_MelodyGet_'):
            data = _without_repeat(data)
        batch.files[FLOW_DIR + name + FLOW_EXT] = data
    add_start(batch, preset)
    return batch.compressed()


def main() -> None:
    nup_path, out = sys.argv[1:3]
    variant = sys.argv[3] if len(sys.argv) > 3 else '22'
    if variant not in VARIANTS:
        raise SystemExit(f'Unknown variant {variant!r}: use one of {", ".join(VARIANTS)}.')
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, variant))


if __name__ == '__main__':
    main()
