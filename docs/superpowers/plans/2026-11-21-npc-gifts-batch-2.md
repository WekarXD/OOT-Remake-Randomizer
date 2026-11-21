# NPC Gifts Batch 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With key items set to "Any chest", the 21 minigame prizes and Gold Skulltula house rewards become item locations, as in OoTR.

**Architecture:** The prizes are appended to batch 1's `GIFTS` table (`randomizer/gifts.py`), so they become synthetic fill sites `-315`..`-335` through the existing code. Four things are new:
- `Gift` matches calls by entry (`via`) and by several keys;
- the flow patch resolves same-flow prizes before renaming;
- the fill places the Golden Scale only where the Silver one is needed;
- ammo gating uses OoTR item names.

**Tech Stack:** Python 3.14, `unittest`; the repo's `bfevfl`, `fill`, `logic`, `gifts` and `generate` modules.

**Spec:** `docs/superpowers/specs/2026-11-21-npc-gifts-batch-2-design.md`

## Global Constraints

- Always on with `key_items_mode == 'any_chest'`; with `'vanilla'` nothing changes.
- Batch 1 site ids `-301`..`-314` do not move; the batch 2 rows come after them in `GIFTS` (ids `-315`..`-335`).
- Lookups by value (and by entry with `via`), never by event index; a gift with no matching call raises `GiftPatchError`.
- The Golden Scale's location must be unreachable without the Silver Scale; excluding either scale excludes both.
- Upgrades (`Item_BulletBag_Medium/Large`, `Item_Quiver_Medium/Large`) and `Item_BombchuBundle_Large` are minor items, never `KEY_ITEMS`.
- Repo docs in English; Spanish guides only in `local/`. Commits `type: description`. Never commit game data (`*.nup`, `test-mod/`, `output/`).
- Test batches are built on the full skip, with a start-preset teleport next to each checked scene.
- Test command: `python -m unittest discover -s tests` with `OOT_NUP` set (about 13 minutes; run it in the background).

## Review Focus

1. **Same-flow swaps:** two prizes in one flow exchanging items (Kak 10 ↔ Kak 30 wallets, child ↔ adult fishing) must each end with the other's item. Test in Task 3.
2. **Frogs:** the ocarina game (`MushiToriGame` calls 71/91) and the rain (event 247) share `Obj_Heart_Piece`; each must rename only its own calls. Test in Task 3.
3. **Scale order under exclusions and Dungeon Rewards:** the Golden Scale rule must hold when other items are excluded and with `shuffle_songs='dungeon_rewards'`. Test in Task 4.
4. **Ammo gating with three bomb bags:** bombchus must never land where any bag is unneeded. Test in Task 4.
5. **Full-skip copies:** a prize flow the skip rewrote is renamed in every copy. Test in Task 3 (`FullSkipFlowsTest`).

---

### Task 1: Test batch 30 (gate)

**Files:**
- Modify: `tools/make_npc_gift_batch.py` (variants `30a`..`30e`)
- Create: `local/test-batch-30.md` (Spanish); append results to `docs/test-batch-27.md` under `## Batch 30`

- [ ] **Step 1:** Add the variants. Each teleports next to its NPC (positions from the map's `Static` banc, as in batch 29). For 30a, 30c and 30d the grant gives `Item_Boomerang`.
  - **30a (Talon):** `Gift('Minigame_FindOutCucco', 'ActorName', ('Item_Bottle_Milk',))` and the same with `'ReveiveItem'`, plus `Entry('Minigame_FindOutCucco', 'GetInEventInBottle', GENERIC_NPC)`. Child at Lon Lon Ranch, in Talon's house.
  - **30b (milk):** start-preset item `Item_Bottle_Milk`, at Lon Lon Ranch.
  - **30c (Dampe):** `Gift('Npc_Hylia_Dampe_001', 'ActorName', ('Obj_Heart_Piece',))` and `Entry('Npc_Hylia_Dampe_001', 'GetInEvent_NotTurn_NotNpc_Dampe', 'GetInEvent_NotTurn_NotNpc')`. Child in the graveyard at night; set the flags Dampe's tour reads.
  - **30d (LW Target):** `Gift('Dm_LostWood_0040', 'ActorName', ('Item_BulletBag_Large', 'Item_BulletBag_Medium'))`. Child with the Slingshot next to the target stump.
  - **30e (quivers):** adult with `Item_Quiver_Large`, then `Item_Quiver_Medium`, then `Item_Range_Bow`, in Kakariko.
- [ ] **Step 2:** Build all five into `test-mod/0400486024DEC000/TestBatch30<x>`. Check that 30a, 30c and 30d contain the Boomerang grants.
- [ ] **Step 3:** Write the Spanish guide and commit: `test: NPC gifts batch 30 (Talon, milk, Dampe, LW Target, quiver order)`.
- [ ] **Step 4: STOP** for the user's in-game results. Record them in `docs/test-batch-27.md`. Every failing gift goes into `FIXED_GIFTS` in Task 3. If 30e fails, add a Task 4 step that applies the scale rule to quivers, with the Bow as the prerequisite.

### Task 2: Items and logic

**Files:**
- Modify: `randomizer/items.py`, `randomizer/logic/world.py`
- Test: `tests/test_logic.py`, `tests/test_location_map.py`

**Interfaces:**
- Produces:
  - the 7 new `KEY_ITEMS` rows, with `LABELS`, `KEY_ITEM_HOME` and `ITEM_LEVEL` (spec table);
  - `FAMILIES` rows `Item_BulletBag_Medium`/`_Large` → `Slingshot`, `Item_Quiver_Medium`/`_Large` → `Bow`, `Item_BombchuBundle_Large` → `Bombchus`;
  - `UPGRADES: frozenset[str]` (the four bags and quivers).

- [ ] **Step 1: Failing tests.**
  - `test_logic.test_scale_levels`: collecting `Item_Scale_Gold` gives `items['Progressive Scale'] == 2`, and a later `Item_Scale_Silver` leaves it at 2.
  - `test_logic.test_wallet_levels`: the same for the wallets (1 and 2).
  - `test_logic.test_lab_dive_needs_child`: the compiled `LH Lab Dive` rule is false for an adult with both scales and true for a child with `Item_Scale_Gold`.
  - `test_location_map`: 38 key items, and each new home is in OoTR's `locations.json` with that vanilla item.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3:** Implement the tables and the `REMAKE_RULES` row `('LH Lab', 'locations', 'LH Lab Dive'): '({orig}) and is_child'`.
- [ ] **Step 4:** Run the suite. Update the tests that count key items (31 → 38), each with a ledger ruling.
- [ ] **Step 5:** Commit: `feat: minigame and Skulltula reward items join the key items; LH Lab Dive needs a child`.

### Task 3: `gifts.py` batch 2

**Files:**
- Modify: `randomizer/gifts.py`
- Test: `tests/test_gifts.py`

**Interfaces:**
- Consumes: Task 2's `KEY_ITEMS` and `FAMILIES`.
- Produces:
  - `Gift(location, content, flow, key: str | tuple[str, ...], vanilla, entry=None, via: str | None = None)`;
  - `GIFTS` with 35 rows;
  - `gift_flow_patches` with unchanged signatures.

- [ ] **Step 1: Failing tests** in `tests/test_gifts.py`.
  - `test_table_matches_ootr`: 35 rows, 2 world gifts. Each row's content matches OoTR's vanilla item through `items.content_matches`, which replaces the current "key item or heart piece" check.
  - `_Base.test_patch_gives_new_item`: unchanged; it now covers the 21 rows.
  - `_Base.test_same_flow_swap`: `{'Kak 10 Gold Skulltula Reward': 'Item_Wallet_Large', 'Kak 30 Gold Skulltula Reward': 'Item_Wallet_Medium'}`. In `GatheringTokenGold`, the call that gave `Item_Wallet_Medium` now gives Large, and vice versa (compare the call sets before and after). Do the same for child fishing ↔ adult fishing.
  - `_Base.test_frogs_separate`: a Boomerang at `ZR Frogs in the Rain` changes only the call whose entry is `GetInEvent_NotTurn_NotNpc`; both `MushiToriGame` calls still give `Obj_Heart_Piece`. Then the reverse with `ZR Frogs Ocarina Game`.
  - `_Base.test_two_keys_renamed`: a Boomerang at `LH Child Fishing` renames the `ReveiveItem` call and the `ActorName` call. Do the same for `LLR Talons Chickens`.
  - `_Base.test_special_entry_goes_generic_only_when_changed`: extend it with Dampe and Talon.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement.**
  - **`Gift` fields:**
    - `key` accepts a tuple; a call matches if any of its keys holds a vanilla value;
    - `via` filters on `ev.sub_entry`.
  - **`gift_flow_patches`:** group the changed gifts by flow; on each flow's current bytes, collect every gift's `(event, key)` pairs first, then apply all renames, then the entry changes.
  - **Rows:** append the spec's 21 rows in its table order.
    - The upgrade sites list both sizes in `vanilla`, as the rolling Goron does.
    - The frogs' rows use `via='MushiToriGame'` and `via='GetInEvent_NotTurn_NotNpc'`.
    - Dampe uses `entry=('GetInEvent_NotTurn_NotNpc_Dampe', 'GetInEvent_NotTurn_NotNpc')`, and Talon uses `entry=('GetInEventInBottle', GENERIC_NPC)`.
    - Fishing and Talon use `key=('ReveiveItem', 'ActorName')`.
  - **`FIXED_GIFTS`:** set it from Task 1's failures.
  - **`gift_subflow_list`:** `subflow_closure` gets the generic entry's flow, which is not always `GRANT_FLOW`. Read it from the redirected calls' `sub_flow` (Dampe's call is in `Dm_SY_GetInEvent`).
- [ ] **Step 4:** Run `python -m unittest tests.test_gifts`; expect a pass. Then run the whole suite.
- [ ] **Step 5:** Commit: `feat: NPC gifts batch 2 (minigames and Gold Skulltula rewards) in the gifts table`.

### Task 4: Fill rules

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: Task 2's `UPGRADES` and `ITEM_LEVEL`; Task 3's `GIFTS`.
- Produces:
  - `LINKED_EXCLUSIONS: tuple[frozenset[str], ...] = (frozenset({'Item_Scale_Silver', 'Item_Scale_Gold'}),)`;
  - `NEEDS_FIRST: dict[str, str] = {'Item_Scale_Gold': 'Item_Scale_Silver'}`;
  - `AMMO_CONTAINER` values become OoTR names (`'Bomb Bag'`, `'Bow'`).

- [ ] **Step 1: Failing tests** in a new `test_fill.ScaleOrderTest` and in `GiftFillTest`.
  - `test_gold_needs_silver`: over 30 seeds with "Any chest", the Golden Scale's location is not in `world.reachable_locations(fixed with the Silver Scale's site set to FILLER)`.
  - `test_excluding_one_scale_excludes_both`: excluding `Item_Scale_Gold` keeps both scales at their vanilla sites (`LH Adult Fishing`, `ZD Diving Minigame`).
  - `test_bombchus_need_any_bag`: for each seed, compute reach with all three bomb bags replaced by `FILLER`; every `Item_BombchuBundle_*` site lies outside it.
  - `test_upgrades_avoid_song_scenes_and_skulltulas`: with `shuffle_songs='anywhere'` and Tokensanity `'all'`, no song scene site holds an item in `UPGRADES`.
  - `test_gift_sites_batch_2`: `r.gifts` has 35 locations; the multiset invariant of `test_gifts_are_sites` holds.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement.**
  - **`place_all`:** compute the effective exclusions with `LINKED_EXCLUSIONS`, so that one scale excluded means both are. Use them for `moving` and pass them on (instead of `settings.excluded_items`).
  - **`_attempt`:** for an item in `NEEDS_FIRST`, also compute `without = world.reachable_locations(fixed, owned=` the remaining names minus the prerequisite `)`. Drop the candidates whose location is in `without`.
  - **Ammo gating:** compare `KEY_ITEMS.get(item, item) == container` on `fixed_now`.
  - **`_scene_forbidden`:** a song-scene site also forbids `UPGRADES`.
- [ ] **Step 4:** Run `python -m unittest tests.test_fill`, then the whole suite.
- [ ] **Step 5:** Commit: `feat: the Golden Scale only where the Silver one is needed; ammo gated by any bag`.

### Task 5: Generate and spoiler

**Files:**
- Modify: `randomizer/generate.py`
- Test: `tests/test_generate.py`

- [ ] **Step 1: Failing tests.**
  - `test_gs_forbidden_has_gift_minors`: `_gs_forbidden(..., extra)` is called with every `GIFTS` content (check with a spy on `generate._gs_forbidden`, or assert on the set built by a new helper `_moving_extras()`).
  - `test_npc_gifts_in_mod` is extended: a generated mod with "Any chest" contains `GatheringTokenGold` and `MiniGame_Fishing` when their prizes moved.
  - The `test_npc_gifts_section` spoiler test now lists 35 locations.
- [ ] **Step 2:** Run them and watch them fail.
- [ ] **Step 3: Implement** `_moving_extras() -> frozenset[str]`, which returns `FAIRY_REWARDS | {g.content for g in GIFTS}`, and use it for `_gs_forbidden`.
- [ ] **Step 4:** Run the suite.
- [ ] **Step 5:** Commit: `feat: Skulltulas never drop a gift item they cannot hand over`.

### Task 6: Docs and acceptance seed

**Files:**
- Modify:
  - `docs/npc-gifts-research.md`: correct the frogs and point to the design;
  - `docs/TODO.md`: batch 2 built, the untested items, tokens from gifts;
  - `README.md` and `site/index.html`: the key items help.
- Create: `docs/test-npc-gifts-2.md` and `local/test-npc-gifts-2.md` (acceptance seed `REGALOS2`).

- [ ] **Step 1:** Update the docs.
- [ ] **Step 2:** Generate `REGALOS2` with "Any chest" and the full skip into `test-mod/0400486024DEC000/Rando_REGALOS2`. From its spoiler, write the guide's four checks (spec, "In-game acceptance").
- [ ] **Step 3:** Commit: `docs: NPC gifts batch 2 acceptance guide (seed REGALOS2) and TODO`.
