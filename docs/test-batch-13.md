# Test batch 13: what keeps the item from reaching the inventory

In batches 11 and 12 the items floated and were picked up, but did not reach the inventory. The rupee copy from batch 10 seemed to give the Slingshot (with the A button), but the user already had it from the chest, so it is unclear that it gave it. This batch tests that copy again with an item that is not owned, and tests each difference from the token separately.

## Setup

- [ ] Remove `TestBatch12` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch13` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and go to the Deku Tree. They are the same Skulltulas.

## What changes

| Skulltula | Room | Drops | How it is made |
|---|---|---|---|
| A | Compass room (upper floor) | **Boomerang** | Copy of the token, but with the "catching" method of normal items (not the token's) |
| B | Basement | **Hookshot** | Copy of the rupee, as in batch 10, but with pickup by walking over it enabled |
| C | Basement | **Bomb Bag** | Exactly the rupee copy from batch 10 (picked up with A). This is the clean test |
| D | Back room of the basement | Its normal token | Nothing (control) |

With each one, first try **walking over it**. If it is not picked up, try the **A button**.

## Check

- [ ] **A:** Does it float or fall? Is it picked up by walking over it or with A? Does the **Boomerang show in the inventory**? ______
- [ ] **B:** Does it float or fall? Is it picked up by walking over it or with A? Does the **Hookshot show in the inventory**? ______
- [ ] **C:** Does it float or fall? Is it picked up by walking over it or with A? Does the **Bomb Bag** show in the inventory? ______
- [ ] Does the "you got it" animation appear in any? ______
- [ ] Does the token counter go up with A, B or C? ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-10):

- **A (token with the normal catching method, Boomerang):** floats and is picked up by walking over it, but does not reach the inventory.
- **B (rupee with automatic pickup, Hookshot):** falls slowly and cannot be picked up.
- **C (exact copy of the rupee from batch 10, Bomb Bag):** falls slowly and cannot be picked up. So batch 10 proved nothing: no copy has given an item yet.
- **D: normal token.**

Cause found: there is a third registry, **`RSDB/PouchActorInfo`**, which says which actors can go to the inventory and how. The game's Ruto's letter (`Obj_Bottle_Letter`) has a row there, a copy of the one for `Item_Bottle_Letter`; the token and the rupees do too. The copies were not in it, so the game did not know what to do when they were picked up. This is tested in batch 14.
