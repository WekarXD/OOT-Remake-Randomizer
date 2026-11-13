# Full skip: adult phase (plan)

Spec: `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §6 step 3. The
childhood (phase 1 in `full_skip.json`) is closed (rounds 1–5). This plan adds phase 2:
the adult game without Ganon's Castle and the ending (spec step 4, a later phase 3).

## Decisions

- **Scope = everything left, minus phase 3.** The age of a scene only decided the rollout
  order; the methods do not depend on it. Phase 2 targets every `Dm_*` scene not in phase 1
  except: Ganon's Castle and the ending (`FinalBattle`, `GanonCastle`, `InsideGanonCastle`,
  `Ending` zones), boss intros and defeats (kept by the user), and `NOT_SKIPPED` (scenes
  left out for a reason: minigames, no `EntryPoint0`, the Zora's Fountain black screen).
- **Story flows:** every `cutscenes.json` story flow not already in `CUTSCENE_FLOWS`, except
  `Defeat_Ganon` and `EscapeFromCrumblingGanonCastle` (phase 3).
- **Door of Time:** its remaining `cutscenes.json` entries.
- **Movies:** every movie with a caller, except `Dm_FinalBattle_0002` (phase 3).
- **Forced talks** (from `find_forced_talks.py --age adult`, new): adult Mido's block,
  the carpenter before Gerudo Fortress, the Gerudo before the Haunted Wasteland, Navi after
  the Water Temple level change, Navi's soft-soil notice at Zora's River. Gift: the windmill
  man's Song of Storms. Puzzle cameras (`*_Gimmick`), minigames, the Poe guide, the running
  man and the `Dm_SY_*` dungeon clear events are left out (not conversations, or the user
  keeps the boss scenes).
- **Phases per entry:** a flow already in phase 1 (e.g. `DoorOfTime`) can gain phase 2
  entries; `full_skip.json` records them in an optional `entry_phases` map
  (entry -> phase) and `load_targets` filters by it.
- **Generation uses phase 2.**

## Tasks

1. `find_forced_talks.py --age adult` (done while planning).
2. `entry_phases` in `full_skip.json` + `load_targets` (unit test).
3. Builder: phase-2 rules above; regenerating keeps phase 1 byte-identical except for
   added phase-2 records/entries (check the diff).
4. Forced talks: add the adult ones to `FORCED_TALKS` (old trimming) and the full skip lists.
5. `generate.py` builds phase 2; full test suite; report diff phase 1 vs 2 (no phase-1
   regression).
6. Seed `Rando_FullSkipAdult1`, guide `local/test-full-skip-adult-1.md` grouped by zone,
   to be tested from the user's save in the Temple of Time right after becoming adult.
