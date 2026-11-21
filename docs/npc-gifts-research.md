# NPC gifts in the pool: research notes (2026-11-15, completed 2026-11-17)

OoTR always shuffles about 45 NPC gifts. In this randomizer none moves yet. The user approved doing them in batches, each with a teleport test batch and always on with "Any chest", as OoTR does:

1. **Batch 1:** one-time gifts that give progress items. On 2026-11-17 the user chose to include Zelda's Letter, the Weird Egg and the two tunics.
2. **Batch 2:** repeatable minigames: the galleries, bowling, diving, fishing, the frogs and the lab.
3. **Batch 3:** OoTR's optional settings (the old plan `docs/superpowers/plans/2026-11-10-gifts-phase-b.md`) and the trade sequence.

The old phase B plan predates the synthetic sites, the patches on top of the full skip and value lookups (it uses event indices). Reuse its data, not its tasks.

Method:

- Every flow event that hands over an `Item_*`/`Obj_*`/`TBox_*` actor (`Dm_SY_GetInEvent:*`, `GetPouchContent:*`, `PouchSystemActor.*`), listed from the game's flows.
- Every `NpcCommon:NpcCommon_HandOver_NpcToPlayer_NoDisplay*` call. Its `ReveiveItem` parameter (the game's spelling) is the item; `NpcCommon` passes it on to `Dm_SY_GetInEvent`.
- Paths to each grant traced with the real case values (0 is true).

**Status (2026-11-20):** batch 1 is built (design `docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md`, `randomizer/gifts.py`). Test batches 27 and 28 answered every open question below (`docs/test-batch-27.md`).

## Batch 1: where each gift is

| OoTR location | Vanilla item | Remake grant |
|---|---|---|
| GC Darunias Joy | Goron's Bracelet | `Dm_Goron_0030` event 128, `Dm_SY_GetInEvent:GetInEvent_Goron` `Item_Gauntlet_Goron` (a special entry) |
| HC Zeldas Letter | Zelda's Letter | `Dm_HrlCastle_0050` event 238, `GetInEvent_Zeldaletter` `Item_ZeldaLetter` (a special entry) |
| HC Malon Egg | Weird Egg | `Goto_HyruleCastle` event 149, `GetInEvent_NotTurn` `Item_WeirdEgg` |
| LW Skull Kid | Piece of Heart | `Npc_SkullKid_Child` and `Npc_SkullKid_Child_02`, `GetInEvent_NotTurn_NotNpc` `Obj_Heart_Piece` |
| ToT Light Arrows Cutscene | Light Arrows | `Dm_TimeTemple_0130`, `GetPouchContent:GetPouchContentByActorName` `Item_Arrow_Light` |
| GC Rolling Goron as Child | Bomb Bag | `Npc_Goron_006_Child` events 72 and 73, `NpcCommon_HandOver_NpcToPlayer_NoDisplay_BombBag` with `Item_BombBag_Medium` or `Item_BombBag_Large` (a bigger bag than the one Link has) |
| GC Rolling Goron as Adult | Goron Tunic | `SageOfFire` event 177, `GetInEvent_NotTurn` `Obj_Armor_Goron`, given by `Npc_Goron_DaruniaJr_Adult` (the rolling Goron as an adult) |
| ZD King Zora Thawed | Zora Tunic | `SageOfWater` event 252, `GetInEvent_NotTurn_PosCamera` `Obj_Armor_Zora`, given by `Npc_Zora_KingZora_adult` (entry `KingZora_IsMelted_Ice`) |
| Kak Anju as Child | Bottle | `Minigame_CatchCucco` event 124, `NpcCommon_HandOver_NpcToPlayer_NoDisplay` `Item_Bottle` (event 125 gives a red rupee on later rounds) |
| Market Lost Dog | Piece of Heart | `SubEvent_FindRichard` event 35, `NpcCommon_HandOver_NpcToPlayer_NoDisplay` `Obj_Heart_Piece` (event 34 gives a blue rupee) |
| Kak Man on Roof | Piece of Heart | `Npc_Hylia_001_Adult` event 14, `GetInEvent` `Obj_Heart_Piece`. Only the adult gives it; `Npc_Hylia_001_Child` has no grant |
| Market 10 Big Poes | Bottle | `Npc_Hylia_048_BottleShop`, `GetInEvent_Poeshop` `Item_Bottle` |
| LH Sun | Fire Arrows | **Not a flow grant:** an `Obj_Arrow_Fire` actor in `HyruleField_Adult_Static` (hash 4598657944866228526), revealed by `GetFireArrow_FireArrowAppear` |
| LH Underwater Item | Ruto's Letter | **Not a flow grant:** an `Obj_Bottle_Letter` actor in `HyruleField_Child_Static` (hash 474136620438465634) |

`Npc_Hylia_045_Child` (the Lake Hylia scientist, `HyruleField_Child_Static`) gives a Piece of Heart for the dive. That is batch 2.

## What the flows check

- **Nothing checks its own reward to decide whether to give it.** No batch 1 flow reads `IsGet.<its item>` before its grant, unlike the Great Fairies. The only `IsGet` reads of these items are elsewhere: the castle soldier's dialogue (`Npc_Hylia_Soldier_009_Child`, `IsGet.Item_WeirdEgg`) and the Deku scrubs' stock (`IsGet.Item_Bottle`, `Item_Arrow_Fire`, `Item_Arrow_Light`).
- **The tunics:** `SageOfFire` and `SageOfWater` ask `IsExistInPouch Armor_Adult_Goron` / `Armor_Adult_Zora`. The grant can be reached with either answer (checked by removing each case), so owning the tunic already does not block the gift. The King Zora grant is also reachable whether `SageOfWater_GetWaterSerenade` is set or not.
- **Zelda's Letter is removed only when shown:** `Npc_Hylia_Soldier_003` (the Kakariko gate guard) removes it in its `ShowItem_ZeldaLetter` entry, after Link shows it. This needs the letter, wherever it came from. That entry also opens the gate (`Npc_Hylia_Soldier_003_GateOpen`), which matches OoTR's rule for the gate.
- **The egg hatches on an engine timer:** the `EggHatch` entry of `Goto_HyruleCastle` (event 200) removes `Item_WeirdEgg` (event 24) and gives `Item_AlarmCucco` (event 198, `GetInEvent_EggHatche`). No flow calls this entry. The timer is engine code: `GameDataList` has `EggHatch` flags, `Logic/HyruleCastle_HatchTimerStopAreaPrefab` stops it in some castle areas (`HyruleCastle_StopWeirdEggHatchTimer`), and challenges can set `IsStopEggHatchTimer`. Whether it runs for an egg found elsewhere, or before Malon's scene, is **untested**.
- **Talon wakes for the Cucco itself:** `Goto_HyruleCastle` event 41 asks `IsExistInPouch Item_AlarmCucco`.

## Open, for the test batch

- **The egg from elsewhere:** does it hatch, and does Talon wake?
- **The bomb bags:** the rolling Goron gives a bigger bag than Link's. As a site it would give one fixed item. And as a moving item, a chest could give `Item_BombBag_Medium` before the Small one, or the Small one after it. Whether a smaller bag lowers the capacity is **untested**, as it was for the magic before batch 26.
- **Special grant entries:** `GetInEvent_Goron` and `GetInEvent_Zeldaletter` add their own animation. For another item, point them at a generic entry, as with the Great Fairies.
- **The world actors** (Fire Arrows, Ruto's Letter) are swapped like the boss Heart Containers: the actor's `Gyaml` becomes a wrapper, as Dungeon Rewards does.

## Not in batch 1

- **The ocarinas** (Saria's `Dm_Kokiri_0155`, the Ocarina of Time in `Dm_MelodyGet_Time`): they are an OoTR option (Shuffle Ocarinas, off by default). Batch 3.
- **The Gold Skulltula rewards** (Kakariko house: wallets, Stone of Agony, ...): OoTR always shuffles them. They are counter rewards like the minigames. Batch 2.
- **Biggoron and the trade items:** batch 3.

## Batch 2: where each minigame and reward is (2026-11-20)

Built: design `docs/superpowers/specs/2026-11-21-npc-gifts-batch-2-design.md`, test batches 29 and 30 (`docs/test-batch-27.md`). Talon's first win is event 262 only; event 261 (`GetInEventInBottle`) is the repeat refill.

Same method as batch 1. Every grant uses one of the patterns batch 1 already patches. The item is either a `Dm_SY_GetInEvent` `ActorName`, an `NpcCommon` hand-over `ReveiveItem`, or a by-reference parameter: the Gold Skulltula house passes `TakenRewardActor` to its own `TakenReward_Common_Event` entry, as the rolling Goron passes `ReveiveItem`.

| OoTR location | Vanilla item | Remake grant |
|---|---|---|
| Kak 10 Gold Skulltula Reward | Progressive Wallet | `GatheringTokenGold` event 245, `TakenRewardActor` `Item_Wallet_Medium` |
| Kak 20 Gold Skulltula Reward | Stone of Agony | event 246, `Item_AgonyStone` |
| Kak 30 Gold Skulltula Reward | Progressive Wallet | event 247, `Item_Wallet_Large` |
| Kak 40 Gold Skulltula Reward | Bombchus (10) | event 248, `Item_BombchuBundle_Large` |
| Kak 50 Gold Skulltula Reward | Piece of Heart | event 249, `Obj_Heart_Piece` (event 250, 100 tokens: 200 rupees, not an OoTR location) |
| Market Shooting Gallery Reward | Slingshot upgrade | `MiniGame_HitTarget` events 291/292, `ReveiveItem` `Item_BulletBag_Large`/`_Medium` (a bigger bag than Link's) |
| Kak Shooting Gallery Reward | Bow upgrade | `MiniGame_HitTarget` events 293/294, `Item_Quiver_Large`/`_Medium` |
| LW Target in Woods | Slingshot upgrade | `Dm_LostWood_0040` events 84/85, `ActorName` `Item_BulletBag_Large`/`_Medium` |
| Market Bombchu Bowling First Prize | Bomb Bag | `MiniGame_BombchuBowling` events 297/298, `Item_BombBag_Medium`/`_Large` |
| Market Bombchu Bowling Second Prize | Piece of Heart | event 296, `Obj_Heart_Piece` |
| LH Child Fishing | Piece of Heart | `MiniGame_Fishing` events 482 (`NpcCommon`) and 489 (`GetInEvent_NotTurn`), `Obj_Heart_Piece` |
| LH Adult Fishing | Golden Scale | events 483 and 490, `Item_Scale_Gold` |
| LH Lab Dive | Piece of Heart | `Npc_Hylia_045_Child` event 55, `ReveiveItem` `Obj_Heart_Piece` |
| ZD Diving Minigame | Silver Scale | `MiniGame_Diving` event 316, `Item_Scale_Silver` (event 315: red rupee on later rounds) |
| LW Ocarina Memory Game | Piece of Heart | `Npc_SkullKid_Child_02` event 203, `Obj_Heart_Piece` (events 201, 202, 204: rupees) |
| ZR Frogs Ocarina Game | Piece of Heart | `MiniGame_FrogTenors` events 71/91, the `MushiToriGame` entry's `ActorName` (the remake's butterfly game; by reference, then event 246) |
| ZR Frogs in the Rain | Piece of Heart | `MiniGame_FrogTenors` event 247, `Obj_Heart_Piece` (on the Song of Storms path; corrected 2026-11-21) |
| GF HBA 1000 Points | Piece of Heart | `Minigame_HorsebackArchery` event 313, `Obj_Heart_Piece` |
| GF HBA 1500 Points | Bow upgrade | events 311/312, `Item_Quiver_Large`/`_Medium` |
| Graveyard Dampe Gravedigging Tour | Piece of Heart | `Npc_Hylia_Dampe_001` event 602, `Obj_Heart_Piece`; special entry `GetInEvent_NotTurn_NotNpc_Dampe` |
| LLR Talons Chickens | Bottle with Milk | `Minigame_FindOutCucco` events 261 (`GetInEventInBottle`) and 262 (`NpcCommon`), `Item_Bottle_Milk` |

Not in batch 2:
- the Treasure Chest Game (its chests and keys);
- the Deku Theater masks (trade, batch 3);
- the repeat prizes (rupees after the first win).

### Open, for the design and a test batch

- **Upgrades come in sizes:** wallets, bullet bags, quivers, bomb bags and scales. The remake hands over "a bigger one than Link's", picking the event by his current size. As fill items these become OoTR's progressive items: `Progressive Wallet`, `Progressive Scale`, the Slingshot and Bow upgrades, and `Bomb Bag`. A chest gives one fixed size.
  - Batch 27b showed that a smaller bomb bag never lowers the capacity.
  - Still to check: a Golden Scale before the Silver one (dive depth), a Large Wallet before the Medium one, and a quiver or bullet bag upgrade before the Bow or Slingshot.
- **Stone of Agony** (`Item_AgonyStone`) and the wallets are new item types for the fill.
- **Two grants for one prize** (fishing 482/489, Talon 261/262): rename both, as the full skip's copies are.

## Batch 3a: OoTR's optional switches (2026-11-21)

| OoTR location | OoTR setting | Grant |
|---|---|---|
| LW Gift from Saria | Shuffle Ocarinas | `Dm_Kokiri_0155` event 51 (`EventTriggerAddOrRemovePouchContent`, `Actor`) and 52 (`GetPouchContent:DisplayGetByActorName`, `ActorName`), `Item_Ocarina_Fairy`. Started by `Goto_HyruleCastle:KokiriForest_ArriveLostWood` (the bridge) |
| HF Ocarina of Time Item | Shuffle Ocarinas | `Dm_MelodyGet_Time` event 106 (action, `Actor`) and 255 (display, `ActorName`), `Item_Ocarina_Time`. Event 93 is the Song of Time (a song site). Started by `DoorOfTime:DoorOfTime_GetOcarinaOfTime` (the moat) |
| Hideout Gerudo Membership Card | Shuffle Gerudo Card | `Dm_Gerudo_0025` event 120, `GetInEvent_NotLookatObjectTurnOff` `Item_Token_Gerudo`. Started by `SageOfSpirit:Meet_FourCarpenter_ClearEvent` |
| GC Medigoron | Shuffle Expensive Merchants | `Npc_Goron_Medigoron_Adult` event 6, `SimpleShop:SimpleShopRoot_Npc_Goron_Medigoron_Adult`, by-reference `ActorName` `Shop_Sword_Giant` (200 rupees, as in OoTR); `SimpleShop` event 112 grants it through its own `GetInEventItemSwordMedigoron` |
| Wasteland Bombchu Salesman | Shuffle Expensive Merchants | `Npc_Hylia_044_Adult` event 0, `SimpleShop:SimpleShopRoot`, `ActorName` `Shop_BombchuBundle_01` (90 rupees), handed over by `SimpleShop` event 39 (`NpcCommon_HandOver_NpcToPlayer_NoTurn_NoWaitAS`, `ReceiveItem` by reference) |
| Kak 100 Gold Skulltula Reward | (always in OoTR's pool) | `GatheringTokenGold` event 250 (`TakenRewardActor` `Obj_Rupee_Gold`, entry `TakenReward_Common_Event_200Rupee`) and event 573 (literal `ActorName` `Obj_Rupee_Gold`) |

Findings:

- **The shuffle skip keeps every grant:** the full skip rewrites `Dm_Kokiri_0155`, `Dm_MelodyGet_Time` and `Dm_Gerudo_0025`, and all the grants above are still in its copies.
- **Nothing checks the Gerudo Card.** No flow tests `Item_Token_Gerudo`. The guards, the gate and the Training Ground follow the quest: `SageOfSpirit_IsAfter_Step01_Exp`/`Step03_Exp` (for example `Npc_Gerudo_006`, `Npc_Gerudo_007`, `Npc_Gerudo_013`). So in the remake the card's effect comes from freeing the carpenters, not from the item. OoTR's rules that need `Gerudo_Membership_Card` must need the rescue instead.
- **Nothing checks which ocarina Link has**, apart from the Kokiri's dialogue (`Npc_Kokiri_005_Child`, `Npc_Kokiri_007_Child`: `Item_Ocarina_Fairy`). The Door of Time checks the stones (`DoorOfTime_CheckStoneNum`). OoTR's `stones_oot_sot` asks for both ocarinas (`(Ocarina, 2)`), which is stricter than the game: safe.
- **The merchants never sell out by item:** Medigoron stops when `Weapon_Sword_Giant` is in the pouch; the carpet salesman has no check at all. A moved item may be sold again (test batch 31d and 31e).
- **Left for batch 3b:** Granny's Blue Potion (`Npc_Hylia_053_Adult`, `GetInEventInBottle_BlueBottleShop`: a bottle refill, and OoTR ties it to the Odd Mushroom) and the bean seller (`Npc_Hylia_047_Child`: ten sales at rising prices, granted by `SimpleShop` event 63's literal `Item_MagicBean`, with no one-time gate).
