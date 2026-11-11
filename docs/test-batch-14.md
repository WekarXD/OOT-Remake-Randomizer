# Test batch 14: registering the items in the inventory registry

In batches 11 to 13 the items floated and were picked up like a token, but did not reach the inventory. They were missing from the inventory registry (`RSDB/PouchActorInfo`), where Ruto's letter, the token and the rupees are present. In this batch, each copy carries its row in that registry, identical to that of the item it gives.

All three are copies of the gold token and should float and be picked up by walking over them, as in batches 11 to 13. Each uses a different variant of those already tested, to see which works best.

## Setup

- [ ] Remove `TestBatch13` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch14` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and go to the Deku Tree. They are the same Skulltulas.

## What changes

| Skulltula | Room | Drops | Variant |
|---|---|---|---|
| A | Compass room (upper floor) | **Boomerang** | Token as is (like batch 11) |
| B | Basement | **Hookshot** | Token with the generic "ending" (like A in batch 12) |
| C | Basement | **Bomb Bag** | Token with generic ending, behavior and catching method (like A in batch 13) |
| D | Back room of the basement | Its normal token | Control |

## Check

- [ ] **A:** Does it float? Is it picked up by walking over it? Does the **Boomerang show in the inventory** and can it be thrown? ______
- [ ] **B:** Does it float? Is it picked up? Does the **Hookshot show in the inventory**? ______
- [ ] **C:** Does it float? Is it picked up? Does the **Bomb Bag** show up and can you carry bombs? ______
- [ ] Does the "you got it" animation or message appear? ______
- [ ] Does the token counter go up with A, B or C? It should only go up with D. ______
- [ ] If you have the Boomerang, can you catch any from a distance with it? ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-10): **works.**

- **A (token as is, Boomerang):** floats, is picked up by walking over it, shows in the inventory and can be used.
- **B (token with generic ending, Hookshot):** floats, can be picked up with the Boomerang and shows in the inventory.
- **C (token with everything generic, Bomb Bag):** floats, is picked up with the Boomerang and shows in the inventory with 20 bombs, but they cannot be thrown. This is the same known v1 failure: the Bomb Bag outside its original chest never lets you throw bombs (commit 2ad8165). It has nothing to do with the Skulltulas.
- **D: normal token.**

Conclusion: for a world object to give a key item, four things are needed:

1. A new actor, a copy of `Obj_Token_Gold` with the item's model, name and `PouchContentParam` (plus `DefaultAutoGet`).
2. Its entry in the RSTB.
3. Its rows in `RSDB/ActorInfo`, `RSDB/GameActorInfo` and **`RSDB/PouchActorInfo`** (a copy of the item's row).
4. Pointing `Drop__DropActor` at it.

The simplest variant, the token as is (A), is enough.
