# To do

Pending work, most important first within each section.

## To investigate

- **Song wrappers look like a rupee** (Dungeon Rewards boss hearts, batch 25): songs have no world model, so the wrapper keeps the token's look; the boss drop cutscene still shows a Heart Container. Cosmetic.
- **`Item_BulletBag_Small` or `TBox_DekuSeedBundle` hang `Dm_SY_GetInEvent:GetInEvent`** (batch 25, attempts 2-4): if a song scene can give them (Anywhere, Dungeon Rewards), check that path too.
- **Ammo with a Slingshot or Bow from a song scene** (Anywhere, Dungeon Rewards): given through `Dm_SY_GetInEvent:GetInEvent` (the start preset), the Slingshot comes without its Bullet Bag or seeds (batch 25, attempt 1). Song scenes give with `GetPouchContentByActorName`; check whether the Slingshot and the Bow come with their ammo that way, otherwise keep them off song scenes.
- **Chests outside the logic.** 61 unmapped chests now take part in the fill with minor items only (`filler_sites` in `randomizer/fill.py`), so their ammo moves to chests that require its container. Still to do: identify the 39 ambiguous ones in game (most are small keys in the Fire Temple, Gerudo Training Ground and Water Temple) so they can also hold key items, and find out whether the remake-only DreamWorld chests can be revisited.
- **Everything a Skulltula drops should float** (built, waiting for test batch 18). Key items and tokens float (token-clone wrappers), but rupees and other minor items use the game's own drop actor and fall to the floor like an enemy drop (batch 17: the purple rupee from the Deku Tree basement vines). On a wall above water or a pit the drop can be lost (the Skulltula then respawns and drops it again, but it may never be reachable). Find a way to make every drop float where the Skulltula was. In batch 12 the rupee clones could not be picked up, before the PouchActorInfo row was understood; retry with the batch 14 recipe.
- **Boomerang and the Deku Tree vine Skulltulas.** `REMAKE_RULES` only accepts the Slingshot, Bow or Hookshot for the Deku Tree upper floor; check whether the Boomerang kills those Skulltulas in the remake.
- **Soft-soil Skulltulas** (bugs on the soil) are untested with Tokensanity (batch 17, attempt 3).
- **Chest image and text** may still show the original item.
- **Movie cutscenes** (26 `.webm` in `Event/Movie`): removing the transition that starts them works (TestMovies2) and timelines are shortened; both are built into the childhood full skip (`Rando_FullSkipChild1`, waiting for the test). The Royal Family Tomb wall movies (`Dm_MelodyGet_Sun_*`): transitions dropped, untested in game.
- **Which file plays "Mido and Saria"** in Kokiri Forest (spike: `Dm_Kokiri_0060` was rewritten but the user still saw a conversation with them).

## To test in game

- Bomb Bag outside its chest (guide `docs/test-bomb-bag.md`, seed `Rando_BOMBAS16`): **accepted without an in-game test** (user's call, 2026-11-13). Optional: play it to confirm bombs only after the Goron's Bracelet and that Dodongo's Cavern plays normally without its Bomb Bag event.
- `Rando_FullSkipChild1` (guide `docs/test-full-skip-child.md`): the childhood full skip.
- `Rando_FullSkipChild3` (guide `docs/test-full-skip-child-3.md`): shared forced talks done by growing the flow files (exit Kokiri, Mido, Zelda, castle, Royal Family Tomb 276 KB); pending the game test.
- Adult batch of the full skip: `AllSage` and `Get_Epona`, whose old-trim output changed when the parser began to show the case slots of subflow switches (kind 5). `Goto_HyruleCastle` and `SubEvent_GetEponaSong` changed the same way and are in the childhood guide.
- **Dampe's gravedigging prize with another item** (NPC gifts batch 2, test batch 30c/30c2): accepted without an in-game test (user's call, 2026-11-21). The start preset could not keep the night in the graveyard: the Sun's Song made night and day came back at once, even with the castle quest complete. Check it in a normal playthrough (dig at night as a child; the Piece of Heart is a lottery). If it fails, put `Graveyard Dampe Gravedigging Tour` in `gifts.FIXED_GIFTS`. Find out also what keeps the time from running in the start preset.
- Batch 17, attempt 3: seed `TestTokens3`.
- Batch 16 (optional): confirm the 27 "guessed" Skulltulas with a rupee-colour mod so they can also hold key items.
- Acceptance seed `ACEPTACION1` and the round 2b cutscene re-test.

- **The Gerudo Card scene gave nothing** (NPC gifts batch 3a, test batch 32f–32f4, 2026-11-22). The card was renamed to the Boomerang at `Dm_Gerudo_0025` 120 (`GetInEvent_NotLookatObjectTurnOff`), on the full skip. Freeing the last carpenter the game's way (32f4) ran the rescue's ending: the quest reached `Step02` and the Gerudo stopped attacking. But no card scene showed and no Boomerang came. The grant is reachable from the entry in both versions, and the `SubFlowList` rows are complete. Booting `Dm_Gerudo_0025` directly (32f2) stays black. The user accepted it anyway (2026-11-22). With `shuffle_gerudo_card` on, the card's site holds only minor items, and the logic keeps the vanilla card there. Next: the same test without the full skip, and a check of whether the vanilla card is given on the skip at all (the card does nothing in the remake, so a missing card goes unnoticed).

- **OoTR parity, minor findings left** (final review, 2026-11-22):
  - with key items Vanilla, the rewards never move but the spoiler and the site say "Dungeon Reward Locations";
  - `tests/test_gifts.py` reads the full skip's flows by plain path, not `game.flow_path`;
  - `site/presets.js` does not set Shuffle Dungeon Rewards;
  - `generate.FLOW_DIR`/`FLOW_EXT` are unused.

  To watch in play:
  - a stone at an adult boss (if the engine checks the stones themselves, the Door of Time would not open);
  - the Pocket Egg before meeting adult Anju;
  - a lower Hookshot or Gauntlet level after the higher one;
  - the six chests' story events with another item.
- **Time stands still until Link meets Zelda** (seen in play, seed `OOTR1`, 2026-11-22): in the remake the day/night cycle only starts after the garden meeting, and in a seed where Zelda comes late (here she gives the Longshot) the whole early game is frozen at day. OoT and OoTR run the clock from the start. No flow or `WorldParam` flag stops the clock: the flows only set the hour (`EventTrigger_SetTime`: Sun's Song, bed, first field entry). So the gate is likely in the code, on the story quest:
  - `Goto_HyruleCastle` reaches `Complete` in `Goto_HyruleCastle` event 3, after `Dm_HrlCastle_0045`, and `DoorOfTime` `Step01` starts at event 5;
  - `LinkSleepInBed` has a `SleepBeforeMeetZelda` entry and checks `HavePlayedEvent.HyruleCastle_Goto_HyruleCastle_MeetZelda`;
  - dozens of NPC flows check `Goto_HyruleCastle_IsCompleted_Exp`.

  Planned test batch, on the full skip, teleported to Hyrule Field:
  - (a) progress `Goto_HyruleCastle` to `Complete` at the start;
  - (b) set only `HavePlayedEvent.HyruleCastle_Goto_HyruleCastle_MeetZelda`.

  Check for each that time passes, and that Zelda's garden scene still plays and gives the `HC Zeldas Letter` gift. If the clock runs but the scene is lost, move Zelda's gift elsewhere. Workaround meanwhile: the Sun's Song changes the hour. Batch 30c (Dampe at night) hit the same wall, see above.
- **Versioned flows** (found 2026-11-22): `EventFlowFileEntry.Product.110` makes the game load `<name>.110.bfevfl.zs` for 13 flows:
  - the five `Dm_Awake_*_Get` and `Dm_InsideJabu_Jabu_0030`;
  - `Dm_DodongoCave_0010`, `Dm_FinalBattle_BossOut`, `Dm_Goron_0040`, `Dm_HrlCastle_0020`, `DreamBossStage`, `MiniGame_HorseRace`, `Npc_Hylia_Dampe_001`.

  The flow patches (songs, fairies, gifts, merchants) now go to that copy (`GameData.flow_path`). Before this, Dampe's gift (batch 2) was patched in the plain file the game never loads, so a seed with another item at Dampe kept the Piece of Heart in game.

  The cutscene skip already lists most `.110` copies in `full_skip.json` and `cutscenes.json`. Only Dampe's, `MiniGame_HorseRace` and `DreamBossStage` lack one (final review, 2026-11-22). The test batch tool (`tools/make_start_batch.py`) does the same, so batch 30c tested Dampe's plain file.

## To build

- **Gold Skulltula tokens from song scenes (Anywhere):** the fill never puts a token on a song scene, because a token given by a scene's `GetPouchContentByActorName` grant is untested in game (a token is a counter, not a pouch item). To allow it: a test batch where a song scene gives `Obj_Token_Gold`, then drop the rule in `fill._attempt` (the `open_scenes` block).
- **What the Great Fairy fountains cannot give yet** (design `docs/superpowers/specs/2026-11-15-great-fairies-design.md`):
  - **Gold Skulltula tokens:** untested from a fountain's `Dm_SY_GetInEvent` grant, as for song scenes. To allow them: a test batch where a fountain gives `Obj_Token_Gold`.
  - **`Item_BulletBag_Small` and `TBox_DekuSeedBundle`:** they hang `GetInEvent` (batch 25). `Item_ScrubBusinessSeed` (Deku seeds) is kept off too. To allow them: find out why, or give them through another grant.
  - **The Bow, the Slingshot and the Bomb Bag:** `GetInEvent` handed over the Slingshot without its ammo (batch 25), so a fountain could give a weapon the logic counts but that cannot shoot. To allow them: a test batch where a fountain gives each one, checking the ammo.
- **NPC gifts batch 1: decisions to revisit** (design `docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md`):
  - **What a scene gift never gives:** the 12 gifts handed over in a scene use the fountains' forbidden set: Gold Skulltula tokens, `Item_BulletBag_Small`, `TBox_DekuSeedBundle`, `Item_ScrubBusinessSeed`, the Bow, the Slingshot and the Small Bomb Bag. Batch 27b showed that the Medium Bomb Bag comes with its bombs through `GetInEvent`. To allow the others: a test batch where a gift gives each one, checking the ammo.
  - **The world-actor gifts** (LH Sun's Fire Arrows, Ruto's Letter) only receive contents that can be wrapped (`wrappers.can_wrap`, as the Boomerang in 27f), never a token. Rupees and other minor items cannot go there yet. To allow them: find out how to place a minor item there (the game's own world actor, or a wrapper with a pouch row).
  - **The egg has no remake rule:** OoTR asks for `Weird_Egg or Chicken` at Hyrule Castle Grounds, where Malon is, and her talk starts the hatch (27a). If a later version ties the hatch to something else, check this again.
  - **Kak Man on Roof needs an adult:** only `Npc_Hylia_001_Adult` has the grant (`Npc_Hylia_001_Child` has none). Check in game whether the child can get it some other way.
- **The Skull Kid memory game has three prizes** (seen in play, seed `OOTR1`, 2026-11-22): in the remake the game has three grades. `Npc_SkullKid_Child_02` sets `Minigame_SkullKidSession_CurrentGradeSoundNumForSession` to 6 and then 8 notes. The first win gave a blue rupee, the second a red rupee, and the third the shuffled item. Only the last grant (the Piece of Heart, `Minigame_SkullKidSession_IsGetHeartPiece`) is a site today (`LW Ocarina Memory Game`). The two rupee grants (`GetInEvent_NotTurn_NotNpc` calls at events 201 and 202, the 6- and 8-note grades) could be two more remake-only sites, with the logic rule of the memory game. Check which `GetInEvent_NotTurn_NotNpc` call is which grade, and that each one is given once only (not again on a replay).
- **Free Great Fairies still name a price** (batch 26a): the pay question (`Dm_FairyFountain_0009_01`, tag `GreatFairy_Price1..6`) still says "25 rupias" and so on, though nothing is charged. Change the text or the tag's value, or drop the question.
- **Bring back the Great Fairies' price** (the remake charges: Din 25, Power 50, Farore 100, Wisdom 200, Nayru 300, Courage 500). Batch 26 makes the fairies free, as in OoTR. `HavePlayedEvent.Dm_FairyFountain_<name>` is set even when the payment is refused, so with the price kept a refusal would mark the fountain as visited and lose its item. There is no cheap per-fountain flag either: `GameDataList` is a big-endian BYML v7 with hashed names. Possible ways:
  - `TriForcePoint` only summons the fairy when Link has enough rupees (an `EventQueryHasRuppe` before the transition), and the fountain then always charges.
  - Add a new flag to `GameDataList`.

  The logic would then need rupees and the wallet: Courage costs 500, more than the starting wallet of 200 holds. See `docs/great-fairies-research.md`.
- **The castle guards loop on the full skip** (batch 27a, 2026-11-17): when the guards catch Link in the castle garden, they start to talk, the animation cuts and starts again, in a loop. `HyruleCastle_FoundBySecurity` is one of the shared forced talks the full skip grows (`docs/test-full-skip-child-3.md`). Seen with the castle quest moved straight to Step01 by the start preset, so check it on a normal seed too.
- **Remaining full-skip failures** (shared forced talks are done by growing, pending the round 3 test): the targeting tutorial `ActionTutorial_1st_Talk` (conflict), `Dm_InsideJabu_Jabu_0050` (conflict). **Din's Great Fairy plays whole**: its rewrite (copies per call site) took the rupees and gave nothing (batch 26e). Find out why before skipping it again. Compounding growth (copy of a copy) could be optimised by growing in place.
- **"No result" hash `0xa6da0479`** (event 28 of `SubEvent_GetEponaSong`, not a case of its switch 32): find out what produces it.
- **New END cases:** five scene files refuse rewrites that add a case to END (`Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040.110`); decide whether to allow them.
- **Full skip, adult phase:** the same method for the adult scenes, after the childhood test batch.
- **Browser generator on GitHub Pages:** built (`site/`, `randomizer/browser.py`); confirm a full generation in the browser with a real `.nup`.
- **NPC gifts:** batches 1 and 2 are built (designs `docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md` and `2026-11-21-npc-gifts-batch-2-design.md`; acceptance seeds `REGALOS1` and `REGALOS2`, guides `docs/test-npc-gifts.md` and `docs/test-npc-gifts-2.md`). Next: batch 3 (OoTR's optional settings, the ocarinas and the trade sequence). Still to check in game:
  - **The Big Poes' gift with another item** (`Npc_Hylia_048_BottleShop`, its `GetInEvent_Poeshop` entry pointed at `GetInEvent_NotTurn`): untested; the only batch 1 entry change not tried in batch 27.
  - **Gold Skulltula tokens from NPC gifts:** the gifts never give a token (as the fountains and song scenes). Test batch 29c suggests tokens from `GetInEvent` count (the start preset's 10 tokens earned the house reward; the counter was not checked). To allow it: confirm the counter, then drop the token from `GIFT_FORBIDDEN` and `FOUNTAIN_FORBIDDEN`.
  - **The Golden Scale is predictable** (batch 2 final review): `fill.NEEDS_FIRST` puts it only where the Silver Scale is needed, and with every other item assumed owned the Iron Boots reach most dives, so it lands at LH Underwater Item in most seeds (18 of 20 on the fixtures). The rule is what keeps a Silver Scale from coming after the Golden one (test batch 29a2). Ways out: a game patch so a Silver Scale never lowers the Golden one, or a looser rule.
  - **With Tokensanity on, the Gold Skulltula house rewards never get a key item** (batch 2 final review): the fill does not assume the unplaced tokens while placing key items, so the rewards look unreachable. Safe, but less shuffled than OoTR.
  - **The spoiler lists only the user's exclusions**: excluding one scale also keeps the other at its minigame (`fill.linked_exclusions`), which the spoiler does not say.
  - **Batch 2 decisions to revisit** (design `2026-11-21-npc-gifts-batch-2-design.md`): LH Lab Dive needs a child (only the child's flow has the grant; check the adult in game); the Slingshot and Bow upgrades never go to a song scene (`GetPouchContentByActorName` with a bag is untested); the Golden Scale rule (`fill.NEEDS_FIRST`) holds only within the logic.
- **OoTR generator options:** Open Forest / Kakariko / Door of Time / Zora's Fountain / Gerudo Fortress, and the timesavers (skip child stealth, free Rauru reward, skip tower escape, skip Epona race, minigame phases, fast chests, fast bunny hood, plant beans, Ruto on F1, fast shadow boat, free scarecrow, cucco/poe counts, ...).
- **Key items in the Water Temple, Fire Temple, Bottom of the Well and Gerudo Training Ground:** the small-key layout in the remake differs from the N64, so the logic is not reliable there yet.

## Small clean-ups

- Minor test gaps noted during the Tokensanity review (weak node-order test, no test of the RSTB formula for tables, tokens not counted during the assumed fill).
