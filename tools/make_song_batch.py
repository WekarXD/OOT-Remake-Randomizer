"""Test batch 22: the two song scenes that check their own song (Song Locations).

On top of the full skip, the crater's Sheik gives Song of Storms and the windmill man
gives the Bolero of Fire. Leaving Link's house for the first time makes Link an adult
and teleports him to the crater's warp pad, with the fire quest at the step where
Sheik appears. Getting Storm there first is what used to stop the windmill scene.
Usage: python -I tools/make_song_batch.py <nup> <out_mod_dir>
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
from randomizer.songs import SONGS, song_flow_patches  # noqa: E402
from randomizer.test_start import StartPreset  # noqa: E402

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
PLACEMENT = {s.location: s.actor for s in SONGS} | {
    'Sheik in Crater': 'Item_Melody_StormSong',
    'Song from Windmill': 'Item_Melody_FireBolero',
}


def build(nup: NupArchive) -> dict[str, bytes]:
    game = GameData(nup)
    skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
    batch = Batch(nup)
    batch.files.update(batch.unpack(skip))

    def read(name: str) -> bytes:
        return batch.read(FLOW_DIR + name + FLOW_EXT)

    for name, data in song_flow_patches(read, PLACEMENT).items():
        batch.files[FLOW_DIR + name + FLOW_EXT] = data
    add_start(batch, PRESET)
    return batch.compressed()


def main() -> None:
    nup_path, out = sys.argv[1:3]
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup))


if __name__ == '__main__':
    main()
