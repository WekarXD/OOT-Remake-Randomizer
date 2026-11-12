# Test: FullSkipChild1 (childhood full skip)

First test batch of phase 2 of the full cutscene skip (spec `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §12). It is a normal randomizer seed with "Skip cutscenes" on, so it also carries the item placement and the spoiler.

Generated with `randomizer.generate.generate` (seed `FullSkipChild1`, default settings, skip cutscenes on, spoiler on) into `test-mod/0400486024DEC000/Rando_FullSkipChild1` (397 files).

## Setup

1. Copy `test-mod/0400486024DEC000/Rando_FullSkipChild1` to `load/0400486024DEC000/` and enable only that mod.
2. Start a **new** game. Keep the spoiler open to know where the key items are.

## Path and checks

Play: new game, Deku Tree, Gohma, Saria, castle (Malon, Zelda, letter, Lullaby), Kakariko, Death Mountain, Goron City, Dodongo's Cavern, Zora's Domain, Jabu-Jabu, Door of Time.

| Stop | Should no longer play | Must still happen | Link ends up |
|---|---|---|---|
| New game | Intro movie, Navi flying to the house (only a 10 s fade-in is left) | Link wakes up in his house | In the house, with control |
| Kokiri Forest | Navi/Saria/Mido scenes, targeting and shield tutorials | Fairy Ocarina from Saria; the way to the Deku Tree opens | Free in the forest |
| Deku Tree and Gohma | Gohma intro and defeat scenes, the Deku Tree's speech, movie and Ganondorf vision | Kokiri Emerald; the forest exit opens | Outside the tree |
| Castle | Malon, Zelda (garden, story), Impa | Zelda's Letter, Zelda's Lullaby, Epona's Song from Malon | In the castle or market, with control |
| Kakariko | Entry and gate scenes | The gate opens with the letter | Free in Kakariko |
| Death Mountain | Trail and Darunia-related scenes | The way up opens | Free on the mountain |
| Goron City | Goron scenes | Goron's Ruby, Goron Tunic as in the seed | In Goron City |
| Dodongo's Cavern | Opening and boss scenes | The cavern opens, boss dies, the reward is received | Outside the cavern |
| Zora's Domain | King Zora, Ruto scenes | Zora's Sapphire, Ruto's Letter as in the seed | In the Domain |
| Jabu-Jabu | Entry, Ruto scenes, boss | The reward is received | Outside Jabu-Jabu |
| Door of Time | Temple of Time scenes | The door opens | In the Temple of Time |

Also note:
- **Loading screen after the intro** is longer: the intro movie used to hide it.
- **Navi's colour** after she flies to Link's house (`Dm_Kokiri_0030` is cut to its fade-in): is it right?
- **Gifts**: does Link still raise the item when an NPC gives it, or is it simply received? (Decides whether the item-get presentation becomes a task.)

## Scenes that will still play

From the spoiler's "Cutscenes not skipped" section (the full list is there). They are not bugs; they are the known gaps.

| Group | Scenes | Why |
|---|---|---|
| Conversations that share lines with ones you start yourself | About 56 forced talks: Kokiri blocking the exit (`Npc_Kokiri_007_Child`, `Npc_Kokiri_011_Child`), Mido's Talk, Zelda and Malon talks, castle guards (`HyruleCastle_FoundBySecurity`), `SubEvent_GetEponaSong` | Cutting them would also cut the talks you start. They use the old trimming, or stay as they are. |
| Not proven safe yet | `Dm_Kokiri_0045` (the door fork), `Dm_InsideJabu_Jabu_0050` | A flag race, or two paths that need different next steps. |
| Needs a new "end" case | `Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040.110`, and parts of `Get_StoneOfFire`, `Get_StoneOfForest`, `Get_StoneOfWater` | The rewrite would have to add a way to finish that does not exist. Refused on purpose. |
| No spare slot to copy | Parts of `Get_StoneOfForest`, `MelodyGet_Sun_SubEvent`, `SubEvent_GetEponaSong` | Nothing in the game data can host the copy. |
| Royal Family Tomb | `GimmickFlow_RoyalFamilyTomb`, `MelodyGet_Sun_SubEvent` | Sun's Song scenes; the movies there have no flow. Not on the childhood path. |

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
