# Shuffle Songs: Song Locations — Design

Status: approach approved by the user on 2026-11-14; this document awaits approval. It is part of the "resemble OoTR" work. Batch 20 (`docs/test-batch-20.md`) is the spike it builds on.

## Why

OoTR's "Shuffle Songs" setting is one of the item groups this randomizer lacks. Its first value, **Song Locations**, shuffles the 12 songs among the 12 places that teach a song. Batch 20 showed that a song scene gives whatever its grant names, even when you already own the scene's original song. Both swapped songs worked (Impa ↔ Saria).

## Goals, non-goals, anti-goals

- **Goal:** a new setting, "Shuffle Songs", with **Off** (the default) and **Song Locations**. With Song Locations, the 12 songs are placed among the 12 song locations, the seed stays beatable, and each scene teaches and gives its new song.
- **Goal:** with the setting Off, every existing seed comes out identical to today.
- **Non-goals:** the other two values, Anywhere and Dungeon Rewards (later projects, in that order), and changing dialogue text. Sheik still says "Minuet of Forest" while giving another song.
- **Anti-goal:** a song location whose scene no longer plays because you already own its original song. The song placed there would be lost.

## The 12 song locations

| OoTR location | Scene flow(s) | Original song (actor, OoTR name, `MelodyType`) |
|---|---|---|
| Song from Impa | `Dm_MelodyGet_Zelda` | `Item_Melody_ZeldaLullaby`, Zeldas Lullaby, 0 |
| Song from Malon | `Dm_MelodyGet_Epona` | `Item_Melody_EponaSong`, Eponas Song, 1 |
| Song from Saria | `Dm_MelodyGet_Saria` | `Item_Melody_SariaSong`, Sarias Song, 2 |
| Song from Royal Familys Tomb | `Dm_MelodyGet_Sun` (lessons), `Dm_MelodyGet_Sun_03` (grant) | `Item_Melody_SunSong`, Suns Song, 3 |
| Song from Ocarina of Time | `Dm_MelodyGet_Time` | `Item_Melody_TimeSong`, Song of Time, 4 |
| Song from Windmill | `Dm_MelodyGet_Storm` | `Item_Melody_StormSong`, Song of Storms, 5 |
| Sheik in Forest | `Dm_MelodyGet_Forest` | `Item_Melody_ForestMinuet`, Minuet of Forest, 6 |
| Sheik in Crater | `Dm_MelodyGet_Fire` | `Item_Melody_FireBolero`, Bolero of Fire, 7 |
| Sheik in Ice Cavern | `Dm_MelodyGet_Water` | `Item_Melody_WaterSerenade`, Serenade of Water, 8 |
| Sheik at Colossus | `Dm_MelodyGet_Spilit` | `Item_Melody_SpiritRequiem`, Requiem of Spirit, 9 |
| Sheik in Kakariko | `Dm_MelodyGet_Shadow` | `Item_Melody_ShadowNocturne`, Nocturne of Shadow, 10 |
| Sheik at Temple | `Dm_MelodyGet_Shine` | `Item_Melody_LightPrelude`, Prelude of Light, 11 |

In each scene:

- **Lesson:** subflow calls to `Dm_SY_Ocarina` (`LearningOcarinaPlayExample` shows the notes, `LearningOcarinaFollowExample` makes you repeat them), with a `MelodyType` int.
- **Grant:** a call to `GetPouchContent:GetPouchContentByActorName` with an `ActorName`.

## What triggers each scene (research, 2026-11-14)

The scene flows are started by trigger entries in other flows, such as `SageOfFire:SageOfFire_MelodyGetFire` and `DoorOfTime:Step01_Npc_Hylia_Impa_Child_Talk`. Those entries are in turn requested by map actors and `Logic/*.ainb` graphs. Most conditions are quest steps (`Sage*` challenges) or the scene's own `HavePlayedEvent.Dm_MelodyGet_*` flag, which is the case for the crater and the Colossus. Neither depends on which songs you own.

Every flow that reads a song flag (`IsGet.Item_Melody_*`, `EventQueryCheckIsGet`) was checked. Note that in a boolean query, the case with value 1 is *false* and value 0 is *true*.

- **Windmill: breaks.** `Npc_Hylia_009_Adult` reads `IsGet.Item_Melody_StormSong` four times, and each time the song-not-owned branch is the one that leads to the grant. If Song of Storms was found elsewhere first, the location is lost.
  - Events 51 and 54 (entries `PlayStormSong_Adult` and `PlayStormSong_Back_Adult`) go to `Dm_MelodyGet_Storm`.
  - Event 4 (`Talk`) is what sets `KakarikoVillage_Npc_Hylia_009_Adult_BeforeStormSong` and moves on to `StormSong_Near`, which advances the `SubEvent_GetStormSong` quest to `ReadyForGetStormSong`.
  - Event 17 (`Near`, `StormSong_Near`) only picks a balloon line.
- **Crater: wrong flag.** `Dm_MelodyGet_Fire` event 0 sets `IsGet.Item_Melody_FireBolero` to true, whatever song the scene gives.
- **Harmless:** the remaining checks only choose dialogue lines:
  - Sheik's talk after Kakariko (`Npc_Hylia_Sheik_Adult` 22);
  - Navi's repeat lines in `SageOfWater` 267–269 and `BottomOfTheWell` 10;
  - Sheik's lines at the Temple (`AllSage` 72, 73, 125);
  - the Kokiri lines about Saria's Song;
  - the Kakariko townsfolk lines about Song of Storms (`Npc_Hylia_007_Adult`, `Npc_Hylia_051_Adult` 140, the child windmill man).
- **Unrelated:** the Serenade is triggered by the Ice Cavern's Iron Boots chest (`GetEventName: SageOfWater_MelodyGet_Water`). That chest is already fixed (`needs_event_patch`), so its trigger never moves.

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| Shuffle all 12, and fix the scenes that check their original song (windmill, crater) | Matches OoTR; two small flow patches that need an in-game check | **Chosen** |
| Shuffle only the scenes that don't check their song | No patches, but it is no longer OoTR's setting | Rejected |

## Design

**Setting.**

- `Settings.shuffle_songs: str = 'off'`, with values `SHUFFLE_SONGS = ('off', 'song_locations')`. An unknown value raises `FillError`.
- `_settings_key` drops the field when it is `'off'`, like `tokensanity`, so existing seeds keep their RNG.
- The site gets a "Shuffle Songs" select (Off / Song Locations), saved like the other options.
- `browser.py` validates the value.
- The spoiler log shows the setting when it is not Off, plus a "Songs" section mapping each song location to its song.

**Song table.** A data module (e.g. `randomizer/songs.py`) holds the 12 rows of the table above: OoTR location, flows, actor, OoTR song name and `MelodyType`. It is the single source for the fill, the patch and the spoiler. A test checks that each OoTR name matches `vanilla_item` in `locations.json`.

**Fill.**

- With Song Locations, the songs are placed **before** the key items, because songs gate key items (Requiem opens the Spirit Temple, for example).
- They use assumed fill, as OoTR does with restricted pools. Each song in shuffled order goes to a random song location reachable while assuming the remaining songs and all the key items still to place are owned.
- The key-item phase then runs with the songs fixed in `fixed`. The final `can_beat` check covers both phases.
- When the setting is Off, the song phase draws nothing from the RNG.
- **My call:** songs shuffle even in the `vanilla` key-item mode. The two settings are independent, as in OoTR.
- The songs' placement is returned beside the chest placement, as `{OoTR song location: song actor}`.

**Patch.** For each song location whose song changed, the flows are edited on top of the full skip's version when Skip cutscenes is on (as batch 20 did):

- Grant: `ActorName` becomes the new actor.
- Lessons: every `MelodyType` lesson value becomes the new song's value. With the full skip, the lessons are dropped (`subflows_drop`), so this only shows with the skip off.
- Events are found **by value**, not by index: the grants with the old actor and the lessons with the old type. The build fails loudly if a scene has no grant.
- Crater: the `IsGet.Item_Melody_FireBolero` set in `Dm_MelodyGet_Fire` names the new song's flag instead.
- Windmill: all four `IsGet.Item_Melody_StormSong` queries in `Npc_Hylia_009_Adult` (events 4, 17, 51 and 54) read the location's own flag, `HavePlayedEvent.Dm_MelodyGet_Storm`, instead. They are found by value, and the build fails if there are not exactly four.
- Royal Family's Tomb: the lessons are in `Dm_MelodyGet_Sun` and the grant in `Dm_MelodyGet_Sun_03`.
- Lesson end (found in batch 22): a lesson ends with `Dm_SY_Ocarina:LearningOcarinaPlayAuto` for melodies 0–5 and `LearningOcarinaPlayAutoForSeek` for the warp songs 6–11. Each handles only its own group, and any other melody hangs the game. When the new song is of the other group, the call is retargeted (`bfevfl.set_subflow_entry`).

**Logic.** OoTR's world files already treat these 12 locations as song locations (`shuffle_song_items: "song"` in `vanilla_settings.json`). Their rules are used as they are. The remake starts the Sheik scenes through quest steps that may differ from OoTR's conditions. The in-game test is meant to catch that; any difference found becomes a `REMAKE_RULES` entry.

**Tests.**

- The table matches OoTR.
- With Off, placements and output are identical to today, including for a fixed existing seed.
- With Song Locations:
  - each song is placed exactly once, only on song locations;
  - the result is deterministic per seed;
  - every seed in a sample is beatable.
- Patching a scene changes only its grant, its lesson values and, for the crater and the windmill, those flags. The other events stay identical.
- After the windmill patch, `Npc_Hylia_009_Adult` no longer reads `IsGet.Item_Melody_StormSong` anywhere.

**Adult start presets (for batch 22; the user's choice, 2026-11-14).** The test teleport (`randomizer/test_start.py`) learns to make Link an adult. It copies what the game does when the Master Sword is drawn again (`Market_Child_Field_ChildToAdult`):

1. call `ReplaceEquipmentForEraChange:ReplaceEquipmentForEraChange`, which swaps the equipment;
2. set `Sequence_IsChildhood` to false;
3. change to an `*_Adult` map.

- `StartPreset` gains `adult: bool = False`. When it is true, the chain runs steps 1 and 2 right before the teleport, whose `banc` must then be an `*_Adult` map (checked).
- The subflow call goes through the existing entry-list and `SubFlowList` handling (`chain_calls`, `subflow_closure`).
- Batch 22 uses two adult presets:
  - Kakariko by the windmill, with the `SubEvent_GetStormSong` steps it needs;
  - the crater's `FireBolero` start position, with the `SageOfFire` steps that make Sheik appear.
- Either preset may also give the Master Sword and an ocarina. Which quest steps and `HavePlayedEvent` flags each scene needs is found while building the batch, as the castle quest was for batch 20.

**In game.**

- **Test batch 22:** the windmill and the crater given swapped songs, with the full skip, to check the two patches. Either a hand-built batch, or a seed with a chosen placement.
- **Afterwards:** a full Song Locations seed, played as far as is practical.

## Left to the builder

- The module and function names.
- How the placement reaches `patch.write_mod` and the spoiler.
- The sample size for the beatable-seed test.
- Each adult preset's start position, quest steps and flags (see Adult start presets).
