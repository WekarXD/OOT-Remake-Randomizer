# Test batch 6: what can Gold Skulltulas drop?

Goal: find out whether a Gold Skulltula can drop another item instead of its token. There are two cases:

- an **important item** (`Item_*`, such as the Hookshot);
- a **"ground" item** (`Obj_*`, such as a rupee or a piece of heart).

The result decides what can be placed in Skulltulas, pots, crates and beehives.

## Setup

- [ ] Disable any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch6` to `load/0400486024DEC000/` in Lichii.
- [ ] Start a **new game**: the mod only changes the Deku Tree, so you can go straight there.

## What changes

There are four Gold Skulltulas in the Deku Tree. The rooms are my guess from the data.

| Skulltula | Room (I think) | Should drop |
|---|---|---|
| A | Compass room (upper floor, on the vine wall) | **Hookshot** |
| B | Basement, first room (one of the two) | **Red rupee** |
| C | Basement, first room (the other) | **Piece of Heart** |
| D | Back room of the basement | Its normal token (unchanged, control) |

## Check

For each Skulltula note what it dropped and whether you could keep it:

- [ ] **A:** Hookshot? Does it appear in the inventory and can it be used? ______
- [ ] **B:** Red rupee? Does the counter go up by 20? ______
- [ ] **C:** Piece of Heart? Does the piece counter go up? ______
- [ ] **D:** Normal Skulltula token? ______
- [ ] If any dropped its normal token instead of the new item, or nothing, or the game hung, note which. ______

If you have time:

- [ ] Leave the Deku Tree and come back in. Do Skulltulas A, B or C reappear? ______

## Results

In-game results (2026-11-10):

- **A (Hookshot, `Item_Hookshot`): it is visible, but cannot be picked up.** `Item_*` objects do not work as loose items in the world.
- **B (red rupee, `Obj_Rupee_Red`): works.**
- **C (piece of heart, `Obj_Heart_Piece`): works.** In this game pieces of heart are picked up with an action, not by walking over them; that is also the case in the original game.
- **Conclusion:** `Drop__DropActor` on a Gold Skulltula is respected, but only with `Obj_*` objects. Key items cannot go in Skulltulas, pots, crates or beehives; only minor items fit there.
