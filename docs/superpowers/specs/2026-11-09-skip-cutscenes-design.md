# "Skip cutscenes" option — Design

Status: draft for approval. Part of randomizer v1 (branch `feat/v1`, base design in `2026-11-08-oot-remake-randomizer-design.md`).

## 1. What it is and why

The user tests randomizer seeds in Lichii, always starting new games. Long cutscenes and story conversations waste a lot of time:

- The game lets some of them be skipped with a button.
- Others have to be watched in full. The one the user mentioned is **the first scene**, the Kokiri Forest introduction.
- Conversations cannot be skipped.

The user wants one more option on the page, **"Skip cutscenes"**, to play faster. First for acceptance testing and later on any seed.

## 2. Goals, non-goals and anti-goals

**Goals**
- With the option enabled, the Kokiri Forest introduction can be skipped with the game's skip button.
- With the option enabled, story scenes built as event flows play without their steps that only display:
  - dialogue;
  - camera and animations;
  - waits and visual effects.
  All steps that change the game state are kept.
- The story advances exactly as if the scene had been watched:
  - the same game flags are set;
  - the same items and songs are received;
  - the player ends up in the same place and zone.

**Non-goals**
- Normal character conversations (shops, villagers, minigames), Navi's messages, signs and the texts shown when receiving an item are not touched.
- Text is not sped up and video speed is not changed.
- The end credits and the title screen are left as they are.

**Anti-goals (a failure even if it "works")**
- A game getting stuck or losing an item, song or flag because a scene was skipped.
- Enabling the option changing where items are placed: the same seed must give the same placement with the option enabled or not.
- Writing to the `.nup` or putting game files in the repository.

## 3. Verified facts (exploration of 2026-11-09)

- **Event flows:** `romfs/Event/EventFlow/*.bfevfl.zs`, 914 files (487 with the `Dm_` prefix). The format is BFEVFL with the `EVFL` flowchart at `u64(u64(0x28))`.
  - Actors take 0x38 bytes each and events 0x30.
  - An action event (type 0) stores the `u16` of the next event at `+0x0A`, and the actor and action indices at `+0x0C` and `+0x0E`.
  - A switch (type 1) stores its case list at `+0x18`; each case takes 0x10 bytes, with the value (u32) and the event (u16 at +4).
  - A fork (type 2) stores its branch list (u16) at `+0x10` and the join at `+0x0C`.
  - A join (type 3) and a subflow (type 4) store the next one at `+0x0A`.
  - Entry points take 0x20 bytes, with the main event at `+0x1C`.
  - There is an exploration reader in the session scratchpad (`evflib.py`). It is disposable and must be rewritten with tests.
- **Event settings:** `RSDB/EventSetting.Product.111.rstbl.byml.zs` has 2380 rows. Each one carries its `EventSettingComponentList`, its flow and its entry point.
- **Skip lock:** only 3 component lists include `SkipSetting/DisableSkip` (`IsDisableSkip: True`):
  - `Dm_Kokiri_0000`: the introduction, which is the scene the user mentioned;
  - `Dm_Title_0005`;
  - `Dm_StaffCredit_0005`.

  They are in `Event/EventSetting/EventSettingComponentList/<name>.engine__event__EventSettingComponentList.bgyml`, in uncompressed BYML.
- **Most used actions across all flows** (by number of occurrences):

  | Action | Count |
  |---|---|
  | `Npc_EventStarter.EventTalk` | 5038 |
  | `EventWait` | 3226 |
  | `GameDataActor.EventTriggerSetGameDataBool` | 3058 |
  | `EventCamera.EventMoveToTargetPosCamera` | 2086 |
  | `Player_Event.EventPlayerPlayASForFlowchart` | 1493 |
  | `EventTalk` of specific characters | many |

  Those that change the game state include: `EventTriggerSetGameData*`, `EventTriggerAddOrSubGameDataInt`, `PouchSystemActor.EventTriggerAddOrRemovePouchContent`, `EventTransition`, `EventReserveBancChange`, the `Warp*` actions, `EventTriggerRequestAutoSave` and `EventTriggerSetEventBool`.
- Scenes can be trimmed without touching the RSTB table **if the file does not change size**. For that it is enough to rewrite the event indices (u16) in place.

## 4. Behaviour

### 4.1 Option
- New setting `skip_cutscenes: bool` in `Settings`, off by default.
- On the page it is a "Skip cutscenes" checkbox, in the General tab.
- It is saved in the user's configuration like the other options.
- It is **not part of the RNG settings key** (like `spoiler`): it does not change placement.
- The spoiler log states whether it was enabled.
- In Vanilla key item mode with the option enabled, the mod is still generated, with only the scene changes. The "no changes" warning only appears if there are no changes at all.

### 4.2 Unlocking the introduction skip
- With the option enabled, the mod includes `Dm_Kokiri_0000…EventSettingComponentList.bgyml` without the `SkipSetting` component. Its RSTB entry is not touched: the new file is smaller, and the RSTB value is an upper bound for the buffer. If it ever came out larger, generation fails.
- `Dm_Title_0005` and `Dm_StaffCredit_0005` are not touched.

### 4.3 Trimming story scenes
- **Which scenes:** a fixed, versioned list of "story" flows/entry points in `randomizer/data/`.
  - It is built by a tool (`tools/`) from the prefixes `Dm_`, `Get_Stone*`, `Sage*`, `Meet_*`, `Goto_*`, `MelodyGet_*`, `SubEvent_Get*`, `Get_Epona`, `DoorOfTime`, `OpeningEvent` and the story entry points of the Zelda, Impa, Saria, Darunia, Ruto, Nabooru, Rauru and Sheik flows.
  - It is then reviewed by hand.
  - Normal character conversations are left out.
- **Which steps are removed:** only actions from an **allowlist of display-only actions**:
  - dialogue (`EventTalk`, speech bubbles);
  - camera;
  - animations (`EventPlayAS`, `EventPlayerPlayASForFlowchart`);
  - waits (`EventWait`);
  - turns and gazes;
  - depth of field and lighting;
  - vibration;
  - sound and music;
  - Navi movements.

  Any action not in the allowlist is kept. Fades, transitions, warps and zone changes are always kept.
- **Dialogues with a choice:** an `EventTalk` whose result is read by a later decision node (switch) is **not** removed.
- **How:** every index that points to a removed action is rewritten in place to point to the first kept action that follows it, in a chain. That includes:
  - the "next" of actions, joins and subflows;
  - the switch cases;
  - the fork branches;
  - the main event of the entry points.

  No event changes size or position, so the file keeps its size and there are no RSTB changes. If a removed chain ends in "end" (0xFFFF), it points to "end".

### 4.4 Output
- The modified flows are recompressed into `romfs/Event/EventFlow/...`, like the banc files.
- Generation remains deterministic: the same seed and options give the same bytes.

## 5. Tests

- Unit tests:
  - BFEVFL reader and rewriter: round trip with no byte-for-byte changes;
  - a trim that keeps all the state-changing actions at every entry point;
  - settings key without `skip_cutscenes`;
  - checkbox on the page.
- **In-game tests in rounds** (test mods like the `TestBatch` ones), starting with:
  1. the introduction (skip with the button; see §6b);
  2. the Deku Tree up to the Kokiri Emerald, with phase 1;
  3. Zelda and Zelda's Lullaby;
  4. the sages.

  Each round has a guide in `docs/` with what must be received and where the player must end up.

## 6. Done when

- The introduction is skipped with the button.
- A new game with the option enabled reaches the Kokiri Emerald and Zelda's Lullaby without story dialogue and without losing anything.
- The tests pass.
- The acceptance seed is regenerated with the option and the user plays it.

## 6b. Decisions made after review (my decision, not the user's)

- **Introduction skip, first as a test.** It is not known whether the engine's skip button runs or skips the actions that remain in `Dm_Kokiri_0000`.
  - The first round is only the introduction, with the skip unlocked.
  - The user checks that everything afterwards is still the same: Navi, the talk with Saria and the entrance to the Deku Tree.
  - If anything is lost, the introduction is trimmed as in §4.3 instead of unlocking the skip.
- **The allowlist is extended in phases, each one tested in game before the next.**
  - **Phase 1:** dialogue (`EventTalk` without a choice, bubbles), waits (`EventWait`), camera, turns and gazes, depth of field and lighting, vibration and development comments (`EventDemoProductSupportComment`).
  - **Phase 2:** player and character animations (`EventPlayAS`, `EventPlayerPlayASForFlowchart`, `EventPlayerMove*`), sound and music, and Navi movements. This phase only goes in if phase 1 breaks nothing. Animations can move the player to a mark, so they are kept apart.
- **Forks and joins:** never removed or restructured. If trimming a fork branch would leave it empty (pointing directly to the join or to "end"), that branch is not trimmed.
- **Chests with randomizer events:** the current fill does not edit flows; it only removes `GetEventName` in the banc files. Trimming is the only BFEVFL edit, so there is no conflict. Trimming `Get_StoneOfForest_GetSword` and similar only removes their visual part.
- **What the tests check:** for each entry point, the trimmed graph must equal the original with the removed nodes "contracted". That is, every path of the original, removing the allowlisted actions, is a path of the trimmed one and vice versa. In addition, no action outside the allowlist disappears.
- **Compression:** flows are read and written with the same `ZsCodec` (dictionary according to the path) as the banc files. They go into the mod at the same path `romfs/Event/EventFlow/<name>.bfevfl.zs`. The settings `.bgyml` files go uncompressed.

## 7. Left to whoever builds it

- The exact list of story entry points and allowlisted actions, starting from §4.3 and the data.
- How to detect which switch depends on a dialogue with a choice (for example, dialogue-result queries immediately after the `EventTalk`).
- If an entry point turns out to be dangerous to trim in testing, it is taken off the list: it is better to see a scene than to block the game.

## 8. Extension 1 (2026-11-09, approved by the user)

Result of round 2 in game: it reaches the Deku Tree with no crashes or losses. But conversations still appear that the user wants removed, such as Mido blocking the way or the Z-targeting tutorial. They were out because of the non-goal in §2 (character conversations and Navi messages).

**New rule, which replaces that non-goal:**
- **Conversations that trigger by themselves or block the way are trimmed**, even if they are in character flows (`Npc_*`) or Navi flows (`NaviHint` and similar).
  - Examples: Mido blocking, the Kokiri who explain controls, forced Navi prompts (for example `NaviLockOnHint`), Saria on the bridge, Zelda in the garden, Impa.
- **Those chosen by the player stay:**
  - talking to a character by walking up to them;
  - shops;
  - minigames;
  - asking Navi for a hint with her button.
- **What the conversation checks or gives is kept:**
  - checks (switch), items and flags are never removed;
  - all the rules of §4.3, §6b and the final review still apply: loops, dialogues with a choice and pointers to "end".
- **Scope of this extension:** childhood first (Kokiri Forest, Deku Tree, Hyrule Field, Market, Castle and Kakariko). The rest will come in another extension, after testing this one.
- **How they are chosen:** a hand-reviewed list of (flow, entry) pairs in `cutscenes.json`, supported by a tool that finds the forced conversations (how they are triggered in the banc files and in EventSetting).
  - When in doubt, a conversation is left alone.
- **In-game test:** `TestScenes3`, from a new game to the Deku Tree and the Castle/Kakariko.

### 8.1 Round 2 (2026-11-09, after playing the acceptance seed)

- **Gameplay hints are never trimmed.** The Deku in the Deku Tree who gives the order clue lost its conversation because `Get_StoneOfForest` was "*".
  - `tools/build_cutscene_list.py` has a `KEEP_TALKS` list of (flow, entry) pairs that stay: the Dekus in the Deku Tree, Navi at Darunia's door, the altar of the stones, Navi hints in dungeons, the Deku target minigame and showing masks.
  - A "*" flow with any of them becomes the list of its other entries. The story-flow entries that are called as a subflow also drop out, in a chain. The trimming already protects everything reachable from an unlisted entry, so `cutscenes.py` does not change.
  - When in doubt, a talk is left alone.
- **The Kokiri who blocks the exit** (`Npc_Kokiri_007_Child`): `Near_FirstReaction` is added (a bubble launched by a zone trigger). It is a single bubble that ends in "end", so the pointer-to-end rule keeps it. What the Kokiri keeps saying when bumped into are dialogues followed by a switch (chance, flags), which the dialogue-with-a-choice rule keeps; changing that means changing a safety rule and is left to be decided.

### 8.2 Round 2b (controller decisions)

- **Dialogues with a choice, linear rule:** a dialogue followed by a switch is only a question if the switch's query reads the answer. That is if it contains `TalkChoice` (the same criterion as the fork/join rule) or `Select` (`EventQueryFairyFountainSelectSpecialAbility`). Chance switches (`RandomChoice*`) and flag switches no longer count.
- **Forks:** the original game has no fork branch that goes straight to the join, or that reaches it without actions: 0 of 12369 branches across 914 flows. The rule in §6b stands, so the Great Deku Tree lines that run in parallel with an animation are kept.
- **Frozen Link:** scenes whose join waits for animations that are not removed are not trimmed (`FROZEN_LINK` in the tool): `Dm_Kokiri_0060/0130/0145/0155`, `Dm_Deku_0003`, `Dm_HrlField_0020`, `Dm_HrlCastle_0000/0020(.110)/0035/0050`, `Dm_LonLon_0020` and `Dm_Kakariko_0010`.
