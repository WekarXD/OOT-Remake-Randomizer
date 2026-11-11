# Full Cutscene Skip — Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the effects-only scene rewriter and its action table, and produce test mod `TestScenes4` with four rewritten scenes for the user's go/no-go (spec §6 step 1).

**Architecture:** `bfevfl.py` learns subflow targets and a named map of its link slots. A data table (`skip_actions.json`, built by a tool) says which actions, switch queries and cross-file subflows survive. `skipflow.py` linearizes a scene into its kept steps and turns that into link rewrites, applied in place with `patch_pointers` (no size change in this phase). A tool writes the four rewritten flows as a LayeredFS test mod.

**Tech Stack:** Python 3.14 standard library, `unittest`.

**Spec:** `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md`

## Global Constraints

- Never write to the `.nup`; never commit game files (test mods go to `test-mod/`, which is gitignored).
- Everything committed is in English; user-facing test guides in Spanish go to `local/` (gitignored).
- No attribution lines in commits.
- Python 3.14 standard library only.
- Unknown action types default to *keep* (spec §4.1): a visible step is better than a broken game.
- In this phase the rewrite only relinks existing events: the file keeps its size and the RSTB is untouched. A scene that needs new events (spec §8.1) is reported, not handled.
- Game-reading tests use `OOT_NUP` and are skipped without it, like the existing ones.

## Facts the plan relies on (checked 2026-11-11)

- Subflow events (type 4): u64 string pointer at `+0x18` = called flow file (`''` = same file), at `+0x20` = called entry point. In `Dm_Kokiri_0155`: event 2 → (`''`, `C01`); event 52 → (`GetPouchContent`, `DisplayGetByActorName`).
- `GetPouchContent/DisplayGetByActorName` only shows the item window; `GetPouchContent/GetPouchContentByActorName` adds the item **and** shows it (no silent variant exists).
- Spike scenes, all through entry `EntryPoint0`:
  - `Dm_Kokiri_0155`, Saria gives the Fairy Ocarina: event 51 adds `Item_Ocarina_Fairy`; event 52 is the display subflow.
  - `Dm_Kokiri_0060`, a `FROZEN_LINK` scene.
  - `Dm_HrlCastle_0050`, Zelda in the garden: event 238 is the subflow `Dm_SY_GetInEvent/GetInEvent_Zeldaletter` (`ActorName` = `Item_ZeldaLetter`). The spec's §6 names `_0020` by mistake; `_0020` is Malon's egg.
  - `Dm_MelodyGet_Zelda`, Zelda's Lullaby: subflows 4, 5 and 6 go to `Dm_SY_Ocarina/LearningOcarina*` (play-along); 66 goes to `GetPouchContent/GetPouchContentByActorName` (`Item_Melody_ZeldaLullaby`).

## Review Focus

- A scene that keeps a fade-out but loses the matching fade-in leaves a black screen. Test: in each spike scene, every kept `EventEventFadeOut` is followed later on the same path by a kept `EventEventFadeIn` (Task 4).
- An item or song action lost. Test: every `EventTriggerAddOrRemovePouchContent`, `EventTriggerSetGameData*` and `EventTriggerSetEventBool` reachable before is reachable after (Task 3 real-data test).
- An event shared with an entry point that is not rewritten gets relinked and breaks that other entry. Test: `shared` error in a synthetic case (Task 3).
- A switch on a dialogue answer collapsing to the wrong case. Test: the default picks the case that reaches kept effects; `choices` overrides it (Task 3).
- An unknown action dropped by mistake. Test: an unlisted action name is kept (Task 2).

---

### Task 1: Subflow targets and named link slots in `bfevfl.py`

**Files:**
- Modify: `randomizer/formats/bfevfl.py` (`Event`, `EventFlow._parse`)
- Test: `tests/test_bfevfl.py`

**Interfaces:**
- Produces:
  - `Event.sub_flow: str | None = None` and `Event.sub_entry: str | None = None`, set for SUBFLOW events (`''` for the same file).
  - `EventFlow.link_slots: dict[tuple, int]`, mapping link keys to the offset of their u16: `('next', i)` for actions, switches' none, joins and subflows; `('case', i, k)`; `('fork', i, k)`; `('join', i)`; `('entry', name)`. Its offsets are exactly those of `pointer_slots()`.

- [ ] **Step 1: Failing tests** in `tests/test_bfevfl.py`:
  - `EventTests.test_defaults`: also asserts `Event(0, 0).sub_flow is None and .sub_entry is None`.
  - `BfevflTests.test_subflow_targets` (needs `OOT_NUP`): in `Dm_Kokiri_0155`, `events[2].sub_flow == ''`, `events[2].sub_entry == 'C01'`, `(events[52].sub_flow, events[52].sub_entry) == ('GetPouchContent', 'DisplayGetByActorName')`.
  - `BfevflTests.test_link_slots` (needs `OOT_NUP`): for `Dm_Kokiri_0155`, `sorted(flow.link_slots.values()) == sorted(o for o, _ in flow.pointer_slots())`; `('entry', 'EntryPoint0') in flow.link_slots`; `('next', 51) in flow.link_slots`; and `patch_pointers(data, {flow.link_slots[('next', 51)]: 0xFFFF})` re-parses with `events[51].next == 0xFFFF`.
- [ ] **Step 2:** Run `python -m unittest tests.test_bfevfl` and see the new tests fail.
- [ ] **Step 3:** Implement: in `_parse`, read the two strings for SUBFLOW events, and record each `slot(...)` call under its key.
- [ ] **Step 4:** Run `python -m unittest tests.test_bfevfl` (with `OOT_NUP`): PASS. Run the full suite: PASS.
- [ ] **Step 5:** Commit `feat: bfevfl subflow targets and named link slots`.

### Task 2: Action table (`skip_actions.json`) and its loader

**Files:**
- Create: `tools/build_skip_actions.py`, `randomizer/data/skip_actions.json` (generated, committed), `randomizer/skipflow.py` (loader part)
- Test: `tests/test_skipflow.py`

**Interfaces:**
- Produces, in `randomizer/skipflow.py`:
  - `TABLE_PATH: Path` (`randomizer/data/skip_actions.json`).
  - `class SkipTable` with:
    - `@classmethod load(cls, path: Path = TABLE_PATH) -> SkipTable`;
    - `keeps(self, actor: str | None, action: str) -> bool`: an `actor_actions["<actor>.<action>"]` entry wins over `actions[action]`; `review` and unknown → `True`;
    - `collapses(self, query: str) -> bool`: `queries[query] == 'collapse'`; anything else → `False`;
    - `drops_subflow(self, flow: str, entry: str) -> bool`: `fnmatch` of `f'{flow}/{entry}'` against `subflows_drop`.
- JSON shape: `{"actions": {name: "keep"|"drop"|"review"}, "actor_actions": {}, "queries": {name: "state"|"collapse"|"review"}, "subflows_drop": [patterns], "counts": {name: int}}`, keys sorted, `indent=1`.

- [ ] **Step 1: Failing tests** in `tests/test_skipflow.py`, class `TableTests`, against the committed table:
  - drop: `EventWait`, `EventTalk`, `EventMoveToTargetPosCamera`, `EventMoveCameraAnimationInstructionsForFlowchart`, `EventPlayAS`, `EventPlayerPlayASForFlowchart`, `EventPlayASWithClothWarp`, `EventDemoProductSupportComment`, `EventSetAdvancedDoFForFlowchart`, `EventTriggerEmitXLink`, `EventTriggerXLinkFadeByKey`, `EventTriggerControllerRumble`, `EventNaviLookAtObject`, `EventCloseMessageDialog`, `EventDoNothing`;
  - keep: `EventTriggerSetGameDataBool`, `EventTriggerSetEventBool`, `EventTriggerAddOrRemovePouchContent`, `EventTransition`, `EventWarpToTargetPosAndRot`, `EventPlayerWarpToTargetPosAndRot`, `EventEventFadeOut`, `EventEventFadeIn`, `EventTriggerRequestAutoSave`, and the unknown `EventNotARealAction`;
  - `collapses('NotARealQuery') is False`;
  - `drops_subflow('GetPouchContent', 'DisplayGetByActorName')`, `drops_subflow('Dm_SY_Ocarina', 'LearningOcarinaFollowExample')`, `drops_subflow('Common_Camera_Pln', 'CameraDoF_Default')` are `True`; `drops_subflow('GetPouchContent', 'GetPouchContentByActorName')` and `drops_subflow('Dm_SY_GetInEvent', 'GetInEvent_Zeldaletter')` are `False`;
  - an `actor_actions` entry overrides `actions` (build a table from a temp JSON).
- [ ] **Step 2:** Run `python -m unittest tests.test_skipflow` and see it fail.
- [ ] **Step 3:** Implement `tools/build_skip_actions.py <nup>`. It reads every `Event/EventFlow/*.bfevfl.zs`, counts action names and switch queries, and classifies each name in this order (first match wins, case-sensitive substrings):
  - action **drop**: `PlayAS`, `XLink`, `Talk`, `Camera`, `Wait`, `LookAt`, `Turn`, `DoF`, `Light`, `Palette`, `Rumble`, `Sound`, `Bgm`, `Voice`, `Shake`, `Emotion`, `Ducking`, `Comment`, `DoNothing`, `Navi`, `Ballon`, `CloseMessageDialog`, `ShadingParams`, `Effect`, `NorifyCutChange`;
  - action **keep**: `GameData`, `EventBool`, `Pouch`, `Transition`, `BancChange`, `Warp`, `AutoSave`, `Fade`;
  - otherwise **review**;
  - query **collapse**: `TalkChoice`, `Select`, `Random`, `Anim`, `Camera`; query **state**: `GameData`, `Pouch`, `Flag`, `Item`, `Count`, `Have`, `Is`; otherwise **review**;
  - `subflows_drop` is fixed: `["GetPouchContent/DisplayGetByActorName", "Dm_SY_Ocarina/LearningOcarina*", "Common_Camera_*/*"]`.

  Then implement `SkipTable` and generate the JSON with the tool.
- [ ] **Step 4:** Run `python -m unittest tests.test_skipflow`: PASS. Look at the `review` names the tool prints and report them in the task report; do not reclassify by hand in this task.
- [ ] **Step 5:** Commit `feat: skip action table and loader`.

### Task 3: Effects-only rewriter

**Files:**
- Modify: `randomizer/skipflow.py`
- Test: `tests/test_skipflow.py`

**Interfaces:**
- Consumes: Task 1 (`Event.sub_flow/sub_entry`, `EventFlow.link_slots`), Task 2 (`SkipTable`).
- Produces:
  - `@dataclass class Rewrite: links: dict[tuple, int]; kept: list[int]; error: str | None = None`, with `links` keyed like `EventFlow.link_slots`, and `kept` the kept events in first-seen order.
  - `linearize(events: list[Event], entries: dict[str, int], entry: str, keep: Callable[[Event], bool], collapse: Callable[[Event], bool], choices: Mapping[int, int] = {}, protected: frozenset[int] = frozenset()) -> Rewrite`, a pure function on event lists. `keep` is asked about actions and cross-file subflows; `collapse` about switches.
  - `reachable(events, entries, starts: Iterable[int]) -> set[int]`, following next, cases, forks, joins and same-file subflows.
  - `effects_only(flow: EventFlow, entry: str, table: SkipTable, choices: Mapping[int, int] = {}) -> Rewrite`: builds `keep`/`collapse` from the table, and `protected` = what is reachable from entry points other than `entry` and the ones `entry` reaches through same-file subflows.
  - `apply_rewrite(data: bytes, flow: EventFlow, rw: Rewrite) -> bytes`: `patch_pointers` over `flow.link_slots`; raises `ValueError` if `rw.error`.

**Rules `linearize` implements (spec §4.1 and §8.2):**
- Walk every path from `entries[entry]`.
  - An action is a kept node if `keep(ev)`; otherwise it is skipped.
  - A same-file subflow is replaced by the walk of its entry point, then the walk continues at its `next`. A subflow that calls itself, directly or indirectly, gives `error='recursive subflow'`.
  - A cross-file subflow is a kept node if `keep(ev)`.
  - A fork walks its branches in order, each up to its join, then continues after the join. Forks and joins are never kept nodes.
  - A switch with `collapse(ev)` follows one case: `choices[i]` if given, otherwise the first case whose walk contains a kept node, otherwise case 0.
  - Any other switch is a kept node. Each of its cases is walked with whatever follows it, including what comes after an enclosing join.
- Links: `('entry', entry)` → first kept node (or `0xFFFF`); each kept action or subflow `('next', i)` → the next kept node on its path (or `0xFFFF`); each kept switch `('case', i, k)` → the first kept node of case `k`.
- `error='conflict'` if one link key needs two different targets.
- `error='loop'` if a path revisits an event without passing a kept node.
- `error='shared'` if a link would change on an event in `protected`.

- [ ] **Step 1: Failing synthetic tests** (`LinearizeTests`; events built with `Event(...)`; `keep` = "action name starts with `K`"; `collapse` = "query starts with `C`"):
  - `test_linear`: `K0 → D1 → K2 → END` gives `links == {('entry','E'): 0, ('next',0): 2, ('next',2): 0xFFFF}`, `kept == [0, 2]`.
  - `test_all_dropped`: `D0 → D1` gives `{('entry','E'): 0xFFFF}`.
  - `test_fork_flattened`: fork with branches `[K1 → join]`, `[D2 → K3 → join]`, `join → K5` gives the chain `1 → 3 → 5`, and no fork or join index in any link value.
  - `test_same_file_subflow_inlined`: `S0(sub '' 'X') → K1`, entry `X: K2` gives `2 → 1`; `test_recursive_subflow`: entry `E` calls `E` → `error == 'recursive subflow'`.
  - `test_cross_file_subflow`: kept when `keep` says so (gets a `next` link), skipped otherwise.
  - `test_state_switch`: kept switch with cases `[K1, D2 → K3]`, both continuing to `K4`: `('case', s, 0) → 1`, `('case', s, 1) → 3`, `('next', 1) → 4`, `('next', 3) → 4`.
  - `test_collapse_default_and_choice`: collapsing switch with cases `[D1, K2]` follows case 1 by default; with `choices={s: 0}` the entry links straight to `END`.
  - `test_conflict`: a kept action reached on two paths that need different `next` → `error == 'conflict'`.
  - `test_loop`: `D0 → D1 → D0` → `error == 'loop'`.
  - `test_shared`: `protected={0}` with a link change on 0 → `error == 'shared'`.
- [ ] **Step 2:** Run them and see them fail.
- [ ] **Step 3:** Implement the functions above.
- [ ] **Step 4: Real-data test** `SpikeScenesTests` (needs `OOT_NUP`). For each of `Dm_Kokiri_0155`, `Dm_Kokiri_0060`, `Dm_HrlCastle_0050` and `Dm_MelodyGet_Zelda`, at `EntryPoint0`:
  - `effects_only(...)` returns `error is None`;
  - after `apply_rewrite`, re-parse and compute `reachable` from `EntryPoint0`:
    - no FORK or JOIN in it;
    - no action for which `table.keeps` is `False`;
    - every action that `table.keeps` and that was reachable before is still reachable;
  - `Dm_Kokiri_0155`: 51 reachable, 52 not;
  - `Dm_MelodyGet_Zelda`: 66 reachable, 4, 5 and 6 not;
  - `Dm_HrlCastle_0050`: 238 reachable;
  - the output has the same length as the input.

  If a scene fails with `conflict` or `shared`, stop and report it: it needs the growth of spec §8.1, which this plan does not build.
- [ ] **Step 5:** Run `python -m unittest tests.test_skipflow` and the full suite: PASS.
- [ ] **Step 6:** Commit `feat: effects-only scene rewriter`.

### Task 4: Spike test mod `TestScenes4` and its guides

**Files:**
- Create: `tools/make_skip_spike.py`, `docs/test-scenes-4.md`, `local/test-scenes-4.md` (Spanish, not committed)
- Test: `tests/test_skipflow.py`

**Interfaces:**
- Consumes: Task 3 (`effects_only`, `apply_rewrite`, `reachable`), `ZsCodec`, `NupArchive`.
- Produces:
  - `SPIKE_SCENES: tuple[str, ...] = ('Dm_Kokiri_0155', 'Dm_Kokiri_0060', 'Dm_HrlCastle_0050', 'Dm_MelodyGet_Zelda')`, in `randomizer/skipflow.py`;
  - `build_spike_files(nup) -> dict[str, bytes]` (romfs path → compressed bytes), in `randomizer/skipflow.py`;
  - the tool `python -I tools/make_skip_spike.py <nup> <out_dir>`, which writes `<out_dir>/romfs/Event/EventFlow/<name>.bfevfl.zs` for the four scenes and prints, for each, the kept events as `index actor.action`.

- [ ] **Step 1: Failing test** `test_spike_fades` (needs `OOT_NUP`): in each spike scene after the rewrite, on every path from `EntryPoint0`, each kept `EventEventFadeOut` is followed later by a kept `EventEventFadeIn`. Also `test_build_spike_files`: four keys, each round-trips through the codec to a file of the original length.
- [ ] **Step 2:** Implement `build_spike_files` and the tool. If `test_spike_fades` fails for a scene, report which fade is unmatched and stop: whether to keep the fade-out is the controller's call.
- [ ] **Step 3:** Run the tool to `test-mod/0400486024DEC000/TestScenes4`. Write the guides:
  - `docs/test-scenes-4.md` in English;
  - `local/test-scenes-4.md` in Spanish, for the user.

  Each covers:
  - setup: only this mod enabled; new game with "Skip cutscenes" off, since the mod carries the four scenes itself;
  - what should happen in each scene:
    - Saria: Fairy Ocarina received, no scene and no item window;
    - the Kokiri Forest scene with Saria, Mido and Navi (`Dm_Kokiri_0060`, a `FROZEN_LINK` scene): no scene, and Link is not frozen;
    - Zelda in the garden: Zelda's Letter received;
    - Zelda's Lullaby: song learned with no play-along; the "You got" window may still show, see spec §8.7;
  - the checks: freeze, missing item, song or flag, wrong position, black screen;
  - a Results section.
- [ ] **Step 4:** Run the full suite (with `OOT_NUP`): PASS.
- [ ] **Step 5:** Commit `feat: TestScenes4 spike tool and guide` (the Spanish guide stays uncommitted).

**Gate:** after Task 4, stop. The user plays `TestScenes4`; nothing else is built for the next phases until their verdict (spec §8.6).
