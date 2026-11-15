# Great Fairy rewards in the pool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With key items set to "Any chest", the six Great Fairy rewards join the moving items and the six fountains become item locations. The fountains are free, a revisit only heals, and there is no Din's Fire gate. The seed stays beatable.

**Architecture:** a new module `randomizer/fairies.py` holds the fountain table and the flow patches, taken from the `tools/make_fairy_batch.py` spike and proven by batch 26. The fill adds the fountains as synthetic sites (ids `-201` to `-206`), as Anywhere does for song scenes. The rewards become key items, and one remake logic helper makes any magic item count as the meter. `generate` applies the patches on top of the full skip, like the song flows.

**Tech Stack:** Python 3.14, `unittest` (`python -m unittest`, game tests need `OOT_NUP`), the repo's BFEVFL/BYML/ZS formats.

**Spec:** `docs/superpowers/specs/2026-11-15-great-fairies-design.md`

## Global Constraints

- Repo docs in English. Spanish guides go in `local/` (git-ignored). The chat is in Spanish.
- Commits are `type: description`. Never commit game data (`*.nup`, `test-mod/`, `output/`).
- Flow lookups are by value (actor, action, parameter), never by event index. An unexpected count raises `FairyPatchError`.
- "Vanilla" key items: the placement and the output are unchanged (no fountain site, no fountain patch).
- Fountains never receive `Obj_Token_Gold`, `Item_BulletBag_Small` or `TBox_DekuSeedBundle`.
- The six fountains, in this order (synthetic ids `-201` to `-206`):

  | `Fountain.name` | OoTR location | Reward |
  |---|---|---|
  | Power | HC Great Fairy Reward | Item_FairyBless_MP |
  | Din | DMT Great Fairy Reward | Item_DinFire |
  | Wisdom | DMC Great Fairy Reward | Item_FairyBless_MPDouble |
  | Frore | ZF Great Fairy Reward | Item_FaroreWind |
  | Nayru | Colossus Great Fairy Reward | Item_NayruLove |
  | Courage | OGC Great Fairy Reward | Item_FairyBless_DefenseDouble |

## Review Focus

1. **A fountain flow the full skip rewrote**, with inlined copies of `Pay` and rupee checks. No rupee check, payment or refusal may be reachable from `EntryPoint0`, and every grant copy must give the new item. A test on the full skip's versions covers this.
2. **An excluded reward** stays at its own fountain. The fountain is still patched (free, revisit fix) and gives its own item.
3. **A fairy reward on a Gold Skulltula** under Tokensanity: `_gs_forbidden` must consider the six rewards, which are not in any chest, so one that cannot be wrapped never goes there.
4. **The Power fountain keeping `Item_FairyBless_MP`** must keep the spin attack guide. Only a changed item drops it.
5. **"Vanilla" key items combined with Shuffle Songs** (Song Locations) must not create fountain sites.

---

### Task 1: Rewards as key items; the magic helper

**Files:**
- Modify: `randomizer/items.py` (`KEY_ITEMS`, `LABELS`, `KEY_ITEM_HOME`)
- Modify: `randomizer/logic/world.py` (`REMAKE_HELPERS`)
- Test: `tests/test_logic.py`

**Interfaces:**
- Produces:
  - `KEY_ITEMS` gains:
    - `'Item_FairyBless_MP': 'Magic Meter'`
    - `'Item_FairyBless_MPDouble': 'Magic Meter'`
    - `'Item_DinFire': 'Dins Fire'`
    - `'Item_FaroreWind': 'Farores Wind'`
    - `'Item_NayruLove': 'Nayrus Love'`
    - `'Item_FairyBless_DefenseDouble': 'Double Defense'`
  - `LABELS` gains "Magic Meter", "Double Magic", "Din's Fire", "Farore's Wind", "Nayru's Love" and "Double Defense".
  - `KEY_ITEM_HOME` maps each reward to its fountain's OoTR location (the table above). `vanilla_fixed` then puts the remake's own rewards there, with Power's at HC.
  - `REMAKE_HELPERS['Magic_Meter'] = "'Magic Meter' or Dins_Fire or Farores_Wind or Nayrus_Love"`.

- [ ] **Step 1: Write the failing tests** in `tests/test_logic.py`, next to `test_bombs_need_bracelet` (same `World`/state helpers):
  - `test_magic_meter_from_any_magic_item`: the Lens of Truth's use (`can_use(Lens_of_Truth)` through a rule that needs it) or the helper `Magic_Meter` evaluates True with only `Item_DinFire`, only `Item_FaroreWind`, only `Item_NayruLove`, only `Item_FairyBless_MP` or only `Item_FairyBless_MPDouble`, and False with none of them.
  - `test_vanilla_fixed_has_remake_fairy_rewards`: `World(...).vanilla_fixed()['HC Great Fairy Reward'] == 'Item_FairyBless_MP'` and `['DMT Great Fairy Reward'] == 'Item_DinFire'`.
  - The existing `test_vanilla_is_beatable` and `test_baseline_is_beatable` must stay green.
- [ ] **Step 2: Run** `python -m unittest tests.test_logic -v`. Expected: the two new tests FAIL (KeyError / False).
- [ ] **Step 3: Implement the table entries and the helper.**
- [ ] **Step 4: Run** `python -m unittest tests.test_logic tests.test_browser`. Expected: PASS. `browser.items()` now lists the six rewards; they are movable, because their homes are not chests with event patches.
- [ ] **Step 5: Commit** `feat: Great Fairy rewards as key items; any magic item brings the meter`.

### Task 2: `randomizer/fairies.py` — table and flow patches

**Files:**
- Create: `randomizer/fairies.py`
- Create: `tests/test_fairies.py` (game tests: `@unittest.skipUnless(NUP_PATH, ...)` as in `tests/test_songs.py`)

**Interfaces:**
- Consumes: `songs._rename_flag(data, kind, old, new) -> (bytes, int)`, `songs.bypass(data, events) -> bytes`, and `bfevfl.EventFlow`, `patch_pointers`, `set_string_param`, `set_subflow_entry`, `SUBFLOW`, `SWITCH`.
- Produces:
  ```python
  @dataclass(frozen=True)
  class Fountain:
      name: str      # flow suffix: Dm_FairyFountain_<name>
      location: str  # OoTR location
      reward: str    # remake actor it gives in the game
      @property
      def flow(self) -> str: ...  # 'Dm_FairyFountain_' + name
  FOUNTAINS: tuple[Fountain, ...]            # the six, in the table order
  FOUNTAIN_BY_LOCATION: dict[str, Fountain]
  FAIRY_REWARDS: frozenset[str]
  FOUNTAIN_FORBIDDEN: frozenset[str] = frozenset({'Obj_Token_Gold', 'Item_BulletBag_Small', 'TBox_DekuSeedBundle'})
  TRIFORCE_FLOW = 'TriForcePoint'
  class FairyPatchError(ValueError): ...
  def fairy_flow_patches(read: Callable[[str], bytes], fairies: dict[str, str]) -> dict[str, bytes]
  ```
  - `fairy_flow_patches` returns `{}` for empty `fairies`.
  - Otherwise `fairies` must name exactly the six locations; anything else raises `FairyPatchError`.
  - It returns the six fountain flows plus `TriForcePoint`, each patched as follows:
    - **Grant:** every `Dm_SY_GetInEvent` call whose `ActorName` is the reward gets the new item (at least one). When the item changed and the call's entry is not `GetInEvent_Demo_NotLookatObjectEntry`, the entry is set to that.
    - **Spin attack guide:** when the item changed, every `ActionGuide` subflow call is bypassed.
    - **Revisit:** `_rename_flag(data, 'EventQueryIsGameDataBool', 'IsGet.' + reward, 'HavePlayedEvent.' + flow)` must return exactly 1.
    - **Free (`make_free`):** every `EventQueryTalkChoice2` and `EventQueryHasRuppe` switch is retargeted to its case-value-0 target, and every `EventTriggerIncreaseRupee` is bypassed.
    - **`TriForcePoint`:** the single two-case `IsGet.Item_DinFire` bool switch is retargeted to its case-value-0 target.

  The helpers come from `tools/make_fairy_batch.py`: `_switch_case_targets`, `_retarget`, `make_free`, `patch_fountain` and `patch_triforce`. They raise `FairyPatchError` instead of `SystemExit`.

- [ ] **Step 1: Write the failing tests** (`tests/test_fairies.py`). A `read` helper decompresses from the nup. A second class reads the full skip's versions from `full_skip.files_with_fallback(game, FULL_SKIP_PHASE)`, falling back to the nup for flows it did not write (Din). Each test runs on both versions. A `reachable(flow, 'EntryPoint0')` helper follows next, cases, forks, join and same-file subflow calls (`sub_flow in ('', flow name)`).
  - `test_table_matches_ootr`: the six locations exist in the logic's locations with `'Great Fairies'` in their categories. `FAIRY_REWARDS` is the six rewards, and each is in `items.KEY_ITEMS`.
  - `test_empty_placement_changes_nothing`: `fairy_flow_patches(read, {}) == {}`.
  - `test_wrong_locations_raise`: five locations raise `FairyPatchError`, and so does an unknown location.
  - `test_grant_gives_new_item`: with Power → `Item_Boomerang` and Wisdom → `Item_NayruLove` (the others vanilla):
    - every `Dm_SY_GetInEvent` call in Power's output has `ActorName` `Item_Boomerang`;
    - Wisdom's calls have `Item_NayruLove` and `sub_entry == 'GetInEvent_Demo_NotLookatObjectEntry'`;
    - Din's (unchanged) keeps `GetInEvent_GreatFairyDin`.
  - `test_spin_guide_only_when_changed`: Power → `Item_Boomerang` has no `ActionGuide` call reachable from `EntryPoint0`; Power keeping `Item_FairyBless_MP` still has one.
  - `test_free_on_every_fountain`: for each of the six outputs, no `EventQueryTalkChoice2`, `EventQueryHasRuppe`, `EventTriggerIncreaseRupee` or `DontPay1`/`DontPay2` call is reachable from `EntryPoint0` (for Din, also from the entries `Pay`, `DontPay1` and `DontPay2`), and a grant is reachable.
  - `test_revisit_reads_have_played`: each output has exactly one `EventQueryIsGameDataBool` on `HavePlayedEvent.Dm_FairyFountain_<name>` beyond the vanilla `HavePlayedEvent` checks. Count against the input: +1. It has no `IsGet.<reward>` query left in its entry branch.
  - `test_triforce_gate_removed`: no `IsGet.Item_DinFire` two-case switch is reachable from any `TriForcePoint` entry `Demo_FairyFountain_*`.
- [ ] **Step 2: Run** `python -m unittest tests.test_fairies -v` with `OOT_NUP` set. Expected: FAIL, `ModuleNotFoundError: randomizer.fairies`.
- [ ] **Step 3: Implement `randomizer/fairies.py`** from the spike's functions, with the interfaces above.
- [ ] **Step 4: Run** `python -m unittest tests.test_fairies -v`. Expected: PASS.
- [ ] **Step 5: Point the spike at the module.** `tools/make_fairy_batch.py` imports `fairies.make_free`, `patch_fountain` and `patch_triforce` instead of its own copies, so there is one implementation. Then run `python -I tools/make_fairy_batch.py <nup> output/check 26a` and confirm it builds.
- [ ] **Step 6: Commit** `feat: Great Fairy flow patches (randomizer/fairies.py)`.

### Task 3: Fill — fountains as sites

**Files:**
- Modify: `randomizer/fill.py` (`Placement`, `place_all`, `_attempt`'s scene block, new `FOUNTAIN_SITE_IDS`)
- Test: `tests/test_fill.py` (new `FairyFillTest`, using the `AnywhereFillTest` set-up)

**Interfaces:**
- Consumes: `fairies.FOUNTAINS`, `FOUNTAIN_FORBIDDEN`; Task 1's `KEY_ITEMS`.
- Produces:
  - `FOUNTAIN_SITE_IDS: dict[str, int] = {f.location: -(201 + k) for k, f in enumerate(FOUNTAINS)}`.
  - `Placement` gains `fairies: dict[str, str] = field(default_factory=dict)`, mapping OoTR fountain location to actor. It is filled only with "Any chest".
  - `place_all`: with "Any chest", each fountain becomes a site (`original[id] = reward`, `site_loc[id] = location`, added to `eligible`), so its reward is moving through `KEY_ITEMS`. `Placement.chests` keeps only ids `>= 0` in every mode. `songs`, `hearts` and `fairies` come from the synthetic ids.
  - In `_attempt`, the scene block (ids `< 0`) uses a per-site forbidden set: song scenes `{TOKEN}`, fountains `FOUNTAIN_FORBIDDEN`. The error message says "song scenes or fountains". Key items going to a fountain also skip `FOUNTAIN_FORBIDDEN`, which matters for no key item today; it is a guard.
- [ ] **Step 1: Write the failing tests** in `FairyFillTest`:
  - `test_fountains_hold_six_items`: `placed.fairies` has the six locations, and the multiset of `chests` values plus `fairies` values plus songs equals the original multiset plus the six rewards.
  - `test_fairy_rewards_move`: across 10 seeds, at least one reward is not at its own fountain, and every placed reward is at a location reachable in the logic.
  - `test_beatable_many`: 20 seeds give `world.can_beat` on the final fixed.
  - `test_fountains_never_get_forbidden`: across 20 seeds with Tokensanity "all", no fountain gets an item in `FOUNTAIN_FORBIDDEN`.
  - `test_excluded_reward_stays`: `excluded_items={'Item_DinFire'}` puts `fairies['DMT Great Fairy Reward'] == 'Item_DinFire'`.
  - `test_vanilla_keys_no_fountains`: "Vanilla" key items (songs off, and Song Locations) give `fairies == {}`, and `chests` are equal to the result before this task (`test_vanilla_mode_identity` stays green).
  - `test_with_songs_anywhere_and_dungeon_rewards`: both work, and the song and fountain sites are disjoint.
- [ ] **Step 2: Run** `python -m unittest tests.test_fill -v`. Expected: the new tests FAIL (no `fairies`).
- [ ] **Step 3: Implement** the changes listed in Interfaces.
- [ ] **Step 4: Run** `python -m unittest tests.test_fill tests.test_songs -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: the Great Fairy fountains join the fill`.

### Task 4: Generate, spoiler, Skulltula check

**Files:**
- Modify: `randomizer/generate.py`:
  - `_with_song_flows` becomes `_with_flow_patches(game, patches_fn, extras, sizes)`, where `patches_fn(read) -> {flow: bytes}`; songs and fairies both use it;
  - `_gs_forbidden(..., extra=())`.
- Modify: `randomizer/spoiler.py` (`build(..., fairies=None)`, the text section).
- Test: `tests/test_generate.py`, `tests/test_spoiler*` or the spoiler tests already in `tests/test_generate.py`.

**Interfaces:**
- Consumes: `fairies.fairy_flow_patches`, `FAIRY_REWARDS`; `Placement.fairies`.
- Produces:
  - **generate:** when `placed.fairies`, the fountain and `TriForcePoint` flows are patched on top of the skip's files, with their size deltas in `sizes`. Errors become `GenerationError('Could not prepare the Great Fairies: …')`. With Tokensanity, `_gs_forbidden` gets `extra=FAIRY_REWARDS`, so a reward that cannot be wrapped never goes on a Skulltula.
  - **spoiler:** `result['great_fairies'] = [{'location', 'item', 'label'}]` sorted by location. The rows of key items given by fountains appear in `key_items` with zone `'Great Fairy'`. The text gets a `Great Fairies` section after `Boss hearts`.
- [ ] **Step 1: Write the failing tests:**
  - `test_great_fairies_in_mod` (game, "Any chest", seed fixed, skip on and off): the mod has `Event/EventFlow/Dm_FairyFountain_{Power,Din,Wisdom,Frore,Nayru,Courage}.bfevfl.zs` and `TriForcePoint.bfevfl.zs`. Decompressed, each fountain's grant `ActorName` equals the spoiler's `great_fairies` item for that location. RSTB entries exist (no RSTB report line).
  - `test_spoiler_great_fairies`: `spoiler.build` with a `fairies` dict produces the JSON list and the text section.
  - `test_gs_forbidden_extra`: `_gs_forbidden(game, chests, loc_map, extra={'Item_X'})` includes a content that cannot be wrapped from `extra`. Use a fake actor name that is not in the RSDB.
  - `test_vanilla_mode_no_changes` stays green: there are no fountain files in "Vanilla".
- [ ] **Step 2: Run** `python -m unittest tests.test_generate -v`. Expected: the new tests FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `python -m unittest tests.test_generate -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: generate patches the Great Fairies; spoiler lists them`.

### Task 5: Site, docs, acceptance seed, full suite

**Files:**
- Modify:
  - `site/index.html`: the `tip-mode` help says that with "Any chest" the six Great Fairy rewards are shuffled too, the fairies are free and only heal on a second visit;
  - `README.md`: the "moved" list and the Great Fairies;
  - `docs/great-fairies-research.md` ("Next" points to this plan);
  - `docs/TODO.md`.
- Create: `docs/test-great-fairies.md` (English) and `local/test-great-fairies.md` (Spanish guide).

- [ ] **Step 1:** Run `python -m unittest tests.test_build_site tests.test_site_js`. Then build the site (`python tools/build_site.py`, as its tests expect) and check the Items tab lists the six rewards in "Exclude items".
- [ ] **Step 2: Acceptance seed.** Generate `HADAS1` with "Any chest", Skip cutscenes on and the spoiler on (`python -m randomizer` CLI, or `generate()` from a scratch script) into `output/`, then copy it to `test-mod/0400486024DEC000/`. From its spoiler, the guide lists:
  - three fountains with their items, including one with a minor item if the spoiler has one; otherwise regenerate with `HADAS2` and so on;
  - the castle and mountain fountains in particular.
- [ ] **Step 3:** Run the full suite: `python -m unittest discover -s tests` with `OOT_NUP` set. Expected: all pass, with 1 expected failure as today.
- [ ] **Step 4: Commit** `docs: Great Fairies in the pool, site help and acceptance guide`.
- [ ] **Step 5:** Final whole-branch review, then wait for the user's acceptance test.
