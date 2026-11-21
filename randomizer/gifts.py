"""NPC gifts as item locations: batch 1, the one-time gifts (design
docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md; test batches 27 and 28),
and batch 2, the minigame prizes and the Gold Skulltula rewards (design
2026-11-21-npc-gifts-batch-2-design.md; test batches 29 and 30).

With the key items shuffled, each gift gives what the fill puts there:
- a flow gift's grant (a subflow call whose `ActorName`, `ReveiveItem` for an `NpcCommon`
  hand-over, or a by-reference parameter such as `TakenRewardActor`, is the vanilla item)
  gets the placed item, in every copy the full skip made; a special grant entry (its own
  animation) is pointed at a generic one. Several gifts in one flow are resolved on the
  unpatched flow first, so two gifts can swap items;
- a `Dm_` scene whose entry changed gets the new entry's flows in its `SubFlowList`
  (`RSDB/GameAnalyzedEventInfo`): the game skips a call to a flow missing from it (27d);
- a world gift (an actor in a map) becomes a wrapper of the placed item.
A gift that keeps its own item is not touched.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .fairies import FOUNTAIN_FORBIDDEN
from .formats import byml
from .formats.bfevfl import SUBFLOW, EventFlow, set_string_param, set_subflow_entry
from .items import KEY_ITEMS
from .analyzed_info import subflow_closure

GRANT_FLOW = 'Dm_SY_GetInEvent'
GENERIC_SCENE = 'GetInEvent_Demo_NotLookatObjectEntry'  # in a Dm_ scene (27c, 27d)
GENERIC_NPC = 'GetInEvent_NotTurn'  # in an NPC's flow (27b)
# What a flow gift never gives: the Great Fairies' set, the same GetInEvent-family risks.
GIFT_FORBIDDEN = FOUNTAIN_FORBIDDEN


class GiftPatchError(ValueError):
    pass


@dataclass(frozen=True)
class Gift:
    """A gift handed over by subflow calls in `flow` whose `key` (one, or any of several)
    is one of `vanilla`; with `via`, only calls to that entry."""
    location: str  # OoTR location
    content: str  # what it gives in the game
    flow: str
    key: str | tuple[str, ...]  # 'ActorName', 'ReveiveItem', 'TakenRewardActor'...
    vanilla: tuple[str, ...]
    entry: tuple[str, str] | None = None  # (special entry, generic entry)
    via: str | None = None  # the calls' entry, when one flow holds two such gifts

    @property
    def keys(self) -> tuple[str, ...]:
        return (self.key,) if isinstance(self.key, str) else self.key


@dataclass(frozen=True)
class WorldGift:
    """A gift that is an actor in a map (`banc`, `hash`)."""
    location: str
    content: str
    banc: str
    hash: int


_FIELD = 'Banc/HyruleField/HyruleField_{}_Static.bcett.byml.zs'
_HOUSE = 'GatheringTokenGold'  # the Gold Skulltula house: by-reference TakenRewardActor
_FISH = ('ReveiveItem', 'ActorName')  # a normal fish and the loach: two grants
_FROGS = 'MiniGame_FrogTenors'
_BULLET_BAGS = ('Item_BulletBag_Large', 'Item_BulletBag_Medium')
_QUIVERS = ('Item_Quiver_Large', 'Item_Quiver_Medium')

GIFTS: tuple[Gift | WorldGift, ...] = (
    Gift('GC Darunias Joy', 'Item_Gauntlet_Goron', 'Dm_Goron_0030', 'ActorName',
         ('Item_Gauntlet_Goron',), ('GetInEvent_Goron', GENERIC_SCENE)),
    Gift('HC Zeldas Letter', 'Item_ZeldaLetter', 'Dm_HrlCastle_0050', 'ActorName',
         ('Item_ZeldaLetter',), ('GetInEvent_Zeldaletter', GENERIC_SCENE)),
    Gift('HC Malon Egg', 'Item_WeirdEgg', 'Goto_HyruleCastle', 'ActorName', ('Item_WeirdEgg',)),
    # Npc_SkullKid_Child_02 (the stump) is the memory game, batch 2.
    Gift('LW Skull Kid', 'Obj_Heart_Piece', 'Npc_SkullKid_Child', 'ActorName',
         ('Obj_Heart_Piece',)),
    Gift('ToT Light Arrows Cutscene', 'Item_Arrow_Light', 'Dm_TimeTemple_0130', 'ActorName',
         ('Item_Arrow_Light',)),
    # The remake gives a bag bigger than Link's: Medium or Large.
    Gift('GC Rolling Goron as Child', 'Item_BombBag_Medium', 'Npc_Goron_006_Child',
         'ReveiveItem', ('Item_BombBag_Medium', 'Item_BombBag_Large'),
         ('GetInEvent_NotTurn_BombBag', GENERIC_NPC)),
    Gift('GC Rolling Goron as Adult', 'Obj_Armor_Goron', 'SageOfFire', 'ActorName',
         ('Obj_Armor_Goron',)),
    Gift('ZD King Zora Thawed', 'Obj_Armor_Zora', 'SageOfWater', 'ActorName', ('Obj_Armor_Zora',)),
    Gift('Kak Anju as Child', 'Item_Bottle', 'Minigame_CatchCucco', 'ReveiveItem', ('Item_Bottle',)),
    Gift('Market Lost Dog', 'Obj_Heart_Piece', 'SubEvent_FindRichard', 'ReveiveItem',
         ('Obj_Heart_Piece',)),
    Gift('Kak Man on Roof', 'Obj_Heart_Piece', 'Npc_Hylia_001_Adult', 'ActorName',
         ('Obj_Heart_Piece',)),
    Gift('Market 10 Big Poes', 'Item_Bottle', 'Npc_Hylia_048_BottleShop', 'ActorName',
         ('Item_Bottle',), ('GetInEvent_Poeshop', GENERIC_NPC)),
    WorldGift('LH Sun', 'Item_Arrow_Fire', _FIELD.format('Adult'), 4598657944866228526),
    WorldGift('LH Underwater Item', 'Item_Bottle_Letter', _FIELD.format('Child'),
              474136620438465634),
    # Batch 2: the minigame prizes and the Gold Skulltula rewards. A prize that comes in
    # sizes lists both: the remake gives a bigger one than Link's.
    Gift('Kak 10 Gold Skulltula Reward', 'Item_Wallet_Medium', _HOUSE, 'TakenRewardActor',
         ('Item_Wallet_Medium',)),
    Gift('Kak 20 Gold Skulltula Reward', 'Item_AgonyStone', _HOUSE, 'TakenRewardActor',
         ('Item_AgonyStone',)),
    Gift('Kak 30 Gold Skulltula Reward', 'Item_Wallet_Large', _HOUSE, 'TakenRewardActor',
         ('Item_Wallet_Large',)),
    Gift('Kak 40 Gold Skulltula Reward', 'Item_BombchuBundle_Large', _HOUSE,
         'TakenRewardActor', ('Item_BombchuBundle_Large',)),
    Gift('Kak 50 Gold Skulltula Reward', 'Obj_Heart_Piece', _HOUSE, 'TakenRewardActor',
         ('Obj_Heart_Piece',)),
    Gift('Market Shooting Gallery Reward', 'Item_BulletBag_Medium', 'MiniGame_HitTarget',
         'ReveiveItem', _BULLET_BAGS),
    Gift('Kak Shooting Gallery Reward', 'Item_Quiver_Medium', 'MiniGame_HitTarget',
         'ReveiveItem', _QUIVERS),
    Gift('LW Target in Woods', 'Item_BulletBag_Large', 'Dm_LostWood_0040', 'ActorName',
         _BULLET_BAGS),
    Gift('Market Bombchu Bowling First Prize', 'Item_BombBag_Large', 'MiniGame_BombchuBowling',
         'ReveiveItem', ('Item_BombBag_Medium', 'Item_BombBag_Large')),
    Gift('Market Bombchu Bowling Second Prize', 'Obj_Heart_Piece', 'MiniGame_BombchuBowling',
         'ReveiveItem', ('Obj_Heart_Piece',)),
    Gift('LH Child Fishing', 'Obj_Heart_Piece', 'MiniGame_Fishing', _FISH, ('Obj_Heart_Piece',)),
    Gift('LH Adult Fishing', 'Item_Scale_Gold', 'MiniGame_Fishing', _FISH, ('Item_Scale_Gold',)),
    Gift('LH Lab Dive', 'Obj_Heart_Piece', 'Npc_Hylia_045_Child', 'ReveiveItem',
         ('Obj_Heart_Piece',)),
    Gift('ZD Diving Minigame', 'Item_Scale_Silver', 'MiniGame_Diving', 'ActorName',
         ('Item_Scale_Silver',)),
    Gift('LW Ocarina Memory Game', 'Obj_Heart_Piece', 'Npc_SkullKid_Child_02', 'ActorName',
         ('Obj_Heart_Piece',)),
    # The remake's ocarina game (butterflies) passes its prize to its MushiToriGame entry;
    # the Song of Storms path reaches the other grant.
    Gift('ZR Frogs Ocarina Game', 'Obj_Heart_Piece', _FROGS, 'ActorName', ('Obj_Heart_Piece',),
         via='MushiToriGame'),
    Gift('ZR Frogs in the Rain', 'Obj_Heart_Piece', _FROGS, 'ActorName', ('Obj_Heart_Piece',),
         via='GetInEvent_NotTurn_NotNpc'),
    Gift('GF HBA 1000 Points', 'Obj_Heart_Piece', 'Minigame_HorsebackArchery', 'ActorName',
         ('Obj_Heart_Piece',)),
    Gift('GF HBA 1500 Points', 'Item_Quiver_Large', 'Minigame_HorsebackArchery', 'ActorName',
         _QUIVERS),
    # Accepted without an in-game test (test batch 30c2; docs/TODO.md).
    Gift('Graveyard Dampe Gravedigging Tour', 'Obj_Heart_Piece', 'Npc_Hylia_Dampe_001',
         'ActorName', ('Obj_Heart_Piece',),
         ('GetInEvent_NotTurn_NotNpc_Dampe', 'GetInEvent_NotTurn_NotNpc')),
    # The first win (event 262); the GetInEventInBottle refill is the repeat prize.
    Gift('LLR Talons Chickens', 'Item_Bottle_Milk', 'Minigame_FindOutCucco', 'ReveiveItem',
         ('Item_Bottle_Milk',)),
)
GIFT_BY_LOCATION: dict[str, Gift | WorldGift] = {g.location: g for g in GIFTS}
GIFT_ITEMS: frozenset[str] = frozenset(g.content for g in GIFTS if g.content in KEY_ITEMS)
# Gifts that stay out of the fill. Empty: test batches 28 and 30 passed every gate.
FIXED_GIFTS: frozenset[str] = frozenset()


def _changed(gifts: dict[str, str]) -> list[Gift | WorldGift]:
    unknown = sorted(set(gifts) - set(GIFT_BY_LOCATION))
    if unknown:
        raise GiftPatchError(f'Unknown NPC gift locations: {unknown}')
    return [g for loc, item in gifts.items()
            for g in [GIFT_BY_LOCATION[loc]] if item != g.content]


def _grants(flow: EventFlow, gift: Gift) -> list[tuple[int, str]]:
    """(event, key) of every subflow call in `flow` that grants `gift`'s vanilla item."""
    return [(i, k) for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW
            and (gift.via is None or ev.sub_entry == gift.via)
            for k in gift.keys if flow.action_params(i).get(k) in gift.vanilla]


def _give(data: bytes, gifts: list[tuple[Gift, str]]) -> bytes:
    """`data` (one flow) with each (gift, item) granting its item. Every gift's calls are
    found before any rename, so a gift never renames another's freshly given item."""
    flow = EventFlow(data)
    renames: list[tuple[int, str, str]] = []
    for gift, item in gifts:
        calls = _grants(flow, gift)
        if not calls:
            raise GiftPatchError(f'{gift.flow}: no grant of {gift.vanilla} ({gift.location}).')
        renames += [(i, k, item) for i, k in calls]
    for i, k, item in renames:
        data = set_string_param(data, i, k, item)
    for gift, _ in gifts:
        if gift.entry is not None:
            data = _redirect(data, gift)
    return data


def _redirect(data: bytes, gift: Gift) -> bytes:
    special, generic = gift.entry
    flow = EventFlow(data)
    entries = [i for i, ev in enumerate(flow.events)
               if ev.kind == SUBFLOW and ev.sub_entry == special]
    if not entries:
        raise GiftPatchError(f'{gift.flow}: no call to {special} ({gift.location}).')
    for i in entries:
        data = set_subflow_entry(data, i, generic)
    return data


def gift_flow_patches(read: Callable[[str], bytes], gifts: dict[str, str]) -> dict[str, bytes]:
    """{flow: patched bytes} for the flow gifts in `gifts` (OoTR location -> item) whose
    item changed. `read(flow)` gives the current version (the full skip's if it wrote one).
    Raises GiftPatchError for an unknown location or a missing grant."""
    by_flow: dict[str, list[tuple[Gift, str]]] = {}
    for g in _changed(gifts):
        if isinstance(g, Gift):
            by_flow.setdefault(g.flow, []).append((g, gifts[g.location]))
    return {name: _give(read(name), todo) for name, todo in by_flow.items()}


def gift_subflow_list(info: bytes, load: Callable[[str], EventFlow | None],
                      gifts: dict[str, str]) -> bytes:
    """`ANALYZED_INFO` (decompressed) with the `SubFlowList` of each event whose grant entry
    changed extended by what the generic entry calls. Events with no row (NPC flows) are
    left alone; `info` comes back unchanged when nothing changed."""
    ver, rows = byml.load(info)
    by_id = {r['__RowId']: r for r in rows}
    changed = False
    for g in _changed(gifts):
        if not isinstance(g, Gift) or g.entry is None or g.flow not in by_id:
            continue
        row = by_id[g.flow]
        need = set(subflow_closure(load, [(GRANT_FLOW, g.entry[1])], skip=g.flow))
        have = set(row.get('SubFlowList', []))
        if not need <= have:
            row['SubFlowList'] = sorted(have | need)
            changed = True
    return byml.dump(rows, ver) if changed else info


def gift_actor_swaps(gifts: dict[str, str]) -> dict[int, tuple[str, str]]:
    """{actor hash: (banc, item)} for the world gifts whose item changed (for
    `patch.write_mod(actor_swaps=...)`, which builds the wrappers)."""
    return {g.hash: (g.banc, gifts[g.location]) for g in _changed(gifts)
            if isinstance(g, WorldGift)}
