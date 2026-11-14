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
- [ ] Afterwards, to reach Saria: go back to Kokiri Forest from Hyrule Field, then Lost Woods → Sacred Forest Meadow.

## Check

Impa:

- [ ] Do the notes you are asked to repeat belong to **Saria's Song** (↓ → ← ↓ → ←)? ______
- [ ] Do you end up with Saria's Song in the song list, and **not** Zelda's Lullaby? ______
- [ ] Does the scene end cleanly, with no hang? ______

With Saria's Song from Impa:

- [ ] Can you play it? Does it work where it should (Saria on the ocarina, Darunia)? ______

Saria, at the Sacred Forest Meadow:

- [ ] **Does her scene play even though you already have Saria's Song?** ______
- [ ] Do the notes belong to **Zelda's Lullaby** (← ↑ → ← ↑ →)? Do you get Zelda's Lullaby? ______
- [ ] Does the lullaby work (for example the Triforce blocks, or Zora's Domain)? ______

In general:

- [ ] Does any message name the wrong song? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

(To be filled in after testing.)
