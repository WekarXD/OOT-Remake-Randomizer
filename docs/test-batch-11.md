# Test batch 11: key items with the gold token's behavior

The goal is for the item to stay floating where the Skulltula was and to be picked up by walking over it, with the Hookshot or the Boomerang, just like a token.

Each new actor is a copy of the **gold token** (`Obj_Token_Gold`) with the model and identity of a key item. It also has automatic pickup (`DefaultAutoGet`) enabled, which key items do not come with.

## Setup

- [ ] Remove `TestBatch10` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch11` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and go to the Deku Tree. They are the same Skulltulas as in batches 9 and 10.

## What changes

| Skulltula | Room | Should drop |
|---|---|---|
| A | Compass room (upper floor) | **Boomerang** |
| B | Basement (the one that dropped the Boomerang in batch 10) | **Hookshot** |
| C | Basement (the one that dropped the Hookshot in batch 10) | **Bomb Bag** |
| D | Back room of the basement | Its normal token (control) |

If you can, pick up the item from A, B or C in different ways: one by walking over it, one with the Boomerang once you have it, and one with the A button.

## Check

- [ ] **A:** Does the Boomerang appear? Does it float where the Skulltula was? Is it picked up by walking over it? Does it show in the inventory and can it be thrown? ______
- [ ] **B:** Does the Hookshot appear? Does it float? How did you pick it up? Does it show in the inventory? ______
- [ ] **C:** Does the Bomb Bag appear? Does it float? How did you pick it up? Can you carry bombs? ______
- [ ] Was any picked up with the Boomerang from a distance? ______
- [ ] Did the token counter go up when picking up A, B or C? It should only go up with D. ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-10):

- **A (Boomerang), B (Hookshot) and C (Bomb Bag): they appear, float like a token, with its glow, and can be picked up.** But the item **does not reach the inventory** and cannot be used.
- **D: normal token.**

Cause: when picked up, the token runs its own "ending", which adds a token, instead of the generic ground-object ending, which puts the item in the inventory. In the files these are the `DeathRef` (`Item_Token_Gold`, versus `DropItem`) and the behavior (`AIInfoRef`). The rupee in batch 10 used the generic one, which is why it gave the Slingshot. This is tested in batch 12.
