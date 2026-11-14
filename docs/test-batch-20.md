# Test batch 20: Impa and Saria swap songs

First step of "Shuffle Songs" (OoTR's option: Song Locations, then Anywhere, then Dungeon Rewards). Each song scene (`Dm_MelodyGet_*`) has a **lesson**, the `MelodyType` number that picks the notes you repeat, and a **grant**, the `Item_Melody_*` you receive. This batch changes both in two scenes.

| Scene | Normally | In this batch |
|---|---|---|
| Impa, at Hyrule Castle (`Dm_MelodyGet_Zelda`) | Teaches and gives Zelda's Lullaby | Teaches and gives **Saria's Song** |
| Saria, at the Sacred Forest Meadow (`Dm_MelodyGet_Saria`) | Teaches and gives Saria's Song | Teaches and gives **Zelda's Lullaby** |

The key question: some scenes check whether you already own their song. After Impa, you will **already have Saria's Song** before meeting Saria. Does her scene still play?

The rest of the game is vanilla.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch20` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and walk out of Link's house. You get the **Fairy Ocarina** and are teleported to the **Hyrule Castle courtyard**, next to Impa, with Zelda further ahead (start preset, see batch 21). The castle quest is moved to its last step (Step04), which Zelda's meeting needs.
- [ ] The batch also has the **full cutscene skip**, as a seed with "Skip cutscenes" would.
- [ ] Walk up to Zelda (the meeting triggers on approach, it is not a normal talk), then go to Impa. If Impa reacts before Zelda, note it.

Attempt 1 (2026-11-14): Zelda's meeting would not start. Cause: it only triggers with the castle quest at Step04, which the teleport skipped. Rebuilt for attempt 2 with the quest steps and the full skip. The lesson's second half (`LearningOcarinaFollowExample`, the notes you repeat) is now swapped too; attempt 1 only swapped the notes you are shown.

Attempt 2 (2026-11-14): Zelda's meeting worked. **Impa teaches and gives Saria's Song**, and it plays correctly. Going back from Hyrule Field to the forest left a black screen: the bridge triggers Saria's farewell (`KokiriForest_ArriveLostWood`), which the teleport had skipped, and Saria is not there. Presets now mark that farewell as played (`FOREST_EXIT_FLAGS`). Rebuilt for attempt 3, which only needs the Saria half.

Attempt 3 (2026-11-14): Impa gives Saria's Song and the scene ends cleanly, but there are **no notes to repeat**. Expected: the full skip drops the ocarina lessons (`subflows_drop` has `Dm_SY_Ocarina/LearningOcarina*`), so the note swap only shows without the skip. The song plays; Darunia was not reachable (needs Zelda's Lullaby). Going back into the forest, an **invisible wall** by the exit guard (`Npc_Kokiri_007_Child`) blocked the way: a `FldObj_AirWall_Player_GenerateNavMesh` whose Presence is `KokiriForest_Npc_Kokiri_007_Child_Blocker_00`, which he clears after the Deku Tree. Presets now set it to false (`FOREST_EXIT_FLAGS`, 156e078). Rebuilt for attempt 4 (Saria half only).
- [ ] Afterwards, to reach Saria: go back to Kokiri Forest from Hyrule Field, then Lost Woods → Sacred Forest Meadow.

## Check

Impa:

- [x] Do the notes you are asked to repeat belong to **Saria's Song** (↓ → ← ↓ → ←)? No notes: the full skip drops the lesson.
- [x] Do you end up with Saria's Song in the song list, and **not** Zelda's Lullaby? Yes.
- [x] Does the scene end cleanly, with no hang? Yes.

With Saria's Song from Impa:

- [x] Can you play it? Does it work where it should (Saria on the ocarina, Darunia)? Yes, it works with Darunia.

Saria, at the Sacred Forest Meadow:

- [x] **Does her scene play even though you already have Saria's Song?** Yes (she gives her song, so the scene runs).
- [x] Do you get Zelda's Lullaby? (With the full skip there are no notes to repeat.) Yes.
- [x] Does the lullaby work (for example the Triforce blocks, or Zora's Domain)? Yes, it opens Darunia's area.

In general:

- [ ] Does any message name the wrong song? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

Attempt 4 (2026-11-14): **works.** Saria's scene plays even though her song is already owned, and it gives Zelda's Lullaby, which works (opens Darunia's area). Saria's Song from Impa works with Darunia. Conclusion: a song scene grants whatever its `ActorName` says, regardless of the songs owned; this is the basis for Song Locations.
