# Test batch 9: key items inside a "ground" object

Goal: a Gold Skulltula (and later pots, rupees, etc.) can drop a key item **and it can be picked up**.

In batch 6 the Hookshot was visible but could not be picked up. The reason is that key items (`Item_*`) are only a model for scenes and lack the part that allows picking them up.

Ground objects (`Obj_*`) do have it, and some already "wrap" a key item. For example, Ruto's letter at the lake is an `Obj_Bottle_Letter` that, when picked up, gives you the `Item_Bottle_Letter` item.

This batch tests three ways of doing it. Two of them are **new** actors, created by copying one from the game and changing the item they give.

## Setup

- [ ] Disable any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch9` to `load/0400486024DEC000/` in Lichii.
- [ ] Start a **new game** and go to the Deku Tree. They are the same Skulltulas as in batch 6.

## What changes

| Skulltula | Room (the one from batch 6) | Should drop | How |
|---|---|---|---|
| A | Compass room (upper floor) | **Ruto's Letter** (bottle with letter) | The game's object as is (`Obj_Bottle_Letter`) |
| B | Basement, the one that dropped the red rupee | **Boomerang** | New actor: copy of Ruto's letter that gives the Boomerang |
| C | Basement, the one that dropped the piece of heart | **Hookshot** | New actor: copy of the piece of heart that gives the Hookshot |
| D | Back room of the basement | Its normal token | Unchanged (control) |

## Check

For each one, note what is visible on death and whether it can be picked up. The action button may be needed, as with the piece of heart.

- [ ] **A:** Does the bottle with the letter appear? Can it be picked up? Does it show in the inventory? ______
- [ ] **B:** Does anything appear? What does it look like? Can it be picked up? Does the Boomerang show in the inventory and can it be thrown? ______
- [ ] **C:** Does anything appear? What does it look like? Can it be picked up? Does the Hookshot show in the inventory? (it cannot be used as a child; it is enough that it appears) ______
- [ ] **D:** Normal token? ______
- [ ] Did the game hang or show a black screen at any point? When? ______

## Results

In-game results (2026-11-10):

- **A (Ruto's letter, `Obj_Bottle_Letter`): it gives it**, but it stays floating where the Skulltula was and does not fall to the ground. If the Skulltula is high up, it could not be picked up. This is due to its behavior (it floats as if in water), so it is not useful as a base.
- **B and C (new actors): nothing appears.**
- **D: normal token.**

Cause of B and C: the game has an actor registry (`RSDB/ActorInfo` and `RSDB/GameActorInfo`), and the new actors had not been registered. That registry is also what makes the letter work: its row says `ActorName: Item_Bottle_Letter`, that is, "when picked up, I am the letter". This is tested in batch 10.
