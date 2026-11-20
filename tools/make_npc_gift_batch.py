"""NPC gifts test batch 27 (spike, docs/npc-gifts-research.md), on the full skip.

Each variant teleports Link next to one gift and makes it give the Boomerang (a child
item that shows in the inventory), the way the shuffle would:
- a grant's item parameter (`ActorName` of a `Dm_SY_GetInEvent` call, or `ReveiveItem`
  of an `NpcCommon` hand-over) is renamed wherever it appears, as the full skip can copy
  it;
- a special grant entry (Darunia's, Zelda's, the bomb bag one) is pointed at a generic
  one, as with the Great Fairies.

27a: castle, next to Malon. She gives the Boomerang; Link starts with the Weird Egg (not
     from her): does it hatch, and does Talon wake?
27b: Goron City, by the rolling Goron, who gives the Boomerang. Link starts with the
     Medium Bomb Bag and then the Small one: does the bag shrink? Also the Goron's
     Bracelet: attempt 1 could not use bombs without it.
27c: Goron City, in Darunia's room: his dance gives the Boomerang.
27d: castle courtyard (the quest at Step04): Zelda gives the Boomerang.
27e: Kakariko, next to Anju: the Cucco round gives the Boomerang (an NpcCommon hand-over).
27f: Lake Hylia, above Ruto's Letter: the bottle actor is a wrapper of the Boomerang;
     Link has the Silver Scale.
27d2-27d4: Zelda without the skip, with her own entry, untouched (27d gave nothing).
28a-28c: Fire Arrows as a wrapper, Ruto's Letter from elsewhere, Silver Gauntlets without
     the bracelet (the plan's gate, docs/superpowers/plans/2026-11-20-npc-gifts-batch-1.md).
Usage: python -I tools/make_npc_gift_batch.py <nup> <out_mod_dir> [27a..27f, 27d2..27d4, 28a..28c]
"""
import math
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import FLOW_DIR, FLOW_EXT, Batch, add_start, write_mod  # noqa: E402
from randomizer.formats import byml  # noqa: E402
from randomizer.formats.bfevfl import (SUBFLOW, EventFlow, set_string_param,  # noqa: E402
                                       set_subflow_entry)
from randomizer.formats.rstb import Rstb  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.patch import RSTB_PATH  # noqa: E402
from randomizer.test_start import (ANALYZED_INFO, NewStartPos, StartPreset,  # noqa: E402
                                   subflow_closure)
from randomizer.wrappers import WRAPPER_PREFIX, build_wrapper_files, wrap_sources  # noqa: E402

ITEM = 'Item_Boomerang'
GENERIC_CUTSCENE = 'GetInEvent_Demo_NotLookatObjectEntry'  # the fountains' generic grant
GENERIC_NPC = 'GetInEvent_NotTurn'


@dataclass(frozen=True)
class Gift:
    """Subflow calls in `flow` whose `key` parameter is one of `vanilla` give the item."""
    flow: str
    key: str  # 'ActorName' or 'ReveiveItem'
    vanilla: tuple[str, ...]


@dataclass(frozen=True)
class Entry:
    """Subflow calls in `flow` to entry `old` call `new` instead."""
    flow: str
    old: str
    new: str


@dataclass(frozen=True)
class Variant:
    preset: StartPreset
    gifts: tuple[Gift, ...] = ()
    entries: tuple[Entry, ...] = ()
    swap: tuple[str, int, str] | None = None  # (banc path, actor hash, content)


def _pos(name: str, at: tuple[float, float, float],
         face: tuple[float, float, float]) -> NewStartPos:
    yaw = math.atan2(face[0] - at[0], face[2] - at[2])
    return NewStartPos(name, (at[0], at[1] + 0.2, at[2]), (0.0, yaw, 0.0))


def _preset(banc: str, pos: NewStartPos, items: tuple[str, ...] = (),
            steps: tuple[tuple[str, str], ...] = (), adult: bool = False) -> StartPreset:
    return StartPreset(banc, pos.name, items=items, new_pos=pos, challenge_steps=steps,
                       adult=adult)


CASTLE_STEPS = tuple(('Goto_HyruleCastle', f'Step0{i}') for i in (1, 2, 3, 4))
MALON = (17.6, 105.5, -25.1)
ROLLING_GORON = (-10.3, 109.6, -16.5)
DARUNIA = (-0.2, 98.6, -41.8)
ANJU = (-72.1, 99.3, 73.1)
RUTO_LETTER = (-151.6, 125.0, 461.0)
RUTO_LETTER_HASH = 474136620438465634
FIELD_CHILD = 'Banc/HyruleField/HyruleField_Child_Static.bcett.byml.zs'
FIELD_ADULT = 'Banc/HyruleField/HyruleField_Adult_Static.bcett.byml.zs'
FIRE_ARROWS = (-158.1, 131.5, 523.4)
FIRE_ARROWS_HASH = 4598657944866228526
KING_ZORA_CHILD = (67.3, 118.9, 15.6)
BOMB_FLOWER_ADULT = (-18.8, 105.0, -9.1)
# The Water Temple quest done (the Fire Arrows quest depends on SageOfWater_IsAfter_Step08),
# then the Fire Arrows quest's steps (the stone tablet moves it to Step02, the sun to Step03).
WATER_DONE = tuple(('SageOfWater', s) for s in (
    'Ready', 'Step00', 'Step01', 'Step03', 'Step04', 'Step05', 'Step06', 'Step07', 'Step07_00',
    'Step07_1', 'Step07_2', 'Step08', 'Complete'))
FIRE_ARROWS_STEPS = tuple(('SubEvent_GetFireArrow', s) for s in ('Ready', 'Step01', 'Step02', 'Step03'))
# The castle courtyard on Impa's anchor (batches 20, 23a and 24a).
COURTYARD = NewStartPos('RandoTest_MeetImpa',
                        (5.134531497955322, 126.82830810546875, -236.39134216308594),
                        (0.0, 3.141592653589793, 0.0))

VARIANTS: dict[str, Variant] = {
    '27a': Variant(
        _preset('HyruleCastle', _pos('RandoTest_GiftMalon', (14.9, 105.5, -23.7), MALON),
                items=('Item_WeirdEgg',), steps=CASTLE_STEPS[:1]),
        gifts=(Gift('Goto_HyruleCastle', 'ActorName', ('Item_WeirdEgg',)),)),
    '27b': Variant(
        _preset('GoronCity_Child',
                _pos('RandoTest_GiftRollingGoron', (-6.3, 109.6, -16.5), ROLLING_GORON),
                items=('Item_BombBag_Medium', 'Item_BombBag_Small', 'Item_Gauntlet_Goron')),
        gifts=(Gift('Npc_Goron_006_Child', 'ReveiveItem',
                    ('Item_BombBag_Medium', 'Item_BombBag_Large')),),
        entries=(Entry('Npc_Goron_006_Child', 'GetInEvent_NotTurn_BombBag', GENERIC_NPC),)),
    '27c': Variant(
        _preset('GoronCity_Child', _pos('RandoTest_GiftDarunia', (-0.2, 98.6, -38.3), DARUNIA),
                items=('Item_Ocarina_Fairy', 'Item_Melody_SariaSong',
                       'Item_Melody_ZeldaLullaby')),
        gifts=(Gift('Dm_Goron_0030', 'ActorName', ('Item_Gauntlet_Goron',)),),
        entries=(Entry('Dm_Goron_0030', 'GetInEvent_Goron', GENERIC_CUTSCENE),)),
    '27d': Variant(
        _preset('HyruleCastle', COURTYARD, items=('Item_Ocarina_Fairy',), steps=CASTLE_STEPS),
        gifts=(Gift('Dm_HrlCastle_0050', 'ActorName', ('Item_ZeldaLetter',)),),
        entries=(Entry('Dm_HrlCastle_0050', 'GetInEvent_Zeldaletter', GENERIC_CUTSCENE),)),
    # 27d gave nothing on the full skip (attempt 1). These tell the skip's rewrite of
    # Dm_HrlCastle_0050 from the generic entry: 27d2 without the skip, 27d3 keeps Zelda's
    # own entry, 27d4 leaves her scene untouched (does the skip lose the letter itself?).
    '27d2': Variant(
        _preset('HyruleCastle', COURTYARD, items=('Item_Ocarina_Fairy',), steps=CASTLE_STEPS),
        gifts=(Gift('Dm_HrlCastle_0050', 'ActorName', ('Item_ZeldaLetter',)),),
        entries=(Entry('Dm_HrlCastle_0050', 'GetInEvent_Zeldaletter', GENERIC_CUTSCENE),)),
    '27d3': Variant(
        _preset('HyruleCastle', COURTYARD, items=('Item_Ocarina_Fairy',), steps=CASTLE_STEPS),
        gifts=(Gift('Dm_HrlCastle_0050', 'ActorName', ('Item_ZeldaLetter',)),)),
    '27d4': Variant(
        _preset('HyruleCastle', COURTYARD, items=('Item_Ocarina_Fairy',), steps=CASTLE_STEPS)),
    # Batch 28 (the plan's gate): what batch 27 left untested.
    # 28a: LH Sun's Fire Arrows as a wrapper (of the Hookshot, usable by the adult): does
    #      it show (before or after shooting the sun) and give the Hookshot?
    #      Attempt 1: no arrows to shoot, and the quest was not started (it depends on
    #      SageOfWater_IsAfter_Step08). Now the Water Temple quest is complete, the Fire
    #      Arrows quest is at Step02 (the sun can be shot; it moves to Step03, the arrows
    #      appear) and Link has a quiver. 28a2: the quest already at Step03.
    '28a': Variant(
        _preset('HyruleField_Adult',
                _pos('RandoTest_GiftFireArrows', (-160.1, 131.5, 521.4), FIRE_ARROWS),
                items=('Item_Range_Bow', 'Item_Quiver_Medium'),
                steps=WATER_DONE + FIRE_ARROWS_STEPS[:3], adult=True),
        swap=(FIELD_ADULT, FIRE_ARROWS_HASH, 'Item_Hookshot')),
    '28a2': Variant(
        _preset('HyruleField_Adult',
                _pos('RandoTest_GiftFireArrows', (-160.1, 131.5, 521.4), FIRE_ARROWS),
                items=('Item_Range_Bow', 'Item_Quiver_Medium'),
                steps=WATER_DONE + FIRE_ARROWS_STEPS, adult=True),
        swap=(FIELD_ADULT, FIRE_ARROWS_HASH, 'Item_Hookshot')),
    # 28b: Ruto's Letter from elsewhere (the start preset): does King Zora take it?
    '28b': Variant(
        _preset('ZoraDomain_Child',
                _pos('RandoTest_GiftKingZora', (63.3, 118.9, 15.6), KING_ZORA_CHILD),
                items=('Item_Bottle_Letter',))),
    # 28c: adult with the Silver Gauntlets and a bomb bag but no Goron's Bracelet: can he
    #      throw bombs and lift a bomb flower?
    '28c': Variant(
        _preset('GoronCity_Adult',
                _pos('RandoTest_SilverNoBracelet', (-15.8, 105.0, -9.1), BOMB_FLOWER_ADULT),
                items=('Item_Gauntlet_Silver', 'Item_BombBag_Medium'), adult=True)),
    '27e': Variant(
        _preset('KakarikoVillage_Child', _pos('RandoTest_GiftAnju', (-72.1, 99.3, 76.1), ANJU)),
        gifts=(Gift('Minigame_CatchCucco', 'ReveiveItem', ('Item_Bottle',)),)),
    '27f': Variant(
        _preset('HyruleField_Child',
                _pos('RandoTest_GiftRutoLetter', (-151.6, 131.0, 459.0), RUTO_LETTER),
                items=('Item_Scale_Silver',)),
        swap=(FIELD_CHILD, RUTO_LETTER_HASH, ITEM)),
}


NO_SKIP = {'27d2'}  # variants built without the full skip


def _calls(data: bytes, match) -> list[int]:
    flow = EventFlow(data)
    return [i for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW and match(flow, i, ev)]


def give(data: bytes, gift: Gift, item: str) -> bytes:
    """`gift.flow` giving `item` wherever it gave a vanilla value. Raises ValueError
    when there is no such call."""
    calls = _calls(data, lambda f, i, ev: f.action_params(i).get(gift.key) in gift.vanilla)
    if not calls:
        raise ValueError(f'{gift.flow}: no call with {gift.key} in {gift.vanilla}.')
    for i in calls:
        data = set_string_param(data, i, gift.key, item)
    return data


def redirect(data: bytes, entry: Entry) -> bytes:
    """`entry.flow` calling `entry.new` instead of `entry.old`. Raises ValueError when
    there is no such call."""
    calls = _calls(data, lambda f, i, ev: ev.sub_entry == entry.old)
    if not calls:
        raise ValueError(f'{entry.flow}: no call to {entry.old}.')
    for i in calls:
        data = set_subflow_entry(data, i, entry.new)
    return data


def _allow_subflows(batch: Batch, entry: Entry) -> None:
    """Adds what `entry.new` calls to the event's `SubFlowList`: the game ignores a
    call to a flow missing from it (27d, attempt 2: Zelda's scene lacked
    `ActionGuide`, which the generic grant calls)."""
    ver, rows = byml.load(batch.read(ANALYZED_INFO))
    row = next((r for r in rows if r['__RowId'] == entry.flow), None)
    if row is None:
        return  # not an analysed event (NPC flows): nothing to keep in step
    need = subflow_closure(batch.flow, [('Dm_SY_GetInEvent', entry.new)], skip=entry.flow)
    missing = sorted(set(need) - set(row['SubFlowList']))
    if missing:
        print(f'{entry.flow}: SubFlowList += {missing}', file=sys.stderr)
        row['SubFlowList'] = sorted(set(row['SubFlowList']) | set(need))
        batch.files[ANALYZED_INFO] = byml.dump(rows, ver)


def build(nup: NupArchive, variant: str) -> dict[str, bytes]:
    v = VARIANTS[variant]
    game = GameData(nup)
    batch = Batch(nup)
    if variant not in NO_SKIP:
        skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
        batch.files.update(batch.unpack(skip))
    for gift in v.gifts:
        path = FLOW_DIR + gift.flow + FLOW_EXT
        batch.files[path] = give(batch.read(path), gift, ITEM)
    for entry in v.entries:
        path = FLOW_DIR + entry.flow + FLOW_EXT
        batch.files[path] = redirect(batch.read(path), entry)
        _allow_subflows(batch, entry)
    add_start(batch, v.preset)
    if v.swap is not None:
        banc, actor, content = v.swap
        ver, root = byml.load(batch.read(banc))
        hits = [a for a in root['Actors'] if isinstance(a, dict) and a.get('Hash') == actor]
        if len(hits) != 1:
            raise SystemExit(f'FAIL: {len(hits)} actors with hash {actor} in {banc}')
        hits[0]['Gyaml'] = WRAPPER_PREFIX + content
        batch.files[banc] = byml.dump(root, ver)
    files = batch.compressed()
    if v.swap is not None:  # the wrapper, with its RSTB entries
        rstb = Rstb.load(game.codec.decompress(RSTB_PATH, files[RSTB_PATH]))
        files.update(build_wrapper_files(game, wrap_sources(game, [v.swap[2]]), rstb))
        files[RSTB_PATH] = game.codec.compress(RSTB_PATH, rstb.dump())
    return files


def main() -> None:
    nup_path, out = sys.argv[1:3]
    variant = sys.argv[3] if len(sys.argv) > 3 else '27a'
    if variant not in VARIANTS:
        raise SystemExit(f'Unknown variant {variant!r}: use one of {", ".join(VARIANTS)}.')
    with NupArchive(nup_path) as nup:
        write_mod(out, build(nup, variant))


if __name__ == '__main__':
    main()
