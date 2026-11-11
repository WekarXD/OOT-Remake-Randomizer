# Gifts — Phase B: Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add to the page the switches for the ocarinas, the Gerudo Card, the Skulltula rewards, the frogs and the Loach fish. With a switch on, the gifts of those scenes enter the fill.

**Architecture:**
- A data file (`gift_map.json`) maps each gift to its OoTR location, its flow, the events and keys to change, and the original item.
- The fill treats active gifts as additional locations. A gift only receives `Item_*` items from the set that moves, and all active gifts receive one.
- The minor originals of the gifts (`Obj_*`) go to the chests.
- The mod rewrites the text parameters with `set_string_param`, on top of the "Skip cutscenes" trim if it is active. It also updates the RSTB if the flow grows.

**Tech Stack:** Python 3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-11-10-gifts-design.md` (§4.2, §4.3, §4.4 B and §7). Phase A passed in game (`docs/test-batch-7.md`).

## Global Constraints

- The `.nup` is never written to and game files are never committed.
- Tests that use the game carry `@unittest.skipUnless(NUP_PATH, 'OOT_NUP not defined')` and run with `python -m unittest` (without `-I`).
- Standard library only. User-facing texts are in English and commits carry no attribution lines.
- Compatibility (spec §7): with all the new switches off, the RNG key, the fill and the mod are identical to today's. The new settings only enter the key when they are on.
- What can go in a gift (spec §7): only `Item_*` items, that is, the key items of the fill and the original `Item_*` of the active gifts.
- Shared scenes (spec §7): only a parameter that belongs to that location is changed. If `string_param_owners` shows foreign events, the location is left out.
- If a location cannot be confirmed (it is not known which event it is, or the gift can be received more than once), it is left out and documented. It does not block the others (spec §6).
- OoTR's logic is loaded with `vanilla_settings.json` unchanged. None of these settings appears in the vendored rules (`grep` of 2026-11-10); they only change which locations enter the fill.

## Review Focus

1. **Out-of-order ocarinas.** If the Ocarina of Time is obtained before the Fairy Ocarina, the logic counts level 2 and does not lower it on receiving the other. Also, in vanilla (no switches) the Door of Time is still reachable. Test in task 2.
2. **All active gifts receive an item.** A gift is never left empty nor receives an `Obj_*` or `TBox_*` item. Chests receive exactly the items that remain. Test in task 3.
3. **Gift in a flow that "Skip cutscenes" also trims.** The gift's event remains reachable after the trim, and both changes land in the same file. Test in task 4.
4. **A flow that grows.** The mod's RSTB carries that flow's entry, even if no Banc has changed. Test in task 4.
5. **Invalid data or request.** A location or a setting that does not exist in OoTR, or a switch that is not a boolean in the request, gives a clear error and generates nothing. Tests in tasks 1 and 5.

---

### Task 1: Gift data

**Files:**
- Create:
  - `randomizer/data/gift_map.json`
  - `randomizer/gifts.py`
  - `tests/test_gifts.py`

**Interfaces:**
- Consumes: `EventFlow`, `string_param_owners` (`randomizer/formats/bfevfl.py`) and `ootr_data.load_locations()`.
- Produces, in `randomizer/gifts.py`:
  - `GiftSite`, a frozen dataclass with these fields:
    - `location: str` (OoTR location, which serves as the id);
    - `option: str` (name of the setting in `Settings`);
    - `flow: str` (path without `.zs`, for example `'Event/EventFlow/Dm_Kokiri_0155.bfevfl'`);
    - `edits: tuple[tuple[int, str], ...]` (event and key pairs);
    - `original: str` (original actor).
  - `GIFT_MAP_PATH` and `load_gift_map(path=GIFT_MAP_PATH) -> dict[str, GiftSite]` (by location).
  - `OPTIONS: tuple[tuple[str, str], ...]`, with the setting and its English label, in this order:
    - `('shuffle_ocarinas', 'Ocarinas (Shuffle Ocarinas)')`
    - `('shuffle_gerudo_card', 'Gerudo Card (Shuffle Gerudo Card)')`
    - `('shuffle_skulltula_rewards', 'Skulltula rewards (Shuffle 100 Skulltula Reward and 10 to 50)')`
    - `('shuffle_frogs', "Frogs' Pieces of Heart")`
    - `('shuffle_loach_reward', 'Loach fish reward (Shuffle Hyrule Loach Reward)')`
  - `available_options() -> list[tuple[str, str]]`: those in `OPTIONS` with at least one location in the map.
- JSON format: `{"<OoTR location>": {"option": ..., "flow": ..., "edits": [[event, "key"], ...], "original": ..., "note": ...}}`.

Locations confirmed by the 2026-11-10 exploration (`action_params` on the game):

| OoTR location | option | flow (`Event/EventFlow/…bfevfl`) | edits | original |
|---|---|---|---|---|
| LW Gift from Saria | shuffle_ocarinas | Dm_Kokiri_0155 | (51,'Actor'), (52,'ActorName') | Item_Ocarina_Fairy |
| HF Ocarina of Time Item | shuffle_ocarinas | Dm_MelodyGet_Time | (106,'Actor'), (255,'ActorName') | Item_Ocarina_Time |
| Hideout Gerudo Membership Card | shuffle_gerudo_card | Dm_Gerudo_0025 | (120,'ActorName') | Item_Token_Gerudo |
| Kak 10 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (245,'TakenRewardActor') | Item_Wallet_Medium |
| Kak 20 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (246,'TakenRewardActor') | Item_AgonyStone |
| Kak 30 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (247,'TakenRewardActor') | Item_Wallet_Large |
| Kak 40 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (248,'TakenRewardActor') | Item_BombchuBundle_Large |
| Kak 50 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (249,'TakenRewardActor') | Obj_Heart_Piece |
| Kak 100 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (250,'TakenRewardActor') | Obj_Rupee_Gold |

Unconfirmed; the implementer decides:
- **Frogs.** `MiniGame_FrogTenors`: events 71 and 91 (`Obj_Heart_Piece`, with `IsRetry` false and true), 72 and 92 (`Obj_Rupee_Blue`) and 247 (`Obj_Heart_Piece`). It must be worked out which one is "ZR Frogs in the Rain" and which "ZR Frogs Ocarina Game", and whether the `IsRetry` branch can give the prize again.
- **Loach fish.** `MiniGame_Fishing`, events 655 to 660 (rupees). It must be worked out whether any of them is the Loach prize ("LH Loach Fishing") and whether it is given only once.
- **Rule for both cases.** A location only goes in if it has a clear event and is received once. Otherwise it is left out and explained in `docs/superpowers/specs/2026-11-10-gifts-design.md` §8 (new section "Phase B: discarded locations"). `available_options()` then hides that option.

- [ ] **Step 1: Tests**
  - Tests without the game:
    - `test_map_loads`: `load_gift_map()` returns `GiftSite` and each `option` is in `dict(OPTIONS)`.
    - `test_locations_exist`: each key exists in `ootr_data.load_locations()`.
    - `test_bad_option_rejected`: a temporary JSON with an unknown `option` or a nonexistent location makes `load_gift_map(path)` raise `ValueError`, with the location in the message.
    - `test_available_options`: only options with locations come out, in the order of `OPTIONS`.
  - Test with `OOT_NUP`, `test_sites_match_game`:
    - for each location and each edit, `action_params(event)[key] == original`;
    - `set(string_param_owners(...))` is contained in the events of that location.
- [ ] **Step 2:** Run `python -m unittest tests.test_gifts -v`. A FAIL is expected.
- [ ] **Step 3:** Investigate the frogs and the Loach with the BFEVFL reader, following the `switch` branches, the event queries and the flags. Write the JSON and `gifts.py`, and document in spec §8 whatever is discarded.
- [ ] **Step 4:** Run the tests and the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: gift site map`.

### Task 2: Gift items in the logic

**Files:**
- Modify:
  - `randomizer/items.py`
  - `randomizer/logic/rules.py` (`State.collect`)
  - `randomizer/logic/world.py` (`vanilla_fixed`, `_relevant`)
- Test: `tests/test_logic.py`

**Interfaces:**
- Produces, in `items.py`:
  - `GIFT_ITEMS: dict[str, str]`, from actor to OoTR item:
    - `Item_Ocarina_Fairy` → `'Ocarina'`
    - `Item_Ocarina_Time` → `'Ocarina'`
    - `Item_Token_Gerudo` → `'Gerudo Membership Card'`
    - `Item_Wallet_Medium` → `'Progressive Wallet'`
    - `Item_Wallet_Large` → `'Progressive Wallet'`
    - `Item_AgonyStone` → `'Stone of Agony'`
    - `Item_BombchuBundle_Large` → `'Bombchus (10)'`
  - In `ITEM_LEVEL`, add:
    - `Item_Ocarina_Fairy` → `('Ocarina', 1)` and `Item_Ocarina_Time` → `('Ocarina', 2)`;
    - `Item_Wallet_Medium` → `('Progressive Wallet', 1)` and `Item_Wallet_Large` → `('Progressive Wallet', 2)`.
  - `GIFT_ITEM_HOME: dict[str, str]`, from actor to vanilla location, for the seven actors in `GIFT_ITEMS`:
    - `Item_Ocarina_Fairy` → 'LW Gift from Saria'
    - `Item_Ocarina_Time` → 'HF Ocarina of Time Item'
    - `Item_Token_Gerudo` → 'Hideout Gerudo Membership Card'
    - `Item_Wallet_Medium` → 'Kak 10 Gold Skulltula Reward'
    - `Item_AgonyStone` → 'Kak 20 Gold Skulltula Reward'
    - `Item_Wallet_Large` → 'Kak 30 Gold Skulltula Reward'
    - `Item_BombchuBundle_Large` → 'Kak 40 Gold Skulltula Reward'
  - `LABELS` adds:
    - Fairy Ocarina
    - Ocarina of Time
    - Gerudo Card
    - Adult's Wallet
    - Giant's Wallet
    - Stone of Agony
    - Bombchus (10)
  - `ALL_ITEMS = {**KEY_ITEMS, **GIFT_ITEMS}`.
- `rules.State.collect` and `World._relevant` accept any actor in `ALL_ITEMS`.
- `World.vanilla_fixed` also puts the actors from `GIFT_ITEM_HOME`. This is needed because `'Ocarina'` and `'Progressive Wallet'` become `LEVELED`, and two generic `'Ocarina'` values no longer add up to level 2.
- `KEY_ITEMS`, `KEY_ITEM_HOME` and the page's list do not change.

- [ ] **Step 1: Tests**
  - `test_vanilla_still_beatable`: `World(load_vanilla_settings()).can_beat(world.vanilla_fixed())` still gives the same result as today.
  - `test_door_of_time_vanilla`: with `vanilla_fixed()`, 'Song from Ocarina of Time' is reached. At least one 'Temple of Time' location that asks for `(Ocarina, 2)` is also reached, because `stones_oot_sot` requires the Ocarina of Time.
  - `test_ocarina_out_of_order`: a `State()` that collects `Item_Ocarina_Time` and then `Item_Ocarina_Fairy` has `items['Ocarina'] == 2`.
  - `test_wallet_out_of_order`: the same with the wallets.
  - `test_no_other_leveled_vanilla`: no location in `locations.json` with `vanilla_item` in `{'Ocarina', 'Progressive Wallet'}` is left outside `GIFT_ITEM_HOME.values()`.
- [ ] **Step 2:** Run `python -m unittest tests.test_logic -v`. A FAIL is expected.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite. A PASS is expected, with `test_fill` and `test_generate` unchanged.
- [ ] **Step 5:** Commit with the message `feat: gift items in logic`.

### Task 3: Fill with gifts

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `GiftSite` and `load_gift_map` (task 1), and `GIFT_ITEMS` and `ALL_ITEMS` (task 2).
- Produces:
  - `Settings` adds the fields `shuffle_ocarinas`, `shuffle_gerudo_card`, `shuffle_skulltula_rewards`, `shuffle_frogs` and `shuffle_loach_reward`, all `bool = False`.
  - `_settings_key` removes each of those fields when it is `False`. That way the key with everything off is identical to today's.
  - `place_full(chests, loc_map, world, settings, gift_map: dict[str, GiftSite]) -> tuple[dict[int, str], dict[str, str]]`: the chest fill (as today) and the gift fill (location → actor), only for the active gifts.
  - `place(...)` keeps the same signature and the same result: it calls `place_full` with `{}` and returns the first element.
- Fill rules:
  - **Active gifts:** those in `gift_map` whose setting is on in `settings`. In `vanilla` mode there are none.
  - **Items that move:** the key items of the chests, as today, plus the originals of the active gifts that are in `GIFT_ITEMS`.
  - **Minor originals:** those not in `GIFT_ITEMS`, such as `Obj_Heart_Piece` and `Obj_Rupee_Gold`. They go to the `rest` pile, which fills chests.
  - **Free locations:** today's free chests plus the active gifts. A gift only accepts items from the set that moves.
  - **Logic base:** the active gifts are set to `FILLER` in the base, just like the eligible chests.
  - **Location choice at each step of the *assumed fill*.** `g` is the number of empty gifts and `r` the number of items left to place, including the current one:
    - if `g == r`, the candidates are only the reachable empty gifts;
    - otherwise, with probability `g / r` (using the attempt's RNG) the choice is among the reachable empty gifts, and if there are none, among the chests;
    - in the other case the choice is among the reachable free chests, as today;
    - if a candidate set ends up empty, the attempt returns `None`.
  - **Counts:** free chests remaining = `len(rest)`, without `strict=False`. `_fixed` uses `ALL_ITEMS` instead of `KEY_ITEMS`.

- [ ] **Step 1: Tests** (with the chest fixture that `test_fill` already uses and the real locations from `load_gift_map()`)
  - `test_all_off_identical`: `place(...)` and `place_full(..., load_gift_map())[0]` with `Settings(seed='X')` are equal. In addition `_settings_key` equals that of a `Settings` without the new fields, comparing the JSON against a fixed string generated today.
  - `test_gifts_filled_with_items`: with `shuffle_ocarinas` and `shuffle_skulltula_rewards` on, each active gift receives an actor from `ALL_ITEMS`, none `Obj_*` or `TBox_*`, and `World.can_beat` is `True` with the result.
  - `test_minor_originals_go_to_chests`: `Obj_Heart_Piece` (50 Skulltulas) and `Obj_Rupee_Gold` (100) appear in some chest of the fill. The multiset of chest and gift contents is the same as before, with the active gifts included.
  - `test_deterministic`: the same seed and the same settings give the same result. Turning on `shuffle_ocarinas` changes the key.
  - `test_vanilla_mode_no_gifts`: with `key_items_mode='vanilla'`, the gifts dictionary is empty.
- [ ] **Step 2:** Run `python -m unittest tests.test_fill -v`. A FAIL is expected.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: place items in NPC gifts`.

### Task 4: Write the gifts to the mod and the spoiler log

**Files:**
- Modify:
  - `randomizer/gifts.py`
  - `randomizer/patch.py`
  - `randomizer/generate.py`
  - `randomizer/spoiler.py`
- Test: `tests/test_gifts.py`, `tests/test_generate.py`

**Interfaces:**
- Consumes:
  - `set_string_param`;
  - `build_cutscene_files(game) -> dict[str, bytes]` (`.zs` paths and compressed data);
  - `place_full` (task 3);
  - `Rstb`, `RSTB_PATH` and `GameData` (`game.codec`, `game.nup`).
- Produces:
  - `gifts.build_gift_files(game, gifts: dict[str, str], gift_map, base_files: dict[str, bytes]) -> tuple[dict[str, bytes], dict[str, int]]`. It returns the files (those in `base_files` plus the gift flows) and the RSTB values of the flows that grow.
    - For each flow, start from the decompressed `base_files[flow + '.zs']` if it exists. Otherwise, start from the `.nup`.
    - All the edits of that flow's gifts whose actor is not the original are applied.
    - If the flow grows, the RSTB value is the original + (growth rounded up to 0x100) + 0x1000, like `tools/make_gift_batch.py`.
  - `patch.write_mod(..., extra_files=None, extra_rstb: dict[str, int] | None = None)`. It applies `extra_rstb` to the same RSTB and writes it also if there are no changed Banc files but `extra_rstb` is not empty.
  - `generate` calls `place_full` and `build_gift_files` (on `extras` if cutscenes are skipped) and passes `extra_rstb`. `BfevflError` errors are converted into `GenerationError('Could not prepare the gifts: …')`.
  - `spoiler.build(..., gifts: dict[str, str] | None = None)` adds the key `'gifts'`: a sorted list of `{'location', 'item'}` with `LABELS`. `to_text` adds the "Gifts" section only if there are any. "Shuffle" in the spoiler's settings lists the switches that are on.

- [ ] **Step 1: Tests** (with OOT_NUP)
  - `test_build_gift_files_roundtrip`: Saria becomes `Item_Gauntlet_Silver`, which is longer and forces growth. When the flow is reread, both edits give the new actor and there is an RSTB value for that flow.
  - `test_gift_over_trim`:
    - With `base_files = build_cutscene_files(game)`, if `Dm_Kokiri_0155` or another gift flow is in `base_files`, the result contains both the trim (the pointers from `base_files`) and the new actor.
    - Each edit event is still reachable from some entry point. The test includes a simple walk through `next`, `cases`, `forks` and `join`.
  - `test_write_mod_rstb_without_banc`: `write_mod` with vanilla placement and `extra_rstb={'Event/EventFlow/X.bfevfl': 123}` writes the RSTB, and when loaded `get` gives 123.
  - `test_generate_all_on`:
    - A seed with the five switches writes the gift flows.
    - The spoiler JSON has `'gifts'` with one element per active gift.
    - With everything off, the list of written files is identical to today's.
- [ ] **Step 2:** Run the tests. A FAIL is expected.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: write NPC gifts to the mod and spoiler`.

### Task 5: "Shuffle" section on the page

**Files:**
- Modify:
  - `randomizer/web/server.py`
  - `randomizer/web/static/index.html`
  - `randomizer/web/static/app.js`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `gifts.available_options()` and the new `Settings` fields.
- Produces:
  - The configuration GET adds `'shuffle_options': [{'key', 'label'}]`, in the order of `available_options()`.
  - The POST accepts each key as a strict boolean, like `skip_cutscenes`. If it is not a boolean, it returns a 400 error `'<key> must be true or false'`. A key that is not in `available_options()` also gives a 400 error.
  - The page has, in the Items panel, a `<fieldset>` with the legend "Shuffle". It carries one checkbox per option, with id `shuffle-<key>`, unchecked by default. They are saved and loaded like the page's other options.

- [ ] **Step 1: Tests**
  - `test_shuffle_options_listed`
  - `test_shuffle_strict_bool` (a `"yes"` gives 400)
  - `test_unknown_shuffle_key_400`
  - `test_shuffle_passed_to_settings`: the `Settings` that reaches `generate` carries `shuffle_ocarinas=True`.
- [ ] **Step 2:** Run `python -m unittest tests.test_server -v`. A FAIL is expected.
- [ ] **Step 3:** Implement. Check the page in the panel browser, with screenshots of the section.
- [ ] **Step 4:** Run the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: Shuffle section in the web UI`.

### Task 6: Test batch 8 (seed with everything on)

**Files:**
- Create: `docs/test-batch-8.md`

- [ ] **Step 1:** Generate `output/test/Rando_TestGifts1` (ignored by git) with these settings:
  - seed `TestGifts1`;
  - `any_chest`;
  - all the Shuffle switches on;
  - "Skip cutscenes" enabled;
  - spoiler log enabled.

  It is generated with `python -m randomizer` or with the `generate` function, and what each gift received is noted down.
- [ ] **Step 2:** Write `docs/test-batch-8.md` in English, with checkboxes:
  - new game and only this mod;
  - a table with what each gift gives according to the spoiler log;
  - check each gift that is reachable without much effort: Saria, Ocarina of Time, the 10 Skulltulas reward, frogs or Loach if they went in;
  - does the new item arrive and can it be used at that age?;
  - if one ocarina comes before the other, can songs be played? Is either lowered on receiving the second?;
  - if the Gerudo Card is outside the fortress: does the Training Grounds door open with the card obtained elsewhere? Do the guards turn friendly when the carpenters are rescued without the card? This is the risk from §3.5;
  - Adult's and Giant's Wallets out of order;
  - an empty "Results" section.
- [ ] **Step 3:** Run the full suite. A PASS is expected.
- [ ] **Step 4:** Commit with the message `test: gift test batch 8 (all Shuffle on)`.

### Gate (after task 6)

The user tests `Rando_TestGifts1` in Lichii.
- **If it works:** the phase C plan is written (beans and expensive merchants).
- **If a type of gift fails:** that location is removed from `gift_map.json`, documented, and the others continue.
