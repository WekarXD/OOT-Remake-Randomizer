# Rainbow Bridge medallions and Ganon's Trials (design, 2026-11-22)

The user asked for OoTR's "Medallions Required for Bridge" and "Ganon's Trials Count" with "Random Number of Ganon's Trials" ("vamos a implementar esto").

## How the game does it (research, 2026-11-22)

**Bridge.** `Banc/GanonCastle/GanonCastle_Static` has an `EventRequestActor` that fires `Defeat_Ganon:GanonCastle_Adult_Field_Rainbow` (the bridge scene). Its AINB module `Logic/GanonCastle_Level_Field_00_Prefab_14ba` creates the trigger areas while `Defeat_Ganon_IsAfter_Ready_Exp AND Defeat_Ganon_IsAfter_Step01_Exp` hold (node 5 = AND(node 4, node 6), node 6 = AND(node 3); the multi-input array is `(node, output)` pairs and a `BoolMulti` input holds `-100 - base`). In the vanilla game, `AllSage:Market_Adult_Field_GetArrowLight` (Zelda's Light Arrows scene, after the Shadow and Spirit awakenings) moves `Defeat_Ganon` to `Step01`.

**Bool expressions.** `*_Exp` names are rows of the `BoolExp` table of `GameData/GameDataList.Product.110.byml.zs` (big-endian BYML). `Values` is an RPN program of `U64` pairs:

| op | meaning |
|---|---|
| `[0, hash]` | push the Bool flag `hash` |
| `[10, hash]` | push another BoolExp |
| `[12, enum]`, `[2, value]` | push "quest step is at or after value" |
| `[3]`, `[4]`, `[5]` | AND, OR, NOT |

Each medallion has a saved flag `IsGet.Item_Medal_<Forest|Fire|Water|Shadow|Spirit|Light>`.

**Trials.** Each trial's flow (`Defeat_Ganon:InsideGanonCastle_Dungeon_BarrierRemove_<X>`) sets `InsideGanonCastle_Dungeon_BarrierRemove_<X>` and subtracts 1 from `InsideGanonCastle_Dungeon_Barrier_Count` (default 6). At 0, `BarrierRemove_All` plays the barrier movie and sets `InsideGanonCastle_IsAllBarrierClear`. The central barrier (`Logic/InsideGanonCastle_Level_Room_01_Prefab_75af`) reads `InsideGanonCastle_IsAllBarrierClear` and `HavePlayedEvent.Dm_InsideGanonCastle_0090`. Each trial room's AINB reads its own `BarrierRemove_<X>` flag. The tower checks `Defeat_Ganon` `Step05`, which Ganondorf's arrival sets.

## Design

Settings (OoTR names), defaults keep the current game:

- `bridge`: `'vanilla'` (default) or `'medallions'`;
- `bridge_medallions`: 0–6 (default 6);
- `trials`: 0–6 (default 6);
- `trials_random`: when on, the count is random (0–6).

They change the RNG key only when not at their defaults, so old seeds stay the same.

**Bridge = medallions (game).**

- **Attempt 1 failed.** Rewriting the two BoolExps in GameDataList did nothing in game: 34a and 34c showed no bridge, even with 0 medallions. When the preset moved `Defeat_Ganon` to `Ready` and `Step01` (34f), the bridge appeared. The game does not use the BoolExp `Values` for these quest expressions. `byml.dump` keeps its `big_endian` mode.
- **Attempt 2.** Right after the grant in each of the nine dungeon-reward scenes (`gifts` rows with `shuffle_dungeon_rewards`), a decision diagram of `PouchSystemActor.EventQueryIsExistInPouch` switches asks for the six `Item_Medal_*`. Case 0 means the item is held. With N or more, the flow moves `Defeat_Ganon` to `Ready` and then `Step01`, then goes on. With N = 0 the quest moves on leaving home (`Dm_Kokiri_0045`).
- **New `evfl_append` tools.** `SwitchSpec` and `add_queries` appeared for this.
- **Zelda's Light Arrows scene.** `AllSage`'s `Defeat_Ganon Step01` call becomes a second `AllSage Complete`. If Zelda's scene came after the bridge, that call could move the quest back to Step01, and the bridge no longer needs it.

**Trials (game).** At the start of `GanonCastle_Adult_Field_Rainbow`, the bridge scene that plays once before Link can enter the castle, add these actions for each skipped trial:

- set `InsideGanonCastle_Dungeon_BarrierRemove_<X>`;
- set `InsideGanonCastle_Dungeon_Barrier_Count` to the number of active trials;
- with 0 trials, also set `InsideGanonCastle_IsAllBarrierClear` and `HavePlayedEvent.Dm_InsideGanonCastle_0090`.

The actions are built with `evfl_append`. They set game data only, so no subflow lists change. The quest step `Step04` is not set: nothing reads it.

**Logic.** The World gets `bridge`, `bridge_medallions`, `trials` and `skipped_trials`. OoTR's `has_medallions` counts the medallion *items*, so the fill must know where they really are. The dungeon-reward shuffle (`_shuffle_rewards`, seeded by the settings alone) is now computed before the fill, and its items go into the fill's base. Nothing else counts reward items: the Door of Time and LACS read the bosses through `REMAKE_HELPERS`, so their results do not change.

**Which trials.** OoTR picks the active trials at random. Here a separate RNG stream comes from the seed and settings: `_rng(settings, -2)` gives the count (when random) and the sample.

**Spoiler.** The Settings section lists the bridge and the trial count, and a new section names the active trials.

**Site.** A "Rainbow Bridge Requirement" select (Vanilla / Medallions), a 0–6 medallions slider, a "Random Number of Ganon's Trials" switch, and a 0–6 trials slider.

## Result (2026-11-25)

Attempt 2 passes in game: 34a (bridge with 3 of 3), 34b (no bridge with 2 of 3), 34c (bridge with 0; no central barrier with 0 trials) and 34d (only the Forest trial left). In the batch, the preset's gifts stand in for a reward scene; the check after a real reward grant is the same chain.

## Test in game (batch 34, with the full skip and a teleport)

- 34a: bridge 3 medallions (the longest program); the preset gives 3 medallions and puts adult Link in front of the bridge. The bridge must appear.
- 34b: the same with 2 medallions. No bridge.
- 34c: trials 0 after the bridge. Inside, the central barrier must be gone.
