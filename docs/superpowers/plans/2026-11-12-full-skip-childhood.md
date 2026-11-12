# Full Cutscene Skip, Phase 2 (Childhood) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With "Skip cutscenes" on, every childhood story scene, movie and forced conversation is skipped automatically, its effects still happen, and one childhood test batch proves it in game.

**Architecture:** Three methods, all proven in the spikes (spec §11): event-flow scenes and forced conversations are rewritten effects-only (`randomizer/skipflow.py`), timelines are shortened (`randomizer/timeline_skip.py`), movies are removed from the flow that starts them (`randomizer/movie_skip.py`). A reviewed data file lists every childhood target and its method. A builder applies them, and falls back to the old trimming for any scene it cannot rewrite, reporting it. Before more scenes are rewritten, the rewriter gets the safety work of spec §10, understands two event kinds it treats as dead ends today, and can give a targeted path its own copies of shared events.

**Tech Stack:** Python 3 standard library, `unittest` (no pytest). Real-data tests run only with `OOT_NUP` set (`C:/Users/...` path form).

**Spec:** `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` (§4, §8, §10, §11).

## Global Constraints

- Never write to the `.nup`; never commit game files (`test-mod/`, `local/` and output mods are gitignored).
- Everything committed is in English (code, comments, docs). Guides for the user are in Spanish in `local/`, with an English copy in `docs/`.
- Commits: no attribution lines; author is the configured noreply address. No push and no merge without the user's OK.
- Only parse OoTR; never execute it.
- Same seed, same placement with the option on or off (`fill.py` already ignores `skip_cutscenes`; keep it that way).
- Rewritten flows keep their size wherever possible. Copies of shared events reuse slots of events the rewrite left unreachable, so the RSTB is not touched (Task 5).
- A scene that cannot be rewritten safely is never forced: it keeps the old trimming and is listed in the build report (spec §8.1: "a visible step is better than a broken game").
- Unknown action types default to *keep* (spec §4.1).

## Review Focus

1. **Option off:** with `skip_cutscenes=False` the mod must be byte-identical to today's. Task 8 tests this.
2. **One file, several methods:** a flow that has a movie transition removed *and* entries rewritten *and* the old trimming must come out of one pipeline, never two writes of the same path. Task 7 tests this on `Goto_HyruleCastle`.
3. **Rewrite fallback:** a scene whose rewrite fails must be written with the old trimming (or untouched), never half-rewritten. Task 7 tests this with a forced failure.
4. **Pointers the parser does not see:** kind 5 and 6 events hold event pointers today's parser ignores, so a removed or relinked event could still be reached through them. Task 2 parses them, and Task 7's real-data test checks that no dropped event is still reachable after the rewrite.
5. **Black screen:** a kept fade-out with no later fade-in. The §10 rule stays: accepted only if the original had none either. Task 6's checker reports it.

## Facts this plan relies on (measured 2026-11-12)

- **Childhood `Dm_*` event flows** (actors `_Child` only, not `_Adult`): 58 of 60 rewrite cleanly with `effects_only(…, 'EntryPoint0', …)`. The two that don't:
  - `Dm_InsideJabu_Jabu_0050` fails with `conflict`;
  - `Dm_LostWood_0000` has no `EntryPoint0`.
- **Forced conversations and story entries** in the childhood flows of `cutscenes.json`: 100 of 164 rewrite. The rest fail:
  - 54 with `shared`: their path runs through events that also belong to entries the player starts;
  - 7 with `dead end`: they reach an event of kind 5;
  - 3 with `conflict`.
  - The failures include the exit Kokiri (`Npc_Kokiri_007_Child/GoToDekuTree`), Malon (`SubEvent_GetEponaSong/GuideToLonLonRanch_*`) and Zelda (`Npc_Hylia_Zelda_Child/Talk`).
- **Event kinds 5 and 6** (155 and 144 game-wide) are not parsed.
  - Kind 5 looks like a switch keyed by hashes: u16 count at +0xA, and at +0x18 a pointer to 8-byte cases (u32 hash, u16 event).
  - Example: `SubEvent_GetEponaSong` event 27, cases → 28 and 112.
- **BFEVFL header:** 0x18 u32 is the relocation table offset, 0x1C u32 is the file size.
- **Childhood movies and their callers:**
  - `Dm_Kokiri_0000` ← `OpeningEvent`;
  - `Dm_Kokiri_0095` ← `Dm_SY_BancChange_EscapeDungeon`;
  - `Dm_HrlCastle_0045` ← `Goto_HyruleCastle`;
  - `Dm_MelodyGet_Sun_*` ← `GimmickFlow_RoyalFamilyTomb`.
- **Timeline shortening caveat:** several `EventTriggerSetFairyColor` clips can land on the same frame (`Dm_Kokiri_0030`). That is accepted, and the test batch checks Navi's colour.

---

### Task 1: Rewriter robustness (spec §10 gaps)

**Files:**
- Modify: `randomizer/skipflow.py` (`linearize.advance`)
- Test: `tests/test_skipflow.py` (use its `A`, `SW`, `SUB`, `FK`, `JN`, `lin` helpers)

**Interfaces:**
- Produces: `Rewrite.error` may now be `'join mismatch'`. A fork whose join is `END` runs its branches in order, then ends.

- [ ] **Step 1: Write the failing tests**

```python
def test_fork_with_end_join_runs_all_branches(self):
    # 0 fork [1, 2] join END; 1 keep -> END; 2 keep -> END
    rw = lin([FK(0, [1, 2], END), A(1, 'K'), A(2, 'K')], {'E': 0})
    self.assertIsNone(rw.error)
    self.assertEqual(rw.kept, [1, 2])
    self.assertEqual(rw.links[('next', 1)], 2)
    self.assertEqual(rw.links[('next', 2)], END)

def test_branch_back_to_own_fork_is_a_loop(self):
    rw = lin([FK(0, [1], 2), A(1, 'D', 0), JN(2), ], {'E': 0})
    self.assertEqual(rw.error, 'loop')

def test_join_of_another_fork_is_refused(self):
    # branch of fork 0 reaches join 4, which belongs to fork 3
    rw = lin([FK(0, [1], 2), A(1, 'K', 4), JN(2), FK(3, [], 4), JN(4)], {'E': 0})
    self.assertEqual(rw.error, 'join mismatch')

def test_protected_event_cannot_be_relinked(self):
    # entry E: 0 drop -> 1 keep -> 2 drop -> 3 keep; entry F (untargeted) starts at 1
    events = [A(0, 'D', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K')]
    rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}))
    self.assertEqual(rw.error, 'shared')

def test_apply_rewrite_refuses_a_failed_rewrite(self):
    with self.assertRaises(ValueError):
        apply_rewrite(b'', None, Rewrite({}, [], 'loop', 'x'))
```

(Adapt the helper call shapes to the existing `lin`. If `lin` doesn't take `protected`, add a keyword that passes it to `linearize`.)

- [ ] **Step 2: Run, expect failures**

Run: `python -m unittest tests.test_skipflow -v`.
Expected: the fork/END test fails with `loop`, and the join test fails because no error is reported.

- [ ] **Step 3: Implement**

In `advance`:
- when a branch reaches END, or the fork's join, and the open frame is a fork, continue with the next branch; after the last branch, continue with the join's `next`, or END when the join is END;
- a JOIN that does not belong to the innermost open fork, while a fork is open, raises `_Fail('join mismatch', f'event {i}')`.

- [ ] **Step 4: Run all tests**

Run: `python -m unittest discover -s tests`.
Expected: all pass.

- [ ] **Step 5: Commit**

`fix: rewriter handles END joins, refuses mismatched joins`.

---

### Task 2: Event kinds 5 and 6

**Files:**
- Modify: `randomizer/formats/bfevfl.py` (`_parse`, constants), `randomizer/skipflow.py` (walkers), `randomizer/cutscenes.py` (`_successors` only if needed)
- Test: `tests/test_bfevfl.py` (real data), `tests/test_skipflow.py` (synthetic)

**Interfaces:**
- Produces: constants `HASH_SWITCH = 5` and `KIND6 = 6`, renamed to what the decoding shows.
  - A kind 5 event has `cases` (event indices) registered in `pointer_slots` under the keys `('case', i, k)`, so every walker, `compute_trim`, `patch_pointers` and `linearize` see its edges.
  - `linearize` treats a kind 5 event as a **collapsing** switch, using the existing `choose`.

- [ ] **Step 1: Decode.**
  - Script in the scratchpad (not committed): dump the 0x30 bytes of every kind 5 and kind 6 event in a few flows, and follow their pointers.
  - Confirm the kind 5 layout above and find what kind 6 holds.
  - Write the findings into the module docstring of `bfevfl.py`, next to the existing layout notes.
  - If kind 6 holds event pointers, it gets the same treatment as kind 5. If it has none, it stays a terminal marker; say so in the docstring.

- [ ] **Step 2: Failing real-data test** (in `BfevflTests`)

```python
def test_kind5_cases_are_parsed(self):
    with NupArchive(NUP_PATH) as nup:
        codec = ZsCodec.from_archive(nup)
        flow = EventFlow(_load(nup, codec, 'SubEvent_GetEponaSong.bfevfl.zs'))
    self.assertEqual(flow.events[27].kind, 5)
    self.assertEqual(flow.events[27].cases, [28, 112])
    self.assertIn(28, [v for _, v in flow.pointer_slots()])
```

- [ ] **Step 3: Failing synthetic test**: `linearize` collapses a kind 5 event like a switch, and does not report `dead end`. Build it with a new helper `HS(i, cases)` beside `SW`.

- [ ] **Step 4: Implement**
  - Parse kind 5 cases at `cases_p + 8 * k + 4`, as for SWITCH.
  - In `linearize`, `is_kept` is false for kind 5, and `advance` follows `cases[choose(i)]`.
  - `reachable_chosen` and `compute_trim`'s `keep_if` already iterate `ev.cases`. Check that they do, and that `_successors` in `cutscenes.py` includes the cases.

- [ ] **Step 5: Re-measure.**
  - Rerun the childhood survey (scratchpad).
  - The 7 `dead end` failures must be gone; write the new counts into the commit message.

- [ ] **Step 6: Run all tests; commit**

`feat: parse event kinds 5/6 (hash switches)`.

---

### Task 3: Fork dependency flag (spec §8.4)

**Files:**
- Modify: `randomizer/skipflow.py`
- Test: `tests/test_skipflow.py`

**Interfaces:**
- Produces: `fork_dependencies(flow: EventFlow, entry: str) -> list[tuple[int, str]]`, returning (fork index, flag name).
  - A flag counts when a fork branch reaches a SWITCH (kind 1 or 5) whose parameters name a flag that a sibling branch writes.
  - A flag is a string parameter under the keys `GameDataName`, `EventBoolName` or `FlagName`; use the keys found in the data and list them in a module constant `FLAG_KEYS`.
  - "Writes" means an ACTION whose name contains `Set`.
- Produces: `effects_only(..., reviewed_forks: frozenset[int] = frozenset())` fails with `'fork dependency'` when `fork_dependencies` finds a fork that is not in `reviewed_forks`.

- [ ] **Step 1: Failing tests**
  - A flagged case: two branches, one sets `X`, the sibling's switch reads `X`. `effects_only` returns `error == 'fork dependency'`.
  - An unflagged case: two independent branches.
  - Real-data check: none of the 4 spike scenes (`SPIKE_SCENES`) is flagged.

  Build the synthetic flows with a minimal fake of `EventFlow` that has `events`, `entry_points` and `action_params`. The rewriter only needs those.

- [ ] **Step 2: Run, fail. Step 3: Implement. Step 4: Run all tests.**

- [ ] **Step 5: Commit**

`feat: flag fork branches that depend on each other`.

---

### Task 4: External callers (spec §10, first must-do)

**Files:**
- Create: `randomizer/flow_callers.py`
- Modify: `randomizer/skipflow.py` (`effects_only` signature)
- Test: `tests/test_flow_callers.py`

**Interfaces:**
- Produces: `entry_callers(flows: Mapping[str, EventFlow]) -> dict[tuple[str, str], set[str]]`, mapping each (flow, entry) to the names of the *other* flows that call it.
  - It records every cross-file SUBFLOW event as `(sub_flow, sub_entry or 'EntryPoint0')`.
  - It records every ACTION parameter `EventName` or `BootEventName` whose value is a flow name as `(value, 'EntryPoint0')`.
- Produces: `effects_only(flow, entry, table, choices={}, reviewed_forks=frozenset(), external: frozenset[str] = frozenset())`.
  - Entries in `external` are never inlined: they and everything they reach are protected, like untargeted entries.
  - The targeted entry itself is ignored if it is in `external`, because the caller wants the rewrite.

- [ ] **Step 1: Failing tests**
  - `entry_callers` on two fake flows: A calls `B/C01` through a subflow, and A has an `EventTransition` to B.
  - Expected: `{('B','C01'): {'A'}, ('B','EntryPoint0'): {'A'}}`.
  - `effects_only` with `external={'C01'}`, on a flow whose `EntryPoint0` inlines `C01`, returns `'shared'` when the rewrite would relink `C01`'s events.

- [ ] **Step 2–4: Run, fail, implement, run all.**

- [ ] **Step 5: Commit**

`feat: index cross-file callers; never inline an entry others call`.

---

### Task 5: Private copies of shared events (spec §8.1, without growing the file)

**Files:**
- Modify: `randomizer/skipflow.py`, `randomizer/formats/bfevfl.py`
- Test: `tests/test_skipflow.py`, `tests/test_bfevfl.py`

**Rule (my call, in place of the spec's "grow the file"):**
- A copy is written into the 0x30-byte slot of an ACTION event that the rewrite leaves **unreachable from every entry point** (a *donor*).
- Copy and donor must both be ACTION events with the same non-null pointer fields (+0x00 name, +0x10 parameters, +0x18, +0x20). That way every pointer position stays in the relocation table and the file size is unchanged.
- SWITCH, kind 5 and SUBFLOW events are never copied. A protected switch that needs relinking still fails with `'shared'`.

**Interfaces:**
- Produces: `bfevfl.copy_event(data: bytes, src: int, dst: int) -> bytes`. It copies the slot and raises `BfevflError` if the pointer-field rule above does not hold.
- Produces: `Rewrite.copies: dict[int, int]`, mapping the copy's slot to the original event.
  - In `links`, a key may name the copy slot (`('next', copy)`).
  - `apply_rewrite` writes the copies first, then patches the links.
- `linearize`, instead of failing with `'shared'`:
  - copies each protected kept ACTION whose outgoing link would change;
  - redirects the targeted path's links that point at it to the copy;
  - repeats until nothing changes, because a redirected predecessor may itself be protected;
  - takes donors from events unreachable after the rewrite, lowest index first;
  - fails with `'no donor'` when it runs out of donors.

- [ ] **Step 1: Failing tests**
  - The flow of Task 1's protected test, now with one unreachable donor ACTION:
    - the rewrite succeeds;
    - `copies == {donor: 1}`;
    - entry `F` still reaches 1 → 2 → 3 unchanged;
    - entry `E` reaches the copy and then 3.
  - The same flow with no donor gives `'no donor'`.
  - `copy_event` refuses a donor whose parameter pointer is null while the source's is not.
  - Real data: re-measure the childhood survey. `Npc_Kokiri_007_Child/GoToDekuTree` must now rewrite. If it is still blocked by a switch, write that in the commit message and the report; do not force it.

- [ ] **Step 2–4: Run, fail, implement, run all.**

- [ ] **Step 5: Commit**

`feat: give targeted paths private copies of shared events`. Put the new survey counts in the message.

---

### Task 6: Rewrite checker (spec §5 "same order along each path", §10)

**Files:**
- Modify: `randomizer/skipflow.py`
- Test: `tests/test_skipflow.py`

**Interfaces:**
- Produces: `check_rewrite(old: EventFlow, new_data: bytes, entry: str, rw: Rewrite) -> list[str]`, returning problems (empty means OK):
  1. The kept nodes reachable from `entry` in the new flow, with copies mapped to their originals, equal `set(rw.kept)` mapped the same way.
  2. No FORK or JOIN is reachable from `entry` in the new flow.
  3. Order: for every new link a → b between kept nodes, b is reachable from a in the old flow augmented with an edge from each JOIN to every branch of the fork that uses it, and a is not reachable from b in the unaugmented old flow (unless a is on a cycle there).
  4. Every entry point other than `entry` and the inlined ones reaches exactly the same events as before.
  5. Fades: a kept `EventEventFadeOut` with no later kept fade-in is reported unless the old flow had none after it either.

- [ ] **Step 1: Failing tests**
  - A hand-made bad rewrite: swap two links. `check_rewrite` reports an order problem.
  - A correct `lin` output gives `[]`.
  - A rewrite that leaves a JOIN reachable is reported.

- [ ] **Step 2–4: Run, fail, implement, run all.**

- [ ] **Step 5: Commit**

`feat: rewrite checker (order, forks, other entries, fades)`.

---

### Task 7: Childhood target list and builder

**Files:**
- Create: `tools/build_full_skip_list.py`, `randomizer/data/full_skip.json`, `randomizer/full_skip.py`
- Test: `tests/test_full_skip.py`

**Data format** (`full_skip.json`):

```json
{
  "flows":     {"Dm_Kokiri_0155": {"phase": 1, "entries": ["EntryPoint0"], "choices": {"12": 0}}},
  "timelines": {"Dm_Kokiri_0150": 1},
  "movies":    {"Dm_Kokiri_0000": {"phase": 1, "callers": ["OpeningEvent"]}},
  "reviewed_forks": {"Dm_X": [34]}
}
```

`choices` (switch index → case) and `reviewed_forks` are optional and hand-edited. The tool keeps them when it regenerates the file.

**The tool** (only reads the `.nup`; prints a review table):
- **`flows`, phase 1:**
  - every `Dm_*` event flow whose bytes mention `_Child`/`_child` and not `_Adult`/`_adult` (`EntryPoint0`);
  - plus the entries listed in `cutscenes.json` for these childhood flows: `OpeningEvent`, `Meet_DekuTree`, `Get_StoneOfForest`, `Goto_HyruleCastle`, `Get_StoneOfFire`, `Get_StoneOfWater`, `SubEvent_GetEponaSong`, `HyruleCastle_FoundBySecurity`, `MelodyGet_Sun_SubEvent`, `Npc_Hylia_Zelda_Child`, `Npc_Kokiri_007_Child`, `Npc_Kokiri_010_Child`, `Npc_Kokiri_011_Child`, `Npc_Kokiri_Mido_Child`, `Npc_Hylia_052_Child`, `Npc_Hylia_ImperialSoldier_001_Child`;
  - plus the childhood entries of `DoorOfTime` (`Step01_Npc_Hylia_Impa_Child_Talk`, `Dm_MelodyGet_Zelda_After_Npc_Hylia_Impa_Child_Talk`, `DoorOfTime_GetOcarinaOfTime`, `DoorOfTime_GetOcarinaOfTime_AreaOut`, `Dm_MelodyGet_Time_After`);
  - minus `KEEP_TALKS` (import it from `tools/build_cutscene_list.py`).
  - `Dm_*` flows that mention neither age or both go through a hand-kept `CHILD_EXTRA` set in the tool: the review lists them with their zone, and adds the ones that are childhood (Kokiri, Deku, Hyrule Field, Castle, Market, Lon Lon, Kakariko, Death Mountain, Goron, Dodongo, Zora, Jabu-Jabu, child songs).
- **`timelines`, phase 1:** timeline-only `Dm_*` files with the same age rule and `CHILD_EXTRA`, excluding `_Effect`/`_Env` (those follow their parent) and the `movies`.
- **`movies`, phase 1:** `Dm_Kokiri_0000`, `Dm_Kokiri_0095`, `Dm_HrlCastle_0045` and `Dm_MelodyGet_Sun_*`. Callers are found by scanning every flow for `EventTransition` to that name.
- **NPC gifts and songs** in conversations the player starts (spec §4.3), as a hand-kept `GIFT_TALKS` dict, initial list:
  - Malon's egg;
  - Epona's Song (`SubEvent_GetEponaSong/GetEponaSong_MelodyGet_Epona`);
  - Saria's Song;
  - the Sun's Song;
  - Zelda's Lullaby after the letter.

  The review prints each entry's kept effects so a human confirms them.
- The tool prints, per target: method, `effects_only` result (error/detail), external callers, `fork_dependencies`.

**The builder** (`randomizer/full_skip.py`):
- `load_targets(phase: int = 1) -> Targets`: a dataclass with `flows`, `timelines`, `movies`, `choices`, `reviewed_forks`, filtered to `phase <= phase`.
- `build_full_skip_files(game, phase: int = 1, flows_cache=None) -> tuple[dict[str, bytes], list[str]]` returns (romfs path → compressed bytes, report lines).
  - It decompresses every flow it needs once, and builds `entry_callers` once over all `Event/EventFlow/*.bfevfl.zs`.
  - **Per flow file, one pipeline, in this order:**
    1. `drop_transitions` for the movies this file calls;
    2. for each targeted entry, `effects_only` with `external` = callers' entries minus this one, `choices` and `reviewed_forks`;
    3. `check_rewrite`, applying the entry only if it reports nothing.

    Entries that fail are reported and skipped. The others are applied in sequence: re-parse after each, because copies use donors.
  - **Per timeline:** `shorten` it and its subtimelines (existing code).
  - Returns only files that changed.
- `files_with_fallback(game, phase) -> dict[str, bytes]`: the full skip's files, plus `build_cutscene_files(game)` for every path the full skip did not write.
  - A flow file where *every* targeted entry failed is not in the full skip's output, so it keeps the old trimming.
  - A file with some entries rewritten is not old-trimmed as well. Report it.

- [ ] **Step 1: Write the tool and generate `full_skip.json`.**
  - Review the printed table.
  - Fill `CHILD_EXTRA` and `GIFT_TALKS`.
  - Remove targets whose kept effects look wrong.
  - Commit the tool and the JSON together, with the table's summary counts in the message.

- [ ] **Step 2: Failing tests** (`tests/test_full_skip.py`, real data, `OOT_NUP`):

```python
def test_every_applied_entry_passes_the_checker(self): ...
    # rebuild; for every (flow, entry) the report marks applied, check_rewrite(...) == []
def test_goto_hyrulecastle_is_written_once_with_all_methods(self): ...
    # the movie transition is gone AND the targeted entries are rewritten in the same output file
def test_failed_scene_falls_back_to_old_trimming(self): ...
    # patch load_targets to target a flow/entry known to fail (e.g. Dm_InsideJabu_Jabu_0050),
    # its output equals build_cutscene_files' version of that path (or is absent if that is absent)
def test_dropped_events_unreachable(self): ...
    # for each rewritten entry, no event the table drops is reachable from it in the output
def test_option_off_writes_nothing(self): ...  # goes in Task 8
```

- [ ] **Step 3–4: Implement the builder; run all tests.**

- [ ] **Step 5: Commit**

`feat: childhood full-skip builder with fallback to trimming`.

---

### Task 8: Wire the option

**Files:**
- Modify: `randomizer/generate.py` (where `build_cutscene_files(game)` is called)
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `files_with_fallback(game, phase=1)`.
- Produces: with `skip_cutscenes`, `extras = files_with_fallback(game, 1)`. Without it, nothing changes.
  - Catch `(ValueError, BfevflError, TimelineError)` and raise `GenerationError`, as today.
  - Write the report lines into the spoiler log under a "Cutscenes not skipped" heading, and only when the spoiler is on.
  - `browser.py` goes through `generate`; check that nothing else calls `build_cutscene_files` directly.

- [ ] **Step 1: Failing tests**
  - Same seed with the option on and off: same `placement`.
  - Option off: the set of written files and their bytes equal those of a run with the full skip code absent. Compare against a run where `files_with_fallback` is not called.
  - Option on: the mod contains `Event/EventFlow/OpeningEvent.bfevfl.zs`, and the spoiler has the heading.

- [ ] **Step 2–4: Run, fail, implement, run all.**

- [ ] **Step 5: Commit**

`feat: "Skip cutscenes" uses the full skip for childhood`.

---

### Task 9: Childhood test batch

**Files:**
- Create: `docs/test-full-skip-child.md`; `local/test-full-skip-child.md` (Spanish, gitignored)
- Modify: `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` (new §12 "Phase 2 build notes": counts, rulings, what fell back); `docs/TODO.md`

- [ ] **Step 1: Generate a seed with the option on.**
  - Use the project's normal CLI. Seed `FullSkipChild1`, default settings.
  - Write it into `test-mod/0400486024DEC000/Rando_FullSkipChild1`, which is gitignored.

- [ ] **Step 2: Write the guides.**
  - The play path is new game → Deku Tree → Gohma → Saria → castle (Malon, Zelda, letter, Lullaby) → Kakariko → Death Mountain → Goron City → Dodongo → Zora's Domain → Jabu-Jabu → Door of Time.
  - Per stop, list what should be skipped and what must still be received or opened (items, songs, stones, flags that open the way), and where Link should end up.
  - Add Navi's colour after `Dm_Kokiri_0030` and the longer loading screen after the intro.
  - Add a table of the report's fallbacks: scenes that will still play, and why.
  - Add a results section for the user to fill in.

- [ ] **Step 3: Update the spec and the TODO; commit.**
  - Commit: `docs: phase 2 build notes and childhood test guide`.
  - Then stop. The user plays the batch before anything else is built (spec §8.6).

---

## Rulings made while planning (my calls)

- **Copies use donor slots instead of growing the file** (Task 5).
  - Why: growing a BFEVFL would need a relocation-table writer, while donor slots keep the file size and the RSTB untouched.
  - Cost if wrong: some shared paths still fail for lack of a donor, or because a switch would need copying. They fall back to the old trimming and are listed.
- **Kind 5 events are collapsing switches** (Task 2).
  - Why: their layout matches a switch keyed by hashes, most likely a dialogue choice.
  - Cost if wrong: a scene follows the wrong case. The checker cannot see that, so the game test must.
- **Childhood is decided from actor names** (`_Child` only), plus a reviewed `CHILD_EXTRA` list.
  - Cost if wrong: a scene of the wrong age is or is not skipped. The adult phase will catch it.
- **Old trimming stays for everything outside phase 1, and for scenes the full skip cannot rewrite.**
- **`Dm_InsideJabu_Jabu_0050` and other leftovers are not forced in this phase.** They are reported and listed in the guide.
- **The item-get presentation for NPC gifts (spec §4.2, §8.7) is not touched in this phase.**
  - Why: the spikes showed that the items arrive.
  - The test batch records whether Link still raises the item; that decides whether it becomes a task later.
