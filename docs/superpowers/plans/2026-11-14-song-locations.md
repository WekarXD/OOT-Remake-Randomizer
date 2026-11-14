# Song Locations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** add OoTR's "Shuffle Songs: Song Locations". Before that, add adult start presets and test batch 22, which check the two scene patches in game.

**Architecture:**

- `randomizer/songs.py` holds the 12-row song table and the pure flow patches: grants, lessons, the crater flag and the windmill queries.
- `fill.py` gains a song phase. It runs before the key items in the same attempt, and `place_all` returns chests and songs.
- `generate.py` patches the song flows on top of the full skip's files and passes them to `patch.write_mod` as extra files.
- `test_start.py` gains `adult`, used by the batch 22 tool.

**Tech Stack:** Python 3.14, unittest (`python -m unittest`), the repo's own BFEVFL/BYML/zstd code.

**Spec:** `docs/superpowers/specs/2026-11-14-song-locations-design.md`

## Global Constraints

- With `shuffle_songs == 'off'`, every placement and every output file is byte-identical to today. The song phase draws nothing from the RNG, and `_settings_key` omits the field.
- `SHUFFLE_SONGS = ('off', 'song_locations')`. The default is `'off'`.
- Find flow events **by value** (old actor, old `MelodyType`, flag name), never by hard-coded index. Raise on a missing grant, and on a windmill count other than 4.
- Never commit game data (`*.nup`, `test-mod/`, `output/`).
- Commits use `type: description`. Repo docs are in English. Spanish test guides go in `local/` (git-ignored).
- Tests that need the game read `OOT_NUP` and skip without it. Run them with `OOT_NUP="C:/Users/wekar/Documents/Github/Randomizer OOT Remake/The Legend of Zelda Ocarina of Time [0400486024DEC000][v131072].nup" python -m unittest ...`.
- In a boolean query, case value 0 is true and case value 1 is false.

## Review Focus

1. **Full skip on with Song Locations.** The full skip rewrites `Dm_MelodyGet_*`, and its lessons are dropped. The patch must find the grant in the *skip's* version and must not fail when no lesson remains. This is tested in Task 6.
2. **A song location that keeps its own song.** The flow is left untouched, but the windmill and crater patches still apply when Storm or Bolero is elsewhere. This is tested in Task 3.
3. **Songs on with key items in `vanilla` mode.** Only songs move, and the seed is still beatable. This is tested in Task 5.
4. **A seed whose songs block every key item.** A failed attempt retries rather than crashing, through `MAX_ATTEMPTS`. This is covered by the beatable-sample test in Task 5.
5. **Bad `shuffle_songs` from the site.** It is rejected with a clear message. This is tested in Task 7.

---

### Task 1: Adult start presets

**Files:**
- Modify: `randomizer/test_start.py` (`StartPreset`, `_chain`)
- Test: `tests/test_test_start.py`

**Interfaces:**
- Produces:
  - `StartPreset.adult: bool = False`;
  - constants `ERA_CHANGE = ('ReplaceEquipmentForEraChange', 'ReplaceEquipmentForEraChange')` and `CHILDHOOD_FLAG = 'Sequence_IsChildhood'`.

- [ ] **Step 1: Write the failing tests** in `tests/test_test_start.py`:
  - `test_adult_chain`. Build `StartPreset('DeathMountainCrater_Adult', 'FireBolero', adult=True)` and walk the chain from `HOOK_ENTRY`, as `test_chain_order` does. Assert that, right before the final `Dm_SY_BancChangeGo` call:
    - there is a SUBFLOW `ERA_CHANGE`;
    - before that SUBFLOW there is a `EventTriggerSetGameDataBool` with `(CHILDHOOD_FLAG, False)`.

    Also assert that `chain_calls(preset)` contains `ERA_CHANGE`.
  - `test_adult_needs_adult_map`. Assert that `_chain`, and therefore `apply_start`, raises `ValueError` for `StartPreset('HyruleField_Child', 'X', adult=True)`.
  - `test_child_chain_unchanged`. The default preset's chain has no `ERA_CHANGE` call.

- [ ] **Step 2: Run** `python -m unittest tests.test_test_start`. Expected: the new tests FAIL (`adult` is an unexpected keyword).

- [ ] **Step 3: Implement.**
  - Add the field and the constants.
  - In `_chain`, when `preset.adult` is set, raise `ValueError` unless `preset.banc.endswith('_Adult')`. Then append `_flag(CHILDHOOD_FLAG, False)` and `SubflowSpec(*ERA_CHANGE, {})` immediately before the teleport spec. This mirrors `Market_Child_Field_ChildToAdult` events 3 and 1.

- [ ] **Step 4: Run** `python -m unittest tests.test_test_start tests.test_evfl_append`. Expected: all pass.

- [ ] **Step 5: Commit** `feat: start presets can make Link an adult`.

### Task 2: Song table and `set_int_param`

**Files:**
- Create: `randomizer/songs.py`
- Modify: `randomizer/formats/bfevfl.py` (add `set_int_param` next to `set_string_param`)
- Test: `tests/test_songs.py` (new), `tests/test_bfevfl.py`

**Interfaces:**
- Produces:
  - `set_int_param(data: bytes, event_index: int, key: str, value: int) -> bytes`. It raises `BfevflError` if the parameter is missing or is not INT.
  - `@dataclass(frozen=True) class SongLocation: location: str; song: str; actor: str; melody: int; flows: tuple[str, ...]`. Here `song` is the OoTR name, and `flows` are the flows holding its lessons or grant.
  - `SONGS: tuple[SongLocation, ...]`, with the 12 rows in the spec's table order.
  - `SONG_BY_LOCATION: dict[str, SongLocation]` and `SONG_BY_ACTOR: dict[str, SongLocation]`.
  - `SHUFFLE_SONGS = ('off', 'song_locations')`.

- [ ] **Step 1: Write the failing tests.**
  - `tests/test_songs.py::test_table_matches_ootr`: for every row, `ootr_data.load_locations()[row.location]['vanilla_item'] == row.song`.
  - `test_table_is_a_permutation`: there are 12 distinct locations, actors and melodies, and `sorted(melody) == [0..11]`.
  - `tests/test_bfevfl.py::test_set_int_param`: on the real `Dm_MelodyGet_Zelda` (skip without `OOT_NUP`), setting event 4 `MelodyType` to 2 reads back 2. All other events' params are unchanged, and a STRING key raises.

- [ ] **Step 2: Run** `python -m unittest tests.test_songs tests.test_bfevfl`. Expected: FAIL with an ImportError.

- [ ] **Step 3: Implement** the table from the spec. The Royal Family's Tomb row has `flows=('Dm_MelodyGet_Sun', 'Dm_MelodyGet_Sun_03')`. Implement `set_int_param` like `set_string_param`'s slot lookup, packing `<i` at `it + 0x10` (the same as batch 20's helper).

- [ ] **Step 4: Run** the same tests. Expected: PASS.

- [ ] **Step 5: Commit** `feat: song location table`.

### Task 3: Song flow patches

**Files:**
- Modify: `randomizer/songs.py`
- Test: `tests/test_songs.py`

**Interfaces:**
- Consumes: `SONGS`, `set_int_param`, `bfevfl.set_string_param`.
- Produces:
  - `GRANT_CALL = ('GetPouchContent', 'GetPouchContentByActorName')`;
  - `WINDMILL_FLOW = 'Npc_Hylia_009_Adult'`;
  - `CRATER_FLOW = 'Dm_MelodyGet_Fire'`;
  - `song_flow_patches(read: Callable[[str], bytes], placement: dict[str, str]) -> dict[str, bytes]`. `placement` maps OoTR location to song actor. `read(flow_name)` returns the decompressed current flow, so the caller decides between the skip's version and the game's. The result maps flow name to decompressed new bytes, for the changed flows only.

Rules:

- For each location whose actor differs from its row's actor, in each of its `flows`:
  - every event whose `ActorName == old actor` gets the new actor;
  - every event whose `MelodyType == old melody` gets the new melody, but only in subflow calls to `Dm_SY_Ocarina` whose `sub_entry` starts with `LearningOcarina`.
- Raise `ValueError` if no grant with the old actor exists across the location's flows.
- If the crater's song is not Bolero, the `EventTriggerSetGameDataBool` with `GameDataName == 'IsGet.Item_Melody_FireBolero'` in `CRATER_FLOW` gets `'IsGet.' + new actor`.
- If Song of Storms is not at the windmill, every `EventQueryIsGameDataBool` with `GameDataName == 'IsGet.Item_Melody_StormSong'` in `WINDMILL_FLOW` gets `'HavePlayedEvent.Dm_MelodyGet_Storm'`. Raise if there are not exactly 4.
- `placement` must be a permutation of the 12 actors over the 12 locations. Otherwise raise `ValueError`.

- [ ] **Step 1: Write the failing tests** (game data; skip without `OOT_NUP`; `read` from the `.nup` through `ZsCodec`):
  - `test_identity_placement_changes_nothing`: the vanilla placement returns `{}`.
  - `test_swap_impa_saria`: the result has exactly the keys `{'Dm_MelodyGet_Zelda', 'Dm_MelodyGet_Saria'}`.
    - In Zelda, the grant actor is `Item_Melody_SariaSong`, and both `LearningOcarina*` calls have `MelodyType` 2.
    - Every other event's params are equal to the original's.
  - `test_crater_flag_follows_song`: putting Storm at the crater and Bolero at the windmill makes the crater's flag `IsGet.Item_Melody_StormSong`.
  - `test_windmill_queries`: with that same swap, `WINDMILL_FLOW` is in the result and no event in it reads `IsGet.Item_Melody_StormSong`. Exactly 4 events read `HavePlayedEvent.Dm_MelodyGet_Storm`.
  - `test_windmill_untouched_when_storm_stays`: in a swap of Impa and Saria only, `WINDMILL_FLOW` is not in the result.
  - `test_sun_split`: putting Saria's Song at the Royal Family's Tomb and the Sun's Song at Saria changes `Dm_MelodyGet_Sun` (lessons) and `Dm_MelodyGet_Sun_03` (grant).
  - `test_bad_placement_raises`: a duplicate actor raises `ValueError`.

- [ ] **Step 2: Run** `python -m unittest tests.test_songs`. Expected: the new tests FAIL (`song_flow_patches` is missing).

- [ ] **Step 3: Implement** `song_flow_patches` and its private helpers, each under 50 lines.

- [ ] **Step 4: Run** the same tests. Expected: PASS.

- [ ] **Step 5: Commit** `feat: patch song scenes for a song placement`.

### Task 4: Test batch 22 (windmill and crater) — STOP for the in-game test

**Files:**
- Create: `tools/make_song_batch.py`, `docs/test-batch-22.md`, `local/test-batch-22.md` (Spanish, not committed)
- Modify: `docs/TODO.md` ("To test in game")

**Interfaces:**
- Consumes:
  - `make_start_batch.Batch`, `add_start` and `write_mod`;
  - `files_with_fallback(game, FULL_SKIP_PHASE)`;
  - `song_flow_patches`;
  - `StartPreset(adult=True)`.

**Batch:** the full skip, with Storm at the crater and Bolero at the windmill (the rest vanilla). The adult preset starts at `DeathMountainCrater_Adult` / `FireBolero`. The tester gets Song of Storms from the crater's Sheik, walks down to Kakariko and checks that the windmill still gives Bolero. That covers both patches.

- [ ] **Step 1: Research and record in the guide** the facts the preset needs:
  - the `SageOfFire` steps that make the crater's Sheik appear. Read `Logic/DeathMountainCrater_Adult_Prefab_a0e2` and `e63c`'s strings, and the `EventExecuteProgressChallengeStep` calls with `ChallengeName` `SageOfFire` found through the scratchpad `grep_flows.py`.
  - the `SubEvent_GetStormSong` steps (`ReadyForGetStormSong`, `step02`, `step03` are known) and what the windmill needs. Pick the minimum so that the windmill man's `PlayStormSong_Adult` can trigger.
  - the items:
    - an ocarina (`Item_Ocarina_Fairy` is known to work);
    - the Master Sword;
    - the Goron Tunic, for the crater heat.

    Verify the actor names with the `.nup` (`Pack/Actor` or the actor list used by `wrappers.pouch_rows`).

  Each fact goes in the guide with its source. Where the source is a guess, the guide says so.

- [ ] **Step 2: Write `tools/make_song_batch.py`.** It follows `make_start_batch.main()`: `python -I tools/make_song_batch.py <nup> <out_mod_dir>`. It:
  1. builds the full skip;
  2. applies `song_flow_patches` with `read=batch.read` on flow paths;
  3. applies `add_start` with the adult preset;
  4. writes the result.

  Smoke-check by running it to `test-mod/0400486024DEC000/TestBatch22`. Expected: it lists `Dm_MelodyGet_Fire`, `Dm_MelodyGet_Storm`, `Npc_Hylia_009_Adult`, the hook flow, `ANALYZED_INFO` and the RSTB.

- [ ] **Step 3: Write the guides** (English in `docs/`, Spanish in `local/`) in the batch 20 format: setup (new game, leave the house), checks (does Sheik appear, which song he gives, does the windmill still teach after owning Storm and what it gives, black screens) and results.

- [ ] **Step 4: Commit** `feat: test batch 22 for the windmill and crater song patches` (the tool, the docs and TODO).

- [ ] **Step 5: STOP.** Ask the user to play batch 22, and iterate on the preset as for batch 20 (each attempt recorded in both guides) until both patches are confirmed. Tasks 5–8 start only after that.

### Task 5: Song phase in the fill

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `SONGS`, `SHUFFLE_SONGS`.
- Produces:
  - `Settings.shuffle_songs: str = 'off'`;
  - `@dataclass(frozen=True) class Placement: chests: dict[int, str]; songs: dict[str, str]`, where `songs` maps OoTR location to song actor, holding all 12;
  - `place_all(<same args as place>) -> Placement`. `place(...)` keeps its signature and returns `place_all(...).chests`.

Algorithm:

- With `'off'`, `songs` is the vanilla table and nothing changes. `_settings_key` deletes `shuffle_songs` when it is `'off'`.
- Otherwise, in `_attempt`, before the key items:
  1. Shuffle the 12 song actors with `rng`.
  2. In `base`, replace the 12 song locations with `FILLER`.
  3. For each song, compute `reach = world.reachable_locations(base_with_placed_songs, owned=[OoTR names of the remaining songs] + to_place)`, and pick `rng.choice` among the free song locations in `reach`. Return `None` if there are none.
  4. The key-item phase then runs with those songs in `base`.

  Songs enter `fixed` as their OoTR names (`SONG_BY_ACTOR[a].song`).
- `vanilla` key-item mode with songs on: run the song phase with no moving key items. The chests stay original.
- An unknown value raises `FillError`.

- [ ] **Step 1: Write the failing tests:**
  - `test_songs_off_identical`: `place_all(..., shuffle_songs='off').chests == place(...)` for seeds `'A'`, `'B'`, and `songs` is the vanilla map.
  - `test_songs_permutation`: with `'song_locations'`, `songs` is a permutation of the 12 actors over the 12 locations. It differs from vanilla for at least one of 5 seeds, and it is deterministic per seed.
  - `test_songs_beatable_many`: 20 seeds; for each, build `fixed` from the result (chests through `_fixed_for`, songs as OoTR names) and assert `world.can_beat`.
  - `test_songs_with_vanilla_key_items`: the chests equal the originals, and the songs are a permutation.
  - `test_songs_unknown_value_raises`.
  - `test_songs_not_in_key_when_off`: `_settings_key` is unchanged by the field being `'off'`.

- [ ] **Step 2: Run** `python -m unittest tests.test_fill`. Expected: FAIL.

- [ ] **Step 3: Implement** with a new `_place_songs(rng, world, base, to_place) -> dict[str, str] | None` called from `_attempt`. `_attempt` returns `(chests, songs)` or `None`.

- [ ] **Step 4: Run** `python -m unittest tests.test_fill tests.test_logic`. Expected: PASS.

- [ ] **Step 5: Commit** `feat: Song Locations fill`.

### Task 6: Generate, mod files and spoiler

**Files:**
- Modify: `randomizer/generate.py`, `randomizer/spoiler.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `place_all`, `Placement`, `song_flow_patches`.
- Produces: the spoiler JSON gains `settings.shuffle_songs` (only when not `'off'`) and `songs: [{'location', 'song', 'label'}]` sorted by location. The text adds a `Shuffle Songs: Song Locations` line and a `Songs` section.

Wiring:

- `generate` calls `place_all`.
- If any song moved, it builds `read(name)`. That returns the decompressed full-skip version from `extras` when present, and the game's file otherwise.
- It calls `song_flow_patches`, compresses each result to `Event/EventFlow/<name>.bfevfl.zs`, and merges them into `extras` (replacing the skip's version).
- For each patched file, it adds `len(new) - len(base version)` to `sizes` (the dict passed as `extra_sizes`). `base version` is the skip's decompressed size when the skip made the file, and the game's otherwise; this mirrors how the full skip reports growth.

- [ ] **Step 1: Write the failing tests** (`RealTests`, game data):
  - `test_generate_songs_off_unchanged`: the same files and hashes as a run without the field, following `test_generate_tokensanity_off_unchanged`.
  - `test_generate_song_locations`: with `shuffle_songs='song_locations'`, re-read every written `Dm_MelodyGet_*` flow and check its grant actor against `spoiler.json['songs']`.
  - `test_generate_song_locations_with_skip`: the same with `skip_cutscenes=True`. The patched flows are built on the skip's versions, so a skip-only change (for example a removed `LearningOcarina*` call) is still absent.
  - `test_spoiler_songs_section`: the text has `Songs` and 12 lines.

- [ ] **Step 2: Run** `python -m unittest tests.test_generate`. Expected: FAIL.

- [ ] **Step 3: Implement** the wiring and the spoiler rows.

- [ ] **Step 4: Run** the full suite, `python -m unittest`. Expected: OK. Only the existing expected failure remains.

- [ ] **Step 5: Commit** `feat: generate writes the song placement`.

### Task 7: Site and browser option

**Files:**
- Modify: `randomizer/browser.py` (`parse_settings`), `site/index.html`, `site/app.js`
- Test: `tests/test_browser.py`, `tests/test_build_site.py` (if the site test checks the options)

- [ ] **Step 1: Write the failing tests:**
  - `parse_settings({'shuffle_songs': 'song_locations'}).shuffle_songs == 'song_locations'`;
  - the default is `'off'`;
  - `'anywhere'` and `3` raise `ValueError('Invalid Shuffle Songs value.')`.

- [ ] **Step 2: Run** `python -m unittest tests.test_browser`. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - Validate in `parse_settings`.
  - In `index.html`, add a `<select id="shuffle_songs">` labelled "Shuffle Songs", with Off / Song Locations, next to Tokensanity.
  - In `app.js`, add `SHUFFLE_SONGS`, send `shuffle_songs`, and restore the saved value as `tokensanity` does.

- [ ] **Step 4: Run** `python -m unittest tests.test_browser tests.test_build_site`. Expected: PASS.

- [ ] **Step 5: Commit** `feat: Shuffle Songs option on the site`.

### Task 8: Docs and acceptance seed

**Files:**
- Modify: `README.md` (settings list), `docs/TODO.md`
- Create: `docs/test-song-locations.md`, `local/test-song-locations.md`

- [ ] **Step 1:**
  - Document the option in the README: what it does; that the scenes' text still names the original song; that lessons teach the new song's notes only with Skip cutscenes off.
  - Add to `docs/TODO.md`: Anywhere and Dungeon Rewards as next, plus the acceptance seed as "To test in game".

- [ ] **Step 2:** Generate a seed with `shuffle_songs='song_locations'` and Skip cutscenes on, into `output/`. Write the guide: which songs to expect where, taken from its spoiler, and what to check per scene.

- [ ] **Step 3: Commit** `docs: Song Locations option and acceptance guide`.
