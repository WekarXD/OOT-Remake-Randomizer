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
29a-29d: NPC gifts batch 2 (docs/npc-gifts-research.md, "Batch 2"): upgrades given out of
     order, a Gold Skulltula house reward and a minigame prize.
30a-30e: the gate of NPC gifts batch 2 (docs/superpowers/plans/2026-11-21-npc-gifts-batch-2.md):
     Talon, milk from elsewhere, Dampe, LW Target, the quiver order.
31a-31f: NPC gifts batch 3a (docs/npc-gifts-research.md): the ocarinas, Medigoron, the carpet
     salesman and the 100-token reward.
32a-32f: the gate of NPC gifts batch 3a (docs/superpowers/specs/2026-11-21-npc-gifts-batch-3a-design.md):
     the merchants' sold-out patch, their items from elsewhere, Zelda's ocarina scene with no
     ocarina, the Gerudo Card scene.
Usage: python -I tools/make_npc_gift_batch.py <nup> <out_mod_dir> [27a..27f, 27d2..27d4, 28a..28c, 29a..29d, 30a..30e, 31a..31f, 32a..32f3]
"""
import math
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_start_batch import FLOW_DIR, FLOW_EXT, Batch, add_start, write_mod  # noqa: E402
from randomizer.formats import byml  # noqa: E402
from randomizer.formats.bfevfl import (ACTION, SUBFLOW, EventFlow,  # noqa: E402
                                       set_string_param, set_subflow_entry)
from randomizer.formats.rstb import Rstb  # noqa: E402
from randomizer.full_skip import files_with_fallback  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.generate import FULL_SKIP_PHASE  # noqa: E402
from randomizer.merchants import sold_out_patches  # noqa: E402
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
    merchants: bool = False  # the merchants' sold-out patch (randomizer.merchants)


def _pos(name: str, at: tuple[float, float, float],
         face: tuple[float, float, float]) -> NewStartPos:
    yaw = math.atan2(face[0] - at[0], face[2] - at[2])
    return NewStartPos(name, (at[0], at[1] + 0.2, at[2]), (0.0, yaw, 0.0))


def _preset(banc: str, pos: NewStartPos, items: tuple[str, ...] = (),
            steps: tuple[tuple[str, str], ...] = (), adult: bool = False,
            rupees: int = 0, flags: tuple[tuple[str, bool], ...] = (),
            ints: tuple[tuple[str, int], ...] = ()) -> StartPreset:
    return StartPreset(banc, pos.name, items=items, new_pos=pos, challenge_steps=steps,
                       adult=adult, rupees=rupees, flags=flags, ints=ints)


CASTLE_STEPS = tuple(('Goto_HyruleCastle', f'Step0{i}') for i in (1, 2, 3, 4))
CASTLE_DONE = tuple(('Goto_HyruleCastle', s) for s in (
    'Step01', 'Step02', 'Step02_01', 'Step03', 'Step03_02', 'Step04', 'Complete'))
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

SKULL_DAD = (-26.5, 102.9, 72.5)  # his actor sits at y 109.9; the floor is at 102.9
DIVING_ZORA = (30.7, 113.6, -8.2)
LAB_SCIENTIST = (-174.5, 137.8, 422.3)
TALON_RANCH = (-52.4, 150.7, 199.3)
DAMPE_CHILD = (-12.0, 100.8, 20.0)
LW_TARGET = (40.3, 102.9, -0.2)
# Batch 31 (NPC gifts batch 3a).
SARIA_BRIDGE = (-117.1, 114.5, -38.2)  # her farewell actor; the trigger is at x -115.4
# Every start preset marks Saria's farewell as played (FOREST_EXIT_FLAGS); 31a undoes it.
SARIA_FAREWELL_UNPLAYED = (('HavePlayedEvent.KokiriForest_ArriveLostWood', False),
                           ('HavePlayedEvent.Dm_Kokiri_0150', False),
                           ('HavePlayedEvent.Dm_Kokiri_0155', False),
                           ('HyruleField_ChangeENV', False))
# The Ocarina of Time scene (DoorOfTime_GetOcarinaOfTime): its trigger is by the moat, at
# (18.0, 167.3, 52.7); the quest reaches Step03 with the three stones.
DOOR_TO_STEP03 = tuple(('DoorOfTime', s) for s in (
    'Step01', 'Step02', 'Step2_1', 'Srep2_1_1', 'Step2_2', 'Step03'))
MEDIGORON = (36.2, 115.7, 6.7)
CARPET_SALESMAN = (37.3, 90.5, 60.6)
TOKEN_COUNT = 'PouchData.Item_Token_Gold.StockNum'
# Batch 32. The carpenters' rescue ends in SageOfSpirit_RescueCarpenter 328, a transition to
# the event Meet_FourCarpenter_ClearEvent (SageOfSpirit), which moves the quest to Step02 and
# plays Dm_Gerudo_0025 (the card).
SPIRIT_TO_STEP01 = (('SageOfSpirit', 'Ready'), ('SageOfSpirit', 'Step01'))
CARPENTERS_HELPED = 'GerudoFortress_Meet_FourCarpenter_NumOfCarpenterHelped'
CARPENTERS_FOUND = 'GerudoFortress_Meet_FourCarpenter_NumOfCarpenterFound'
CARPENTER_013_THIEF = (23.3, 102.5, -66.8)  # Enemy_MiddleBoss_GerudoThief; he is at x 31.9
MEDIGORON_SALE = (Gift('Npc_Goron_Medigoron_Adult', 'ActorName', ('Shop_Sword_Giant',)),)

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
    # Batch 29 (NPC gifts batch 2). A chest gives one fixed size of an upgrade, so the
    # shuffle can hand them out of order.
    # 29a: Zora's Domain, child: the Golden Scale then the Silver one (how deep can he
    #      dive?), the Giant's Wallet then the Adult's one, and 500 rupees (does it hold
    #      500 or 200?).
    '29a': Variant(
        _preset('ZoraDomain_Child', _pos('RandoTest_UpgradeOrder', (27.0, 113.3, -4.8),
                                         DIVING_ZORA),
                items=('Item_Scale_Gold', 'Item_Scale_Silver', 'Item_Wallet_Large',
                       'Item_Wallet_Medium'), rupees=500)),
    # 29a2: the control for 29a (the menu showed Gold, but the lab dive did not reach the
    #       bottom): the Golden Scale alone, in the Lake Hylia lab.
    '29a2': Variant(
        _preset('HyruleField_Child', _pos('RandoTest_GoldScaleOnly', (-174.5, 137.8, 419.3),
                                          LAB_SCIENTIST),
                items=('Item_Scale_Gold',))),
    # 29b: Kakariko, child: the biggest bullet bag before the Slingshot (seeds, up to 50?).
    '29b': Variant(
        _preset('KakarikoVillage_Child',
                _pos('RandoTest_BagBeforeSlingshot', (-72.1, 99.3, 76.1), ANJU),
                items=('Item_BulletBag_Large', 'Item_Range_SlingShot'))),
    # 29c: the Gold Skulltula house, child, with 10 tokens given by the start preset
    #      (also tests a token from GetInEvent): the 10-token reward gives the Boomerang
    #      (the house's by-reference TakenRewardActor).
    '29c': Variant(
        _preset('KakarikoVillage_Child',
                _pos('RandoTest_GiftSkullHouse', (-27.0, 102.9, 70.0), SKULL_DAD),
                items=('Obj_Token_Gold',) * 10),
        gifts=(Gift('GatheringTokenGold', 'TakenRewardActor', ('Item_Wallet_Medium',)),)),
    # 29d: Zora's Domain, child, by the diving Zora: the first win gives the Boomerang
    #      (a GetInEvent_NotTurn_NotNpc grant of a minigame).
    '29d': Variant(
        _preset('ZoraDomain_Child', _pos('RandoTest_GiftDiving', (27.0, 113.3, -4.8),
                                         DIVING_ZORA)),
        gifts=(Gift('MiniGame_Diving', 'ActorName', ('Item_Scale_Silver',)),)),
    # Batch 30 (the gate of NPC gifts batch 2).
    # 30a: Lon Lon Ranch, child, by Talon (woken, 100 rupees for the 30-rupee game): the
    #      first win (event 262, an NpcCommon hand-over) gives the Boomerang. Event 261
    #      (GetInEventInBottle) is the repeat prize, refilling an empty bottle: untouched.
    '30a': Variant(
        _preset('HyruleField_Child', _pos('RandoTest_GiftTalon', (-52.4, 150.7, 202.3),
                                          TALON_RANCH),
                steps=CASTLE_STEPS, rupees=100),
        gifts=(Gift('Minigame_FindOutCucco', 'ReveiveItem', ('Item_Bottle_Milk',)),)),
    # 30b: the same place, with a Bottle with Milk from the start preset: can he drink it?
    '30b': Variant(
        _preset('HyruleField_Child', _pos('RandoTest_MilkElsewhere', (-52.4, 150.7, 202.3),
                                          TALON_RANCH),
                items=('Item_Bottle_Milk',))),
    # 30c: the graveyard, child, by Dampe, with the Sun's Song (his tour is at night) and
    #      200 rupees: the tour's Piece of Heart (a lottery) gives the Boomerang, through
    #      the generic entry instead of his own.
    '30c': Variant(
        _preset('Graveyard_Child', _pos('RandoTest_GiftDampe', (-12.0, 100.8, 23.0),
                                        DAMPE_CHILD),
                items=('Item_Ocarina_Fairy', 'Item_Melody_SunSong'), rupees=200),
        gifts=(Gift('Npc_Hylia_Dampe_001', 'ActorName', ('Obj_Heart_Piece',)),),
        entries=(Entry('Npc_Hylia_Dampe_001', 'GetInEvent_NotTurn_NotNpc_Dampe',
                       'GetInEvent_NotTurn_NotNpc'),)),
    # 30c2: 30c with the castle quest complete: in 30c the Sun's Song made night, but day
    #       came back (time may be frozen until Zelda's meeting).
    '30c2': Variant(
        _preset('Graveyard_Child', _pos('RandoTest_GiftDampe', (-12.0, 100.8, 23.0),
                                        DAMPE_CHILD),
                items=('Item_Ocarina_Fairy', 'Item_Melody_SunSong'), rupees=200,
                steps=CASTLE_DONE),
        gifts=(Gift('Npc_Hylia_Dampe_001', 'ActorName', ('Obj_Heart_Piece',)),),
        entries=(Entry('Npc_Hylia_Dampe_001', 'GetInEvent_NotTurn_NotNpc_Dampe',
                       'GetInEvent_NotTurn_NotNpc'),)),
    # 30d: the Lost Woods, child, near the target, with the Slingshot (and its biggest bag,
    #      so it has seeds): hitting the target gives the Boomerang (the scene animates a
    #      bullet bag).
    '30d': Variant(
        _preset('LostWood_Child', _pos('RandoTest_GiftLWTarget', (36.3, 102.9, -0.2),
                                       LW_TARGET),
                items=('Item_BulletBag_Large', 'Item_Range_SlingShot')),
        gifts=(Gift('Dm_LostWood_0040', 'ActorName',
                    ('Item_BulletBag_Large', 'Item_BulletBag_Medium')),)),
    # 30e: Kakariko, adult: the biggest quiver, then the medium one, then the Bow: how many
    #      arrows does the Bow hold?
    '30e': Variant(
        _preset('KakarikoVillage_Adult',
                _pos('RandoTest_QuiverOrder', (-72.1, 99.3, 76.1), ANJU),
                items=('Item_Quiver_Large', 'Item_Quiver_Medium', 'Item_Range_Bow'),
                adult=True)),
    # Batch 31 (NPC gifts batch 3a: OoTR's ocarinas, Medigoron, the carpet salesman and
    # the 100-token reward).
    # 31a: Kokiri Forest, child, a few steps from the bridge, with Saria's farewell not
    #      yet played: walking onto the bridge, her ocarina gives the Boomerang (a pouch
    #      action's `Actor` and the get display's `ActorName`).
    '31a': Variant(
        _preset('KokiriForest_Child', _pos('RandoTest_GiftSaria', (-108.1, 115.0, -38.2),
                                           SARIA_BRIDGE),
                flags=SARIA_FAREWELL_UNPLAYED),
        gifts=(Gift('Dm_Kokiri_0155', 'Actor', ('Item_Ocarina_Fairy',)),
               Gift('Dm_Kokiri_0155', 'ActorName', ('Item_Ocarina_Fairy',)))),
    # 31b: Hyrule Field, child, at the market's drawbridge, the castle quest complete and
    #      the Door of Time quest at Step03, with the Fairy Ocarina: walking to the moat,
    #      Zelda's Ocarina of Time gives the Boomerang (and the Song of Time still comes).
    '31b': Variant(
        StartPreset('HyruleField_Child', 'HyruleField_FrontOfMarket',
                    items=('Item_Ocarina_Fairy',), challenge_steps=CASTLE_DONE + DOOR_TO_STEP03),
        gifts=(Gift('Dm_MelodyGet_Time', 'Actor', ('Item_Ocarina_Time',)),
               Gift('Dm_MelodyGet_Time', 'ActorName', ('Item_Ocarina_Time',)))),
    # 31c: Kakariko, child: the Ocarina of Time, then the Fairy Ocarina (out of order), and
    #      Zelda's Lullaby: which ocarina does the menu show, and can he play?
    '31c': Variant(
        _preset('KakarikoVillage_Child',
                _pos('RandoTest_OcarinaOrder', (-72.1, 99.3, 76.1), ANJU),
                items=('Item_Ocarina_Time', 'Item_Ocarina_Fairy', 'Item_Melody_ZeldaLullaby'))),
    # 31d: Goron City, adult, by Medigoron, with 200 rupees: he sells the Boomerang (the
    #      shop's by-reference `ActorName`; his own grant entry points at the generic one).
    #      Talk again after buying: does he sell it again?
    '31d': Variant(
        _preset('GoronCity_Adult', _pos('RandoTest_GiftMedigoron', (31.2, 115.9, 9.7),
                                        MEDIGORON),
                adult=True, rupees=200),
        gifts=(Gift('Npc_Goron_Medigoron_Adult', 'ActorName', ('Shop_Sword_Giant',)),),
        entries=(Entry('SimpleShop', 'GetInEventItemSwordMedigoron', GENERIC_NPC),)),
    # 31e: the Haunted Wasteland, adult, by the carpet salesman, with 200 rupees: he sells
    #      the Boomerang (an NpcCommon hand-over by reference). Again after buying?
    #      The carpet (Obj_Gerudo_FlyingCarpetFloor_A_01, centre 37.65, 59.75) floats:
    #      batch 31 started 4.3 units out and fell off, so the start is on it now, and the
    #      Hover Boots come as a fallback.
    '31e': Variant(
        _preset('HountedWasteland_Adult',
                _pos('RandoTest_GiftCarpet', (38.5, 90.8, 58.4), CARPET_SALESMAN),
                items=('Item_HoverBoot',), adult=True, rupees=200),
        gifts=(Gift('Npc_Hylia_044_Adult', 'ActorName', ('Shop_BombchuBundle_01',)),)),
    # 31f: the Gold Skulltula house, child, with 100 tokens (the count set directly): the
    #      100-token reward (its own entry, and a literal `ActorName`) gives the Boomerang.
    '31f': Variant(
        _preset('KakarikoVillage_Child',
                _pos('RandoTest_GiftSkull100', (-27.0, 102.9, 70.0), SKULL_DAD),
                ints=((TOKEN_COUNT, 100),)),
        gifts=(Gift('GatheringTokenGold', 'TakenRewardActor', ('Obj_Rupee_Gold',)),
               Gift('GatheringTokenGold', 'ActorName', ('Obj_Rupee_Gold',)))),
    # Batch 32 (the gate of NPC gifts batch 3a).
    # 32a: 31d with the sold-out patch: refuse once, then buy, then talk again.
    '32a': Variant(
        _preset('GoronCity_Adult', _pos('RandoTest_SoldMedigoron', (31.2, 115.9, 9.7),
                                        MEDIGORON),
                adult=True, rupees=200),
        gifts=MEDIGORON_SALE,
        entries=(Entry('SimpleShop', 'GetInEventItemSwordMedigoron', GENERIC_NPC),),
        merchants=True),
    # 32b: 31e2 with the sold-out patch.
    '32b': Variant(
        _preset('HountedWasteland_Adult',
                _pos('RandoTest_SoldCarpet', (38.5, 90.8, 58.4), CARPET_SALESMAN),
                items=('Item_HoverBoot',), adult=True, rupees=200),
        gifts=(Gift('Npc_Hylia_044_Adult', 'ActorName', ('Shop_BombchuBundle_01',)),),
        merchants=True),
    # 32c/32c2: the Giant's Knife from elsewhere (two candidate actors), by the patched
    #      Medigoron: does the knife work, and does he still sell with it in the pouch?
    '32c': Variant(
        _preset('GoronCity_Adult', _pos('RandoTest_KnifeElsewhere', (31.2, 115.9, 9.7),
                                        MEDIGORON),
                items=('Item_Sword_Giant',), adult=True, rupees=200),
        gifts=MEDIGORON_SALE,
        entries=(Entry('SimpleShop', 'GetInEventItemSwordMedigoron', GENERIC_NPC),),
        merchants=True),
    '32c2': Variant(
        _preset('GoronCity_Adult', _pos('RandoTest_KnifeElsewhere', (31.2, 115.9, 9.7),
                                        MEDIGORON),
                items=('Shop_Sword_Giant',), adult=True, rupees=200),
        gifts=MEDIGORON_SALE,
        entries=(Entry('SimpleShop', 'GetInEventItemSwordMedigoron', GENERIC_NPC),),
        merchants=True),
    # 32d/32d2: the carpet's bombchus from elsewhere, against the small bundle (with a bag).
    '32d': Variant(
        _preset('KakarikoVillage_Adult', _pos('RandoTest_ShopChus', (-72.1, 99.3, 76.1), ANJU),
                items=('Item_BombBag_Small', 'Shop_BombchuBundle_01'), adult=True)),
    '32d2': Variant(
        _preset('KakarikoVillage_Adult', _pos('RandoTest_ShopChus', (-72.1, 99.3, 76.1), ANJU),
                items=('Item_BombBag_Small', 'Item_BombchuBundle_Small'), adult=True)),
    # 32e: 31b with no ocarina in the pouch: does Zelda's scene start and give both?
    '32e': Variant(
        StartPreset('HyruleField_Child', 'HyruleField_FrontOfMarket',
                    challenge_steps=CASTLE_DONE + DOOR_TO_STEP03),
        gifts=(Gift('Dm_MelodyGet_Time', 'Actor', ('Item_Ocarina_Time',)),
               Gift('Dm_MelodyGet_Time', 'ActorName', ('Item_Ocarina_Time',)))),
    # 32f: the fortress, adult, the rescue at Step01 with four carpenters helped, and the
    #      rescue's closing event booted on arrival: does the card scene give the Boomerang?
    #      32f2 boots the card scene itself.
    '32f': Variant(
        StartPreset('GerudoFortress_Adult', 'GerudoFortress_FromGerudoValley', adult=True,
                    challenge_steps=SPIRIT_TO_STEP01, ints=((CARPENTERS_HELPED, 4),),
                    boot_event='Meet_FourCarpenter_ClearEvent'),
        gifts=(Gift('Dm_Gerudo_0025', 'ActorName', ('Item_Token_Gerudo',)),)),
    '32f2': Variant(
        StartPreset('GerudoFortress_Adult', 'GerudoFortress_FromGerudoValley', adult=True,
                    challenge_steps=SPIRIT_TO_STEP01, ints=((CARPENTERS_HELPED, 4),),
                    boot_event='Dm_Gerudo_0025'),
        gifts=(Gift('Dm_Gerudo_0025', 'ActorName', ('Item_Token_Gerudo',)),)),
    # 32f3: 32f did not play the scene and 32f2 stayed black. Now the real way: three
    #       carpenters counted as helped, Link in carpenter 013's room by his thief. Beat
    #       her, open the cell with her key and talk to him: the count reaches 4 and the
    #       rescue's closing event plays the card scene.
    '32f3': Variant(
        _preset('GerudoFortress_Adult',
                _pos('RandoTest_LastCarpenter', (27.0, 102.6, -64.0), CARPENTER_013_THIEF),
                steps=SPIRIT_TO_STEP01, adult=True,
                ints=((CARPENTERS_HELPED, 3), (CARPENTERS_FOUND, 3))),
        gifts=(Gift('Dm_Gerudo_0025', 'ActorName', ('Item_Token_Gerudo',)),)),
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


def _calls(data: bytes, match, kind: int = SUBFLOW) -> list[int]:
    flow = EventFlow(data)
    return [i for i, ev in enumerate(flow.events) if ev.kind == kind and match(flow, i, ev)]


def give(data: bytes, gift: Gift, item: str) -> bytes:
    """`gift.flow` giving `item` wherever it gave a vanilla value (an action's `Actor`
    for the key 'Actor', a subflow call's parameter otherwise). Raises ValueError when
    there is no such call."""
    kind = ACTION if gift.key == 'Actor' else SUBFLOW
    calls = _calls(data, lambda f, i, ev: f.action_params(i).get(gift.key) in gift.vanilla, kind)
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
    if v.merchants:
        batch.files.update((FLOW_DIR + name + FLOW_EXT, data) for name, data in
                           sold_out_patches(lambda n: batch.read(FLOW_DIR + n + FLOW_EXT)).items())
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
