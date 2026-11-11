# Test batch 17: first seed with Tokensanity

This is the first seed with Tokensanity set to "All Tokens", with "Skip cutscenes" disabled. Skulltulas can drop key items, rupees, etc., and tokens are spread across chests and Skulltulas. The full log is in `spoiler.txt`, inside the mod folder (it lists everything in each place).

## Attempt 1: seed `TestTokens1` (blocked)

- Mido's chests and the Kokiri Sword chest gave what was expected.
- **You could not progress in the Deku Tree.** To get up to the compass room floor you must kill the regular Skulltulas on the vines, and as a child that requires a ranged weapon. The Slingshot was right on that floor, in the side chest of the compass room. OoTR's logic treats that floor as accessible with nothing.
- **Fix:** there are remake-specific rules (`REMAKE_RULES` in `randomizer/logic/world.py`). To require the Slingshot, the Bow or the Hookshot there are:
  - the two chests in the compass room;
  - the Gold Skulltula in the compass room;
  - the drop to the basement (opened by jumping from that floor onto the web).

## Attempt 2: seed `TestTokens2`

### Setup

- [ ] Remove `Rando_TestTokens1` and any other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/Rando_TestTokens2` to `load/0400486024DEC000/`.
- [ ] Start a **new game**.

### What to check (start of the game)

| Place | Should give |
|---|---|
| Kokiri Sword chest (the one in the small maze in Kokiri Forest) | **Token** |
| Mido's house: top left, top right and bottom left | **Token** in each |
| Kokiri Forest storms grotto (the Song of Storms one, for later) | Token |
| Deku Tree, Slingshot room (floor 2, needs the Deku Shield from the shop), side chest | **Slingshot** |
| Deku Tree, Slingshot room, big chest | Bombs |
| Deku Tree, compass room, side chest | Deku Shield |
| Deku Tree, compass room Skulltula | Its token |
| Deku Tree, basement chest | Token |
| Deku Tree, basement grate Skulltula | **Blue rupee** |
| Deku Tree, basement vines Skulltula | **Purple rupee** |
| Deku Tree, basement back room Skulltula | Its token |
| Kokiri Forest, Know-It-All Brothers' house Skulltula (at night, child) | Red rupee |

Key items in Skulltulas, if you get further:

- Dodongo's Cavern, vines Skulltula above the stairs: **Longshot**.
- Death Mountain Crater, bean spot Skulltula: **Golden Gauntlets**.
- Spirit Temple, metal fence Skulltula: **Megaton Hammer**.

### Check

- [ ] Do the chests in the table give what they say? Does the token counter go up with the chest tokens? ______
- [ ] With the Slingshot, can you kill the vine Skulltulas and climb to the compass room? ______
- [ ] Do the basement Skulltulas drop the blue and purple rupees, and can they be picked up? ______
- [ ] Did any Skulltula drop something other than expected, or nothing? Which? ______
- [ ] Is there any other place the logic sends you to that cannot be reached? ______
- [ ] Did the game hang or show a black screen? When? ______

### Results (played up to leaving Kokiri Forest)

- Everything worked up to leaving Kokiri Forest, including climbing to the compass room with the Slingshot.
- **Bug:** the bombs in the Slingshot room big chest unlocked the Bomb Bag in the inventory without the bag, and they could not be used. **Fix:** ammo (bombs, Bombchus, arrows) now only goes to chests that cannot be reached without its container, the Bomb Bag or the Bow (`AMMO_CONTAINER` in `randomizer/fill.py`), and never to a Skulltula.
- The basement Skulltulas dropped the blue and the purple rupee, and both could be picked up. The purple one fell to the floor instead of floating like the tokens. Rupees use the game's own drop actor, which falls like an enemy drop. If it is not collected the Skulltula comes back and drops it again, so nothing is lost.

## Attempt 3: seed `TestTokens3`

### Setup

- [ ] Remove `Rando_TestTokens2`.
- [ ] Copy `test-mod/0400486024DEC000/Rando_TestTokens3` to `load/0400486024DEC000/`.
- [ ] Start a **new game**.

### What to check

| Place | Should give |
|---|---|
| Mido's house, top right | **Fairy Slingshot** |
| Mido's house, bottom left | **Kokiri Sword** |
| Mido's house, top left and bottom right | Token |
| Kokiri Sword chest | Red rupee |
| Deku Tree, Slingshot room big chest | Deku Sticks |
| Deku Tree, Slingshot room side chest | Token |
| Deku Tree, compass room side chest | Green rupee |
| Deku Tree, basement chest | Blue rupee |
| Deku Tree, all four Skulltulas | Their token |
| Kokiri Forest, bean patch Skulltula (child, drop bugs on the soft soil) | **Longshot** (first test of a soft-soil Skulltula) |
| Lost Woods, Skulltula above the theater (adult, at night) | Green rupee |
| Kakariko, Skulltula near the gate guard (child, at night) | **Lens of Truth** |
| Kakariko, Skulltula in the house under construction (child, at night) | Purple rupee |
| Hyrule Field, cow grotto Skulltula | Hylian Shield |

Ammo in this seed is only in late dungeons (Ganon's Castle, Shadow Temple, Gerudo Training Ground).

### Check

- [ ] Does any chest give bombs, Bombchus or arrows before you have the Bomb Bag or the Bow? ______
- [ ] Does the soft-soil Skulltula appear and drop the Longshot? ______
- [ ] Did any Skulltula drop something other than expected, or nothing? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

(To be filled in after testing.)
