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
