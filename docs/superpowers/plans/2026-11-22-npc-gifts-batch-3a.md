# NPC Gifts Batch 3a Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Three OoTR settings, `shuffle_ocarinas`, `shuffle_gerudo_card` and `shuffle_expensive_merchants` (all off), make Saria's and Zelda's ocarinas, the Gerudo Card and the two expensive merchants item locations. The Kak 100 Gold Skulltula Reward joins the always-shuffled house rewards. A shuffled merchant sells once.

**Architecture:**
- The new locations are rows appended to `gifts.GIFTS`; a row with a `setting` is only a site when that setting is on.
- `Gift` learns action grants (key `Actor`) and a special entry in another flow.
- The merchants' sold-out patch (`randomizer/merchants.py`) runs after the gift patch.
- The settings travel like `tokensanity`: `Settings`, `browser.py`, the site, the spoiler, and the logic's settings.

**Tech Stack:** Python 3.14, `unittest`; the repo's `bfevfl`, `evfl_append`, `gifts`, `merchants`, `fill`, `logic`, `generate`, `browser`, `spoiler`; the static site (`site/`).

**Spec:** `docs/superpowers/specs/2026-11-21-npc-gifts-batch-3a-design.md`. Its later sections override the earlier parts:
- "Test batch 32 results": the merchants' items need no twins;
- "Gerudo Card: accepted with a safeguard": the card's site holds only minor items, and the logic keeps the vanilla card there.

## Global Constraints

- **Settings:** `shuffle_ocarinas`, `shuffle_gerudo_card` and `shuffle_expensive_merchants`, each `bool = False`, with OoTR's names. Off means the feature is absent.
  - With all three off, `_settings_key` is unchanged (omit them when False, as `tokensanity` does).
  - With key items "Vanilla", the settings are ignored (no error) and nothing changes.
- **Ids:** batch 1 and 2 site ids (`-301`..`-335`) do not move. The new rows come after them, in this order: Kak 100, LW Gift from Saria, HF Ocarina of Time Item, GC Medigoron, Wasteland Bombchu Salesman, Hideout Gerudo Membership Card (`-336`..`-341`).
- **Grants by value**, never by event index. A gift with no matching call raises `GiftPatchError`; a merchant flow with an unexpected shape raises `MerchantPatchError`.
- **Kept as they are:**
  - the Gerudo Card's site is minor-only and unknown to the logic (user's call; 32f4 gave nothing, `docs/TODO.md`). The logic's own `shuffle_gerudo_card` stays false;
  - the merchants' items move as they are (`Shop_Sword_Giant`, `Shop_BombchuBundle_01`); no twin actors.
- **Repo rules:**
  - docs in English; Spanish guides only in `local/`;
  - commits `type: description`;
  - never commit game data (`*.nup`, `test-mod/`, `output/`).
- **Test command:** `python -m unittest discover -s tests` with `OOT_NUP` set (about 11 minutes; run it in the background).

## Review Focus

1. **Medigoron on shared flows.** The gift patch renames his `ActorName` and points `SimpleShop` 112 at `GetInEvent_NotTurn`. Then the merchants' patch appends a setter after 112 in the same `SimpleShop` bytes. Both changes must survive. Test in Task 5.
2. **The vanilla item back at a merchant.** With the setting on, the fill may put the knife back at Medigoron. The flows still get the sold-out patch, and he sells once. Test in Task 5.
3. **Ocarina grants only.** The key `Actor` matches only `EventTriggerAddOrRemovePouchContent` (51 and 106). The screenshot events' `TargetID` (90 and 279) and the Song of Time stay. This holds in the full skip's copies too. Test in Task 3.
4. **Settings off.** The gated rows are no sites, the three merchant flows and both ocarina scenes are untouched, and an excluded ocarina is harmless. Test in Task 4.
5. **Kak 100 and tokens.** Beatable seeds with Tokensanity off and `all`. The 100-token rule only holds when 100 tokens can be reached. Test in Task 4.

---

### Done before this plan (test batch 32 gate)

`randomizer/merchants.py` and `tests/test_merchants.py` exist (commit `f3b6d47`), and 32a and 32b proved them in game. Task 5 consumes them as they are:
- `sold_out_patches(read) -> dict[str, bytes]` and `MerchantPatchError`;
- the constants `MEDIGORON`, `CARPET`, `SHOP`, `MEDIGORON_SOLD` and `CARPET_SOLD`.

### Task 1: Settings

**Files:**
- Modify: `randomizer/fill.py` (`Settings`, `_settings_key`), `randomizer/browser.py` (`parse_settings`), `randomizer/spoiler.py` (`build`, `to_text`), `randomizer/generate.py` (`world_settings`), `site/index.html`, `site/app.js`, `site/presets.js`
- Test: `tests/test_fill.py`, `tests/test_browser.py`, `tests/test_generate.py` (where the spoiler is tested)

**Interfaces:**
- Produces: `Settings.shuffle_ocarinas`, `Settings.shuffle_gerudo_card`, `Settings.shuffle_expensive_merchants` (each `bool = False`); options keys of the same names (bools, default false); spoiler settings keys of the same names, present only when true.

- [ ] **Step 1: Failing tests.**
  - `test_fill.test_settings_key_ignores_new_switches_when_off`: `_settings_key(Settings('x'))` has neither key, and with `shuffle_ocarinas=True` the key contains `"shuffle_ocarinas": true`.
  - `test_browser`: `parse_settings({'shuffle_ocarinas': 'yes'})` raises `ValueError`; `{'shuffle_expensive_merchants': True}` gives `Settings.shuffle_expensive_merchants is True`; the defaults are False.
  - Spoiler (in `test_generate.py`, next to the existing spoiler tests): with `shuffle_ocarinas=True`, `build(...)` has `settings['shuffle_ocarinas'] is True`, and `to_text` has the line `  Shuffle Ocarinas: Yes`. With both off, neither key nor line appears.
- [ ] **Step 2:** Run them; watch them fail.
- [ ] **Step 3:** Implement.
  - **`parse_settings`:** validate the three bools in the `flags` loop.
  - **Spoiler:** the text labels are `Shuffle Ocarinas`, `Shuffle Gerudo Card` and `Shuffle Expensive Merchants`.
  - **`generate.py`:** `world_settings` gets `shuffle_ocarinas` and `shuffle_expensive_merchants`, but not the card: the logic keeps the vanilla card.
  - **Site:** three checkboxes in the item-shuffle section, ids `shuffle_ocarinas`, `shuffle_gerudo_card` and `shuffle_expensive_merchants`, with OoTR's help texts. They are saved and restored like `skip-cutscenes`, and all presets set them to false.
- [ ] **Step 4:** Run the three test files; all pass.
- [ ] **Step 5:** Commit: `feat: Shuffle Ocarinas and Shuffle Expensive Merchants settings`.

### Task 2: Items and logic

**Files:**
- Modify: `randomizer/items.py`
- Test: `tests/test_logic.py`, `tests/test_location_map.py`

**Interfaces:**
- Produces:
  - `KEY_ITEMS` gets `Item_Ocarina_Fairy` and `Item_Ocarina_Time`, both `'Ocarina'`;
  - `ITEM_LEVEL` gets `('Ocarina', 1)` and `('Ocarina', 2)`;
  - `KEY_ITEM_HOME` gets `LW Gift from Saria` and `HF Ocarina of Time Item`;
  - `LABELS` gets `Fairy Ocarina` and `Ocarina of Time`;
  - `FAMILIES` gets `Shop_BombchuBundle_01` → `Bombchus`, `Shop_Sword_Giant` → `Giants Knife` and `Item_Token_Gerudo` → `Gerudo Membership Card`;
  - `content_matches('Obj_Rupee_Gold', 'Huge Rupee')` is True.

- [ ] **Step 1: Failing tests.**
  - `test_logic.test_ocarina_levels`: collecting `Item_Ocarina_Time` gives `items['Ocarina'] == 2`, and a later `Item_Ocarina_Fairy` leaves it at 2.
  - `test_logic`: the vanilla placement (`vanilla_fixed`) is still beatable.
  - `test_location_map`: the key-item count goes up by 2. Each ocarina's home is in OoTR's `locations.json` with vanilla item `Ocarina`. `content_matches` holds for the four new site contents against their OoTR vanilla items: `Giants Knife`, `Bombchus (10)`, `Huge Rupee`, `Gerudo Membership Card`.
- [ ] **Step 2:** Run them; watch them fail.
- [ ] **Step 3:** Implement the tables. Update the tests that count key items, each with a ledger ruling.
- [ ] **Step 4:** Run the two files; all pass.
- [ ] **Step 5:** Commit: `feat: the ocarinas join the key items (progressive Ocarina)`.

### Task 3: `gifts.py` batch 3a

**Files:**
- Modify: `randomizer/gifts.py`
- Test: `tests/test_gifts.py`

**Interfaces:**
- Consumes: Task 1's `Settings`; Task 2's items.
- Produces:
  - `Gift.setting: str | None = None` (a `Settings` field name);
  - `Gift.entry_flow: str | None = None` (the flow that calls `entry`'s special entry; `None` = `flow`);
  - `active_gifts(settings: Settings) -> tuple[Gift | WorldGift, ...]`: the rows whose `setting` is None or true;
  - the six rows of the Global Constraints. The card is `Gift('Hideout Gerudo Membership Card', 'Item_Token_Gerudo', 'Dm_Gerudo_0025', 'ActorName', ('Item_Token_Gerudo',), setting='shuffle_gerudo_card')`. Kak 100 and the merchants use `key='ActorName'`/`'TakenRewardActor'` as found; Medigoron has `entry=('GetInEventItemSwordMedigoron', GENERIC_NPC)` and `entry_flow='SimpleShop'`;
  - `gift_flow_patches` returns the `entry_flow` file too when it changed.

- [ ] **Step 1: Failing tests** (on the real game file; vanilla and `FullSkipFlowsTest` versions as in batch 2):
  - **Ocarinas:** giving `Item_Boomerang` at each ocarina site renames the action's `Actor` (Saria 51, Zelda 106) and the `DisplayGetByActorName` `ActorName` (52, 255). The screenshot events' `TargetID` and the Song of Time event (93) are unchanged.
  - **Kak 100:** renames 250's `TakenRewardActor` and 573's `ActorName`, and no other house call. It swaps with the 10 reward without overwriting.
  - **Medigoron:** his flow's event 6 `ActorName` and `SimpleShop` 112's entry change only when his item changes. The returned dict holds `SimpleShop` then.
  - **Wasteland:** `Npc_Hylia_044_Adult` event 0's `ActorName` changes.
  - **Card:** `Dm_Gerudo_0025` 120's `ActorName` changes.
  - **`active_gifts`:** `Settings('x')` gives batch 2's rows plus Kak 100. Each setting adds its rows (two, one, two).
  - **Ids:** `GIFTS` has 41 rows, and the first 35 locations are unchanged.
- [ ] **Step 2:** Run; watch them fail.
- [ ] **Step 3:** Implement.
  - **`_grants`:** for key `Actor`, it matches `ACTION` events whose action is `EventTriggerAddOrRemovePouchContent`. For the other keys it matches `SUBFLOW` events, as today.
  - **`_redirect`:** it runs on `entry_flow`'s bytes, through `read`, and adds that file to the result.
  - **`gift_subflow_list`:** unchanged. Its row lookup stays on `g.flow`, and `SimpleShop` has no row.
- [ ] **Step 4:** Run `tests.test_gifts`; all pass.
- [ ] **Step 5:** Commit: `feat: NPC gifts batch 3a rows (ocarinas, merchants, Kak 100)`.

### Task 4: Fill

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `active_gifts`, the new rows.
- Produces:
  - `place_all` adds only `active_gifts(settings)` rows as sites (ids from `GIFT_SITE_IDS`, which still covers every row), and `Placement.gifts` covers only those;
  - `MINOR_ONLY_GIFTS: frozenset[str] = {'Hideout Gerudo Membership Card'}`: such a site is left out of `site_loc` (the logic keeps its vanilla item) and goes into `no_key`.

- [ ] **Step 1: Failing tests.**
  - Settings off: `Placement.gifts` has no ocarina or merchant location, and has `Kak 100 Gold Skulltula Reward`.
  - Each setting on, in 20 seeds:
    - `Placement.gifts` has its two locations;
    - the seed is beatable (`World.can_beat` on the result);
    - a merchant never holds a `GIFT_FORBIDDEN` item;
    - with the card on, its site never holds a `KEY_ITEMS` item or a song, and the logic's `fixed` keeps `Gerudo Membership Card` there.
  - The same with `tokensanity='all'` and the three settings on: 20 seeds, beatable.
  - `excluded_items={'Item_Ocarina_Time'}` with `shuffle_ocarinas` on: it stays at `HF Ocarina of Time Item`. With the setting off, the exclusion changes nothing.
- [ ] **Step 2:** Run; watch them fail.
- [ ] **Step 3:** Implement: the `for g in GIFTS` loop of `place_all`, and the `eligible`/`gifts` lines, use `active_gifts(settings)`; `MINOR_ONLY_GIFTS` rows skip `site_loc` and join `no_key`.
- [ ] **Step 4:** Run `tests.test_fill`; all pass.
- [ ] **Step 5:** Commit: `feat: the fill takes the batch 3a gifts by setting`.

### Task 5: Generate

**Files:**
- Modify: `randomizer/generate.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `merchants.sold_out_patches`, `Settings.shuffle_expensive_merchants`.

- [ ] **Step 1: Failing tests** (real game file):
  - With `shuffle_expensive_merchants=True` and "Any chest", the mod's three merchant flows pass the checks of `tests/test_merchants.py` (reuse its helpers). If Medigoron's item changed, `SimpleShop` also has the redirected entry and the new `ActorName`.
  - The same with a placement that leaves Medigoron's knife in place: the sold-out patch is there.
  - With the setting off, the mod has no merchant flow.
  - The spoiler's `npc_gifts` lists 36 locations with all settings off, and 41 with all three on.
- [ ] **Step 2:** Run; watch them fail.
- [ ] **Step 3:** Implement: after the NPC gifts block, `if shuffled and settings.shuffle_expensive_merchants`, `_with_flow_patches(game, sold_out_patches, extras, sizes)`. Catch `MerchantPatchError` into `GenerationError('Could not prepare the merchants: ...')`.
- [ ] **Step 4:** Run the whole suite in the background; all pass.
- [ ] **Step 5:** Commit: `feat: shuffled merchants sell once`.

### Task 6: Docs and acceptance

**Files:**
- Modify: `README.md`, the site's help text, `docs/npc-gifts-research.md` (status line)
- Create: `local/npc-gifts-batch-3a-acceptance.md` (Spanish)

- [ ] **Step 1:** Write it up.
  - **README and site:** the three settings (the card's site holds only minor items), and the always-shuffled Kak 100 reward.
  - **Acceptance guide:** a seed `REGALOS3A` with "Any chest", the skip on and all three settings on. From its spoiler, list Saria, Zelda, Medigoron, the carpet salesman, the Gerudo Card and Kak 100. At each merchant: buy, then talk again.
- [ ] **Step 2:** Commit: `docs: NPC gifts batch 3a settings and acceptance guide`.
- [ ] **Step 3: STOP** for the user's acceptance in game.
