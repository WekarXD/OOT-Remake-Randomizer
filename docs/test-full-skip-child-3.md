# Test: FullSkipChild3 (childhood full skip, round 3: grown flows)

Third childhood batch of phase 2 (spec §12). Change since `FullSkipChild2` (`docs/test-full-skip-child-2.md`): the rewriter can now **grow** a BFEVFL file, so a forced conversation that shares events with a player-started one gets private copies in new event slots (commits `719a02e`, `29dfc61`, `4612e68`; the RSTB entry of each grown file is updated). Nothing else was retuned.

Measured on this seed: applied 106 -> 130, fallback to the old trimming 35 -> 18, untrimmed (file partly rewritten) 23 -> 16.

Newly applied (all of them need a game check):

- `Npc_Kokiri_007_Child` (`GoToDekuTree`, `GoToMido`, `Talk`): the Kokiri who blocks the exit.
- `Npc_Kokiri_Mido_Child/Talk`: Mido.
- Two `Npc_Hylia_Zelda_Child` `Zelda_CanbeStopped` entries.
- `HyruleCastle_FoundBySecurity` (Courtyard).
- All 16 `MelodyGet_Sun_SubEvent` targets (Royal Family Tomb, Sun's Song). The flow file grew from 126 KB to 276 KB, a size never tried in game.
- `Goto_HyruleCastle/EggHatch` (Malon's egg / cucco). `Step03_01_Npc_Navi_StepStart` still plays in full in the same file.

Generated with `randomizer.generate.generate` (seed `FullSkipChild3`, skip cutscenes and spoiler on) into `test-mod/0400486024DEC000/Rando_FullSkipChild3` (380 files).

## Still shortened as before (old trimming, 18 entries)

`Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040` and `.110`, `Dm_HrlField_0040` and `0050` (owl), `Dm_FairyFountain_Din` (conflict), `Dm_InsideJabu_Jabu_0050` (conflict), `Dm_Kokiri_0045` (fork dependency), `Get_StoneOfForest/GetSword`, `Npc_Kokiri_006_Child/ActionTutorial_1st_Talk` and `AttentionMove_LectureTalk_IsFirst` (targeting tutorial, conflict), and four `SubEvent_GetEponaSong` entries (Malon in the market, Mask talk, `SayHello`).

## Still playing in full (untrimmed, 16 entries)

`Get_StoneOfFire/Get_StoneOfFire_DodongoCavernOpne`, four `Get_StoneOfWater` entries (`IrregularEvent`, `KingZoraCamera`, `StoneOfWater_GetRutoletter`, `fromDream`), `GimmickFlow_RoyalFamilyTomb/CheckStone_To_MelodyGet_Sun`, `Goto_HyruleCastle/Step03_01_Npc_Navi_StepStart`, six `HyruleCastle_FoundBySecurity` entries (`FoundBySecurity`, `_Common`, `_Common_Courtyard`, `_Common_IsFirst`, `Soldier_RandomTalk_IsAfterSecond`), and four `Npc_Hylia_Zelda_Child` entries (`AboutWaterStone`, `InterestTalk_Zelda_Child`, `..._ChangeTheTopic`, `ThatsAll`).

## Setup

1. Copy `test-mod/0400486024DEC000/Rando_FullSkipChild3` to `load/0400486024DEC000/` (Lichii's data folder) and enable only that mod.
2. Start a **new** game.

## Checks

- [ ] The exit Kokiri and Mido no longer stop Link with a conversation? ______
- [ ] Talking to them yourself afterwards works (no freeze; some lines missing is accepted)? ______
- [ ] Targeting tutorial (expected to play, shortened) and Deku Shield tutorial: behaviour? ______
- [ ] Royal Family Tomb / Sun's Song (grown file, 276 KB): song received, no freeze or crash? ______
- [ ] Castle: Malon's egg hatches / the cucco appears, Navi's step plays, nothing stuck? ______
- [ ] Zelda (courtyard and talks) and the castle guards: no freeze, nothing stuck? ______
- [ ] Nothing lost compared with round 2 (items, songs, stones, Door of Time)? ______

## Results

Notes: ______
