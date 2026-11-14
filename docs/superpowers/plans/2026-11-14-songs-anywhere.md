# Shuffle Songs: Anywhere Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (the user chose inline execution for the songs work). Steps use checkbox (`- [ ]`) syntax.

**Goal:** add the `'anywhere'` value to Shuffle Songs: songs in any eligible site, song scenes giving any item.

**Architecture:**

- `songs.py`: `song_flow_patches` handles non-song items. For those it bypasses the lessons and, in the crater, the `IsGet` set.
- `fill.py`: the song scenes become synthetic sites in the existing fill, and the songs become moving items.
- `generate` and the spoiler carry the result.

**Tech Stack:** Python 3.14, unittest.

**Spec:** `docs/superpowers/specs/2026-11-14-songs-anywhere-design.md`

## Global Constraints

- Off and `song_locations` produce byte-identical output to today. Anywhere draws from the RNG only when it is selected.
- `SHUFFLE_SONGS = ('off', 'song_locations', 'anywhere')`. Anywhere together with `key_items_mode == 'vanilla'` raises `FillError('Anywhere needs key items shuffled.')`.
- Find events by value, never by index. Never commit game data. Commits use `type: description`. Repo docs are in English; the Spanish guides go in `local/`.
- Test batches are built on the full skip, with a teleport next to each checked scene (the user's rule). 24a skips the full skip on purpose, because the lesson bypass only happens without it.

## Review Focus

1. **A song scene given a non-song item, Skip cutscenes off:** no lesson call is reachable from the scene's entry, so the original song cannot slip in (Task 1).
2. **The crater given a non-song:** no `IsGet` set remains reachable, and the grant is renamed (Task 1).
3. **Anywhere with Tokensanity:** songs never go to a Skulltula that cannot drop them (Task 3).
4. **Anywhere seeds stay beatable,** with the songs counted in the logic (Task 2).
5. **Song Locations output unchanged** after the refactor (Tasks 1 and 3: the existing tests stay green).

---

### Task 1: Non-song items in song scenes

**Files:** modify `randomizer/songs.py`; test `tests/test_songs.py`.

**Produces:**

- `song_flow_patches(read, placement)`, where `placement` maps each of the 12 locations to any non-empty actor string. It raises `ValueError` if a location is missing, or if a song appears on two locations.
- `bypass(data: bytes, events: Iterable[int]) -> bytes`. Every `link_slots` pointer (next, case, fork, join, entry) that targets a bypassed event is repointed to that event's `next`. Chains are followed. A bypassed event with no `next` (a fork branch end) becomes `0xFFFF`.

**Rules for a location whose item is not a song:**

- rename the grant;
- bypass every `Dm_SY_Ocarina` `LearningOcarina*` call in its flows;
- if it is the crater, also bypass the `EventTriggerSetGameDataBool` on `IsGet.Item_Melody_FireBolero`.

The windmill is patched whenever its item is not Storm, as before.

- [ ] **Step 1: Write the failing tests.** Use game data; tests skip when `OOT_NUP` is missing.
  - `test_impa_gives_shield`: Impa gets `TBox_Shield_Deku`, the rest is vanilla. In the result:
    - the grant actor is `TBox_Shield_Deku`;
    - walking from every entry point, following same-file subflow calls into their entries, reaches no `LearningOcarina*` call;
    - the file size is unchanged apart from the grant string.
  - `test_crater_gives_hookshot`: no `IsGet.Item_Melody_FireBolero` set is reachable from the crater flow's entries, and the grant is `Item_Hookshot`. The windmill is not patched, because Storm stays there.
  - `test_storm_elsewhere_patches_windmill`: Storm sits at the crater and a red rupee at the windmill. The windmill flow is patched, and its grant is `Obj_Rupee_Red`.
  - `test_song_twice_raises`.
  - The existing tests stay green, with `test_bad_placement_raises` reworded so a duplicate song still raises.
- [ ] **Step 2: Run** `python -m unittest tests.test_songs`. Expected: FAIL.
- [ ] **Step 3: Implement** `bypass` and the non-song branch, and relax `_check_placement`.
- [ ] **Step 4: Run** `tests.test_songs tests.test_generate`. Expected: PASS. Song Locations output is unchanged.
- [ ] **Step 5: Commit** `feat: song scenes can give any item`.

### Task 2: Test batch 24 — STOP for the in-game test

**Files:** create `docs/test-batch-24.md` (and `local/test-batch-24.md`, not committed). Modify `tools/make_song_batch.py` so it builds variants from a dict of name to (preset, placement, full skip on/off). 22 stays the default.

The variants:

- **`24a`:** no full skip. The castle preset from batch 23a. Impa gives `TBox_Shield_Deku`.
- **`24b`:** the full skip. The crater adult preset from batch 22. Sheik gives `Item_Hookshot`, so the preset gives the Goron Tunic and the ocarina but not the Hookshot. The tester then gets the Hookshot from Sheik and uses it to leave.

The steps:

- [ ] Build both. Smoke check: list the written flows.
- [ ] Write the guides.
- [ ] Commit `feat: test batch 24 for song scenes giving any item`.
- [ ] **STOP** for the user's test, iterating as in batches 20 to 23.

### Task 3: Anywhere in the fill

**Files:** modify `randomizer/fill.py` and `randomizer/songs.py` (`SHUFFLE_SONGS`); test `tests/test_fill.py`.

**Produces:**

- song sites with ids `SONG_SITE_IDS = {loc: -(k + 1)}`, numbered in `SONGS` order;
- `_logic_name(item)`, the OoTR song name for a song actor and the item itself otherwise, used for `fixed` and `owned`;
- `_fixed`, which puts songs into the logic.

**With `'anywhere'`:**

- `original` gets the 12 synthetic sites holding their songs;
- `site_loc` maps them to their locations;
- `eligible` includes them;
- `moving` adds the songs, sorted together with the key items;
- the result splits into `Placement(chests without the synthetic ids, songs = {loc: result[id]})`.

The existing song phase stays only for `'song_locations'`.

- [ ] **Step 1: Write the failing tests.**
  - `test_anywhere_moves_songs`: over 10 seeds, at least one song lands in a chest, and at least one song scene gets a non-song item.
  - `test_anywhere_multiset`: chest contents plus scene contents keep the same multiset as the originals plus the 12 songs.
  - `test_anywhere_beatable_many`: 20 seeds, with `fixed` built from both parts and songs given by name, are all `can_beat`.
  - `test_anywhere_vanilla_keys_raises`.
  - `test_anywhere_with_tokensanity`: songs never land on a Skulltula when `gs_forbidden` includes them.
- [ ] **Step 2: Run** `tests.test_fill`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `tests.test_fill tests.test_logic`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Shuffle Songs Anywhere fill`.

### Task 4: Generate, spoiler, site, docs

**Files:** modify `generate.py` (`_gs_forbidden` with the songs; `_with_song_flows` unchanged), `spoiler.py` (`_label` knows songs; songs in chests or Skulltulas go to "Key items"; `SHUFFLE_SONGS_LABELS['anywhere'] = 'Anywhere'`), `browser.py`, `site/index.html`, `site/app.js`, `README.md` and `docs/TODO.md`. Tests in `test_generate.py` and `test_browser.py`.

- [ ] **Step 1: Write the failing tests.**
  - `test_generate_songs_anywhere`, with the skip: every song scene in the mod grants `spoiler.songs[loc]`, and every song in a chest appears in a written banc as `Drop__DropActor`.
  - `browser.parse_settings` accepts `'anywhere'`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full suite. Expected: OK.
- [ ] **Step 5:** Generate an acceptance seed and write `docs/test-songs-anywhere.md` and its `local/` version. Commit `feat: Shuffle Songs Anywhere`.
