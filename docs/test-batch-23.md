# Test batch 23: song scenes give minor items

Spike for "Shuffle Songs: Anywhere" (OoTR's setting: songs join the general pool, and the 12 song scenes can give **any** item, the user's choice on 2026-11-14). Key items from a scene already work (batch 7: Saria gave the Boomerang). Not yet known: **minor items**. The game itself gives rupees, Pieces of Heart and ammo with `Dm_SY_GetInEvent:GetInEvent`, while song scenes give with `GetPouchContent:GetPouchContentByActorName`, which the game only uses for pouch items (songs, Light Arrows). This batch renames the grant's item only, to see whether that call is enough.

| Scene | Normally | In this batch |
|---|---|---|
| Impa (`Dm_MelodyGet_Zelda`) | Zelda's Lullaby | **Red Rupee** (`Obj_Rupee_Red`) |
| Saria (`Dm_MelodyGet_Saria`) | Saria's Song | **Deku Nuts** (`TBox_DekuNutBundle`, the chests' ammo) |

Built on the full cutscene skip, so the lessons are gone. From each scene's real entry, no `LearningOcarina*` call is reached (checked on the built files), so the original song cannot slip in through the lesson's end. Every check starts with a teleport next to its scene (the user's standing rule), so there are two mods, each for a new game:

- **`TestBatch23a` (Impa):** the Fairy Ocarina, the castle quest at Step04, teleport to the courtyard by Impa (as batch 20).
- **`TestBatch23b` (Saria):** the Fairy Ocarina, `DoorOfTime` advanced Ready → Step01 → Step02 (her meadow logic, `SacredForestMeadow_Child_Prefab_3265`, starts the scene once that quest is past Step01 and `Dm_MelodyGet_Saria` has not played), teleport to the `ForestMinuet` start position next to her stump.

Builder: scratchpad `batch23.py` (throwaway), `a` or `b`.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] **23a:** copy `test-mod/0400486024DEC000/TestBatch23a` to `load/0400486024DEC000/`, start a **new game** and leave the house: you are in the castle courtyard. Walk up to Zelda, then to Impa.
- [ ] **23b:** replace it with `TestBatch23b`, start **another new game** and leave the house: you appear in the Sacred Forest Meadow next to Saria.

## Check

Impa:

- [ ] Does her scene end cleanly, with no hang? ______
- [x] Do you get the **red rupee** (+20 rupees)? Is there a "you got" message, and what does it show? Yes: the message names the red rupee and it is received (attempt 1).
- [ ] Do you **not** get Zelda's Lullaby? ______

Saria:

- [ ] Does her scene end cleanly? ______
- [ ] Do you get **Deku Nuts** (usable)? What message? ______
- [ ] Do you **not** get Saria's Song? ______

In general:

- [ ] Did the game hang or show a black screen? When? ______

## Results

Attempt 1 (2026-11-14):
- **23a works:** Impa's scene gives the red rupee, with its "you got" message. A minor item can be granted just by renaming the grant's item, so the grant call does not need to change.
- **23b:** Saria was not in the meadow. Cause: `DoorOfTime` depends on `Goto_HyruleCastle_IsCompleted_Exp` (`DependFlagName` in `RSDB/Challenge`), so its steps did not advance while the castle quest was not completed. The 23b preset now completes the castle quest first (every step up to `Complete`) and then advances `DoorOfTime`. Rebuilt for attempt 2 (23b only).
