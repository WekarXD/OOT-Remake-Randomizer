# Test batch 15: Tokensanity, phase 1

Tests in-game what remains to be learned before building Tokensanity (design: `docs/superpowers/specs/2026-11-10-tokensanity-design.md`, section 4). The Skulltulas' items are copies of the gold token, as in batch 14 (A).

## Setup

- [ ] Remove `TestBatch14` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch15` to `load/0400486024DEC000/`.
- [ ] Start a **new game**. Before starting, note how many tokens you have (0).

## What changes

| Place | Where | Drops or contains | What is tested |
|---|---|---|---|
| Top-left chest | Mido's house (the two chests in the back row, which gave blue rupees) | Token (`Obj_Token_Gold`) | Token in a chest |
| Top-right chest | Mido's house | Token (`Item_Token_Gold`) | Token in a chest, another form |
| Night Skulltula | Kokiri Forest, at night, at the Know-It-All Brothers' house | **Silver Gauntlets** | Night Skulltula |
| Soft soil Skulltula | Kokiri Forest, in the soft soil (you must release bugs from a bottle; if you have no bottle, skip it) | **Lens of Truth** | Soft soil Skulltula |
| A | Deku Tree, compass room | **Iron Boots** | Re-entering |
| B | Deku Tree, basement | **Its token**, set by hand | Token dropped by a Skulltula through the new route |
| C | Deku Tree, basement | **Megaton Hammer** | Leaving without picking it up |
| D | Deku Tree, back room of the basement | **Mirror Shield** | Saving and loading |

Adult items (boots, gauntlets, hammer, Mirror Shield) cannot be used as a child. It is enough that they appear in the inventory or equipment.

## Check

- [ ] **Mido's chests:** what comes out of each? Does the token counter go up (it should end at 2)? ______
- [ ] **Night Skulltula:** does it appear at night? Does it drop the Silver Gauntlets? Do they reach the equipment? ______
- [ ] **Soft soil** (if you can): does the Skulltula appear? Does it drop the Lens? Does it reach the inventory? ______
- [ ] **A:** pick up the Boots, leave the room and re-enter. Does the Skulltula reappear? Does it drop the boots again? ______
- [ ] **B:** does the token come out and the counter go up? Leave and return: does the Skulltula reappear? ______
- [ ] **C:** kill the Skulltula and **do not pick up** the Hammer. Leave the room and return. Is the Hammer still floating? Does the Skulltula come back? Then pick it up: does it reach the inventory? ______
- [ ] **D:** pick up the Mirror Shield, **save the game, quit and load it**. Is the shield still in the equipment? Does D's Skulltula reappear? ______
- [ ] **Final counter:** how many tokens do you have at the end? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-11). The game did not hang.

| Test | Result |
|---|---|
| Mido's chests | Both give the token and the counter goes up. `Obj_Token_Gold` and `Item_Token_Gold` both work. |
| Night Skulltula | Works: it drops the Silver Gauntlets and they reach the equipment. Day and night do not advance until you get Zelda's letter and leave the castle. |
| Soft soil | Not tested (no bugs in a bottle). |
| A (Iron Boots) | After picking them up, the Skulltula does not reappear. |
| B (token set by hand) | The counter goes up and the Skulltula does not return. |
| C (leaving without picking up the Hammer) | On returning, the Skulltula has reappeared. It is killed again and the Hammer reaches the inventory. **The item is not lost.** |
| D (save and load) | The Mirror Shield is kept and the Skulltula does not return. |
| Final counter | 3 (two chests plus B), correct. |

Conclusion: **Tokensanity phase 1 is passed.**

- Tokens can go in chests.
- A Skulltula counts as "collected" once what it drops is picked up.
- If it is not picked up, the Skulltula returns and drops it again. Nothing is lost and nothing can be collected twice.
- Night Skulltulas work.
- The wrappers work for several families of key items: boots and gauntlets (`Armor_*`), hammer (`Item_*`) and shield (`Weapon_*`).

The soft soil Skulltula remains untested. It will be checked on the phase 3 test seed.
