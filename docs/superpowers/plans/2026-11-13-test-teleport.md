# Test Teleport (phase 0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test seeds can start a new game with given items and flags and teleport to a chosen spot. Phase 0 proves it in Lichii with TestBatch21.

**Architecture:** A new module `randomizer/formats/evfl_append.py` builds parameter containers from scratch (including the `DIC ` radix tree) and appends new events with their own parameters to a flow, reusing `grow_events`' layout (event array moved after the relocated data, RELT rebuilt). `randomizer/test_start.py` uses it to put a chain (flags → item gifts → teleport) at the start of the hook entry `Dm_Kokiri_0045:EntryPoint0`. A tool writes the spike mod.

**Tech Stack:** Python 3, unittest. Game-data tests need `OOT_NUP`, as the BFEVFL tests do.

**Spec:** `docs/superpowers/specs/2026-11-13-test-teleport-design.md`

## Global Constraints

- Item gift: subflow `Dm_SY_GetInEvent` : `GetInEvent` with `{'ActorName': <actor>}` (the shape MiniGame_Fishing uses).
- Teleport: subflow `Dm_SY_BancChangeGo` : `EntryPoint0` with `NextBanc`, `NextStartPos`, `BootEventName` (string), `IsCheckAir` (bool False) and `NextStartPosAir` (string, same as `NextStartPos`).
- Flag: action `GameDataActor.EventTriggerSetGameDataBool` with `{'GameDataName': name, 'Index': -1, 'Value': bool}` (same keys and order as in `Dm_Kokiri_0045` event 45).
- Hook: `Dm_Kokiri_0045`, entry `EntryPoint0`. The chain also sets the two flags the scene itself sets (`KokiriForest_LinkHouseDoor_Open`, `Dm_Kokiri_0050_After_Near_End`), so the scene does not replay.
- `generate.py` never imports `test_start`.
- New code goes in new files. `bfevfl.py` (575 lines) only gets a public `actors` attribute.

## Review Focus

- **The game's DICs:** keys are read from the end of the string (Nintendo bit order). The oracle test over every container in the 914 flows pins this.
- **Appending to an already grown flow:** `append_events` must work on `grow_events` output too (the full skip grows flows). A test appends to a grown file.
- **Unknown actor or action in an action spec:** it raises `BfevflError` and does not write a broken index. Test it.
- **Teleport loop:** after the teleport, leaving Link's house again must not teleport again. The spike guide checks it in game; the hook flags exist for this.
- **RSTB:** the grown hook flow needs its RSTB entry raised, as `make_gift_batch` does (delta rounded up to 0x100, plus 0x1000). The spike tool asserts the entry exists.

---

### Task 1: `DIC` builder with a whole-game oracle

**Files:**
- Create: `randomizer/formats/evfl_append.py`
- Test: `tests/test_evfl_append.py`

**Interfaces:**
- Produces: `build_dic(keys: Sequence[str], name_ptr: Callable[[str], int]) -> bytes`, the `DIC ` block (`DIC `, u32 count, root plus one 0x10 entry per key: s32 bit index, u16 left, u16 right, u64 pointer to the name). `name_ptr` gives each key's string offset; the root points to the empty string (`name_ptr('')`).

- [ ] **Step 1: Write the failing tests**
  - `test_dic_oracle` (needs `OOT_NUP`): for every flow and every event with a parameter container, read the container's DIC bytes and its key list in item order. Rebuild with `build_dic(keys, ptr)`, where `ptr` maps each name to the pointer found in the original DIC. Assert bytes are equal. Assert more than 10000 containers were checked.
  - `test_dic_small`: `build_dic(['A'], …)` has count 1 and parses back through the same reader `EventFlow` uses (entry j+1 is item j).

- [ ] **Step 2: Run them and watch them fail**

Run: `python -m unittest tests.test_evfl_append -v`
Expected: ImportError.

- [ ] **Step 3: Implement `build_dic`.** It is the standard Nintendo ResDic radix tree: bit `i` of a key is `(key[len-1 - i//8] >> (i % 8)) & 1`, with 0 past the key's length. Insert keys in item order. The oracle is the judge; if it fails, decode one failing DIC by hand before changing the algorithm.

- [ ] **Step 4: Run them and watch them pass**

Run: `OOT_NUP=<nup> python -m unittest tests.test_evfl_append -v`
Expected: PASS.

- [ ] **Step 5: Commit** `feat: build BFEVFL DIC dictionaries`

### Task 2: Append events with their own parameters

**Files:**
- Modify: `randomizer/formats/bfevfl.py` (in `_parse`, keep `self.actors = actors`, the list of `(name, actions, queries)`)
- Modify: `randomizer/formats/evfl_append.py`
- Test: `tests/test_evfl_append.py`

**Interfaces:**
- Consumes: `build_dic`, `grow_events`' layout, `relocation_table` and `build_relocation_table`.
- Produces:
  - `ActionSpec(actor: str, action: str, params: dict[str, str | int | bool | float])`
  - `SubflowSpec(flow: str, entry: str, params: dict[...])`
  - `append_events(data: bytes, specs: Sequence[ActionSpec | SubflowSpec]) -> tuple[bytes, list[int]]`: returns the new file and the new event indices. Each new event has `next = 0xFFFF`; callers link with `patch_pointers`.
- Layout (the builder decides the details): event array moved and grown as `grow_events` does, then per spec its container, DIC, items and their strings (each string right after its item, as in the game), then the event name, flow and entry strings. Every new pointer is added to the RELT. Param types map to INT 2, BOOL 3 (true = 0x80000001), FLOAT 4, STRING 5.

- [ ] **Step 1: Write the failing tests** (they need `OOT_NUP`; flow `Dm_Kokiri_0045`):
  - `test_append_action_and_subflow`: append `ActionSpec('GameDataActor', 'EventTriggerSetGameDataBool', {'GameDataName': 'X_Test', 'Index': -1, 'Value': True})` and `SubflowSpec('Dm_SY_GetInEvent', 'GetInEvent', {'ActorName': 'Item_Ocarina_Fairy'})`. Then check:
    - `_assert_valid` holds;
    - the old events, params and entries are unchanged (copy `GrowEventsTests._check_original`'s checks);
    - the new events have the right kind, actor and action (or flow and entry), and `action_params` equals the given dict.
  - `test_append_to_grown_flow`: first `grow_events(data, [some action])`, then `append_events`. It stays valid.
  - `test_unknown_actor_or_action_raises`: `ActionSpec('NoSuchActor', ...)` and `ActionSpec('GameDataActor', 'NoSuchAction', ...)` both raise `BfevflError`.
  - `test_relt_covers_new_pointers`: every nonzero pointer field of the new slots and containers is in `relocation_table(new)[2]`.

- [ ] **Step 2: Run them and watch them fail**

Run: `OOT_NUP=<nup> python -m unittest tests.test_evfl_append -v`
Expected: FAIL (no `append_events`).

- [ ] **Step 3: Implement** `actors` in `EventFlow._parse` and `append_events`.

- [ ] **Step 4: Run them and the BFEVFL suite**

Run: `OOT_NUP=<nup> python -m unittest tests.test_evfl_append tests.test_bfevfl`
Expected: PASS.

- [ ] **Step 5: Commit** `feat: append BFEVFL events with their own parameters`

### Task 3: Start preset

**Files:**
- Create: `randomizer/test_start.py`
- Test: `tests/test_test_start.py`

**Interfaces:**
- Consumes: `append_events`, `ActionSpec`, `SubflowSpec`, `patch_pointers`, `EventFlow`.
- Produces:
  - `HOOK_FLOW = 'Dm_Kokiri_0045'`, `HOOK_ENTRY = 'EntryPoint0'`, `HOOK_FLAGS = ('KokiriForest_LinkHouseDoor_Open', 'Dm_Kokiri_0050_After_Near_End')`
  - `StartPreset(banc: str, start_pos: str, items: tuple[str, ...] = (), flags: tuple[tuple[str, bool], ...] = ())`, frozen
  - `apply_start(flow_bytes: bytes, preset: StartPreset) -> bytes`: chain = HOOK_FLAGS (True) + preset flags → one gift per item → teleport. The entry's start pointer goes to the first event of the chain; each new event's `next` goes to the following one, and the teleport's `next` stays `0xFFFF`.

- [ ] **Step 1: Write the failing tests** (`OOT_NUP`):
  - `test_chain_order`: with `StartPreset('HyruleField_Child', 'HyruleField_FrontOfLostWoodBridge', items=('Item_Ocarina_Fairy',), flags=(('Foo', True),))`, walking from `EntryPoint0` gives:
    - SetGameDataBool for each HOOK_FLAG, then for `Foo`;
    - GetInEvent with `Item_Ocarina_Fairy`;
    - BancChangeGo with `NextBanc='HyruleField_Child'`, `NextStartPos='HyruleField_FrontOfLostWoodBridge'`;
    - then `0xFFFF`.
  - `test_original_events_untouched`: the events of the vanilla flow keep their shape and params.
  - `test_not_used_by_generate`: `'test_start'` does not appear in `randomizer/generate.py`'s source.

- [ ] **Step 2: Watch them fail.** Run `OOT_NUP=<nup> python -m unittest tests.test_test_start -v`. Expected: ImportError.

- [ ] **Step 3: Implement** `StartPreset` and `apply_start`.

- [ ] **Step 4: Watch them pass, then run the full suite** (`OOT_NUP` set, `python -m unittest discover -s tests -t .`). Expected: everything passes except the 1 known expected failure.

- [ ] **Step 5: Commit** `feat: start presets for test seeds`

### Task 4: Spike mod TestBatch21 and its guide

**Files:**
- Create: `tools/make_start_batch.py` (usage: `python -I tools/make_start_batch.py <nup> <out_mod_dir>`)
- Create: `docs/test-batch-21.md` and `local/test-batch-21.md` (Spanish, not committed)
- Modify: `docs/TODO.md`

- [ ] **Step 1:** The tool reads `Dm_Kokiri_0045` and applies `StartPreset('HyruleField_Child', 'HyruleField_FrontOfLostWoodBridge', items=('Item_Ocarina_Fairy',))`. It writes the compressed flow and the RSTB (asserting the entry exists; delta rounded up to 0x100, plus 0x1000), and replaces the output directory atomically (`.tmp` then rename, like `make_gift_batch`). Run it into `test-mod/0400486024DEC000/TestBatch21`.
- [ ] **Step 2:** Guide. New game; on leaving the house:
  - Do you get the Fairy Ocarina?
  - Do you appear in Hyrule Field by the Lost Woods bridge?
  - Does the game keep working (walk, enter the market)?
  - Go back to Kokiri Forest, enter and leave the house: no second teleport?
  - Any hang?
- [ ] **Step 3: Commit** the tool, the English guide and the TODO line: `test: TestBatch21 start-preset spike`.
