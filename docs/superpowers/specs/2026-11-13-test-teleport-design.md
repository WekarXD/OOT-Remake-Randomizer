# Test teleport (test mode) — Design

Status: draft for approval (2026-11-13).

## 1. Why

In-game tests are getting long: batch 20 (Impa and Saria swap songs) needs half an hour of play before the first check. The user wants each test seed to put them straight where the test happens. They will wait for this before playing batch 20.

The user chose **both** options:

1. **Per-test start.** On a new game, the test seed hands over the items the test needs, sets the story flags and teleports to the test spot.
2. **A generic test character.** A Kokiri near Link's house who gives a starter kit and teleports to fixed places. It comes after (1) and reuses its tools.

## 2. Goals, non-goals, anti-goals

- **Goals:**
  - Test builders (`tools/`) can describe a start preset and get a mod with it: destination (map plus start position), items and flags.
  - Batch 20 is rebuilt with a preset that starts right before Impa.
- **Non-goals:**
  - Player-facing options on the page. This is a testing aid only.
  - New text: no message editing. The generic character reuses existing yes/no questions, and the guide says what each answer means.
  - A real in-game debug menu (it would need changes to the executable).
- **Anti-goals:**
  - Any change to normal seeds.
  - A preset that breaks the save, for example a flag that softlocks the story. Each preset is checked in its own test.

## 3. What we know

- **Teleport:** the game changes map with `GameSystemActor.EventReserveBancChange` (`NextBanc`, `NextStartPos`, `EventStarterName`, `BootEventName`). The common path is the subflow `Dm_SY_BancChangeGo:EntryPoint0`, which takes `NextBanc`, `NextStartPos`, `BootEventName`, `IsCheckAir` and `NextStartPosAir` as arguments. Literal destinations exist, for example `HyruleField_Child` + `HyruleField_FrontOfLostWoodBridge` in `Goto_HyruleCastle`. Start positions are named actors in each map's banc (`HyruleCastle_Static` has `DoorOfTime_MeetImpa_StartPos`, `EventStartPos`…).
- **Items:** a subflow call to `Dm_SY_GetInEvent` with `ActorName` gives an item (Saria → Boomerang, batch 7).
- **Flags:** `GameDataActor.EventTriggerSetGameDataBool` (`GameDataName`, `Value`).
- **The limit today:** `bfevfl.py` can change values that already exist and copy events within a file (`grow_events`, whose copies share their source's parameter container). It cannot add an event with **its own** parameters, or call a flow with literal arguments.
- **Hook:** `Dm_Kokiri_0045` is the scene when Link first leaves his house. It has 74 events, `GameSystemActor` and `GameDataActor`, and the full skip already handles it with care (house door flag). It is the candidate for the start hook; the spike confirms it.

## 4. Approaches (how to add an event with its own parameters)

| Approach | Trade-off | Decision |
|---|---|---|
| **A. Build the parameter container from scratch**, including its `DIC` dictionary, and append it with the new event | General: any keys, any values. The `DIC` is Nintendo's radix-tree dictionary; a test can rebuild every dictionary in the game and compare bytes, which makes it safe | **Chosen** |
| B. Copy a container byte for byte from another file and repoint its strings | Less code, but only works when some flow already has a container with exactly the needed keys and types | Rejected: the arguments of `Dm_SY_BancChangeGo` are of type argument, not string |
| C. Hack an existing call (turn its argument items into strings) | Smallest, but only works in the few flows that already call the banc change | Rejected: no such call near the start |

## 5. Design

### 5.1 New event tool (`randomizer/formats/bfevfl.py`)

- `build_dic(keys) -> bytes`: Nintendo `DIC ` radix tree. Its oracle test rebuilds every parameter dictionary in the game from its key list and compares bytes.
- `append_events(data, specs) -> (bytes, list[int])`: grows the event array (same mechanism as `grow_events`). For each spec it adds a slot with its own parameter container (built with `build_dic`), its strings, and the pointers registered in the RELT. Specs:
  - action: actor and action, which must already exist in the flow's actor table;
  - subflow: called flow, entry and params.
- Param types: string, int, bool, float. That covers banc change, item gift and flag.
- The `next` of each new event is set by the caller (`patch_pointers`), so presets can chain events.

### 5.2 Start preset (`randomizer/test_start.py`)

- `StartPreset(destination: (banc, start_pos), items: list[str], flags: list[(name, bool)])`.
- `apply_start(flow_bytes, preset) -> bytes`: appends the chain at the end of the hook entry: flags, then item gifts, then the teleport. The teleport goes last so the arrival scene loads with the flags set.
- Writes the hook flow and its RSTB entry, like the full skip's grown flows.
- Only test builders use it; `generate.py` never does.

### 5.3 Phases, each with its Lichii test

0. **Spike (TestBatch21):** on leaving the house you get the Fairy Ocarina and appear in Hyrule Field by the Lost Woods bridge (a literal destination the game already uses). It proves the tool, the hook and the teleport.
1. **Batch 20 with a preset:** start right before Impa. Finding the flags ("met Zelda", and so on) is part of this phase: read them from the flows of the Zelda and Impa scenes.
2. **Generic Kokiri:** reuse `append_events` with a chain of existing yes/no questions (a Kokiri flow with choices) towards a fixed list of destinations. It gets its own short design when we get there.

## 6. Done when

- `append_events` and `build_dic` are tested (DIC oracle over the whole game, parse round-trip, RELT consistent).
- TestBatch21 passes in Lichii.
- Batch 20 is regenerated with its preset and its guide starts at Impa.

## 7. Left to the builder

- The exact layout of the appended data: alignment, order of containers and strings.
- How to list a map's start positions: a small helper in `tools/`.
- Which existing yes/no question the generic Kokiri reuses (phase 2).
