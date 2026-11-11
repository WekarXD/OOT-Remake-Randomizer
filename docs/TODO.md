# To do

Pending work, most important first within each section.

## To investigate

- **Chests outside the logic.** 61 unmapped chests now take part in the fill with minor items only (`filler_sites` in `randomizer/fill.py`), so their ammo moves to chests that require its container. Still to do: identify the 39 ambiguous ones in game (most are small keys in the Fire Temple, Gerudo Training Ground and Water Temple) so they can also hold key items, and find out whether the remake-only DreamWorld chests can be revisited.
- **Everything a Skulltula drops should float** (built, waiting for test batch 18). Key items and tokens float (token-clone wrappers), but rupees and other minor items use the game's own drop actor and fall to the floor like an enemy drop (batch 17: the purple rupee from the Deku Tree basement vines). On a wall above water or a pit the drop can be lost (the Skulltula then respawns and drops it again, but it may never be reachable). Find a way to make every drop float where the Skulltula was. In batch 12 the rupee clones could not be picked up, before the PouchActorInfo row was understood; retry with the batch 14 recipe.
- **Bomb Bag outside its vanilla chest** cannot throw bombs, so it stays fixed for now.
- **Boomerang and the Deku Tree vine Skulltulas.** `REMAKE_RULES` only accepts the Slingshot, Bow or Hookshot for the Deku Tree upper floor; check whether the Boomerang kills those Skulltulas in the remake.
- **Soft-soil Skulltulas** (bugs on the soil) are untested with Tokensanity (batch 17, attempt 3).
- **Chest image and text** may still show the original item.

## To test in game

- Batch 17, attempt 3: seed `TestTokens3`.
- Batch 16 (optional): confirm the 27 "guessed" Skulltulas with a rupee-colour mod so they can also hold key items.
- Acceptance seed `ACEPTACION1` and the round 2b cutscene re-test.

## To build

- **Browser generator on GitHub Pages:** built (`site/`, `randomizer/browser.py`); confirm a full generation in the browser with a real `.nup`.
- **NPC gifts:** phase B (plan written), then phases C and D.
- **OoTR generator options:** Open Forest / Kakariko / Door of Time / Zora's Fountain / Gerudo Fortress, and the timesavers (skip child stealth, free Rauru reward, skip tower escape, skip Epona race, minigame phases, fast chests, fast bunny hood, plant beans, Ruto on F1, fast shadow boat, free scarecrow, cucco/poe counts, ...).
- **Key items in the Water Temple, Fire Temple, Bottom of the Well and Gerudo Training Ground:** the small-key layout in the remake differs from the N64, so the logic is not reliable there yet.

## Small clean-ups

- Minor test gaps noted during the Tokensanity review (weak node-order test, no test of the RSTB formula for tables, tokens not counted during the assumed fill).
