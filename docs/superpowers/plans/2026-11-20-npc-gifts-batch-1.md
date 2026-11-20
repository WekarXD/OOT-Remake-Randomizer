# NPC Gifts Batch 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With key items set to "Any chest", the 14 batch 1 NPC gifts become item locations and their items join the shuffle, as in OoTR.

**Architecture:** The gifts become synthetic fill sites (ids `-301`..`-314`), as the Great Fairy fountains are. A new `randomizer/gifts.py` patches each gift's flow, by value and on top of the full skip. It also extends the analysed-event `SubFlowList` of the `Dm_` scenes whose grant entry changed, and lists the world-actor swaps (Fire Arrows, Ruto's Letter) that `patch.write_mod` turns into wrappers.

**Tech Stack:** Python 3.14, `unittest`; the repo's `bfevfl`, `byml`, `wrappers`, `test_start` and `fill` modules.

**Spec:** `docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md`

## Global Constraints

- Always on with `key_items_mode == 'any_chest'`; with `'vanilla'` nothing changes (same placement, no gift files).
- Lookups by value, never by event index; an unexpected count raises `GiftPatchError(ValueError)`.
- Synthetic site ids `-301`..`-314`, in `GIFTS` table order (12 flow gifts, then the 2 world gifts).
- Flow sites never receive `FOUNTAIN_FORBIDDEN`; world sites never receive the token or a content `wrappers.can_wrap` rejects.
- Generic grant entries: `GetInEvent_Demo_NotLookatObjectEntry` for `Dm_` scenes, `GetInEvent_NotTurn` for NPC flows.
- Repo docs in English; Spanish guides only in `local/`. Commits `type: description`. Never commit game data (`*.nup`, `test-mod/`, `output/`).
- Test batches are built on the full skip, with a start-preset teleport next to each checked scene.
- Test command: `python -m unittest discover -s tests` (real-file tests need `OOT_NUP`).

## Review Focus

1. **A gift that keeps its own item** must be left untouched (no rename, no entry change, no `SubFlowList` change); an exclusion pins it. Test in Task 3.
2. **Full-skip copies:** a grant the skip copied or rewrote must be renamed in every copy (e.g. `Goto_HyruleCastle` on the skip). Test in Task 3 on the skip versions.
3. **`ANALYZED_INFO` already changed by the full skip:** the gift patch must apply on top of the skip's version, not the game's. Test in Task 5.
4. **Duplicate contents:** two sites give `Item_Bottle`, three give `Obj_Heart_Piece`; the fill and spoiler must count them per site. Test in Task 4.
5. **Batch 28 fallbacks:** if 28a/28b/28c fail, the affected gift stays fixed; the tables must make that a one-line change. Covered by the `FIXED_GIFTS` constant in Task 3.

---

### Task 1: Test batch 28 (gate)

**Files:**
- Modify: `tools/make_npc_gift_batch.py` (variants `28a`, `28b`, `28c`)
- Create: `local/test-batch-28.md` (Spanish guide); append results to `docs/test-batch-27.md` under a `## Batch 28` heading

**Interfaces:**
- Consumes: the existing `Variant`, `Gift`, `Entry`, `_preset`, `_pos` and `swap` of the batch 27 tool.
- Produces: the results that decide `FIXED_GIFTS` in Task 3.

- [ ] **Step 1:** Add the three variants:
  - **28a:** adult at Lake Hylia, facing the sun spot. Start with the Bow and the flag `HavePlayedEvent.Dm_WaterTemple_0020` (Water Temple clear; check the sun's condition in `GetFireArrow_FireArrowAppear` and set what it reads). `swap=(HyruleField_Adult_Static, 4598657944866228526, 'Item_Boomerang')`.
  - **28b:** child in Zora's Domain, in front of King Zora. Start with `Item_Bottle_Letter`.
  - **28c:** child in Goron City by a bomb flower. Start with `Item_Gauntlet_Silver` and `Item_BombBag_Medium`, without the bracelet.
- [ ] **Step 2:** Build all three, and check that each variant's patched file contains the expected value (as for 27).
- [ ] **Step 3:** Write the Spanish guide and commit with `test: NPC gifts test batch 28 (Fire Arrows wrapper, Ruto's Letter from elsewhere, Silver without the bracelet)`.
- [ ] **Step 4: STOP** for the user's in-game results. Record each in `docs/test-batch-27.md`, and set `FIXED_GIFTS` (Task 3) for every failure.

### Task 2: Items and logic

**Files:**
- Modify: `randomizer/items.py`, `randomizer/logic/world.py`
- Test: `tests/test_logic.py`, `tests/test_location_map.py`

**Interfaces:**
- Produces: the 10 new `KEY_ITEMS` entries, plus `LABELS`, `KEY_ITEM_HOME` and `ITEM_LEVEL['Item_Gauntlet_Goron'] = ('Progressive Strength Upgrade', 1)` (spec table), unless `FIXED_GIFTS` from Task 1 drops one.

- [ ] **Step 1: Failing tests.**
  - `test_logic.test_man_on_roof_needs_adult`: with only child access to `Kak Odd Medicine Rooftop`, `Kak Man on Roof` is not in `reachable_locations(vanilla_fixed())` for a child-only state. Build it by checking that the compiled rule of that location is false for `is_child` and true for `is_adult`.
  - `test_logic.test_bracelet_is_strength_one`: a `State` that collects `Item_Gauntlet_Goron` has `items['Progressive Strength Upgrade'] == 1`, and a later `Item_Gauntlet_Silver` raises it to 2.
  - `test_location_map`: the key item count goes from 21 to 31, and each new home is in OoTR's `locations.json`.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement.**
  - The table rows go into `items.py`. Drop the "Strength level 1 is fixed" comment.
  - Add the `REMAKE_RULES` entry `('Kak Odd Medicine Rooftop', 'locations', 'Kak Man on Roof'): '({orig}) and is_adult'`.
- [ ] **Step 4:** Run the full suite. Expect older tests that count key items or assume a fixed bracelet to fail. Update each with a ledger ruling.
- [ ] **Step 5:** Commit with `feat: NPC gift items join the key items; Kak Man on Roof needs an adult`.

### Task 3: `randomizer/gifts.py`

**Files:**
- Create: `randomizer/gifts.py`
- Test: `tests/test_gifts.py` (real file, `OOT_NUP`; skips without it, like `test_fairies.py`)

**Interfaces:**
- Consumes: `bfevfl.set_string_param`, `set_subflow_entry`, `EventFlow`; `test_start.subflow_closure`, `ANALYZED_INFO`; `byml`.
- Produces:
  - `GiftPatchError(ValueError)`;
  - `Gift(location: str, content: str, flow: str, key: str, vanilla: tuple[str, ...], entry: tuple[str, str] | None)` and `WorldGift(location: str, content: str, banc: str, hash: int)`, both frozen dataclasses;
  - `GIFTS: tuple[Gift | WorldGift, ...]` (14, spec order), `GIFT_BY_LOCATION`, `GIFT_ITEMS: frozenset[str]` (the key-item contents);
  - `FIXED_GIFTS: frozenset[str]` (locations that stay out of the fill; empty unless batch 28 failed);
  - `GIFT_FORBIDDEN = FOUNTAIN_FORBIDDEN`;
  - `gift_flow_patches(read: Callable[[str], bytes], gifts: dict[str, str]) -> dict[str, bytes]` (location -> placed item; flows keyed by name);
  - `gift_subflow_list(info: bytes, read: Callable[[str], EventFlow | None], gifts: dict[str, str]) -> bytes`;
  - `gift_actor_swaps(gifts: dict[str, str]) -> dict[int, tuple[str, str]]`.

- [ ] **Step 1: Failing tests** (each on the vanilla flows and on the full skip's, via `files_with_fallback(game, FULL_SKIP_PHASE)`, as `test_fairies` does):
  - `test_every_gift_has_its_grant`: for each flow `Gift`, the vanilla flow has at least one subflow call whose `key` value is in `vanilla`.
  - `test_patch_gives_new_item`: placing `Item_Boomerang` everywhere leaves no call with a vanilla value, and gives at least one call with `Item_Boomerang` per gift.
  - `test_only_matching_calls_change`: for `Minigame_CatchCucco`, the red-rupee hand-over (`Obj_Rupee_Red`) is unchanged; for `SubEvent_FindRichard`, the blue rupee is unchanged.
  - `test_special_entry_goes_generic_only_when_changed`: Darunia with the Boomerang has no `GetInEvent_Goron` call; with his own bracelet, the flow is byte-identical to the input.
  - `test_unchanged_gift_untouched`: `gift_flow_patches(read, {loc: own content})` returns no flow for that gift.
  - `test_subflow_list_adds_actionguide`: Zelda with the Boomerang makes `Dm_HrlCastle_0050`'s `SubFlowList` contain `ActionGuide`; Zelda with her letter leaves the table byte-identical.
  - `test_actor_swaps`: Ruto's Letter with the Boomerang gives `{474136620438465634: ('Banc/HyruleField/HyruleField_Child_Static.bcett.byml.zs', 'Item_Boomerang')}`; with her own letter it gives `{}`.
  - `test_missing_grant_raises`: a flow without the grant (patch `read` to return another flow) raises `GiftPatchError`.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement.**
  - The tables come from the spec. Every flow's grants are renamed by `(key, value)` match on `SUBFLOW` events.
  - Several gifts in one flow are patched in one pass over that flow.
  - The tunics: `SageOfFire` `Obj_Armor_Goron`, `SageOfWater` `Obj_Armor_Zora`.
  - Light Arrows: `Dm_TimeTemple_0130` `Item_Arrow_Light`.
  - Big Poes: `Npc_Hylia_048_BottleShop` `Item_Bottle`, entry `('GetInEvent_Poeshop', 'GetInEvent_NotTurn')`.
  - Skull Kid: `Npc_SkullKid_Child` only.
- [ ] **Step 4:** Run `python -m unittest tests.test_gifts` and expect a PASS.
- [ ] **Step 5:** Commit with `feat: gifts module patches the NPC gift grants by value`.

### Task 4: Fill sites

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py` (new `GiftFillTest`)

**Interfaces:**
- Consumes: `GIFTS`, `FIXED_GIFTS`, `GIFT_FORBIDDEN` (Task 3); the key items (Task 2).
- Produces:
  - `GIFT_SITE_IDS: dict[str, int]` (`-301`..);
  - `Placement.gifts: dict[str, str]`;
  - `place_all(..., world_forbidden: frozenset[str] = frozenset())`.
  - `_scene_forbidden(h)` returns `GIFT_FORBIDDEN` for flow gift ids and `world_forbidden | {TOKEN}` for world gift ids.

- [ ] **Step 1: Failing tests:**
  - `test_gifts_are_sites`: with "Any chest", `placed.gifts` has the 14 locations (minus `FIXED_GIFTS`).
  - `test_twenty_seeds_beatable`: twenty seeds are beatable.
  - `test_gift_forbidden`: across twenty seeds, no flow site holds a `GIFT_FORBIDDEN` content, and no world site holds the token or a content in a given `world_forbidden`.
  - `test_excluded_gift_item_stays`: excluding `Item_ZeldaLetter` keeps it at `HC Zeldas Letter`.
  - `test_vanilla_unchanged`: "Vanilla" key items give `gifts == {}` and the same chests as before.
  - `test_heart_pieces_counted`: the three `Obj_Heart_Piece` and two `Item_Bottle` contents are all placed somewhere (the multiset of placed contents equals the original).
  - `test_with_songs_and_tokens`: Anywhere songs plus Tokensanity "all" is still beatable.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement**, following the fountains' block in `place_all`: original contents, `site_loc`, `eligible`, and `world_forbidden` threaded through `_run` and `_attempt` to `_scene_forbidden`.
- [ ] **Step 4:** Run the full suite. Update the older tests that count sites, each with a ruling.
- [ ] **Step 5:** Commit with `feat: the NPC gifts join the fill`.

### Task 5: Generate, spoiler, site

**Files:**
- Modify: `randomizer/generate.py`, `randomizer/spoiler.py`, `site/index.html`, `README.md`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: Tasks 3 and 4.
- Produces:
  - `_with_file_patch(game, path: str, fn: Callable[[bytes], bytes], extras) -> extras`, which patches the decompressed file, read from `extras` if present, else the game;
  - `spoiler.build(..., gifts=None)` with an `npc_gifts` list and a "NPC Gifts" text section.

- [ ] **Step 1: Failing tests:**
  - `test_npc_gifts_in_mod` (real file): an "Any chest" seed writes the gift flows that changed, an `ANALYZED_INFO` whose `Dm_HrlCastle_0050` row contains `ActionGuide` when Zelda's item changed, and a `Obj_Rando_*` pack per world swap.
  - `test_npc_gifts_on_full_skip`: with `skip_cutscenes=True` too, `ANALYZED_INFO` keeps the skip's own changes. Compare a row the skip changes against the skip-only build.
  - `test_npc_gifts_not_with_vanilla_keys`: no gift flow is written with "Vanilla" key items.
  - `test_npc_gifts_section`: the spoiler text has `NPC Gifts` with 14 lines, and the key item rows have the zone `NPC gift`.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement.**
  - `world_forbidden` = the contents `wrappers.can_wrap` rejects among the chest contents, `FAIRY_REWARDS` and `GIFT_ITEMS`, plus `Obj_Token_Gold`.
  - `_gs_forbidden(..., extra=FAIRY_REWARDS | GIFT_ITEMS)`.
  - Apply `gift_flow_patches` after the fairies, then `_with_file_patch(ANALYZED_INFO, ...)`.
  - Merge `gift_actor_swaps` into `swaps`.
  - Write the spoiler section and the help text. The help says: "With Any chest, the NPC gifts (Darunia, Zelda, Malon, the tunics, the Fire and Light Arrows, Ruto's Letter...) are shuffled too."
- [ ] **Step 4:** Run the full suite and expect a PASS.
- [ ] **Step 5:** Commit with `feat: generate patches the NPC gifts; spoiler lists them`.

### Task 6: Acceptance guide and docs

**Files:**
- Create: `docs/test-npc-gifts.md`, `local/test-npc-gifts.md` (Spanish)
- Modify: `docs/TODO.md`, `docs/npc-gifts-research.md`

- [ ] **Step 1:** Generate the acceptance seed `REGALOS1` ("Any chest", skip on, spoiler) into `test-mod/`. From its spoiler, pick:
  - one special-entry gift (Darunia or Zelda);
  - one NPC hand-over (Anju, the dog or the rolling Goron);
  - one world actor.

  Write both guides with what each gives.
- [ ] **Step 2:** In the TODO:
  - remove "NPC gifts: phase B";
  - add what stays fixed (`FIXED_GIFTS`, if any);
  - add the untested Big Poes entry;
  - add "Gold Skulltula tokens from gift sites".
- [ ] **Step 3:** Commit with `docs: NPC gifts acceptance guide (seed REGALOS1) and TODO`.
