# To do

Pending work, most important first within each section.

## To investigate

- **Chests outside the logic.** Only 104 of the 203 chests are mapped to OoTR locations; the other 99 keep their original contents and never take part in the fill. That includes some ammo chests (bombs and Bombchus in the Spirit Temple, Gerudo Training Ground and Ganon's Castle; arrows in Ganon's Castle), which can give ammo before the Bomb Bag or the Bow and unlock it in the inventory without it being usable. Map them to their OoTR locations, or failing that make sure their vanilla contents are safe.
- **Everything a Skulltula drops should float.** Key items and tokens float (token-clone wrappers), but rupees and other minor items use the game's own drop actor and fall to the floor like an enemy drop (batch 17: the purple rupee from the Deku Tree basement vines). On a wall above water or a pit the drop can be lost (the Skulltula then respawns and drops it again, but it may never be reachable). Find a way to make every drop float where the Skulltula was. In batch 12 the rupee clones could not be picked up, before the PouchActorInfo row was understood; retry with the batch 14 recipe.
- **Bomb Bag outside its vanilla chest** cannot throw bombs, so it stays fixed for now.
- **Boomerang and the Deku Tree vine Skulltulas.** `REMAKE_RULES` only accepts the Slingshot, Bow or Hookshot for the Deku Tree upper floor; check whether the Boomerang kills those Skulltulas in the remake.
- **Soft-soil Skulltulas** (bugs on the soil) are untested with Tokensanity (batch 17, attempt 3).
- **Chest image and text** may still show the original item.

## To test in game

- Batch 17, attempt 3: seed `TestTokens3`.
- Batch 16 (optional): confirm the 27 "guessed" Skulltulas with a rupee-colour mod so they can also hold key items.
- Acceptance seed `ACEPTACION1` and the round 2b cutscene re-test.

## To build

- **Browser generator on GitHub Pages:** choose the `.nup`, choose the settings, download a `.zip` with the `Rando_<seed>` mod and its spoiler log inside. Runs the existing Python generator in Pyodide 314 (Python 3.14); the `.nup` is read locally in pieces and never uploaded. Remove the local app (`python -m randomizer`) once it works. Design in progress.
- **NPC gifts:** phase B (plan written), then phases C and D.
- **OoTR generator options:** Open Forest / Kakariko / Door of Time / Zora's Fountain / Gerudo Fortress, and the timesavers (skip child stealth, free Rauru reward, skip tower escape, skip Epona race, minigame phases, fast chests, fast bunny hood, plant beans, Ruto on F1, fast shadow boat, free scarecrow, cucco/poe counts, ...).
- **Key items in the Water Temple, Fire Temple, Bottom of the Well and Gerudo Training Ground:** the small-key layout in the remake differs from the N64, so the logic is not reliable there yet.

## Small clean-ups

- ResourceWarning in the full test suite (a `NupArchive` not closed in some `setUpClass`).
- `can_wrap` reloads the RSDB tables on every call (slow).
- The spoiler log has Windows line endings when generated on Windows and Unix ones in the browser; pick one.
- Minor test gaps noted during the Tokensanity review (weak node-order test, no test of the RSTB formula for tables, tokens not counted during the assumed fill).
