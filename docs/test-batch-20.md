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
- [ ] Start a **new game** and play normally up to Zelda and Impa.

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
