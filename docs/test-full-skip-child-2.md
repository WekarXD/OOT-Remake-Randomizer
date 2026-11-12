# Test: FullSkipChild2 (childhood full skip, round 2)

Second childhood batch of phase 2 (spec §12). Changes since `FullSkipChild1` (`docs/test-full-skip-child.md`), from the user's report of 2026-11-12:

- **Boss intros and defeats play again** (user decision): the `*_BossIn` / `*_BossOut` timelines and the boss entries of `Get_StoneOfForest`, `Get_StoneOfFire` and `Get_StoneOfWater` are no longer targeted.
- **King Zora** keeps his animations in `Dm_Zora_0010` (`skip_actions.json` `actor_actions`), so he moves aside after reading Ruto's letter.
- **Zora's Fountain arrival** (`Dm_ZoraFountain_0000`) is no longer rewritten: its fork was serialised so that Link walked on a black screen.
- **Owl**: `Dm_HrlField_0030/0040/0050`, `Dm_LostWood_0010` and `Npc_Kaepora_LakeHylia` (Talk, Near) are now targeted. `Npc_Kaepora_DeathMountainTrail` is unchanged by the rewrite.
- **Great Fairies**: `Dm_FairyFountain_Frore` (Farore's Wind) is now rewritten. `Dm_FairyFountain_Din` (Din's Fire) fails the rewrite (`conflict`) and keeps the old trimming.
- **Tutorials**: `Npc_Kokiri_010_Child/DekuShield_TutorialTalk` (shield) is now rewritten. The targeting tutorial (`Npc_Kokiri_006_Child`) still fails (`conflict`, `shared`) and keeps the old trimming.

Generated with `randomizer.generate.generate` (seed `FullSkipChild2`, default settings, skip cutscenes and spoiler on) into `test-mod/0400486024DEC000/Rando_FullSkipChild2`. The spoiler's "Cutscenes not skipped" section lists 35 entries shortened as before and 23 played in full.

## Setup

1. Copy `test-mod/0400486024DEC000/Rando_FullSkipChild2` to `load/0400486024DEC000/` (Lichii's data folder) and enable only that mod.
2. Start a **new** game.

## Checks

- [ ] Gohma, King Dodongo and Barinade: intro and defeat scenes play, and the reward and blue warp still work? ______
- [ ] King Zora moves aside right after reading Ruto's letter? ______
- [ ] Zora's Fountain arrival: no black screen, Link where expected? ______
- [ ] Owl (Hyrule Field, Lost Woods, Lake Hylia): conversations gone, nothing stuck? ______
- [ ] Great Fairy of Farore's Wind: no conversation, spell received? ______
- [ ] Deku Shield tutorial gone? ______
- [ ] Anything that regressed compared with round 1 (items, songs, stones, freezes)? ______

## Results

Notes: ______
