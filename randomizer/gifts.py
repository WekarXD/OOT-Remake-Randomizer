"""NPC gifts, batch 1, as item locations (design
docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md; proven by test batches 27
and 28).

With the key items shuffled, each gift gives what the fill puts there:
- a flow gift's grant (a subflow call whose `ActorName`, or `ReveiveItem` for an
  `NpcCommon` hand-over, is the vanilla item) gets the placed item, in every copy the
  full skip made; a special grant entry (its own animation) is pointed at a generic one;
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
from .test_start import subflow_closure

GRANT_FLOW = 'Dm_SY_GetInEvent'
GENERIC_SCENE = 'GetInEvent_Demo_NotLookatObjectEntry'  # in a Dm_ scene (27c, 27d)
GENERIC_NPC = 'GetInEvent_NotTurn'  # in an NPC's flow (27b)
# What a flow gift never gives: the Great Fairies' set, the same GetInEvent-family risks.
GIFT_FORBIDDEN = FOUNTAIN_FORBIDDEN


class GiftPatchError(ValueError):
    pass


@dataclass(frozen=True)
class Gift:
    """A gift handed over by subflow calls in `flow` whose `key` is one of `vanilla`."""
    location: str  # OoTR location
    content: str  # what it gives in the game
    flow: str
    key: str  # 'ActorName' or 'ReveiveItem'
    vanilla: tuple[str, ...]
    entry: tuple[str, str] | None = None  # (special entry, generic entry)


@dataclass(frozen=True)
class WorldGift:
    """A gift that is an actor in a map (`banc`, `hash`)."""
    location: str
    content: str
    banc: str
    hash: int


_FIELD = 'Banc/HyruleField/HyruleField_{}_Static.bcett.byml.zs'

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
)
GIFT_BY_LOCATION: dict[str, Gift | WorldGift] = {g.location: g for g in GIFTS}
GIFT_ITEMS: frozenset[str] = frozenset(g.content for g in GIFTS if g.content in KEY_ITEMS)
# Gifts that stay out of the fill. Empty: test batch 28 passed every gate.
FIXED_GIFTS: frozenset[str] = frozenset()


def _changed(gifts: dict[str, str]) -> list[Gift | WorldGift]:
    unknown = sorted(set(gifts) - set(GIFT_BY_LOCATION))
    if unknown:
        raise GiftPatchError(f'Unknown NPC gift locations: {unknown}')
    return [g for loc, item in gifts.items()
            for g in [GIFT_BY_LOCATION[loc]] if item != g.content]


def _give(data: bytes, gift: Gift, item: str) -> bytes:
    flow = EventFlow(data)
    calls = [i for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW
             and flow.action_params(i).get(gift.key) in gift.vanilla]
    if not calls:
        raise GiftPatchError(f'{gift.flow}: no grant of {gift.vanilla} ({gift.location}).')
    for i in calls:
        data = set_string_param(data, i, gift.key, item)
    if gift.entry is not None:
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
    out: dict[str, bytes] = {}
    for g in _changed(gifts):
        if isinstance(g, Gift):
            out[g.flow] = _give(out.get(g.flow) or read(g.flow), g, gifts[g.location])
    return out


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
        if not need <= set(row['SubFlowList']):
            row['SubFlowList'] = sorted(set(row['SubFlowList']) | need)
            changed = True
    return byml.dump(rows, ver) if changed else info


def gift_actor_swaps(gifts: dict[str, str]) -> dict[int, tuple[str, str]]:
    """{actor hash: (banc, item)} for the world gifts whose item changed (for
    `patch.write_mod(actor_swaps=...)`, which builds the wrappers)."""
    return {g.hash: (g.banc, gifts[g.location]) for g in _changed(gifts)
            if isinstance(g, WorldGift)}
