# Test batch 18: minor items floating from Skulltulas

Until now only key items and tokens floated when a Gold Skulltula dropped them; rupees and other minor items used the game's own world actor and fell to the floor (batch 17). Now every drop is a token-clone wrapper. When the chest content is a bundle (`TBox_Rupee_Purple` turns into 50 green rupees), the wrapper takes the identity of the game's world actor instead (`Obj_Rupee_Purple`), with components inherited from its parent actor (`Obj_Rupee_Green`). Only ammo bundles (bombs, Bombchus, sticks, nuts) cannot float, and the fill never puts them on a Skulltula.

The rest of the game is vanilla: no chest changes.

## Setup

- [ ] Remove any other `Rando_*` or `TestBatch*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch18` to `load/0400486024DEC000/`.
- [ ] Start a **new game**.

## What to check

| Skulltula | Should drop |
|---|---|
| Deku Tree, compass room | Purple rupee (50) |
| Deku Tree, basement gate | Blue rupee (5) |
| Deku Tree, basement vines | Red rupee (20) |
| Deku Tree, basement back room | Piece of Heart |
| Kokiri Forest, Know-It-All Brothers' house (child, at night) | Deku Shield |
| Kokiri Forest, soft soil (child, drop bugs on the soil) | Green rupee (1) |
| Lost Woods, soft soil near the bridge (child, bugs) | Deku Seeds |
| Lost Woods, soft soil near the theater (child, bugs) | Gold rupee (200) |
| Kakariko, house under construction (child, at night) | Large magic jar |

## Check

- [ ] Does each drop float where the Skulltula died, instead of falling? ______
- [ ] Is it picked up by walking over it, or with the Boomerang? ______
- [ ] Does the wallet go up by the right amount for each rupee? ______
- [ ] Does the Piece of Heart count (4 pieces = 1 heart)? ______
- [ ] Does the token counter stay the same when picking up these drops? ______
- [ ] Do the soft-soil Skulltulas appear and drop their item? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

(To be filled in after testing.)
