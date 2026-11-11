# Test batch 12: the gold token that gives the item

In batch 11 the items floated and were picked up like a token, but did not reach the inventory. The reason is that, when picked up, the token's "ending" (adding a token) ran instead of the ground objects' ending (putting the item in the inventory).

In this batch, each actor is still a copy of the token, but carries pieces of the generic "ending" taken from the red rupee. Each Skulltula tests a different combination.

## Setup

- [ ] Remove `TestBatch11` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch12` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and go to the Deku Tree. They are the same Skulltulas.

## What changes

| Skulltula | Room | Drops | What differs from the token |
|---|---|---|---|
| A | Compass room (upper floor) | **Boomerang** | Only the "ending" (generic `DeathRef`) |
| B | Basement | **Hookshot** | The "ending" and the rupee's pickup scene |
| C | Basement | **Bomb Bag** | The "ending" and the behavior (generic `AIInfoRef`). It may fall to the ground instead of floating |
| D | Back room of the basement | Its normal token | Nothing (control) |

## Check

- [ ] **A:** Does it float? How is it picked up? Does the **Boomerang show in the inventory** and can it be thrown? ______
- [ ] **B:** Does it float? How is it picked up? Does the **Hookshot show in the inventory**? ______
- [ ] **C:** Does it float or fall? How is it picked up? Does the **Bomb Bag** show up and can you carry bombs? ______
- [ ] Does the "you got it" message or animation appear in any? ______
- [ ] Does the token counter go up with A, B or C? It should only go up with D. ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-10):

- **A, B and C: they float with the token's glow and are picked up by walking over them, but none reaches the inventory.** C also floats, even though it carries the generic behavior.
- **D: normal token.**

Conclusion: the "ending" and the behavior are not the cause. Compared with the rupee in batch 10, which did give the item, two differences remain: automatic pickup (`DefaultAutoGet`) and the token's way of being "caught" (`AttentionSender`), which may trigger the tokens' special pickup. They are tested separately in batch 13.
