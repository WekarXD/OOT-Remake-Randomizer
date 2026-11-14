# Test batch 23: song scenes give minor items

Spike for "Shuffle Songs: Anywhere" (OoTR's setting: songs join the general pool, and the 12 song scenes can give **any** item, the user's choice on 2026-11-14). Key items from a scene already work (batch 7: Saria gave the Boomerang). Not yet known: **minor items**. The game itself gives rupees, Pieces of Heart and ammo with `Dm_SY_GetInEvent:GetInEvent`, while song scenes give with `GetPouchContent:GetPouchContentByActorName`, which the game only uses for pouch items (songs, Light Arrows). This batch renames the grant's item only, to see whether that call is enough.

| Scene | Normally | In this batch |
|---|---|---|
| Impa (`Dm_MelodyGet_Zelda`) | Zelda's Lullaby | **Red Rupee** (`Obj_Rupee_Red`) |
| Saria (`Dm_MelodyGet_Saria`) | Saria's Song | **Deku Nuts** (`TBox_DekuNutBundle`, the chests' ammo) |

Built on the full cutscene skip, so the lessons are gone. From each scene's real entry, no `LearningOcarina*` call is reached (checked on the built files), so the original song cannot slip in through the lesson's end. Same start as batch 20: the Fairy Ocarina, the castle quest at Step04, teleport to the courtyard by Impa. Builder: scratchpad `batch23.py` (throwaway).

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch23` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and walk out of Link's house: you are teleported to the castle courtyard.
- [ ] Walk up to Zelda, then go to Impa. Afterwards, go back to the forest → Lost Woods → Sacred Forest Meadow for Saria.

## Check

Impa:

- [ ] Does her scene end cleanly, with no hang? ______
- [ ] Do you get the **red rupee** (+20 rupees)? Is there a "you got" message, and what does it show? ______
- [ ] Do you **not** get Zelda's Lullaby? ______

Saria:

- [ ] Does her scene end cleanly? ______
- [ ] Do you get **Deku Nuts** (usable)? What message? ______
- [ ] Do you **not** get Saria's Song? ______

In general:

- [ ] Did the game hang or show a black screen? When? ______

## Results

(To be filled in after testing.)
