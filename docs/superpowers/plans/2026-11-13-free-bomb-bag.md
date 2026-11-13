# Free the Bomb Bag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The Bomb Bag is shuffled again, and the logic requires the Goron's Bracelet before bombs or Bombchus can be used.

**Architecture:** A dict of remake helper overrides in `randomizer/logic/world.py`, merged over OoTR's `LogicHelpers.json` before the `Compiler` is built. Helpers take precedence over item names in `Compiler.visit_Name`, so overriding the name `Bomb_Bag` gates every rule that uses it. The Dodongo's Cavern chest entry in `location_map.json` goes back to being movable. Movability is derived from `needs_event_patch` (in `fill.py`, `browser.py` and `spoiler.py`), so no other code changes.

**Tech Stack:** Python 3, unittest (`python -m unittest`).

**Spec:** `docs/superpowers/specs/2026-11-13-free-bomb-bag-design.md`

## Global Constraints

- Override text, verbatim: `'Bomb_Bag': "'Bomb Bag' and Progressive_Strength_Upgrade"`.
- Chest `12161709650443144121` (Dodongos Cavern Bomb Bag Chest): `needs_event_patch: false`, `strip_event: true`. The JSON stays `indent=1, sort_keys=True, ensure_ascii=False` plus a trailing newline (`test_file_is_deterministic`).
- Docs in the repo are in English.

## Review Focus

- A count check `(Bomb_Bag, n)` bypasses helpers through `_lookup_item_or_event`. Expected: no OoTR rule uses one. Task 1 asserts that no World file or helper contains `(Bomb_Bag,`.
- The override must not recurse: it names the item as the string `'Bomb Bag'`, not the name `Bomb_Bag`. Task 1's test compiles `Bombs` and would hit the depth limit if it recursed.
- Silver Gauntlets without the bracelet also give strength ≥ 1 in the direct model. Accepted: the bracelet comes from a fixed event, which is always reached before the Spirit Temple.
- Old seeds change placement once the map changes (ACEPTACION1 too). Accepted. The README says so.

---

### Task 1: Bombs need the Goron's Bracelet in the logic

**Files:**
- Modify: `randomizer/logic/world.py` (next to `REMAKE_RULES`, plus the `Compiler(...)` call in `World.__init__`)
- Test: `tests/test_logic.py`

**Interfaces:**
- Produces: `world.REMAKE_HELPERS: dict[str, str]` and `world.load_helpers() -> dict[str, str]`, which returns OoTR's helpers with `REMAKE_HELPERS` applied over them. `World.__init__` uses it.

- [ ] **Step 1: Write the failing tests** in a new `class BombBagTest(unittest.TestCase)` in `tests/test_logic.py`:
  - `test_bombs_need_bracelet`: compile `Bombs`, then `has_bombchus`, with `rules.Compiler(world.load_helpers(), world.load_vanilla_settings())`.
    - A `State` holding only `'Bomb Bag'` evaluates both to False for `'child'`.
    - After `collect('Progressive Strength Upgrade')`, both evaluate to True.
  - `test_no_count_check_on_bomb_bag`: no text in `ootr_data.load_helpers()` values or in any World rule contains `(Bomb_Bag,`.
  - `test_dodongo_needs_bracelet_with_bag`: in `_vanilla_world()`, set `fixed['GC Darunias Joy'] = 'Rupees (5)'` and check that `'Dodongos Cavern Bomb Bag Chest'` is not in `reachable_locations(fixed)`. The vanilla placement does reach it.

- [ ] **Step 2: Run the tests and see them fail**

Run: `python -m unittest tests.test_logic.BombBagTest -v`
Expected: FAIL (`load_helpers` does not exist).

- [ ] **Step 3: Implement** `REMAKE_HELPERS = {'Bomb_Bag': "'Bomb Bag' and Progressive_Strength_Upgrade"}`, with a comment citing batch 19, and `load_helpers()`, a new dict `{**ootr_data.load_helpers(), **REMAKE_HELPERS}`. Use it in `World.__init__`. Add a bullet to the module docstring next to the other simplifications.

- [ ] **Step 4: Run the whole logic suite**

Run: `python -m unittest tests.test_logic -v`
Expected: all pass, with 1 expected failure (`test_vanilla_is_beatable`).

- [ ] **Step 5: Commit**

```bash
git add randomizer/logic/world.py tests/test_logic.py
git commit -m "feat: logic requires the Goron's Bracelet to use bombs"
```

### Task 2: The Bomb Bag moves again

**Files:**
- Modify: `randomizer/data/location_map.json` (entry `12161709650443144121`)
- Modify: `tests/test_location_map.py` (`EVENT_PATCH_HASHES`, `STRIP_EVENT_HASHES`)
- Test: `tests/test_fill.py`
- Modify: `README.md` (v1 limitations), `docs/TODO.md`

**Interfaces:**
- Consumes: Task 1's logic, through `World`.

- [ ] **Step 1: Update the expectations.** Move `12161709650443144121` from `EVENT_PATCH_HASHES` to `STRIP_EVENT_HASHES`, with the comment `# Bomb Bag (batch 19: bombs need the Goron's Bracelet)`. Add `test_bomb_bag_can_leave_dodongo` to `tests/test_fill.py`: across seeds `'B1'` to `'B20'` with default `Settings`, at least one placement puts `Item_BombBag_Small` on a hash other than `12161709650443144121`. Find the placed hash from `r` like the neighbouring tests do.

- [ ] **Step 2: Run the tests and see them fail**

Run: `python -m unittest tests.test_location_map tests.test_fill -v`
Expected: FAIL on `test_needs_event_patch_from_batch`, `test_strip_event_from_batch` and `test_bomb_bag_can_leave_dodongo`.

- [ ] **Step 3: Edit the JSON entry:** `needs_event_patch: false`, `strip_event: true`, and change the note's "fija: …" clause to `liberada: las bombas necesitan el Brazalete goron (lote 19)`. Rewrite the file with `json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'`.

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover -s tests`
Expected: everything passes except the known expected failure.

- [ ] **Step 5: Docs.**
  - README v1 limitations: 9 items move (add the Bomb Bag) and 6 stay. Add the bullet "Bombs and Bombchus need the Goron's Bracelet (remake behaviour); the logic accounts for it", and note that seeds made before this change place items differently.
  - `docs/TODO.md`: drop the solved Bomb Bag entry from "To investigate".

- [ ] **Step 6: Commit**

```bash
git add randomizer/data/location_map.json tests/test_location_map.py tests/test_fill.py README.md docs/TODO.md
git commit -m "feat: shuffle the Bomb Bag again"
```

### Task 3: In-game test seed

- [ ] **Step 1:** Find a seed from Task 2's test whose spoiler puts the Bomb Bag outside Dodongo's Cavern and somewhere reachable early. Generate it with `python -m randomizer` (spoiler on) into `test-mod/0400486024DEC000/Rando_<SEED>`.
- [ ] **Step 2:** Write the guide `docs/test-bomb-bag.md` (English) and its Spanish copy `local/test-bomb-bag.md`. The guide says where the bag is, asks to confirm that bombs cannot be thrown before the bracelet and can after, and asks to play on until Dodongo's Cavern. Add it under "To test in game" in `docs/TODO.md`.
- [ ] **Step 3: Commit** the English guide and the TODO change.
