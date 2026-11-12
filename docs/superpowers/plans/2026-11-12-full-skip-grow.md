# Full Cutscene Skip: Growing Event Flows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Forced conversations that share events with player-started ones (Mido, the exit Kokiri, the targeting tutorial and ~55 others) are skipped by giving the targeted path private copies of the shared events in new event slots appended to the file.

**Architecture:** `bfevfl.grow_events` moves a flow's event array to the end of the file with extra slots, copies events into them (switches with their own case arrays), and rebuilds the relocation table (RELT). The rewriter's copy step uses new slots when it runs out of donors, and may then copy switches, subflows and subflow switches too. The builder reports each grown file's size change so `write_mod` updates its RSTB entry.

**Tech Stack:** Python 3 stdlib, `unittest`; real-data tests need `OOT_NUP` (`C:/Users/...` form).

**Spec:** `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §8.1 ("the rewriter may duplicate events into new slots and grow the file, updating the RSTB"), §12.

## Global Constraints

- Never write to the `.nup`; never commit game files (`test-mod/`, `local/`).
- Everything committed in English; Spanish guides only in `local/`. No attribution lines; no push or merge without the user's OK.
- Same seed, same placement with the option on or off. Option off: mod byte-identical to today.
- Events reachable from untargeted entries never change in place (spec §8.1); a rewrite is applied only if `check_rewrite` reports nothing.
- A grown file's RSTB entry becomes `original RSTB value + (new length − original length)` (decompressed sizes).

## Facts (measured 2026-11-12, TestGrow1)

- Header: 0x18 u32 RELT offset, 0x1C u32 file size. RELT: `'RELT'`, u32 own offset, u32 section count (1), u32 0; section: u64 0, u32 0, u32 size of the relocated data, u32 first entry 0, u32 entry count; entries: (u32 offset, u32 mask), bit b of the mask = the u64 at offset + 8·b is a pointer; an entry starts at a pointer and covers 0x100 bytes. Rebuilding this from the pointer set reproduces the originals byte for byte.
- Flowchart (`EventFlow._flowchart`): +0x10 u16 counts (actors, actions, queries, events, entries); events pointer at +0x30. Event slot 0x30 bytes.
- The game accepted grown copies of `Npc_Kokiri_006_Child`, `Npc_Kokiri_007_Child`, `Npc_Kokiri_Mido_Child` (array moved to the end + 8 unused slots, RELT rebuilt, RSTB updated): forest loads, NPCs talk as in the original.
- Spike script: `C:\Users\wekar\AppData\Local\Temp\claude\ca659016c6b54b31\405f4ebb-9e3c-4270-b18c-2ad884778902\scratchpad\grow.py` (reference only).

## Review Focus

1. A copied switch must own its case array: patching the copy's cases must leave the original's untouched.
2. Pointers inside the moved/added events must all be in the rebuilt RELT, and nothing else may still point into the old array (the old array stays as dead bytes; its RELT bits may stay).
3. RSTB: a grown flow absent from the RSTB must not crash generation (skip the update and report it).
4. Several grown entries in one file: each later step grows the already-grown file; indices of earlier copies stay valid.
5. Option off / no growth: `write_mod` must not write the RSTB when no flow grew and no banc changed (today's behaviour).

---

### Task 1: `grow_events` and the relocation table

**Files:** Modify `randomizer/formats/bfevfl.py`; Test `tests/test_bfevfl.py`.

**Interfaces (produces):**
- `relocation_table(data: bytes) -> tuple[int, int, set[int]]` → (RELT offset, relocated size, pointer offsets).
- `build_relocation_table(at: int, size: int, pointers: set[int]) -> bytes`.
- `grow_events(data: bytes, sources: Sequence[int]) -> bytes`: the file with the event array moved after the relocated data (16-aligned), then one new slot per source (index `n + j`, a byte copy of event `sources[j]`), event count updated, RELT rebuilt after it (16-aligned), header 0x18/0x1C updated. SWITCH and SUBFLOW_SWITCH copies get their own copy of the 8-byte-per-case array (appended after the slots, pointer at +0x18 repointed). ACTION and SUBFLOW copies keep their pointers (shared names/parameters are read-only). FORK, JOIN and RESULT sources raise `BfevflError`.

- [ ] Step 1 (failing tests, real data):
  - `test_relocation_table_round_trip`: for every `Event/EventFlow/*.bfevfl.zs` with a RELT, `data[:at] + build_relocation_table(*relocation_table(data))` equals `data`.
  - `test_grow_keeps_every_event`: `grow_events(d, [])` and `grow_events(d, [a, s])` (a = first action, s = first switch) on `Npc_Kokiri_007_Child`: every original event, entry point and action's params parse the same; new events equal their sources (kind, actor, action/query, next, cases); event count n+2.
  - `test_switch_copy_owns_its_cases`: in the grown file, `patch_pointers` on the copy's case slot changes the copy's case and not the source's.
  - `test_fork_cannot_be_copied`: `BfevflError`.
- [ ] Step 2–4: run (fail), implement, run all (`python -m unittest discover -s tests` with OOT_NUP, ~4 min).
- [ ] Step 5: commit `feat: grow event flows (moved event array, rebuilt RELT)`.

### Task 2: Copies into new slots

**Files:** Modify `randomizer/skipflow.py`; Test `tests/test_skipflow.py`, `tests/test_full_skip.py` (real data).

**Interfaces:**
- Consumes: `grow_events`.
- Produces: `effects_only(..., grow: bool = False)`. With `grow=True`, `_private_copies` may copy any protected SWITCH, SUBFLOW_SWITCH, SUBFLOW or ACTION whose link changes (fixpoint as today); copies first take donors (ACTION only, as today), the rest take new slots `n, n+1, …` in order. `Rewrite.grown: list[int]` = sources of the new slots in order (empty when nothing grows). `apply_rewrite` grows first (`grow_events(data, rw.grown)`), re-parses, writes donor copies, then patches links with the grown flow's `link_slots`. `check_rewrite` maps new slots to their sources like donor copies (rules 1, 3, 4).
- With `grow=False` behaviour is unchanged ('shared' / 'no donor').

- [ ] Step 1 (failing tests):
  - synthetic: a protected switch whose case must change → with `grow=True` the rewrite succeeds, `rw.grown == [switch]`, untargeted entries walk exactly their original events after `apply_rewrite`.
  - real data: with `grow=True`, `Npc_Kokiri_007_Child/GoToDekuTree`, `Npc_Kokiri_007_Child/Talk`, `Npc_Kokiri_Mido_Child/Talk` rewrite (error None) and `check_rewrite == []`; report which `Npc_Kokiri_006_Child` tutorial entries now pass.
- [ ] Step 2–4: run, implement, run all.
- [ ] Step 5: commit `feat: rewriter copies shared events into new slots`.

### Task 3: Builder, target list and RSTB

**Files:** Modify `randomizer/full_skip.py`, `randomizer/generate.py`, `randomizer/patch.py`, `tools/build_full_skip_list.py`, `randomizer/data/full_skip.json` (regenerated); Test `tests/test_full_skip.py`, `tests/test_generate.py`.

**Interfaces:**
- `skip_flow` and the tool pass `grow=True`.
- `files_with_fallback(game, phase=1) -> tuple[dict[str, bytes], list[str], dict[str, int]]`: the third item maps each grown flow's romfs path to its size change (new − original decompressed length).
- `write_mod(..., extra_files=None, extra_sizes: dict[str, int] | None = None)`: for each path in `extra_sizes`, `rstb.set(path[:-3], rstb.get(path[:-3]) + delta)` (missing entry → leave it and append a line to the report via a returned list or a log line; choose one and test it); the RSTB is loaded and written when `extra_sizes` is non-empty even if no banc changed.
- `generate` passes the sizes through.

- [ ] Step 1 (failing tests): a generated mod with the option on has `Npc_Kokiri_007_Child` grown and its RSTB entry = original + delta; option off: no RSTB written when no banc changed (unchanged behaviour) and same bytes as before; the rewrite of the exit Kokiri is applied.
- [ ] Step 2: regenerate `full_skip.json` with the tool; record new counts.
- [ ] Step 3–4: implement, run all.
- [ ] Step 5: commit `feat: full skip grows flows and updates the RSTB`.

### Task 4: Test batch

- [ ] Generate seed `FullSkipChild3` (skip cutscenes + spoiler) into `test-mod/0400486024DEC000/Rando_FullSkipChild3`.
- [ ] Write `docs/test-full-skip-child-3.md` and `local/test-full-skip-child-3.md` (Spanish, plain): what changed since round 2 (forced conversations now skipped, list from the spoiler: which of Mido, the exit Kokiri, the targeting tutorial, Din's fairy, the owl at Death Mountain, Zelda, guards…), what still plays (from the spoiler), checks (no freeze, nothing lost, the conversations the player starts with those NPCs still work).
- [ ] Add a §12 note to the spec and update `docs/TODO.md`; commit `docs: round 3 childhood guide (grown flows)`. Stop for the user's test.
