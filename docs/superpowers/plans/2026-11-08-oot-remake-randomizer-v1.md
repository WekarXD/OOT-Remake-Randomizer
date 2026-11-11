# OoT Remake Randomizer v1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local application with a web interface that generates a mod folder for Lichii in which the 15 key items found in chests in the OoT remake (Switch 2) are distributed among any allowed chest. A logic derived from OoTR guarantees that the game can be completed without glitches.

**Architecture:** Python package `randomizer/` in layers: (1) game access, which reads the `.nup` by offset, decompresses zstd with dictionaries and reads/writes BYML, SARC and RESTBL; (2) data, with the `remake Hash → OoTR location` table and the item table; (3) logic, which evaluates the OoTR regions and rules copied from a fixed version; (4) seed-deterministic fill; (5) patching, which writes `Rando_<seed>/romfs/...`; (6) web server with the standard library and a static HTML/JS page with tabs.

**Tech Stack:** Python 3.14 (stdlib: `compression.zstd`, `http.server`, `ast`, `unittest`, `random`, `hashlib`, `zlib`, `json`, `secrets`), HTML/CSS/JS without frameworks. No third-party dependencies.

**Spec:** `docs/superpowers/specs/2026-11-08-oot-remake-randomizer-design.md`

## Global Constraints

- Python **3.14+** and standard library only. There is no pip in the normal workflow; tests run with `python -m unittest`.
- **The `.nup` is never written to**: it is always opened in `'rb'` mode.
- Game files are read from the v131072 update package (version 1.1.1); the game ID is `0400486024DEC000`. If it is another version, a clear error is shown.
- Maps: `romfs/Banc/<Zone>/*.bcett.byml.zs`, compressed with zstd and the `bcett.byml.zsdic` dictionary from `romfs/Pack/ZsDic.pack.zs`. A chest's content is `Actors[i].Dynamic.Drop__DropActor`.
- RSTB: `romfs/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs`. For maps, the value is `((n + 31) & ~31) + 264`.
- A logical location is one `Hash`. All copies of a `Hash` (in child or adult maps) receive the same item.
- Output: `<output_dir>/Rando_<seed>/romfs/<romfs path>`. It only contains the modified maps and the RSTB.
- The same seed, with the same settings and the same randomizer version, must produce **byte-for-byte identical** files.
- The repo cannot contain game files. `.gitignore` excludes `*.nup`, `test-mod/`, `output/`, `.superpowers/` and `user_config.json`.
- OoTR's logic is copied from commit `526b4c8d81b7c4023ef4573ffbaf39344e270d5b` of `OoTRandomizer/OoT-Randomizer`. The project is licensed GPL-3.0, with attribution.
- The interface texts are in English.
- Tests that need the game read the path from the environment variable `OOT_NUP`. If it is not defined, they are marked `skip` with `unittest.skipUnless`.

## Review Focus

1. **`.nup` path with spaces and brackets** (`...[0400486024DEC000][v131072].nup`): the user's path looks like this, so it must work. The test goes in Task 2 (`test_minimal_synthetic_nup`).
2. **Pressing Generate twice with the same seed:** it is not overwritten without confirmation. The tests go in Task 9 (`test_existing_dir_not_overwritten`) and Task 10 (`test_generate_exists_flag`).
3. **A file that is not a `.nup`, or a nonexistent path:** a message in English is returned, not a traceback. The tests go in Task 2 (`test_rejects_non_nup`) and Task 10 (`test_validate_bad_path`).
4. **Settings that make it impossible to generate a seed:** a clear error is shown and no half-written mod folder is left behind. The test goes in Task 9 (`test_failed_generation_leaves_nothing`).
5. **Empty seed or seed with odd characters** (spaces, accents, `/`): it is normalized to a safe folder name and always gives the same result. The test goes in Task 9 (`test_safe_seed_name`).

---

## Phase 0 — In-game test batch (user gate)

### Task 1: Repo and R1–R3 test mod batch

**Files:**
- Create: `.gitignore`, `LICENSE` (GPL-3.0 text), `README.md` (how to run, with attribution to OoTR)
- Create: `tools/make_test_batch.py`
- Create: `docs/test-batch-1.md` (checklist for the user)
- Uses: `spikes/peek.py`, `spikes/byml.py`, `spikes/hookshot_test.py` (read only; not modified)

**Interfaces:**
- Produces: `python -I tools/make_test_batch.py <nup> <files.tsv> <out_dir>`, which creates `<out_dir>/0400486024DEC000/TestBatch1/` and `<out_dir>/0400486024DEC000/TestBatch2/`. To get `files.tsv`, run `spikes/nuplist.py` first.

- [ ] **Step 1:** `git init`, create `.gitignore` with the entries from Global Constraints, `LICENSE` and a minimal `README.md`. Commit `chore: init repo`.
- [ ] **Step 2:** Write `tools/make_test_batch.py`. It must reuse the functions from `spikes/` (via `sys.path`) to apply several `Hash → Drop__DropActor` changes across several maps and update all affected RSTB entries in a single RSTB per mod. The changes are:

  **TestBatch1** (Kokiri Forest as child, at the start of the game), in `Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs`:
  | Hash | Original | New | Checks |
  |---|---|---|---|
  | 16757992849254467386 | Item_Sword_Kokiri | TBox_Rupee_Green | R1: does the `Get_StoneOfForest_GetSword` event still give the sword? |
  | 10831981390482426294 | TBox_Rupee_Green | Item_Longshot | R2: Longshot without Hookshot |
  | 4555665598794293658 | TBox_Rupee_Blue | Item_Gauntlet_Gold | R2: Golden Gauntlets without the bracelet or silver |
  | 9725242744547055868 | TBox_Rupee_Blue | Item_Shield_Mirror | R3: adult item as child |
  | 12786193094758345086 | TBox_Rupee_Blue | Item_Arrow_Ice | R2/R3: arrows without a bow |

  The same Hash of the sword chest also exists in `KokiriForest_Adult_Dynamic.bcett.byml.zs`, so the same change is applied there.

  **TestBatch2** (story events; a saved adult game is needed), in `Banc/IceCavern/IceCavern_Static.bcett.byml.zs`: Hash 6859289214373847284, from `Item_HeavyBoot` to `TBox_Rupee_Blue`. Checks R1: is the Serenade of Water still learned?
- [ ] **Step 3:** Run it against the real game. The script rereads each map and confirms each change, like `hookshot_test.py`. Expected output: one `OK <hash> <new>` line per change and `RSTB <path> <old> -> <new>` per map.
- [ ] **Step 4:** Write `docs/test-batch-1.md` in English. For each row: where to go, what to do, what to note down (the item received, the text or scene shown, whether it appears in the inventory or menu and whether it can be used) and OK/FAIL checkboxes. It must remind the user to disable other mods.
- [ ] **Step 5:** Commit `test: add in-game test batch 1`.
- [ ] **Step 6 (GATE):** Give the mods and the checklist to the user and **wait for the results**. Note them down in `docs/test-batch-1.md` and decide:
  - R1: if any event gives the original item, those Hash values are marked `needs_event_patch: true` in Task 6. They stay out of the fill until there is a separate plan for editing BFEVFL, which is another subsystem and another plan. The rest of the plan is unchanged.
  - R2: the progressive item model for Task 7 is chosen. **Direct**: each actor gives its level even if you do not have the previous one. **Sequential**: the game requires the previous level and the logic enforces it.
  - R3: if an adult item obtained as a child is lost, it is noted down in `docs/test-batch-1.md` and Task 8 adds the rule "that item is only placed in locations the adult can reach".

## Phase 1 — Game access

### Task 2: `NupArchive` (reading the `.nup`)

**Files:**
- Create: `randomizer/__init__.py` (with `RANDO_VERSION = '0.1.0'`), `randomizer/nup.py`
- Test: `tests/__init__.py`, `tests/test_nup.py`

**Interfaces:**
- Produces:
  - `class NupError(Exception)`, with a message in English.
  - `class NupArchive`: `__init__(self, path: str | os.PathLike)`, which validates the superblock and the TOC's SHA-256 (raises `NupError`); `.title_id: int` (base); `.update_version: int | None` (version of the kind=1 package); `.has(romfs_path: str) -> bool`; `.read(romfs_path: str) -> bytes` (content without NUP compression, paths relative to `romfs/` with `/`, for example `'Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs'`; from the update package); `.list(prefix: str) -> list[str]`; `close()` and context manager.
  - `SUPPORTED_UPDATE_VERSION = 131072`, `TITLE_ID = 0x0400486024DEC000`.

- [ ] **Step 1: Tests**
  - `test_rejects_non_nup`: a temporary file with `b'hello'` → `NupError`, and the message contains `"not a .nup file"`.
  - `test_minimal_synthetic_nup`: build in the test a minimal NUP per SPEC §7 (1 package with kind=1 and standalone flag, `romfs/hello.bin` with `b'hola'` uncompressed, in a temporary directory called `game [x] and spaces`) → `NupArchive(p).read('hello.bin') == b'hola'` and `has('nope') is False`.
  - `test_real_game` (skipUnless `OOT_NUP`): `title_id == 0x0400486024DEC000`, `update_version == 131072`, `len([p for p in list('Banc/') if p.endswith('.bcett.byml.zs')]) == 160`, and `read('Pack/ZsDic.pack.zs')[:4] == b'\x28\xb5\x2f\xfd'`.
- [ ] **Step 2:** Run `python -m unittest tests.test_nup -v`. It is expected to fail because the module does not exist.
- [ ] **Step 3:** Implement based on `spikes/nuplist.py`, building on open an index `dict[romfs_path, (offset, extent_size, codec)]` for the update package only (or the base if there is no update). `codec==1` → `zstd.decompress`; any other codec other than 0 → `NupError`.
- [ ] **Step 4:** Run the tests again. PASS expected (and `test_real_game` skipped if there is no `OOT_NUP`).
- [ ] **Step 5:** Commit `feat: NupArchive reader`.

### Task 3: Formats — zstd with dictionaries, SARC, BYML and RSTB

**Files:**
- Create: `randomizer/formats/__init__.py`, `randomizer/formats/sarc.py`, `randomizer/formats/byml.py` (port `spikes/byml.py`), `randomizer/formats/rstb.py`, `randomizer/formats/zs.py`
- Test: `tests/test_formats.py`

**Interfaces:**
- Consumes: `NupArchive.read`.
- Produces:
  - `sarc.read(data: bytes) -> dict[str, bytes]`
  - `byml.load(data: bytes) -> tuple[int, object]`, `byml.dump(root, ver: int = 7) -> bytes`, and the classes `U32, I64, U64, F64, F32, Bin` (same as in the spike).
  - `class ZsCodec`: `@classmethod from_archive(nup: NupArchive) -> ZsCodec`; `decompress(romfs_path: str, data: bytes) -> bytes`; `compress(romfs_path: str, data: bytes) -> bytes`. It chooses the dictionary by extension: `.bcett.byml.zs` → `bcett.byml.zsdic`, `.pack.zs` → `pack.zsdic`, `.rsizetable.zs` → no dictionary, and any other `.zs` → `zs.zsdic`. It compresses with `level=19`.
  - `class Rstb`: `@classmethod load(data: bytes) -> Rstb`; `get(path: str) -> int | None`; `set(path: str, size: int) -> None` (`KeyError` if it does not exist); `dump() -> bytes`. `path` is the romfs path **without `.zs`**. It looks first in the name table and, if not found, by `zlib.crc32(path.encode())` in the sorted crc table.
  - `def banc_rstb_size(n: int) -> int` = `((n + 31) & ~31) + 264`.

- [ ] **Step 1: Tests**
  - `test_byml_roundtrip_synthetic`: the tree `{'Actors': [{'Gyaml': 'Obj_TBox_A_01', 'Hash': U64(2**63+5), 'Dynamic': {'Drop__DropActor': 'TBox_Rupee_Blue'}}, {'f': F32(1.5), 'i': -3, 'b': True, 'u': U32(7)}]}` satisfies `load(dump(x))[1] == x`, and also `type(r['Actors'][0]['Hash']) is U64`.
  - `test_byml_shared_nodes_not_aliased`: two actors with identical `Dynamic` are deduplicated on `dump`; after `load`, changing one does not change the other.
  - `test_rstb_roundtrip_synthetic`: a RESTBL created in the test with 3 crc entries and 1 name entry: `set` → `dump` → `load` → `get` returns the new value for both types.
  - `test_banc_rstb_size`: `banc_rstb_size(510884) == 511176`.
  - `test_real_all_banc_roundtrip` (skipUnless `OOT_NUP`): all 160 maps are decompressed, pass `load→dump→load` and are equal with their types. `Rstb.get(path_without_zs) == banc_rstb_size(len(raw))` for all 160.
- [ ] **Step 2:** Run and check that it fails.
- [ ] **Step 3:** Implement. RESTBL format: magic `b'RESTBL'`, `u32 version`, `u32 name_block_size`, `u32 crc_count`, `u32 name_count`, then `crc_count × (u32 crc, u32 size)` sorted by crc and `name_count × (name[name_block_size] NUL-terminated, u32 size)`.
- [ ] **Step 4:** Run and check that it passes.
- [ ] **Step 5:** Commit `feat: zstd/sarc/byml/rstb formats`.

### Task 4: `GameData` — chest inventory

**Files:**
- Create: `randomizer/game.py`
- Create: `tools/dump_chests_fixture.py` → `tests/fixtures/chests.json`
- Test: `tests/test_game.py`

**Interfaces:**
- Consumes: `NupArchive`, `ZsCodec`, `byml`.
- Produces:
  - `@dataclass(frozen=True) class ChestActor: banc: str; hash: int; gyaml: str; drop: str; event: str | None; pos: tuple[float, float, float]`
  - `class GameData`: `__init__(self, nup: NupArchive)`; `.codec: ZsCodec`; `chests() -> list[ChestActor]`, which returns the actors whose `Gyaml` contains `'TBox'` and that have `Dynamic.Drop__DropActor`, sorted by `(banc, hash)` (cached); `load_banc(path: str) -> tuple[int, dict]`.
  - `tests/fixtures/chests.json`: a list of serialized `ChestActor` (only identifiers, actor names and positions), so the Task 8 tests run without the game.

- [ ] **Step 1: Tests** (skipUnless `OOT_NUP`): `test_chest_counts`: `len(chests()) == 238` and `len({c.hash for c in chests()}) == 203`. `test_kokiri_sword_chest`: Hash 16757992849254467386 appears twice (banc files `KokiriForest_Child_Dynamic` and `KokiriForest_Adult_Dynamic`), with `drop == 'Item_Sword_Kokiri'` and `event == 'Get_StoneOfForest_GetSword'`. `test_fixture_matches`: the content of `tests/fixtures/chests.json` equals `chests()`.
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement and generate the fixture. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: chest inventory`.

## Phase 2 — Data and logic

### Task 5: Import the OoTR logic data

**Files:**
- Create: `tools/import_ootr.py`
- Create (generated and versioned): `randomizer/logic/ootr/World/*.json`, `randomizer/logic/ootr/LogicHelpers.json`, `randomizer/logic/ootr/locations.json`, `randomizer/logic/ootr/SOURCE.md` (repo, commit and license)
- Test: `tests/test_ootr_data.py`

**Interfaces:**
- Produces: `python -I tools/import_ootr.py <path_to_OoTR_clone>`. The user clones `https://github.com/OoTRandomizer/OoT-Randomizer` and checks out `526b4c8d81b7c4023ef4573ffbaf39344e270d5b`; the script refuses if `git -C <clone> rev-parse HEAD` does not match.
  - It copies `data/World/*.json` (only the glitchless logic ones; `*MQ*.json` and the `Glitched World` folder are excluded) and `data/LogicHelpers.json`. If the paths do not exist at that commit, it stops with an error saying which one is missing.
  - `locations.json` = `{name: {"type": str, "scene": int|null, "vanilla_item": str|null, "categories": [str]}}`, extracted from `LocationList.py` with `ast` (the `location_table` assignment is looked up and its tuples are evaluated with `ast.literal_eval` element by element, **without importing or running OoTR code**).

- [ ] **Step 1: Tests**
  - `test_key_item_locations_exist`: these 15 locations exist in `locations.json` with `type == 'Chest'`: `KF Kokiri Sword Chest`, `Deku Tree Slingshot Chest`, `Dodongos Cavern Bomb Bag Chest`, `Jabu Jabus Belly Boomerang Chest`, `Forest Temple Bow Chest`, `Fire Temple Megaton Hammer Chest`, `Water Temple Longshot Chest`, `Shadow Temple Hover Boots Chest`, `Ice Cavern Iron Boots Chest`, `Bottom of the Well Lens of Truth Chest`, `Spirit Temple Silver Gauntlets Chest`, `Spirit Temple Mirror Shield Chest`, `Graveyard Dampe Race Hookshot Chest`, `Gerudo Training Ground Maze Path Final Chest` and `Ganons Castle Shadow Trial Golden Gauntlets Chest`. If any name differs at that commit, **the test's list, here and in Task 6,** is corrected with the real name and noted in `SOURCE.md`.
  - `test_world_files_parse`: all the JSON files load. OoTR uses JSON with `#` comments; lines whose first non-blank character is `#` are removed before `json.loads`.
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement and import. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: vendor OoTR logic data @526b4c8` (includes `SOURCE.md`).

### Task 6: Item table and chest mapping

**Files:**
- Create: `randomizer/items.py`, `randomizer/locations.py`, `randomizer/data/location_map.json`, `tools/draft_location_map.py`
- Test: `tests/test_location_map.py`

**Interfaces:**
- Consumes: `GameData.chests()` (or the fixture), `locations.json`.
- Produces:
  - `items.KEY_ITEMS: dict[str, str]` (remake actor → OoTR item): `Item_Sword_Kokiri→'Kokiri Sword'`, `Item_Range_SlingShot→'Slingshot'`, `Item_Boomerang→'Boomerang'`, `Item_Range_Bow→'Bow'`, `Item_Hookshot→'Progressive Hookshot'`, `Item_Longshot→'Progressive Hookshot'`, `Item_Hammer→'Megaton Hammer'`, `Item_HeavyBoot→'Iron Boots'`, `Item_HoverBoot→'Hover Boots'`, `Item_Gauntlet_Silver→'Progressive Strength Upgrade'`, `Item_Gauntlet_Gold→'Progressive Strength Upgrade'`, `Item_GlassTruth→'Lens of Truth'`, `Item_Shield_Mirror→'Mirror Shield'`, `Item_Arrow_Ice→'Ice Arrows'`, `Item_BombBag_Small→'Bomb Bag'`.
  - `items.ITEM_LEVEL: dict[str, tuple[str, int]]` = `{'Item_Hookshot': ('Progressive Hookshot', 1), 'Item_Longshot': ('Progressive Hookshot', 2), 'Item_Gauntlet_Silver': ('Progressive Strength Upgrade', 2), 'Item_Gauntlet_Gold': ('Progressive Strength Upgrade', 3)}`. Strength level 1 is the Goron bracelet, which is fixed, from an event.
  - `items.LABELS: dict[str, str]`, the English display name of each item in `KEY_ITEMS` (Kokiri Sword, Fairy Slingshot, Boomerang, Fairy Bow, Hookshot, Longshot, Megaton Hammer, Iron Boots, Hover Boots, Silver Gauntlets, Golden Gauntlets, Lens of Truth, Mirror Shield, Ice Arrows, Bomb Bag).
  - `items.DUNGEON_ITEM_PREFIXES = ('Item_Dungeon_', 'Obj_MiniGame_SmallKey', 'Obj_Dungeon_SmallKey_')`
  - `location_map.json`: `{"<hash>": {"location": "<OoTR name>"|null, "status": "auto"|"manual"|"unmapped", "needs_event_patch": bool, "note": str}}`, with all 203 keys.
  - `locations.load_map() -> dict[int, LocationEntry]`, with `@dataclass(frozen=True) LocationEntry(hash: int, location: str | None, status: str, needs_event_patch: bool)`.
  - `tools/draft_location_map.py <nup>`: generates a draft by matching on (zone → OoTR prefix, original content). If there is a single candidate → `auto`. If there are several → `null` + `note` with the candidates and positions, to be resolved by hand. It never overwrites `manual` entries.
    - Zone → prefix table, to be completed with the real names from `locations.json`: `KokiriForest→KF`, `LostWood→LW`, `SacredForestMeadow→SFM`, `HyruleField→HF`, `Market→Market`, `HyruleCastle→HC`, `KakarikoVillage→Kak`, `Graveyard→Graveyard`, `DeathMountainTrail→DMT`, `DeathMountainCrater→DMC`, `GoronCity→GC`, `ZoraRiver→ZR`, `ZoraDomain→ZD`, `ZoraFountain→ZF`, `GerudoValley→GV`, `GerudoFortress→GF`, `HountedWasteland→Wasteland`, `DesertColossus→Colossus` (also `Spirit Temple` here), `InsideTheDekuTree→Deku Tree`, `DodongoCavern→Dodongos Cavern`, `InsideJabuJabuBelly→Jabu Jabus Belly`, `ForestTemple→Forest Temple`, `FireTemple→Fire Temple`, `WaterTemple→Water Temple`, `ShadowTemple→Shadow Temple`, `SpiritTemple→Spirit Temple`, `IceCavern→Ice Cavern`, `BottomOfTheWell→Bottom of the Well`, `GerudoTrainingGround→Gerudo Training Ground`, `InsideGanonCastle→Ganons Castle`, `GanonCastle→Ganons Tower`.
    - Remake content → OoTR vanilla item for the comparison: `TBox_Rupee_Green/Obj_Rupee_Green→'Rupee (1)'`, `Blue→'Rupees (5)'`, `Red→'Rupees (20)'`, `Purple→'Rupees (50)'`, `Gold→'Rupees (200)'`, `Item_Dungeon_SmallKey→'Small Key (<dungeon>)'`, `Item_Dungeon_Map→'Map (<dungeon>)'`, `Item_Dungeon_Compass→'Compass (<dungeon>)'`, `Item_Dungeon_BossKey→'Boss Key (<dungeon>)'` and `KEY_ITEMS` for the key items. For the rest, the implementer looks up their equivalent in `locations.json`.
- [ ] **Step 1: Tests**
  - `test_map_covers_all_hashes`: the keys of `location_map.json` are exactly the 203 Hash values of the Task 4 fixture.
  - `test_key_item_hashes_mapped`: these Hash values have `status != 'unmapped'` and these locations: 16757992849254467386→`KF Kokiri Sword Chest`, 821372075822700622→`Deku Tree Slingshot Chest`, 12161709650443144121→`Dodongos Cavern Bomb Bag Chest`, 5527401621172639818→`Jabu Jabus Belly Boomerang Chest`, 11082303891540711688→`Forest Temple Bow Chest`, 12083259659219538030→`Fire Temple Megaton Hammer Chest`, 18059711820131847165→`Water Temple Longshot Chest`, 14535080241831873137→`Shadow Temple Hover Boots Chest`, 6859289214373847284→`Ice Cavern Iron Boots Chest`, 16654774376625985726→`Bottom of the Well Lens of Truth Chest`, 2490063409521505179→`Spirit Temple Silver Gauntlets Chest`, 10012167258643363548→`Spirit Temple Mirror Shield Chest`, 16041366920820397198→`Graveyard Dampe Race Hookshot Chest`, 1941083939696166170→`Gerudo Training Ground Maze Path Final Chest`, 17657623307936361670→`Ganons Castle Shadow Trial Golden Gauntlets Chest`.
  - `test_no_duplicate_locations`: two Hash values never point to the same OoTR location.
  - `test_mapped_locations_are_chests`: every non-null `location` exists in `locations.json` with `type == 'Chest'`.
  - `test_needs_event_patch_from_batch`: the set of Hash values with `needs_event_patch == true` equals that of the test's `EVENT_PATCH_HASHES` constant, which is filled in with the result of the Task 1 GATE (empty if R1 went well).
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement `items.py` and `locations.py`, run the draft and **resolve ambiguous cases by hand** using positions and zone. Those that cannot be made certain stay `unmapped` with the reason in `note`. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: chest→OoTR location map`.
- [ ] **Step 6:** Write `docs/test-batch-2.md`, with up to 10 `manual` chests chosen among the most doubtful ones to check by playing. It is informational and does not block.

### Task 7: Rule evaluator and reachability search

**Files:**
- Create: `randomizer/logic/__init__.py`, `randomizer/logic/rules.py`, `randomizer/logic/world.py`, `randomizer/logic/vanilla_settings.json`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: the Task 5 data and `items.ITEM_LEVEL`.
- Produces:
  - `class RuleError(Exception)`.
  - `rules.compile_rule(text: str, helpers: dict[str, str], settings: dict) -> Callable[[State, str], bool]`. The second argument is the age, `'child'` or `'adult'`. It parses with `ast.parse(text, mode='eval')`, like OoTR. It supports: `and/or/not`, comparisons with settings, `True/False`, item names (`Kokiri_Sword` → `'Kokiri Sword'`, underscores to spaces), `(Item, n)` and `has(Item, n)`, event names, functions and macros from `LogicHelpers.json` (expanded recursively with parameter substitution), `is_adult`, `is_child`, `is_starting_age`, `at_day`, `at_night`, `at_dampe_time`, `here(rule)`, `at(region, rule)`, and the setting names from `vanilla_settings.json`. **Any unknown identifier raises `RuleError` at compile time**, it is never silently treated as `False`.
  - `vanilla_settings.json` contains the OoTR values that reproduce the original game. At a minimum: `open_forest: "closed"`, `open_door_of_time: false`, `zora_fountain: "closed"`, `gerudo_fortress: "normal"`, `bridge: "vanilla"`, `trials: 6`, `starting_age: "child"`, `shuffle_ganon_bosskey: "vanilla"`, all `shuffle_*` off or vanilla, and all `logic_*` tricks set to `false`. The implementer completes **all** the keys that the copied rules ask for, until `test_all_rules_compile` passes.
  - `class State`: `items: Counter[str]`, `events: set[str]`. Method `has(item: str, n: int = 1) -> bool`. Progressive items are stored in `items` as the maximum level obtained, according to `ITEM_LEVEL` ("direct" model). If the R2 GATE said "sequential", `World` only adds a level when the previous one is present.
  - `class World`: `__init__(self, settings: dict)`; `reachable_locations(fixed: dict[str, str]) -> set[str]`, a fixed-point search over regions, exits, events and locations for child and adult, with a shared `State`. Each location in `fixed` (OoTR location → OoTR item, or the remake actor if it is a key item with a level) gives its item when reached. `can_beat(fixed: dict[str, str]) -> bool` checks whether OoTR's victory location (the one that gives `'Triforce'`; taken from `locations.json`) is reached.
  - `world.vanilla_fixed() -> dict[str, str]`: location → `vanilla_item` from `locations.json`, replacing the item of the 15 key chests with the corresponding remake actor (for example `'Water Temple Longshot Chest' → 'Item_Longshot'`), so that `ITEM_LEVEL` is correct.
  - Time of day is an approximation (plan decision): `at_day` and `at_night` are true for an age if that age reaches any region with `"time_passes": true`. `at_dampe_time` is equivalent to `at_night`.
- [ ] **Step 1: Tests**
  - `test_all_rules_compile`: all the region, exit, event and location rules in all the `World/*.json` compile without `RuleError`.
  - `test_unknown_identifier_raises`: `compile_rule('Foo_Bar_Baz', {}, {})` raises `RuleError`.
  - `test_vanilla_is_beatable`: `World(vanilla).can_beat(world.vanilla_fixed())` is `True`.
  - `test_no_sword_not_beatable`: the same with `'KF Kokiri Sword Chest' → 'Rupees (5)'` → `False`, because the closed forest requires the sword.
  - `test_slingshot_gates_deku`: with everything vanilla except `'Deku Tree Slingshot Chest' → 'Rupees (5)'`, the Gohma heart location (`Deku Tree Queen Gohma Heart`, name checked in `locations.json`) is not in `reachable_locations`.
  - `test_longshot_alone_counts_as_hookshot`: with the direct model, a `State` that only has `Item_Longshot` satisfies `has('Progressive Hookshot', 1)` and `has('Progressive Hookshot', 2)`.
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: OoTR rule evaluator and reachability`.

## Phase 3 — Fill, patching and spoiler log

### Task 8: Deterministic fill

**Files:**
- Create: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `World`, `world.vanilla_fixed()`, `locations.load_map()`, `items`, `ChestActor` (from the `tests/fixtures/chests.json` fixture in the tests).
- Produces:
  - `@dataclass(frozen=True) class Settings: seed: str; key_items_mode: str = 'any_chest'  # 'vanilla' | 'any_chest'; excluded_items: frozenset[str] = frozenset(); spoiler: bool = True`
  - `class FillError(Exception)`, with a message in English.
  - `def place(chests: list[ChestActor], loc_map: dict[int, LocationEntry], world: World, settings: Settings) -> dict[int, str]`, which returns a `Hash → Drop__DropActor` map for **all** Hash values (the original value if it does not change).
  - Eligible locations: `status != 'unmapped'`, `not needs_event_patch`, `'HrlCity_Shop' not in gyaml`, and original content without a `DUNGEON_ITEM_PREFIXES` prefix. Items that move: those in `KEY_ITEMS` that are not in `excluded_items` and whose original location is eligible. The rest stay in place.
  - The `fixed` passed to the logic is built like this: start from `world.vanilla_fixed()` and, for each eligible location, the OoTR location receives the placed actor if it is a key item, or `'Rupees (5)'` as neutral filler if it is not.
  - Algorithm: *assumed fill* over the key items, in shuffled order, placing the highest-level progressive ones first. Then, the non-key content of the eligible locations is shuffled among the eligible locations that remain free. At the end, `world.can_beat(...)` on the result; if it fails, up to 100 retries deriving the RNG from `(seed, attempt)`, and then `FillError('Could not generate a completable seed with these settings')`.
  - RNG: `random.Random(int.from_bytes(hashlib.sha256(f'{RANDO_VERSION}|{seed}|{settings_key}|{attempt}'.encode()).digest()[:8], 'big'))`, where `settings_key = json.dumps({...settings without seed, sorted excluded_items...}, sort_keys=True)`. Locations are always traversed in Hash order; an unsorted `set` is never iterated.
- [ ] **Step 1: Tests**
  - `test_deterministic`: `place(..., Settings(seed='ABC'))` twice gives equal results.
  - `test_different_seeds_differ`: seeds `'A'` and `'B'` give different results.
  - `test_multiset_preserved`: the multiset of values from `place` (one value per Hash) equals the original.
  - `test_beatable_many`: with 200 seeds `str(i)`, rebuild `fixed` in the test and check that `world.can_beat` is `True` for each.
  - `test_excluded_stays`: with `excluded_items=frozenset({'Item_Hookshot'})`, Hash 16041366920820397198 keeps `Item_Hookshot`.
  - `test_vanilla_mode_identity`: with `key_items_mode='vanilla'`, the result equals the original.
  - `test_dungeon_item_chests_untouched`: every Hash whose original starts with a `DUNGEON_ITEM_PREFIXES` prefix keeps its value.
  - `test_shop_chests_untouched`: every Hash with `HrlCity_Shop` in `gyaml` keeps its value.
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: deterministic fill`.

### Task 9: Patching, spoiler log and `generate` orchestrator

**Files:**
- Create: `randomizer/patch.py`, `randomizer/spoiler.py`, `randomizer/generate.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `NupArchive`, `GameData`, `ZsCodec`, `Rstb`, `banc_rstb_size`, `place`, `Settings`, `FillError`, `items.LABELS`.
- Produces:
  - `patch.write_mod(game: GameData, placement: dict[int, str], mod_root: Path) -> list[str]`: rewrites every map that has at least one changed chest, applying the change to all copies of each Hash, and updates the RSTB. It returns the romfs paths written, sorted.
  - `spoiler.build(settings: Settings, placement: dict[int, str], chests: list[ChestActor], loc_map: dict[int, LocationEntry], game_version: str) -> dict` and `spoiler.to_text(d: dict) -> str`. The text is in English and has the sections `Seed`, `Settings`, `Randomizer version`, `Game version`, `Key items` (English name → OoTR location and zone), `All chests` and `Excluded / unmapped`.
  - `def safe_seed_name(seed: str) -> str`: NFKD, removes diacritical marks, replaces each character outside `[A-Za-z0-9_-]` with `-`, collapses repeated `-`, strips `-` at the start and end, and limits to 40 characters. If it ends up empty, `ValueError`.
  - `class GenerationError(Exception)`, with `.exists: bool = False` and a message in English.
  - `def generate(nup_path: str, out_dir: str, settings: Settings, overwrite: bool = False) -> GenerateResult`, with `@dataclass GenerateResult: seed: str; mod_dir: str; spoiler_txt: str | None; spoiler_json: str | None; changed_files: list[str]`.
    - If `settings.seed` is empty, it replaces it with 10 alphanumeric characters from `secrets` before anything else.
    - It validates that `update_version == 131072`; if not, `GenerationError('Unsupported game version: ...')`. It converts `NupError` and `FillError` into `GenerationError`, with the same message.
    - If `mod_dir` (`<out_dir>/Rando_<safe_seed_name>`) exists and `overwrite` is false → `GenerationError(exists=True)`.
    - It writes everything to `<mod_dir>.tmp` and at the end renames it to `mod_dir` (with `overwrite`, it deletes the old one first). On any exception, it deletes `.tmp` and re-raises. The spoiler logs go in `mod_dir/spoiler.txt` and `mod_dir/spoiler.json`, outside `romfs/`.
- [ ] **Step 1: Tests**
  - `test_safe_seed_name`: `'My seed ñ/1'` → `'My-seed-n-1'`, `'///'` → `ValueError`, and `'a'*60` → length 40.
  - `test_failed_generation_leaves_nothing` (skipUnless `OOT_NUP`): with `unittest.mock.patch('randomizer.fill.World.can_beat', return_value=False)`, `generate` raises `GenerationError`, and neither `mod_dir` nor `mod_dir.tmp` exist afterwards.
  - `test_existing_dir_not_overwritten` (skipUnless `OOT_NUP`): two `generate` calls with the same seed; the second raises `GenerationError` with `exists is True` and does not change the sha256 of the files.
  - `test_generate_byte_identical` (skipUnless `OOT_NUP`): two generations with the same seed in two different `out_dir` values produce the same files with the same sha256.
  - `test_generated_files_reread` (skipUnless `OOT_NUP`): each written map is decompressed, loaded with `byml.load` and its `Drop__DropActor` matches `placement` for all copies of each Hash. Each RSTB entry in the mod's RSTB for a written map equals `banc_rstb_size(len(raw))`.
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: patch writer, spoiler, generate`.

## Phase 4 — Web interface

### Task 10: Local server

**Files:**
- Create: `randomizer/web/__init__.py`, `randomizer/web/server.py`, `randomizer/__main__.py`, `randomizer/config.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `generate`, `GenerationError`, `NupArchive`, `NupError`, `Settings`, `items.KEY_ITEMS`, `items.LABELS`.
- Produces:
  - `python -m randomizer [--port 8765] [--no-browser]`: starts `ThreadingHTTPServer` only on `127.0.0.1` and opens the browser with `webbrowser.open`, except with `--no-browser`.
  - `def make_server(port: int, config_path: Path) -> ThreadingHTTPServer`, used by the tests with `port=0`.
  - `config.load(path: Path) -> dict` / `config.save(path: Path, d: dict)`: `user_config.json` in the project root, with `{nup_path, out_dir, last_settings}`. If the file does not exist or is corrupt, it returns `{}`.
  - `GET /` → `web/static/index.html`; `GET /static/<f>` serves only files from `web/static/`.
  - `GET /api/config` → the configuration.
  - `POST /api/validate {"nup_path"}` → `{"ok": true, "version": "1.1.1"}` or `{"ok": false, "error": "<en>"}`. If the path does not exist, the error is `"File does not exist: <path>"`. If the version is not the supported one, `ok: false` with the version message.
  - `GET /api/items` → `[{"actor": "Item_Hookshot", "label": "Hookshot"}, ...]`, the 15 items in `KEY_ITEMS` order.
  - `POST /api/generate {"nup_path", "out_dir", "seed", "key_items_mode", "excluded_items": [], "spoiler": bool, "overwrite": bool}` → `{"ok": true, "seed", "mod_dir", "spoiler_txt"}`, `{"ok": false, "exists": true, "error"}` or `{"ok": false, "error"}`. If it goes well, it saves the configuration.
  - `GET /api/spoiler?path=<path>` → the spoiler log text (`text/plain; charset=utf-8`) **only if** the resolved path is inside the configuration's `out_dir` and ends in `spoiler.txt`; otherwise, 403.
  - Unhandled exceptions return HTTP 500 with `{"ok": false, "error": "Internal error: <type>"}` and the traceback on the console.
- [ ] **Step 1: Tests** (the server runs in a thread with `make_server(0, tmp/config.json)`; `generate` is replaced with `unittest.mock.patch('randomizer.web.server.generate')`)
  - `test_validate_bad_path`: `/api/validate` with a nonexistent path → `ok: false` and an error that starts with `"File does not exist"`.
  - `test_generate_exists_flag`: the mocked `generate` raises `GenerationError('x', exists=True)` → the response has `ok: false` and `exists: true`.
  - `test_generate_ok_saves_config`: the mocked `generate` returns a `GenerateResult` → `ok: true`, and `config.json` contains `nup_path` and `out_dir`.
  - `test_spoiler_path_traversal`: `/api/spoiler?path=C:/Windows/win.ini` → 403.
  - `test_items_labels`: `/api/items` returns 15 elements and all the `label` values are non-empty.
  - `test_index_served`: `GET /` → 200, and the HTML contains `General`, `Items`, `Logic` and `Spoiler` (this test passes after Task 11).
- [ ] **Step 2:** Run and check that it fails. **Step 3:** Implement, with a provisional `index.html` that contains the four tab names. **Step 4:** Run and check that it passes. **Step 5:** Commit `feat: local web server`.

### Task 11: Page with tabs (mockup B)

**Files:**
- Modify: `randomizer/web/static/index.html`
- Create: `randomizer/web/static/app.js`, `randomizer/web/static/style.css`

**Interfaces:**
- Consumes: the Task 10 API.
- Content:
  - **General**: a "Game path (.nup)" field that validates on blur with `/api/validate` and shows "✔ Version 1.1.1 detected" or the error; a "Output folder (Lichii mods folder for this game)" field; a "Seed" field with a 🎲 button that generates 10 alphanumeric characters on the client; a **Generate** button.
  - **Items**: a "Key items" dropdown with the options `Vanilla` and `Any chest` (default), and "Excluded items" checkboxes from `/api/items`. Greyed out and disabled, with the label "(coming soon)": "Small keys", "Maps and compasses", "Songs", "NPC items", "Rupees and consumables". Note: "Market Square minigame chests and chests holding keys, maps or compasses do not receive key items in this version."
  - **Logic**: "No glitches" checked and disabled; text "Every generated seed can be completed."
  - **Spoiler**: a "Generate spoiler log" checkbox (on by default); after generating, a "View log" link that loads `/api/spoiler?path=...` into a `<pre>`.
  - On generate: the button is disabled and shows "Generating…". If the response carries `exists`, `confirm('Rando_<seed> already exists. Overwrite?')` appears and it retries with `overwrite: true`. If it goes well: "✔ Mod Rando_<seed> created in <mod_dir>. Disable other Rando_* mods for this game in Lichii." If it fails: the error message in red.
  - On load, the settings are filled in from `/api/config`.
  - Colors defined as CSS variables with a dark theme (`prefers-color-scheme`). It works at 375 px width: the tabs scroll horizontally and the page does not.
- [ ] **Step 1:** Implement the three files.
- [ ] **Step 2:** Run `python -m unittest tests.test_server -v`. PASS expected, including `test_index_served`.
- [ ] **Step 3:** Manual verification: `python -m randomizer --no-browser`, open `http://127.0.0.1:8765` in the internal browser, go through the 4 tabs and check the 375 px width with `resize_window`. With the real `.nup`: validate → generate with seed `TEST1` → the success message appears and "View log" shows the spoiler log. Generate again → the overwrite confirmation appears.
- [ ] **Step 4:** Commit `feat: tabbed web UI`.

## Phase 5 — Wrap-up

### Task 12: Acceptance test and documentation

**Files:**
- Modify: `README.md` (requirements, `python -m randomizer`, how to install the mod in Lichii, v1 limitations, OoTR attribution and license)
- Create: `docs/acceptance.md` (checklist for the user)

- [ ] **Step 1:** `python -m unittest -v` green, with `OOT_NUP` defined. No failed tests; the only `skip` allowed is none when `OOT_NUP` is defined.
- [ ] **Step 2:** Generate the acceptance seed from the interface and give the user `docs/acceptance.md`, which includes: install the mod, start a new game, check 3 key items against the spoiler log and play to Ganon.
- [ ] **Step 3:** Commit `docs: README and acceptance checklist`.
- [ ] **Step 4 (GATE):** The user completes a seed. Any failures that appear are noted as bugs, with their seed and spoiler log.

## Out of this plan

- **Editing events (BFEVFL):** done in a separate plan, only if the R1 GATE marks Hash values with `needs_event_patch`. In the meantime, those chests keep their original content.
- Everything the spec marks as a v1 non-goal.
