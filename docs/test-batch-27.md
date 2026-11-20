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
- **27a, attempt 2:** after talking to Malon, the egg (from the start preset, not from her) hatched. The hatch is not an egg timer: Malon's talk moves the castle quest to `Step03`, and Navi's `Step03_01` schedule (`Goto_HyruleCastle_Step03_01_Npc_Navi`) starts `Step03_01_Npc_Navi_StepStart`, which runs `EggHatch` (remove the egg, give `Item_AlarmCucco`). That path does not check the egg, so talking to Malon may give the Cucco even without it (untested). Talon woke up when shown the Cucco. **27a works.**
- **27b, attempt 1:** the capacity stayed at 30 after the Small Bomb Bag: a smaller bag does not lower it. Link could not use bombs without the Goron's Bracelet, so attempt 2 also starts with it.
- **27b, attempt 2:** stopped with a bomb, the rolling Goron gave the Boomerang (his bomb bag entry pointed at `GetInEvent_NotTurn`). **27b works.**
- **27c:** Link appeared in front of Darunia; Saria's Song made him give the Boomerang (`GetInEvent_Goron` pointed at `GetInEvent_Demo_NotLookatObjectEntry`). **27c works.**
- **27d, attempt 1:** Zelda gave nothing (no Boomerang in the inventory), though her meeting played: Impa then taught the Lullaby. On the full skip, `Dm_HrlCastle_0050` runs `EntryPoint0` straight to the grant (event 238, after `Item_ZeldaLetter` joins the event), so the grant is on the played path. As with Din's fountain (batch 26e), the skip's rewrite may lose the item. Three variants tell the causes apart: **27d2** without the full skip; **27d3** on the skip but keeping Zelda's own `GetInEvent_Zeldaletter` entry; **27d4** on the skip with her scene untouched (does it give the letter?).
- **27d2, attempt 1:** without the skip, still nothing. **Cause:** the generic grant calls `ActionGuide`, and `Dm_HrlCastle_0050`'s `SubFlowList` in `RSDB/GameAnalyzedEventInfo` lacks it (Darunia's and the fountains' lists have it, which is why 27c and batch 26 worked). The game ignores a call to a flow missing from the list. The tool now adds the new entry's closure to the event's list; 27d and 27d2 are rebuilt (attempt 2).
- **27d, attempt 2:** on the full skip, Zelda gave the Boomerang. **27d works**; 27d2-27d4 are not needed. Rule for the implementation: whenever a grant's entry changes, the event's `SubFlowList` must include the new entry's closure.
- **27e:** Anju gave the Boomerang for the Cuccos (`ReveiveItem` of an `NpcCommon` hand-over renamed). **27e works.**
- **27f:** at the bottom of the lake, Ruto's Letter was a floating Boomerang with the Gold Skulltula token's glow (as every wrapper), and picking it up gave the Boomerang. **27f works.**

**Every variant works.**

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

## Batch 28 (the plan's gate)

Built with the same tool (`28a`, `28a2`, `28b`, `28c`); see `docs/superpowers/plans/2026-11-20-npc-gifts-batch-1.md`, Task 1.

- **28a, attempt 1:** the Hookshot wrapper was not on the island, and Link had the Bow but no arrows. The Fire Arrows quest (`SubEvent_GetFireArrow`, steps `Ready`, `Step01`, `Step02`, `Step03`) depends on `SageOfWater_IsAfter_Step08_Exp`, and shooting the sun (`FireArrow_Appear`, then `Dm_LakeHrl_0030`) moves it to `Step03`. Attempt 2 completes the Water Temple quest, puts the Fire Arrows quest at `Step02` and gives a medium quiver. **28a2** puts it at `Step03` (the arrows should already be there).
- **28a, attempt 2:** shooting the sun made the Hookshot wrapper appear on the island. Link could not reach it: the sun is shot from the other island, and the lake stayed empty (the start preset completes the Water Temple quest, but the lake's water level is set elsewhere). In a real game the lake is full after the Water Temple.
- **28a2:** the Hookshot wrapper was on the island; picking it up gave a working Hookshot. **The Fire Arrows site works as a wrapper** (it appears with the sun, as the arrows do).
