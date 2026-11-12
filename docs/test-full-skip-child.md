# Test: FullSkipChild1 (childhood full skip)

First test batch of phase 2 of the full cutscene skip (spec `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §12). It is a normal randomizer seed with "Skip cutscenes" on, so it also carries the item placement and the spoiler.

Generated with `randomizer.generate.generate` (seed `FullSkipChild1`, default settings, skip cutscenes on, spoiler on) into `test-mod/0400486024DEC000/Rando_FullSkipChild1` (397 files).

## Setup

1. Copy `test-mod/0400486024DEC000/Rando_FullSkipChild1` to `load/0400486024DEC000/` in the Lichii emulator's data folder and enable only that mod there.
2. Start a **new** game. Keep the spoiler open to know where the key items are.

## Path and checks

Play: new game, Deku Tree, Gohma, Saria, castle (Malon, Zelda, letter, Lullaby), Kakariko, Death Mountain, Goron City, Dodongo's Cavern, Zora's Domain, Jabu-Jabu, Door of Time.

**This table is what we expect, not something verified.** Tell us what you actually see; the play-through corrects it. The scenes listed in the next section are known to still play (shortened or in full), so they are not failures.

| Stop | Expected to be skipped | Must still be received or opened | Link should end up |
|---|---|---|---|
| New game | The intro movie; Navi's flight to the house is cut to a short fade-in | Link wakes up in his house | In the house, with control |
| Kokiri Forest | Most of the Saria and Navi scenes (Mido and the Kokiri blocking the exit are in the next section) | Fairy Ocarina; the way to the Deku Tree | Free in the forest |
| Deku Tree and Gohma | The Deku Tree's speech, its movie and the Ganondorf vision | Kokiri Emerald | Outside the tree |
| Castle | Malon and Zelda scenes (some Zelda talks are in the next section) | Zelda's Letter, Zelda's Lullaby, Epona's Song | In the castle or market, with control |
| Kakariko, Death Mountain, Goron City | Most cutscenes there (see the next section for the ones that remain) | Whatever opens the way on, and the Goron's Ruby | Free to walk on |
| Dodongo's Cavern | Most scenes (`Dm_DodongoCave_0010` is in the next section) | The cavern opens, the boss dies, the reward is received | Outside the cavern |
| Zora's Domain, Jabu-Jabu | Most scenes (`Dm_InsideJabu_Jabu_0050` is in the next section) | Zora's Sapphire; Ruto's Letter as the seed places it | Free to walk on |
| Door of Time | Most scenes | The door opens | In the Temple of Time |

Also note:
- **Loading screen after the intro** is longer: the intro movie used to hide it.
- **Navi's colour** after she flies to Link's house (`Dm_Kokiri_0030` is cut to its 10 s fade-in): is it right?
- **Gifts**: does Link still raise the item when an NPC gives it, or is it simply received? (Decides whether the item-get presentation becomes a task.)

## Scenes that will still play

Taken from the spoiler's "Cutscenes not skipped" section (the full list, with exact reasons, is there). They are known gaps, not bugs. Counts are entries, not files.

**Shortened as before (29 entries).** The full skip could not rewrite them, so the old trimming applies: they play, but cut down.

| Scenes | Why |
|---|---|
| `Npc_Kokiri_007_Child` (3), `Npc_Kokiri_011_Child` (1): the Kokiri blocking the exit, Mido's guide talks | Share lines with conversations you start yourself |
| `Npc_Hylia_Zelda_Child` (6), `Npc_Hylia_ImperialSoldier_001_Child` (1) | Share lines with conversations you start yourself; one fails the safety check |
| `HyruleCastle_FoundBySecurity` (6): castle guards | Share lines, or two paths needing different next steps |
| `SubEvent_GetEponaSong` (4): Malon in the market | Share lines; one has an unknown result code (`0xa6da0479`); one has no spare slot to copy into |
| `Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040.110` | The rewrite would need a new way to finish, which is refused on purpose |
| `Dm_Goron_0040` | Shares lines with another path |
| `Dm_InsideJabu_Jabu_0050` | Two paths that need different next steps |
| `Dm_Kokiri_0045` | Depends on the house-door flag in another branch; not proven safe |

**Play in full (28 entries).** Other entries of the same files were rewritten, so these are left untouched rather than mixing two edits.

| Scenes | Why |
|---|---|
| `Goto_HyruleCastle` (2: `EggHatch`, `Step03_01_Npc_Navi_StepStart`) | Shares lines / two paths needing different next steps |
| `Get_StoneOfFire` (1), `Get_StoneOfForest` (4, including `GetSword` and three boss-appearance skips), `Get_StoneOfWater` (5, including King Zora's camera and Ruto's letter) | Need a new way to finish, share lines, or have no spare slot to copy into |
| `Npc_Kokiri_Mido_Child/Talk` (1) | Shares lines with another path |
| `GimmickFlow_RoyalFamilyTomb` (1), `MelodyGet_Sun_SubEvent` (14) | Sun's Song scenes: one failed the safety check, the rest share lines or have no spare slot |

**Not written (14 files).** Files where nothing was rewritten at all; the old trimming applies, as in the first table.

## Results

Played: ______

- [ ] New game: intro gone, Link in his house with control? ______
- [ ] Navi's colour right after the house? ______
- [ ] Fairy Ocarina received, forest exit opens? ______
- [ ] Gohma and the Kokiri Emerald; no speech scenes? ______
- [ ] Letter, Lullaby and Epona's Song received? ______
- [ ] Kakariko, Death Mountain, Goron City, Dodongo: anything blocked or missing? ______
- [ ] Zora's Domain and Jabu-Jabu: stone and letter received? ______
- [ ] Door of Time opens? ______
- [ ] Does Link raise gifted items? ______
- [ ] Any freeze, black screen, wrong position or sound left playing? ______
- [ ] Scenes that still played and are not in the table above: ______
