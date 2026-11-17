# Test batch 27: NPC gifts, batch 1 (spike)

Groundwork for shuffling the batch 1 NPC gifts (`docs/npc-gifts-research.md`). Built with `tools/make_npc_gift_batch.py <nup> <out> 27a..27f`, on the full skip. Leaving Link's house teleports you next to the gift (a new start position facing the NPC).

Every variant makes one gift give the **Boomerang**, the way the shuffle would:

- **The item parameter is renamed** wherever it appears. For a `Dm_SY_GetInEvent` call this is `ActorName`; for an `NpcCommon_HandOver_*` call it is `ReveiveItem` (the game's spelling).
- **Special grant entries are pointed at a generic one**, as with the Great Fairies:
  - Darunia's `GetInEvent_Goron` and Zelda's `GetInEvent_Zeldaletter` go to `GetInEvent_Demo_NotLookatObjectEntry`;
  - the rolling Goron's `GetInEvent_NotTurn_BombBag` goes to `GetInEvent_NotTurn`.
- **A world actor is swapped for a wrapper** (`Obj_Rando_Item_Boomerang`), as in Dungeon Rewards.

| Variant | Where | Gift patched | Start | Also checks |
|---|---|---|---|---|
| 27a | Hyrule Castle, by Malon (castle quest at Step01) | `Goto_HyruleCastle` event 149 | Weird Egg (not from Malon) | Does an egg from elsewhere hatch, and does Talon wake? |
| 27b | Goron City, by the rolling Goron | `Npc_Goron_006_Child` events 72, 73 and the bomb bag entry | Medium Bomb Bag, then the Small one | Does the Small bag lower the capacity (30 → 20)? |
| 27c | Goron City, in Darunia's room | `Dm_Goron_0030` event 128 | Fairy Ocarina, Saria's Song, Zelda's Lullaby | |
| 27d | Castle courtyard (quest at Step04) | `Dm_HrlCastle_0050` event 238 | Fairy Ocarina | |
| 27e | Kakariko, by Anju | `Minigame_CatchCucco` event 124 | | An `NpcCommon` hand-over |
| 27f | Lake Hylia, above Ruto's Letter | `Obj_Bottle_Letter` in `HyruleField_Child_Static` | Silver Scale | A world-actor wrapper |

The tunics are not in the batch. Their grants (`SageOfFire`, `SageOfWater`) use the generic `GetInEvent_NotTurn` entries, the same as Malon's in 27a.

## Results

- **27a, attempt 1:** carrying the egg without talking to Malon, it never hatched. Walking into the castle garden, the guards' catch scene looped (the animation cut and restarted); see `docs/TODO.md`.
- **27a, attempt 2:** after talking to Malon, the egg (from the start preset, not from her) hatched. The hatch is not an egg timer: Malon's talk moves the castle quest to `Step03`, and Navi's `Step03_01` schedule (`Goto_HyruleCastle_Step03_01_Npc_Navi`) starts `Step03_01_Npc_Navi_StepStart`, which runs `EggHatch` (remove the egg, give `Item_AlarmCucco`). That path does not check the egg, so talking to Malon may give the Cucco even without it (untested).

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch27a` (then `b`, ... `f`) to `load/0400486024DEC000/`, start a **new game** and leave the house.

## Check

- [ ] Each variant: do you appear next to the NPC? Do you get the Boomerang (message and item screen)? Any hang or black screen? ______
- [ ] 27a: does Malon give the Boomerang? Then, carrying the egg (walk around the field and the market; the castle stops the timer), does it hatch into the Cucco? Does Talon wake with it? ______
- [ ] 27b: after starting, what is the bomb capacity (Medium 30, Small 20)? Stop the Goron with a bomb: does he give the Boomerang? ______
- [ ] 27c: play Zelda's Lullaby at the door if it is closed, then Saria's Song to Darunia: does he dance and give the Boomerang? ______
- [ ] 27d: does Zelda give the Boomerang instead of her letter? ______
- [ ] 27e: catch the Cuccos: does Anju give the Boomerang instead of the bottle? ______
- [ ] 27f: dive to the letter: what does it look like, and does picking it up give the Boomerang? ______
