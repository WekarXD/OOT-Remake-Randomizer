# Test batch 7: Saria gives you the Boomerang instead of the Ocarina

Goal: check that a character's gift can be changed in a scene. Saria gives you the Fairy Ocarina when you say goodbye to her on the bridge; in this batch she will give you the **Boomerang** (`Item_Boomerang`, usable as a child).

If it works, other character gifts (ocarinas, Gerudo Card, etc.) can be placed too.

## Setup

- [ ] Disable any other `Rando_*`, `TestBatch*` and `TestScenes*` mod: only this one should be active.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch7` to `load/0400486024DEC000/` in Lichii.
- [ ] Start a **new game**.

## What changes

Only the scene in which Saria gives you the Fairy Ocarina. It happens when you leave Kokiri Forest for the first time (after the Deku Tree), on the bridge.

Warning: without the Ocarina you cannot play songs until you get the Ocarina of Time later on. For this test it does not matter: we only want to see the gift.

## Check

- [ ] Do the Deku Tree (or the minimum needed to leave the forest) and leave Kokiri Forest by the bridge.
- [ ] Say goodbye to Saria on the bridge.
- [ ] Do you receive the **Boomerang** instead of the Ocarina? ______
- [ ] Does the Boomerang show in the inventory and can it be thrown? ______
- [ ] Does the scene end properly, with no hang or black screen? ______
- [ ] Does the Fairy Ocarina **not** appear? (this is expected) ______
- [ ] If anything failed (another item, nothing, a hang), note what. ______

## Results

In-game result (2026-11-10): **works.** Saria hands over the Boomerang instead of the Fairy Ocarina; it shows in the inventory and can be thrown as a child. The scene ends properly.

Conclusion: changing the text parameter of a gift scene works to hand over another key item (`Item_*`). Phase A is passed.
