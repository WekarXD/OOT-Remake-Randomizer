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
26d: 26a without the full skip.
26e: the full skip, Din's fountain untouched; 100 rupees.
Usage: python -I tools/make_fairy_batch.py <nup> <out_mod_dir> [26a|26b|26c|26d|26e]
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
from randomizer import fairies  # noqa: E402
from randomizer.fairies import make_free, patch_triforce  # noqa: E402
from randomizer.test_start import NewStartPos, StartPreset  # noqa: E402

TRIFORCE_FLOW = fairies.TRIFORCE_FLOW
FOUNTAIN_BY_NAME = {f.name: f for f in fairies.FOUNTAINS}
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
    '26d': ('Din', 'Item_FaroreWind', ('Item_FairyBless_MPDouble',), False),
    '26e': ('Din', None, (), False),
}
# 26e: the full skip and Din's fountain left untouched (it charges: the preset gives
# 100 rupees). 26d gave Farore's Wind without the skip; this tells whether the skip's
# rewrite of Din (copies per call site, the file grows) loses the grant, or the batch's
# own patch of the grown file does (new strings after the relocated data).
# Variants built without the full skip. 26d = 26a without it: attempt 4 of 26a played
# Din's scene but gave nothing, and Din keeps the skip's old trimming (its rewrite
# fails with a conflict), so this tells the trimming from the patch.
NO_SKIP = {'26d'}


def patch_fountain(data: bytes, name: str, item: str) -> bytes:
    return fairies.patch_fountain(data, FOUNTAIN_BY_NAME[name], item)


def _preset(fountain: str, extra: tuple[str, ...], adult: bool, rupees: int) -> StartPreset:
    _, banc, point, basin = FOUNTAINS[fountain]
    yaw = math.atan2(basin[0] - point[0], basin[2] - point[2])  # facing the basin
    pos = NewStartPos(f'RandoTest_Fairy{fountain}', (point[0], point[1] + 0.2, point[2]),
                      (0.0, yaw, 0.0))
    return StartPreset(banc, pos.name, items=SONGS + extra, new_pos=pos, adult=adult,
                       rupees=rupees)


def build(nup: NupArchive, variant: str) -> dict[str, bytes]:
    fountain, item, extra, adult = VARIANTS[variant]
    game = GameData(nup)
    batch = Batch(nup)
    if variant not in NO_SKIP:
        skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
        batch.files.update(batch.unpack(skip))
    path = FLOW_DIR + 'Dm_FairyFountain_' + fountain + FLOW_EXT
    if item is not None:
        batch.files[path] = patch_fountain(batch.read(path), fountain, item)
    if item is not None and fountain != 'Din':  # the other fountains call Din's shared Pay entries
        path = FLOW_DIR + 'Dm_FairyFountain_Din' + FLOW_EXT
        batch.files[path] = make_free(batch.read(path))
    path = FLOW_DIR + TRIFORCE_FLOW + FLOW_EXT
    batch.files[path] = patch_triforce(batch.read(path))
    add_start(batch, _preset(fountain, extra, adult, 100 if item is None else 0))
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
