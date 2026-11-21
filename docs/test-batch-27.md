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
- **28b:** shown Ruto's Letter from the start preset (not from the lake), King Zora moved aside. **Ruto's Letter works from anywhere.**
- **28c:** an adult with the Silver Gauntlets and no Goron's Bracelet could throw bombs and lift bomb flowers. **Any strength level works**, so the logic's level model (the bracelet is level 1, Silver level 2) is right.

**Batch 28: everything works. No gift stays fixed (`FIXED_GIFTS` is empty).**

## Batch 29 (NPC gifts batch 2: upgrades out of order, a Gold Skulltula reward, a minigame)

Built with the same tool (`29a`, `29a2`, `29b`, `29c`, `29d`); Spanish guide `local/test-batch-29.md`.

- **29a:** Zora's Domain, child, given the Golden Scale then the Silver one, the Giant's Wallet (`Item_Wallet_Large`) then the Adult's (`Item_Wallet_Medium`), and 500 rupees. The menu kept the bigger ones: the Golden Scale and the Giant's Wallet, with 500/1000 rupees. **A smaller wallet never lowers the capacity.** But the Lake Hylia lab dive did not reach the bottom.
- **29a2 (control):** the Golden Scale alone, in the lab: the dive reached the bottom. **A Silver Scale received after the Golden one lowers the dive depth to silver's, though the menu still shows Gold.** The shuffle must never let Link get the Silver Scale after the Golden one.
- **29b:** Kakariko, child, given the biggest bullet bag (`Item_BulletBag_Large`) before the Slingshot: the Slingshot held 50 seeds. **A bag received before its weapon is kept.**
- **29c:** the Gold Skulltula house, child, with 10 tokens given by the start preset (`Dm_SY_GetInEvent:GetInEvent` with `Obj_Token_Gold`): the 10-token reward gave the Boomerang. **The house's by-reference `TakenRewardActor` can be renamed**, and the reward was handed over, so the tokens from `GetInEvent` counted.
- **29d:** Zora's Domain, child: winning the diving game gave the Boomerang. **A minigame's `GetInEvent_NotTurn_NotNpc` grant can be renamed.**

**Batch 29: every grant works. The only problem is the Silver Scale after the Golden one.**

## Batch 30 (the gate of NPC gifts batch 2)

Built with the same tool (`30a`..`30e`, `30c2`); Spanish guide `local/test-batch-30.md`.

- **30a:** Talon's Cucco game, first win (event 262, `ReveiveItem`): gave the Boomerang. **Talon's prize moves.**
- **30b:** a Bottle with Milk from the start preset: Link had it and could drink it. **Milk works from elsewhere.**
- **30c:** Dampe: the Sun's Song made night, but day came back, so the tour could not be played. The user suspects time does not run before Zelda's meeting. **30c2** completes the castle quest (`Goto_HyruleCastle` through `Complete`).
- **30d:** LW Target: the scene's animation hands over the bullet bag, then Link holds up the Boomerang, which he gets. **The site moves** (cosmetic: the bag shows first, as the non-goal "item models" allows).
- **30e:** the biggest quiver, then the medium one, then the Bow: 50 arrows. **A smaller quiver never lowers the capacity.** No quiver rule is needed.
- **30c2:** with the castle quest complete, the Sun's Song still turned night and day came back at once. Dampe's tour stays unplayed. **Accepted without an in-game test** (user's call, 2026-11-21): Dampe's prize moves, with his entry pointed at `GetInEvent_NotTurn_NotNpc` (the diving game's, 29d). To check in a later playthrough; see `docs/TODO.md`.

**Batch 30: every site moves (`FIXED_GIFTS` stays empty). No quiver rule is needed.**

## Batch 31 (NPC gifts batch 3a: OoTR's ocarinas, merchants and the 100-token reward)

Built with the same tool (`31a`..`31f`); Spanish guide `local/test-batch-31.md`. Research in `docs/npc-gifts-research.md` ("Batch 3a"). Every variant makes the gift give the Boomerang.

- **31a:** Saria's ocarina on the bridge (`Dm_Kokiri_0155`, from `Goto_HyruleCastle:KokiriForest_ArriveLostWood`): the grant is an `EventTriggerAddOrRemovePouchContent` action (`Actor`) plus `GetPouchContent:DisplayGetByActorName` (`ActorName`); both renamed. The preset clears the farewell flags every other preset sets. Does the scene play, with Saria there, and give the Boomerang?
- **31b:** the Ocarina of Time at the moat (`Dm_MelodyGet_Time`, from `DoorOfTime:DoorOfTime_GetOcarinaOfTime`), the castle quest complete and `DoorOfTime` at `Step03`: the same two grants renamed (event 106 `Actor`, 255 `ActorName`). The Song of Time (event 93) stays. Does the scene start and give the Boomerang and the song?
- **31c:** the Ocarina of Time, then the Fairy Ocarina: which one does the menu show, and can Link play?
- **31d:** Medigoron (`Npc_Goron_Medigoron_Adult` event 6, `SimpleShop:SimpleShopRoot_Npc_Goron_Medigoron_Adult`, by-reference `ActorName` `Shop_Sword_Giant`; his own grant `GetInEventItemSwordMedigoron`, `SimpleShop` event 112, points at `GetInEvent_NotTurn`). He only stops selling when the Giant's Knife is in the pouch: does he sell the Boomerang again?
- **31e:** the carpet salesman (`Npc_Hylia_044_Adult` event 0, `SimpleShop:SimpleShopRoot`, `ActorName` `Shop_BombchuBundle_01`, handed over by `NpcCommon_HandOver_NpcToPlayer_NoTurn_NoWaitAS`). His sale has no sold-out check at all: does he sell it again?
- **31f:** the 100-token reward (`GatheringTokenGold` event 250 `TakenRewardActor`, entry `TakenReward_Common_Event_200Rupee`, and event 573's literal `ActorName`), with the count set directly (`PouchData.Item_Token_Gold.StockNum` = 100).
