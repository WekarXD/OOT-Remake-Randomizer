# NPC gifts in the pool: research notes (2026-11-15)

OoTR always shuffles about 45 NPC gifts. In this randomizer none moves yet. The user approved doing them in batches, each with a teleport test batch and always on with "Any chest", as OoTR does:

1. **Batch 1:** one-time gifts that give progress items.
2. **Batch 2:** repeatable minigames: the galleries, bowling, diving, fishing, the frogs and the lab.
3. **Batch 3:** OoTR's optional settings (the old plan `docs/superpowers/plans/2026-11-10-gifts-phase-b.md`) and the trade sequence.

The old phase B plan predates the synthetic sites, the patches on top of the full skip and value lookups (it uses event indices). Reuse its data, not its tasks.

Method: every flow event that hands over an `Item_*`/`Obj_*`/`TBox_*` actor (`Dm_SY_GetInEvent:*`, `GetPouchContent:*`, `PouchSystemActor.*`), listed from the game's flows.

## Batch 1: where each gift is

| OoTR location | Vanilla item | Remake grant |
|---|---|---|
| GC Darunias Joy | Goron's Bracelet | `Dm_Goron_0030` `Dm_SY_GetInEvent:GetInEvent_Goron` `Item_Gauntlet_Goron` |
| HC Zeldas Letter | Zelda's Letter | `Dm_HrlCastle_0050` `GetInEvent_Zeldaletter` `Item_ZeldaLetter` (`Npc_Hylia_Soldier_003` removes it: `EventTriggerAddOrRemovePouchContent`) |
| HC Malon Egg | Weird Egg | `Goto_HyruleCastle` `GetInEvent_NotTurn` `Item_WeirdEgg` (also an `AddOrRemovePouchContent` at event 24) |
| LW Skull Kid | Piece of Heart | `Npc_SkullKid_Child` and `Npc_SkullKid_Child_02`, `GetInEvent_NotTurn_NotNpc` `Obj_Heart_Piece` |
| ToT Light Arrows Cutscene | Light Arrows | `Dm_TimeTemple_0130` `GetPouchContent:GetPouchContentByActorName` `Item_Arrow_Light` (and `SubEvent_AllBossBattle`) |
| GC Rolling Goron as Adult | Goron Tunic | **In the remake, `SageOfFire` gives it** (`GetInEvent_NotTurn` `Obj_Armor_Goron`) |
| ZD King Zora Thawed | Zora Tunic | **In the remake, `SageOfWater` gives it** (`Obj_Armor_Zora`); a Zora shop sells it too (`Npc_Zora_011_Shop_Adult`) |
| Market 10 Big Poes | Bottle | `Npc_Hylia_048_BottleShop` `GetInEvent_Poeshop` `Item_Bottle` |
| LH Sun | Fire Arrows | **Not a flow grant:** an `Obj_Arrow_Fire` actor in `HyruleField_Adult_Static`, revealed by `GetFireArrow_FireArrowAppear` |
| LH Underwater Item | Ruto's Letter | **Not a flow grant:** an `Obj_Bottle_Letter` actor in `HyruleField_Child_Static` |

## Open

- **Not found in the flows yet:**
  - GC Rolling Goron as Child (Bomb Bag): no `Item_BombBag_*` grant outside the scrubs;
  - Kak Anju as Child (Bottle);
  - Market Lost Dog and Kak Man on Roof (Pieces of Heart): `Npc_Hylia_001_Adult` gives one, to be identified;
  - DMT Biggoron (`Npc_Goron_Biggoron_Adult`, part of the trade sequence).

  Their grants may use another parameter name, or an `Item_*` value outside the pattern searched.
- **Gifts that are world actors** (Fire Arrows, Ruto's Letter) are like the boss Heart Containers: swap the actor's `Gyaml` for a wrapper, as Dungeon Rewards does.
- **Shared and removed items:** the letter and the egg are also removed by later scenes (`AddOrRemovePouchContent`). If the gift changes, those removals must not take away the new item.
- **The tunics** come from story scenes in the remake (sage flows), not from OoTR's NPCs. Decide whether to map them to OoTR's locations.
