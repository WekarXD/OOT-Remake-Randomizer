# Skip cutscenes — Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the "Skip cutscenes" option. It unlocks skipping the introduction and removes the steps that only display (phase 1) in story scenes, keeping everything that changes the game state.

**Architecture:**
- The BFEVFL reader turns each flow into a graph.
- A pure function computes which events to remove and how to redirect each index.
- The rewriter patches those u16 indices in place, without changing the size.
- A policy module (list of flows and actions in `randomizer/data/cutscenes.json`) produces the extra files of the mod.
- `write_mod` writes them next to the banc files.

**Tech Stack:** Python 3.14, stdlib only (`compression.zstd`, `unittest`).

**Spec:** `docs/superpowers/specs/2026-11-09-skip-cutscenes-design.md`

## Global Constraints

- The `.nup` is never written to and commits never include game files. Tests that read the game use `OOT_NUP` and carry `@unittest.skipUnless(NUP_PATH, 'OOT_NUP not defined')`.
- Standard library only. OoTR code is not run.
- `skip_cutscenes` is **not** part of the RNG settings key: the same seed gives the same placement with the option enabled or not.
- Trimmed flows have **exactly the same size** as the original and their RSTB entries are not touched.
- The rewritten introduction component list must have a size **≤ the original**. In that case its RSTB value is kept, as it is an upper bound for the buffer. If it is not, generation fails with an error.
- Active phase: **only phase 1** of actions. Phase 2 stays in the data but is not applied.
- Forks, joins, switches and subflows are never removed. An `EventTalk` whose next event is a switch (dialogue with a choice) is not removed either.
- User-facing messages are in English. Commits carry no attribution lines.

## Review Focus

1. **Event shared between a story entry and a non-story one** (for example, a Zelda flow with a normal conversation). It is expected not to be trimmed. Test in task 3.
2. **Fork branch that would end up empty.** It is expected that the first action of that branch is kept. Test in task 2.
3. **Chain of removed events that ends in "end" (0xFFFF) or in a cycle.** It is expected to be redirected to 0xFFFF without an infinite loop. Test in task 2.
4. **Vanilla mode with the option enabled.** It is expected that the mod is generated with only the scene files, without the "no changes" warning. Test in task 4.
5. **Saved configuration without `skip_cutscenes`** (earlier users). It is expected that the checkbox appears unchecked and that there is no error. Test in task 4.

---

### Task 1: BFEVFL reader and patcher

**Files:**
- Create: `randomizer/formats/bfevfl.py`
- Test: `tests/test_bfevfl.py`

**Interfaces:**
- Produces:
  - `Event`: dataclass with `index: int`, `kind: int` (0 action, 1 switch, 2 fork, 3 join, 4 subflow), `actor: str|None`, `action: str|None`, `query: str|None`, `next: int|None`, `cases: list[int]`, `forks: list[int]`, `join: int|None`.
  - `EventFlow(data: bytes)` with:
    - `.events: list[Event]`;
    - `.entry_points: dict[str, int]` (name → main event);
    - `.pointer_slots() -> list[tuple[int, int]]`: (offset in the file, current index) of **all** the u16 values that reference an event. It includes the next of actions, joins and subflows, the switch cases, the fork branches and joins, and the main event of the entry points.
  - `patch_pointers(data: bytes, new_targets: dict[int, int]) -> bytes`: rewrites each slot (offset → new index). Keeps the length.
- Layout (spec §3):
  - flowchart at `u64(u64(0x28))`;
  - u16 counters at `EVFL+0x10` (actors, actions, queries, events, entries);
  - u64 pointers at `EVFL+0x28/0x30/0x38/0x40` (actors, events, entry dictionary, entries);
  - 0x38-byte actor: name `+0`, actions `+0x18`, queries `+0x20`, number of actions `+0x30`, number of queries `+0x32`;
  - 0x30-byte event with the type at `+8`;
  - dictionary: `DIC ` + n, with the root at +8 and 0x10-byte entries (name at +8);
  - 0x20-byte entry with the main event at `+0x1C`;
  - strings with a u16 length prefix.
  - A fork stores the join at `+0x0C`. The dictionary root is not an entry.

- [ ] **Step 1: Tests**

  In `tests/test_bfevfl.py`, with OOT_NUP:
  - `test_parse_get_stone_of_fire`: `Get_StoneOfFire.bfevfl.zs` has 274 events and 33 entries. From `entry_points['Get_StoneOfFire_GetBombBag']`, the chain of actions is `EventTriggerParticipateEvent → EventTransition → EventNaviRequestBallonMessage → 0xFFFF`.
  - `test_all_flows_parse`: the 914 flows in `Event/EventFlow/` are read without exceptions and every index in `pointer_slots()` is `< len(events)` or `0xFFFF`.
  - `test_patch_roundtrip`: `patch_pointers(d, {})` returns `d` byte for byte. In addition, patching one slot and rereading gives the new index in that slot and the same value in the others.

- [ ] **Step 2:** Run `python -I -m unittest tests.test_bfevfl -v`. An import FAIL is expected.

- [ ] **Step 3:** Implement `randomizer/formats/bfevfl.py` with `struct`. The entry-point slots use the offset of the `+0x1C` field.

- [ ] **Step 4:** Run it again. A PASS is expected.

- [ ] **Step 5:** Commit with the message `feat: BFEVFL reader and in-place pointer patcher`.

### Task 2: Trim computation (pure, no game)

**Files:**
- Create: `randomizer/evtrim.py`
- Test: `tests/test_evtrim.py`

**Interfaces:**
- Consumes: `Event` from task 1.
- Produces: `compute_trim(events: list[Event], removable: set[int]) -> tuple[set[int], dict[int, int]]`. It returns `(removed, retarget)`, where `retarget` maps each removed event index to its final destination (first kept event of the chain, or `0xFFFF`).

**Rules:**
- Only actions (kind 0) that are in `removable` can be removed.
- The chain is followed through `next`.
- A cycle made only of removed events ends in `0xFFFF`.
- If a fork branch would resolve to its `join` or to `0xFFFF`, the first action of that branch is kept again and recalculated.

- [ ] **Step 1: Tests**

  The graphs are built by hand with `Event(...)`.
  - `test_linear_chain`: `0→1→2→FFFF` with `removable={1}` gives `removed={1}` and `retarget={1:2}`.
  - `test_tail_to_end`: with `removable={1,2}`, `retarget[1]==0xFFFF`.
  - `test_cycle_of_removed`: a fully removable cycle `1→2→1` gives `0xFFFF` and terminates.
  - `test_non_action_never_removed`: a switch or fork included in `removable` does not appear in `removed`.
  - `test_fork_branch_kept`:
    - fork 0 has branches [1, 3] and join 5;
    - the chains are `1→2→5` and `3→4→5`;
    - with `removable={1,2,3}`, branch 1 would resolve to the join, so 1 is kept (`1 not in removed`; 2 can indeed be removed);
    - branch 3 resolves to 4, so `retarget[3]==4`.
  - `test_contraction_property`: a random graph with a fixed seed (50 events, no forks) satisfies that, for each path from the entry, the sequence of kept actions matches that of the original, filtered. It is traversed with a step limit.

- [ ] **Step 2:** Run `python -I -m unittest tests.test_evtrim -v`. A FAIL is expected.

- [ ] **Step 3:** Implement `compute_trim`.

- [ ] **Step 4:** Run it again. A PASS is expected.

- [ ] **Step 5:** Commit with the message `feat: event-flow trim computation`.

### Task 3: Scene policy and mod files

**Files:**
- Create:
  - `randomizer/data/cutscenes.json`
  - `tools/build_cutscene_list.py`
  - `randomizer/cutscenes.py`
- Test: `tests/test_cutscenes.py`

**Interfaces:**
- Consumes:
  - `EventFlow` and `patch_pointers` (task 1);
  - `compute_trim` (task 2);
  - `GameData(nup)`, with `.nup.read`, `.nup.list()` and `.codec.compress/decompress(path, data)`;
  - `randomizer.formats.byml.load/dump`.
- Produces:
  - `ACTIVE_PHASE = 1`;
  - `load_policy() -> dict`;
  - `build_cutscene_files(game) -> dict[str, bytes]`: romfs path → final bytes (compressed if it ends in `.zs`), in deterministic order.

**`cutscenes.json`:**
- `"intro_component_lists": ["Dm_Kokiri_0000"]`
- `"story_flows"`: `{ "<flow without extension>": "*" | ["<entry>", ...] }`
- `"actions"`: `{ "1": [[actor|"*", action], ...], "2": [...] }`

**Phase 1 actions** (exact pairs, spec §6b):

| Actor | Action |
|---|---|
| `*` | `EventTalk` |
| `*` | `EventTriggerBalloonMessage` |
| `Npc_Navi` | `EventNaviRequestBallonMessage` |
| `EventSystemActor` | `EventWait` |
| `EventCamera` | `EventMoveToTargetPosCamera` |
| `EventCamera` | `EventMoveCameraAnimationInstructionsForFlowchart` |
| `EventCamera` | `EventBasedOnLookAtCamera` |
| `EventCamera` | `EventTriggerRequestCameraShake` |
| `EventCamera` | `EventSendEventTalkMessageToPlayerCamera` |
| `Player_Event` | `EventPlayerTurnAndLook` |
| `Player_Event` | `EventTriggerPlayerLookAtObject` |
| `*` | `EventNPCTurnToTarget` |
| `*` | `EventTriggerLookAtObject` |
| `Npc_Navi` | `EventNaviLookAtObject` |
| `PostProcessingActor` | `EventSetAdvancedDoFForFlowchart` |
| `PostProcessingActor` | `EventSetDoFForFlowchart` |
| `PostProcessingActor` | `EventNorifyCutChangeForGraphics` |
| `PostProcessingActor` | `EventEditLocationalLight` |
| `GameSystemActor` | `EventTriggerControllerRumble` |
| `DevelopEventSystemActor` | `EventDemoProductSupportComment` |
| `*` | `EventTriggerChangeEmotion` |
| `GameSystemActor` | `EventWaitTalkCameraInterpolationEnd` |

**Phase 2 actions:**

| Actor | Action |
|---|---|
| `*` | `EventPlayAS` |
| `Player_Event` | `EventPlayerPlayASForFlowchart` |
| `Player_Event` | `EventPlayerMove` |
| `Player_Event` | `EventPlayerMoveToAnchor` |
| `SoundSystemActor` | `EventSoundStartSound` |
| `SoundSystemActor` | `EventTriggerSoundReadRiddle` |
| `Npc_Navi` | `EventNaviMoveAroundToPlayer` |
| `Npc_Navi` | `EventNaviMoveAtPos` |

**`story_flows`:**
- It is generated by `tools/build_cutscene_list.py <nup>` and reviewed by hand before the commit.
- `"*"` goes in for each flow whose name starts with `Dm_`, `Get_Stone`, `SageOf`, `AllSage`, `Meet_`, `Goto_`, `MelodyGet_`, `SubEvent_Get`, `Get_Epona`, `DoorOfTime`, `OpeningEvent`, `Defeat_Ganon` or `EscapeFromCrumblingGanonCastle`.
- `DmF_` (Cucco/fall/game over) and `Dm_StaffCredit_*` / `Dm_Title_*` are left out.
- For the NPC flows `Npc_Hylia_Zelda_*`, `Npc_Hylia_Impa_*`, `Npc_Kokiri_Saria_*`, `Npc_Goron_Darunia_*`, `Npc_Zora_Ruto_*`, `Npc_Gerudo_Nabooru_*`, `Npc_Hylia_Rauru*` and `Npc_Hylia_Sheik_*`, the tool writes the list of entries whose name does **not** end in `_Talk`, `_Near` or `_Talk01`… The manual review adjusts that list. What was reviewed is described in the commit message.

**Rules for `build_cutscene_files`:**
- **Introduction:** `Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml` is loaded and `Components['SkipSetting']` is deleted. If it has no `SkipSetting`, it is not included. If the size is greater than the original, `ValueError` is raised.
- **Flows:** start from the `removable` actions according to the actions of the `ACTIVE_PHASE` phase, excluding:
  - an `EventTalk` whose `next` is a switch;
  - events reachable from any entry that is **not** in the list (for `"*"` all entries count as story).

  Then `compute_trim`, and `retarget` is turned into `new_targets` for each slot whose current index is in `removed`. Unchanged flows are not included.

- [ ] **Step 1: Tests (with OOT_NUP)**
  - `test_intro_skip_removed`: the returned bgyml loads without `SkipSetting` and its length is `<=` that of the original.
  - `test_flows_same_size`: each returned flow, decompressed, has the same length as the original.
  - `test_kept_actions_preserved`: in each returned flow, the multiset of (actor, action) pairs of the events reachable from each entry that are not phase 1 equals that of the original.
  - `test_shared_events_untouched`: in an NPC flow with mixed entries, the events reachable from a `_Talk` entry do not change. The slots are compared.
  - `test_choice_talk_kept`: in no returned flow is an `EventTalk` whose original `next` is a switch removed.
  - `test_deterministic`: two calls give identical bytes.
  - `test_policy_shape` (no game): phase 1 and phase 2 do not overlap, and `ACTIVE_PHASE == 1`.

- [ ] **Step 2:** Run `python -I -m unittest tests.test_cutscenes -v`. A FAIL is expected.

- [ ] **Step 3:** Run the tool, review `cutscenes.json` and implement `randomizer/cutscenes.py`.

- [ ] **Step 4:** Run it again. A PASS is expected.

- [ ] **Step 5:** Commit with the message `feat: cutscene trim policy and mod files`.

### Task 4: Option in settings, generation, spoiler log and page

**Files:**
- Modify:
  - `randomizer/fill.py` (`Settings`, `_settings_key`)
  - `randomizer/patch.py` (`write_mod`)
  - `randomizer/generate.py`
  - `randomizer/spoiler.py`
  - `randomizer/web/server.py`
  - `randomizer/web/static/index.html`
  - `randomizer/web/static/app.js`
  - `README.md`
- Test:
  - `tests/test_fill.py`
  - `tests/test_generate.py`
  - `tests/test_server.py`

**Interfaces:**
- Consumes: `build_cutscene_files(game)` from task 3.
- Produces:
  - `Settings.skip_cutscenes: bool = False`;
  - `write_mod(game, placement, mod_root, loc_map, extra_files: dict[str, bytes] | None = None) -> list[str]`. The extras are written as they are and are included in the returned list. It no longer returns early if there are extras but no banc files, and in that case it does not write the RSTB.

**Changes:**
- `_settings_key` removes `skip_cutscenes`.
- `generate` calls `build_cutscene_files(game)` only if the option is enabled.
- The spoiler log adds in Settings the line `Skip cutscenes: Yes|No`.
- The server accepts `skip_cutscenes` as a strict bool (otherwise, 400 `"skip_cutscenes must be true or false"`) and saves it in `last_settings`.
- On the page, the checkbox `<input type="checkbox" id="skip-cutscenes">` carries the label "Skip cutscenes" and goes in `panel-general`, below the seed. It is loaded from `last_settings` only if it is a boolean.

- [ ] **Step 1: Tests**
  - `test_skip_cutscenes_not_in_key` (fill): the same seed with `skip_cutscenes` `True` and `False` gives the same placement.
  - `test_generate_skip_cutscenes` (generate, OOT_NUP): with the option, `changed_files` includes `Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml` and some `Event/EventFlow/…bfevfl.zs`, and the spoiler log contains `Skip cutscenes: Yes`.
  - `test_vanilla_with_skip_cutscenes` (generate, OOT_NUP): with `key_items_mode='vanilla'`, `spoiler=False` and `skip_cutscenes=True`, `mod_dir` exists and `changed_files` has no banc files or RSTB.
  - `test_skip_cutscenes_strict_bool` (server): `"yes"` gives 400.
  - `test_last_settings_without_skip` (server): a configuration without the key loads without error.

- [ ] **Step 2:** Run `python -I -m unittest tests.test_fill tests.test_generate tests.test_server -v`. A FAIL is expected in the new ones.

- [ ] **Step 3:** Implement the changes and add a line to the README under Options explaining that only the visual steps are removed in phase 1.

- [ ] **Step 4:** Run `python -I -m unittest`. A PASS is expected, with the same documented expectedFailure as before.

- [ ] **Step 5:** Commit with the message `feat: skip cutscenes option in settings, generation, spoiler and UI`.

### Task 5: In-game test rounds

**Files:**
- Create:
  - `tools/make_cutscene_batch.py`
  - `docs/test-cutscenes.md`

**Interfaces:**
- Consumes: `build_cutscene_files`, `GameData`, `NupArchive`.
- Produces: `python -I tools/make_cutscene_batch.py <nup> <out_dir> --only intro|flows|all`, which writes `<out_dir>/romfs/...` with only the scene files (no banc files or RSTB).

- [ ] **Step 1:** Implement the tool, which filters the result of `build_cutscene_files` according to `--only`.

- [ ] **Step 2:** Generate the test mods in `test-mod/0400486024DEC000/` (ignored by git):
  - `TestScenes1` with `--only intro`;
  - `TestScenes2` with `--only all`.

- [ ] **Step 3:** Write `docs/test-cutscenes.md` with what to check in a new game:
  - **Round 1:** the introduction can be skipped with the button. Afterwards Navi and Saria appear, and the Deku Tree can be entered after getting the sword and shield.
  - **Round 2:** the scenes in the Deku Tree up to the Kokiri Emerald and of Zelda up to Zelda's Lullaby play without story dialogue; the Emerald, Zelda's Letter and the song are received, and the player ends up in the same place.
  - An empty "Results" section.

- [ ] **Step 4:** Commit with the message `test: in-game cutscene test batches`.

---

## Extension 1 — forced conversations (spec §8)

### Task 6: Find and list the forced childhood conversations

**Files:**
- Create: `tools/find_forced_talks.py`
- Modify: `randomizer/data/cutscenes.json` (`story_flows`: entries of `Npc_*` / `Navi*` flows), `tools/build_cutscene_list.py` (so the curated list is preserved on regeneration)
- Test: `tests/test_cutscenes.py`

**Interfaces:**
- Consumes: `EventFlow` (task 1), `build_cutscene_files` / `trim_flow` / `removable_events` (task 3 and final review), `RSDB/EventSetting.Product.111.rstbl.byml.zs` (rows with `FlowchartFileName`, `EntryPointName`, `EventSettingComponentList`), banc files (`GameData.load_banc`).
- Produces: `python -I tools/find_forced_talks.py <nup> [--zones ...]` → per-zone list of candidates (flow, entry, how it is triggered, actions it would remove); curated entries added to `story_flows` as lists `["<entry>", ...]`.

**Rules:**
- **Forced:** it triggers by itself, through a zone trigger or a pass-through event, or blocks the way. A conversation the player initiates is not: `NPCTalkNoPause` / `NPCTalk` rows of a character who is spoken to by choice, shops, minigames, or asking Navi for a hint with her button (`NaviHelp` / `InitTalk_NaviHelp`).
- **The implementer first investigates how they are triggered** (EventSetting components, trigger actors in the banc files) and documents the criterion in the report and in the tool's docstring.
- **Scope:** childhood in `KokiriForest`, `InsideTheDekuTree`, `HyruleField`, `Market`, `HyruleCastle` and `KakarikoVillage`.
- **Mandatory cases, if confirmed to be forced:**
  - Mido blocking the way (`Npc_Kokiri_Mido_Child`);
  - the Z-targeting tutorial (`Npc_Kokiri_010_Child:FocusOnAttentionRock_ShieldDeku_Short`);
  - the forced Navi prompt (`NaviHint`: the `NaviLockOnHint` entry).
  - If an entry is shared with a voluntary use (for example, `Hint_00` is also used by the voluntary hint), it is left out and noted.
- **When in doubt, leave it out.**

- [ ] **Step 1: Tests (OOT_NUP)**
  - `test_forced_talks_listed`: the confirmed mandatory cases are in `story_flows` and their trim removes at least one `EventTalk`.
  - `test_voluntary_talks_untouched`: in the listed NPC flows, the events reachable from unlisted entries do not change. `test_shared_events_untouched` already covers this; it is extended to all the listed NPC flows.
  - `test_mido_gate_kept`: in the trimmed Mido flow, all switches and all non-phase-1 actions are kept.
- [ ] **Step 2:** Run `python -m unittest tests.test_cutscenes -v`. A FAIL is expected.
- [ ] **Step 3:** Implement the tool, run it, curate the list and regenerate `cutscenes.json`.
- [ ] **Step 4:** Run the tests again and then the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: trim forced childhood conversations` and, in the body, the curated list with its reason.

### Task 7: Round 3 in game

**Files:**
- Modify: `docs/test-cutscenes.md`

- [ ] **Step 1:** Generate `test-mod/0400486024DEC000/TestScenes3` with `python -I tools/make_cutscene_batch.py <nup> test-mod/0400486024DEC000/TestScenes3 --only all`.
- [ ] **Step 2:** Add the "Round 3" section to the guide, in a new game:
  - Mido without text, but still not letting you pass without the sword and shield;
  - the Z-targeting tutorial no longer appears;
  - the Deku Tree, the Castle (Zelda) and Kakariko are reached;
  - no crashes, black screens or missing items;
  - which forced conversations still appear, and where.

  Plus an empty "Results" section.
- [ ] **Step 3:** Commit with the message `test: cutscene test batch 3`.
