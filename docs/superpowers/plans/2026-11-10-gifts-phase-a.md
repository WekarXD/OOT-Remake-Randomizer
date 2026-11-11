# Gifts — Phase A: Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Be able to change the item a scene hands out (a text parameter in a BFEVFL) and check in Lichii whether a scene can hand out a different key item. This is the phase A gate of the design.

**Architecture:**
- The BFEVFL reader is extended to read the actions' parameter containers and to rewrite a text parameter.
- The first attempt is to reuse a string that already exists in the file. If it does not exist, the file is extended and the RSTB is updated with a margin.
- A tool generates the test batch `TestBatch7`: Saria hands out the Hookshot instead of the Fairy Ocarina.

**Tech Stack:** Python 3.14, stdlib only.

**Spec:** `docs/superpowers/specs/2026-11-10-gifts-design.md` (§4.1, §4.4 A and §7)

## Global Constraints

- The `.nup` is never written to and game files are never committed. Tests with the game use `OOT_NUP` and `@unittest.skipUnless(NUP_PATH, 'OOT_NUP not defined')`, and run with `python -m unittest` (without `-I`).
- Standard library only. User-facing messages are in English and commits carry no attribution lines.
- With all the switches off, the mod and the RNG key are identical to today's (spec §7).
- In this phase the fill (`fill.py`) and the page are not touched: only the tool and the test batch.

## Review Focus

1. A text parameter shared by several actions, or a string shared in the pool: changing one action must not change the others. Test in task 1.
2. A flow that "Skip cutscenes" also trims: the two changes coexist on the same bytes. Test in task 1.
3. An extended file: all internal pointers remain valid and the reader rereads the whole file without errors. Test in task 1.
4. A new text that already exists in the pool: it is reused and the size does not change. Test in task 1.
5. A test batch regenerated over an existing one: the tool replaces it safely, like `make_cutscene_batch.py`. Test in task 2.

---

### Task 1: Read and rewrite text parameters in BFEVFL

**Files:**
- Modify: `randomizer/formats/bfevfl.py`
- Test: `tests/test_bfevfl.py`

**Interfaces:**
- Consumes: `EventFlow` and `patch_pointers` from this same module.
- Produces:
  - `EventFlow.action_params(index: int) -> dict[str, object]`: the parameters of an action or subflow. Texts are returned as `str`; the rest are converted to Python values.
  - `set_string_param(data: bytes, event_index: int, key: str, value: str) -> bytes`: returns the file with that parameter changed. An existing string is reused if there is one; otherwise, the file is extended. Raises `BfevflError` if the event does not have that text parameter.
  - `string_param_owners(data: bytes, event_index: int, key: str) -> list[int]`: the events that share the same parameter slot, to detect risk 1.
- **The implementer first investigates** the format of the parameter container (the list of parameters hanging off the event) in real flows. Examples from the exploration: `Dm_Kokiri_0155` events 51 and 52 (`Item_Ocarina_Fairy`) and `GatheringTokenGold` event 250 (`TakenRewardActor: 'Obj_Rupee_Gold'`). The format is documented in the docstring.

- [ ] **Step 1: Tests (OOT_NUP)**
  - `test_read_gift_params`: `action_params` of `Dm_Kokiri_0155` at events 51 and 52 contains the value `'Item_Ocarina_Fairy'` under some key. The test discovers the key and fixes it.
  - `test_set_string_param_roundtrip`: changing that parameter to `'Item_Hookshot'` and rereading gives `'Item_Hookshot'`. All the other parameters of all the events and all the `pointer_slots()` stay the same.
  - `test_reuse_existing_string`: if the new value is already in the file's pool, the length does not change.
  - `test_grow_file_valid`: with a value that does not exist in the pool, the file grows and `EventFlow(new)` reads the same number of events. In addition, `pointer_slots()` gives the same indices.
  - `test_other_events_untouched`: if another event uses the same string (`string_param_owners` returns more than one), changing one does not alter the text the other reads.
  - `test_coexists_with_trim`: applying `patch_pointers` (trim) and then `set_string_param`, or the reverse, gives a valid file with both changes in both cases.
- [ ] **Step 2:** Run `python -m unittest tests.test_bfevfl -v`. A FAIL is expected.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the tests again and then the full suite. A PASS is expected.
- [ ] **Step 5:** Commit with the message `feat: read and rewrite BFEVFL string params`.

### Task 2: Test batch 7 (Saria hands out the Hookshot)

**Files:**
- Create:
  - `tools/make_gift_batch.py`
  - `docs/test-batch-7.md`

**Interfaces:**
- Consumes: `set_string_param`, `string_param_owners`, `ZsCodec`, `NupArchive`, `Rstb` and `randomizer.patch.RSTB_PATH`.
- Produces: `python -I tools/make_gift_batch.py <nup> <out_dir>`, which writes `<out_dir>/romfs/Event/EventFlow/Dm_Kokiri_0155.bfevfl.zs` with the parameters of events 51 and 52 changed from `Item_Ocarina_Fairy` to `Item_Hookshot`.
  - If the file changes size, the RSTB is also written with the flow's entry updated (`Event/EventFlow/Dm_Kokiri_0155.bfevfl`), with value = original value + (new size − original size) rounded up to 0x100, plus a margin of 0x1000.
  - Replacement is safe, as in `tools/make_cutscene_batch.py`: it only replaces an empty folder or one that only contains `romfs`.
  - If `string_param_owners` indicates that the text is shared by events other than 51 and 52, the tool stops with `FAILED: ...` and writes nothing.

- [ ] **Step 1:** Implement the tool and generate `test-mod/0400486024DEC000/TestBatch7` (ignored by git).
- [ ] **Step 2:** Write `docs/test-batch-7.md` in English, with checkboxes:
  - new game and only this mod active;
  - leave the forest and say goodbye to Saria on the bridge;
  - do you receive the Hookshot instead of the Ocarina? Does it appear in the inventory and can it be used?;
  - does the scene end properly, with no crash or black screen?;
  - does the Fairy Ocarina not appear? (this is the expected result);
  - an empty "Results" section.
- [ ] **Step 3:** Run the full suite. A PASS is expected.
- [ ] **Step 4:** Commit with the message `test: gift test batch 7 (Saria gives Hookshot)`.

### Gate (after task 2)

The user tests `TestBatch7` in Lichii.
- **If it works:** the phase B plan is written (ocarinas, Gerudo Card, Skulltula rewards, frogs and Loach with the logic and the page).
- **If it does not work:** stop and go back to the user (spec §7).
