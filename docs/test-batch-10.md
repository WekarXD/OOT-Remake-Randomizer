# Test batch 10: registered new actors

Same as batch 9, but now the new actors are **registered** in the game's actor registry (`RSDB/ActorInfo` and `RSDB/GameActorInfo`). In batch 9 they were not, which is why nothing appeared.

Each new actor is a copy of a ground object that already works when dropped, but that gives a key item when picked up.

## Setup

- [ ] Remove `TestBatch9` from Lichii and disable any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch10` to `load/0400486024DEC000/`.
- [ ] Start a **new game** and go to the Deku Tree.

## What changes

| Skulltula | Room | Should drop | Copy of |
|---|---|---|---|
| A | Compass room (upper floor) | **Slingshot** | Red rupee (picked up by walking over it) |
| B | Basement, the red rupee one from batch 6 | **Boomerang** | Ruto's letter, but with the piece of heart's pickup method |
| C | Basement, the piece of heart one from batch 6 | **Hookshot** | Piece of heart (picked up with the action button) |
| D | Back room of the basement | Its normal token | Unchanged (control) |

Note on A: if you already have the Slingshot from the chest, at least look for whether anything appears and whether the "you got it" message shows. If you can, kill Skulltula A before opening the Slingshot chest.

## Check

- [ ] **A:** Does anything appear? What does it look like? Does it fall to the ground or float? Can it be picked up? Does the Slingshot show in the inventory? ______
- [ ] **B:** Does anything appear? Does it fall or float? Can it be picked up? Does the Boomerang show up and can it be thrown? ______
- [ ] **C:** Does anything appear? Does it fall or float? Can it be picked up? Does the Hookshot show in the inventory? ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen? When? If the game does not start or hangs when entering the Deku Tree, note that too. ______

## Results

In-game results (2026-11-10). To reach the first Skulltula, the Slingshot had to be picked up first, because the remake's collisions force you to kill the Skulltulas on the way.

- **A (copy of the red rupee -> Slingshot): works.** It falls to the ground and can be picked up, but with the A button, not by walking over it. Picking it up while already owning it causes no problems. **Note:** since the Slingshot from the chest was already owned, it is unclear that this copy gave it. Repeated in batch 13 (C) with the Bomb Bag.
- **B (copy of the letter -> Boomerang):** it stays floating and cannot be picked up by walking over it. Because of where it ended up, it could not be picked up.
- **C (copy of the piece of heart -> Hookshot):** it stays floating with the piece of heart's glow and pickup zone. It cannot be picked up by walking over it.
- **D: normal token.** The game did not hang.

Conclusions:

- A new actor registered in the registry appears and hands over the key item from its row (`ActorName`).
- Whether it is picked up by walking over it depends on `DefaultAutoGet` in the `PouchContentParam`. Key items do not have it, which is why the A button was needed.
- What the user wants is for the item to stay floating where the Skulltula was and be picked up by walking over it, with the Hookshot or the Boomerang. That is exactly what the gold token (`Obj_Token_Gold`) does, so batch 11 uses the token as a base.
