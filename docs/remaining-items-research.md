# What is left to resemble OoTR: research (2026-11-22)

The user asked for everything that is left, at once ("vamos con todo lo que falta ahora de golpe"). This file maps it. A test batch (33) answers the open questions, then one design and one plan cover it all.

## Scope: OoTR's default pool minus what the remake already moves

Already moving:
- the chests (key items and minor items) and the Gold Skulltulas (Tokensanity);
- the 12 songs;
- the Great Fairies;
- NPC gifts batches 1, 2 and 3a.

From OoTR's `locations.json`, not Master Quest, what is left out is below. OoTR's own default settings keep the cows, the frogs' song rupees, the shops, the scrubs that are not upgrades, pots, crates and the full adult trade shuffle off, so those stay out.

| Block | Locations | Grant |
|---|---|---|
| A. Trade and theatre | Kak Anju as Adult (Pocket Egg), DMT Biggoron (Biggoron Sword), Deku Theater Skull Mask and Mask of Truth (stick and nut capacity), Kak Granny Buy Blue Potion, ZR Magic Bean Salesman | NPC flows |
| B. Dungeon rewards | the 8 bosses and ToT Reward from Rauru | `Dm_Awake_*_Get` and the stone scenes |
| C. Freestanding Pieces of Heart | about 20 | actors in the maps |
| D. Upgrade scrubs | LW Deku Scrub Near Bridge (sticks), LW Deku Scrub Grotto Front (nuts), HF Deku Scrub Grotto (Piece of Heart) | the scrub's map actor |
| E. The 6 fixed key items | Jabu Boomerang, Dampe Race Hookshot, Ice Cavern Iron Boots, Shadow Hover Boots, Spirit Silver Gauntlets, Spirit Mirror Shield | chests with a story `GetEventName` |

## E. The six fixed chests

They are fixed because each has a story event (`needs_event_patch`). The Kokiri Sword's event handed over the sword itself (test batch 1), so these were kept fixed to be safe. The chests' own test (TestBatch2) never ran.

| Chest | `GetEventName` | What the event does |
|---|---|---|
| Spirit Mirror Shield (Colossus hand) | `SageOfSpirit_GetShield` | only `Dm_SY_Treasurebox` (the generic chest scene) |
| Shadow Hover Boots | `SageOfShdawo_GetHoverBoots` | only `Dm_SY_Treasurebox` |
| Spirit Silver Gauntlets (Colossus hand) | `SageOfSpirit_NaboorIsTakenAway` | Nabooru's scene (`Dm_DesertColossus_0030`), `SageOfSpirit` to `Step07`, then `Dm_SY_Treasurebox` |
| Dampe Race Hookshot | `MiniGame_DampeRace_OpenGoalTBox` | `Dm_SY_Treasurebox`, and sets `Minigame_DampeRace_TreasureBoxState` (`OpenedHookShot` / `OpenedHeartPiece` / rupees) |
| Ice Cavern Iron Boots | `SageOfWater_MelodyGet_Water` | the Serenade of Water (Sheik) |
| Jabu Boomerang | `InsideJabuJabuBelly_TreasureBoxWithRuto09` | the chest with Ruto |

No flow grants any of these six items by value, so no event hands the original item over the way the sword's did. **Likely:** they move like any chest, and their events keep running. Test batch 33 checks each one with another item.

## B. Dungeon rewards

- **Grants:** each one is a `GetPouchContentByActorName` `ActorName`, the grant the song scenes use and that batch 23 proved renamable:
  - medallions: `Dm_Awake_<Forest|Fire|Water|Shadow|Spirit>_Get` event 22;
  - Light Medallion: `Dm_SageRoom_0005` 182;
  - stones: `Dm_Kokiri_0130` 0 (Emerald), `Dm_DeathMtTrail_0025` 9 (Ruby), `Dm_ZoraFountain_0030` 0 (Sapphire; Jabu's `Dm_InsideJabu_Jabu_0030` 79 is Ruto's display).
- **No flow and no map asks for a medallion or a stone** (no query, no `IsGet.Item_Medal_*`/`Item_Stone_*`). The story follows the bosses' flags.
- **Logic question:** the game opens the Door of Time and the bridge on the bosses beaten, while OoTR's logic asks for the items. Fully mixed rewards can make the logic looser than the game. For example, a medallion at Gohma lets the logic open the bridge without Morpha. A safe model shuffles the stones among the 3 child bosses and the medallions among the 6 adult bosses and Rauru. To decide in the design.

## C. Freestanding Pieces of Heart

- **Map actors:** 15 `Obj_Heart_Piece` actors, each with the same hash in the child and adult versions of its map:
  - DMC 2, DMT 1, Colossus 1, Graveyard 1, Hyrule Field 2 (Lake Hylia and Lon Lon are in that map), Kakariko 2, ZF 2, ZR 2;
  - `Obj_GerudoValley_Heart_Piece` (GV waterfall).
- **Not found as actors:** the pot, crate and grotto ones (GC Pot, GV Crate, HF Tektite Grotto, Ice Cavern…).
- **How:** a world gift (wrapper actor, proven for key items in batch 1). It needs a mapping from hash to OoTR location, and the wrapper swap in both era maps.

## D. Upgrade scrubs

- **The item is in the map:** each scrub actor's item is `ScrubBusiness_ShopItemActorName0`. Changing it is a map edit, like a chest's drop.
  - `Item_StickBag_Medium`: Lost Woods near the bridge, and Kokiri Forest;
  - `Item_NutBag_Medium`: Lost Woods;
  - `Obj_Heart_Piece`: the Hyrule Field grotto, and the Crater (child).
- **Dream zone:** the remake's `BossRushIntervalRoom` scrubs sell key items (remake content, out of scope).

## A. Trade and theatre (grants found)

| Location | Grant |
|---|---|
| Kak Anju as Adult | `Npc_Hylia_049_Adult` 223, `ReveiveItem` `Item_PocketEgg` (NpcCommon) |
| DMT Biggoron | `Npc_Goron_Biggoron_Adult` 95, `GetInEventItemSwordBiggoron` (special entry) |
| Kak Granny Buy Blue Potion | `Npc_Hylia_053_Adult` 152, `GetInEventInBottle_BlueBottleShop` (fills a bottle) |
| ZR Magic Bean Salesman | `SimpleShop` 63, literal `Item_MagicBean` (sells ten) |
| Deku Theater masks | to find |

The other trade steps stay vanilla (OoTR's default `adult_trade_shuffle` is off). The Pocket Egg's hatch (`SubEvent_GetSwordBigGoron` 132) is an engine timer, like the Weird Egg's.
