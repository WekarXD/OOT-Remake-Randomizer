# To do

Pending work, most important first within each section.

## To investigate

- **Chests outside the logic.** 61 unmapped chests now take part in the fill with minor items only (`filler_sites` in `randomizer/fill.py`), so their ammo moves to chests that require its container. Still to do: identify the 39 ambiguous ones in game (most are small keys in the Fire Temple, Gerudo Training Ground and Water Temple) so they can also hold key items, and find out whether the remake-only DreamWorld chests can be revisited.
- **Everything a Skulltula drops should float** (built, waiting for test batch 18). Key items and tokens float (token-clone wrappers), but rupees and other minor items use the game's own drop actor and fall to the floor like an enemy drop (batch 17: the purple rupee from the Deku Tree basement vines). On a wall above water or a pit the drop can be lost (the Skulltula then respawns and drops it again, but it may never be reachable). Find a way to make every drop float where the Skulltula was. In batch 12 the rupee clones could not be picked up, before the PouchActorInfo row was understood; retry with the batch 14 recipe.
- **Bomb Bag outside its vanilla chest** cannot throw bombs, so it stays fixed for now.
- **Boomerang and the Deku Tree vine Skulltulas.** `REMAKE_RULES` only accepts the Slingshot, Bow or Hookshot for the Deku Tree upper floor; check whether the Boomerang kills those Skulltulas in the remake.
- **Soft-soil Skulltulas** (bugs on the soil) are untested with Tokensanity (batch 17, attempt 3).
- **Chest image and text** may still show the original item.
- **Movie cutscenes** (26 `.webm` in `Event/Movie`): removing the transition that starts them works (TestMovies2) and timelines are shortened; both are built into the childhood full skip (`Rando_FullSkipChild1`, waiting for the test). The Royal Family Tomb wall movies (`Dm_MelodyGet_Sun_*`): transitions dropped, untested in game.
- **Which file plays "Mido and Saria"** in Kokiri Forest (spike: `Dm_Kokiri_0060` was rewritten but the user still saw a conversation with them).

## To test in game

- `Rando_FullSkipChild1` (guide `docs/test-full-skip-child.md`): the childhood full skip.
- `Rando_FullSkipChild3` (guide `docs/test-full-skip-child-3.md`): shared forced talks done by growing the flow files (exit Kokiri, Mido, Zelda, castle, Royal Family Tomb 276 KB); pending the game test.
- Adult batch of the full skip: `AllSage` and `Get_Epona`, whose old-trim output changed when the parser began to show the case slots of subflow switches (kind 5). `Goto_HyruleCastle` and `SubEvent_GetEponaSong` changed the same way and are in the childhood guide.
- Batch 17, attempt 3: seed `TestTokens3`.
- Batch 16 (optional): confirm the 27 "guessed" Skulltulas with a rupee-colour mod so they can also hold key items.
- Acceptance seed `ACEPTACION1` and the round 2b cutscene re-test.

## To build

- **Remaining full-skip failures** (shared forced talks are done by growing, pending the round 3 test): the targeting tutorial `ActionTutorial_1st_Talk` (conflict), Din's fairy (conflict), `Dm_InsideJabu_Jabu_0050` (conflict). Compounding growth (copy of a copy) could be optimised by growing in place.
- **"No result" hash `0xa6da0479`** (event 28 of `SubEvent_GetEponaSong`, not a case of its switch 32): find out what produces it.
- **New END cases:** five scene files refuse rewrites that add a case to END (`Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040.110`); decide whether to allow them.
- **Full skip, adult phase:** the same method for the adult scenes, after the childhood test batch.
- **Browser generator on GitHub Pages:** built (`site/`, `randomizer/browser.py`); confirm a full generation in the browser with a real `.nup`.
- **NPC gifts:** phase B (plan written), then phases C and D.
- **OoTR generator options:** Open Forest / Kakariko / Door of Time / Zora's Fountain / Gerudo Fortress, and the timesavers (skip child stealth, free Rauru reward, skip tower escape, skip Epona race, minigame phases, fast chests, fast bunny hood, plant beans, Ruto on F1, fast shadow boat, free scarecrow, cucco/poe counts, ...).
- **Key items in the Water Temple, Fire Temple, Bottom of the Well and Gerudo Training Ground:** the small-key layout in the remake differs from the N64, so the logic is not reliable there yet.

## Small clean-ups

- Minor test gaps noted during the Tokensanity review (weak node-order test, no test of the RSTB formula for tables, tokens not counted during the assumed fill).
