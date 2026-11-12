# Full cutscene skip — Design

Date: 2026-11-11 · Status: draft for approval. Replaces how the "Skip cutscenes" option works; the earlier design is `2026-11-09-skip-cutscenes-design.md`, and everything it learned (§3, §6b, §8) still holds as background.

## 1. What it is and why

The user plays randomizer seeds in Lichii. In a randomizer the story does not matter. Today's "Skip cutscenes" only removes the display-only steps of some childhood scenes (dialogue, camera, waits), so a lot still plays:
- 12 scenes play in full, because trimming them left Link frozen (`FROZEN_LINK`);
- the Great Deku Tree still talks;
- adult-era scenes and later dungeons are untouched.

The user wants, in their words: every cutscene and every conversation skipped, without having to skip anything by hand.

## 2. Goals, non-goals, anti-goals

**Goals (the user's rules)**

| Situation | With the option on |
|---|---|
| Story cutscenes (intro, Deku Tree death, Zelda, sages, bosses, arrivals…) | Do not play. Their effects happen and the player ends up where the scene would have left them. No button press needed. |
| Conversations that start by themselves or block the way (Mido, Navi interrupting, Kokiri explaining controls…) | Do not play. |
| A character who gives an item in a conversation (Saria and the Fairy Ocarina) | The whole scene and conversation disappear; the item is simply received. |
| Songs | Same as items: no scene and no playing it back; the song is simply learned. |
| Conversations the player starts (walking up to a character), shops | Unchanged. |
| Minigames | Their conversation stays. |
| Opening a chest | Unchanged (Link raises the item, "You got…" text). Showing the right item there is a separate project. |

- Scope: the whole game, childhood and adult, rolled out zone by zone with a test batch each (§6).
- The option keeps its name and checkbox ("Skip cutscenes"); it simply becomes the full skip. *My call:* no separate "light" mode; the old trimming is replaced.

**Non-goals**
- The end credits and the title screen.
- Gameplay hints the player asks for (Navi's button, Deku hints in the Deku Tree, `KEEP_TALKS`) stay.
- Item-get presentation for chests (separate project).

**Anti-goals (a failure even if it "works")**
- The game getting stuck, or Link frozen, after a skipped scene.
- Losing an item, song, medallion, stone, flag or warp because a scene was skipped; ending up in the wrong place or zone.
- The option changing item placement: same seed, same placement with it on or off.
- Writing to the `.nup` or committing game files.

## 3. Facts found (2026-11-11)

- 519 story flows (prefixes `Dm_`, `Get_`, `MelodyGet_`, `Sage`, `Meet_`, `Goto_`, `SubEvent_Get`, `DoorOfTime`, `OpeningEvent`) use 496 distinct action types. The most common are display-only: `EventWait` (2868), `EventTalk` (1424), camera moves (1239 + 476), `EventPlayAS` (1186), developer comments (883), player animations (755), depth of field (707). The ones that change the game are few and recognisable: `EventTriggerSetGameDataBool` (549), warps (`EventWarpToTargetPosAndRot` 540, `EventWarpToTargetActor` 291, `EventPlayerWarpTo*` 300+), `EventTransition` (226), fades (334), `EventTriggerSetEventBool`, `PouchSystemActor.EventTriggerAddOrRemovePouchContent`, autosave.
- Example, `Dm_Kokiri_0155` (Saria gives the Fairy Ocarina): 92 events and several entry points (`EntryPoint0`, `ready`, `C01`–`C04`), the cuts chained through subflows and forks. What matters: event 51 (`AddOrRemovePouchContent` of `Item_Ocarina_Fairy`), the fades and the player warp (event 40). Everything else is animation, camera, lighting, waits and developer comments.
- **Why Link froze before:** in those scenes a join waits for several parallel branches (for example an animation and a dialogue line); removing one branch's content while the join still waited for an animation left the scene unable to end. The old trimming never removes forks or joins.
- **"Mark as already seen" route:** the flag list (`GameData/GameDataList.Product.110.byml.zs`) is big-endian BYML with hashed names, which the project cannot read or write yet, and the scenes' side effects (items, warps) would still have to be reproduced. Not chosen (§4.1).

## 4. Behaviour

### 4.1 Method: effects-only scenes (my call)

For each targeted entry point, the scene is rewritten **in place** so that it runs only its effects, in order, as a straight line:

- Walk every path the scene can take from the entry point, **including into fork branches and into subflows to other entry points of the same flow**, and collect the *kept* actions in the order a playthrough would meet them (fork branches one after another, in branch order, then what follows the join).
- Switches are kept, with each case reduced the same way, because they read the game state (they decide, for example, whether an item was already received).
- Forks and joins are dropped: nothing points to them any more, so nothing can wait on them.
- Every kept action's "next" is rewritten to the next kept action; the entry point's main event to the first one. As today, only u16 indices change, so the file keeps its size and the RSTB is untouched. If a scene's straight line cannot be expressed by relinking existing events (for example, a kept action appears on two paths that need different "next" values), that scene is left as it is and reported by the tool.

**Which actions are kept** is a versioned table in `randomizer/data/` (`keep` / `drop` / `review` per action type), built by a tool over all flows and reviewed by hand:
- **Keep:** game data and event flags, pouch content (items, songs), dungeon rewards, transitions, banc changes, warps of the player and of the actors that the rest of the game needs in place, autosave, the final fade-in.
- **Drop:** dialogue (`EventTalk`, bubbles, message dialogs), camera, animations, waits, look-at and turn, depth of field, lighting, palette, rumble, sound, music, voices, effects, Navi movements, developer comments, "do nothing".
- **Review (decided per type during the spike):** actions that put actors or the player into or out of the scene (`EventTriggerParticipateEvent`, `EventGoOffstageForUser`, `EventPlayerEventStartWithDrawn`, unequip, model bind), and anything not in the first two lists. Unknown types default to *keep*: a visible step is better than a broken game.

### 4.2 Items and songs given in a scene

- The `AddOrRemovePouchContent` action is kept, so the item arrives. Its "get" presentation (Link raising the item) is turned off when the action has a boolean parameter for it, by rewriting that parameter in place; otherwise it stays.
- Songs: the learning action is kept; the play-along (the player repeating the notes) is dropped.
- NPC gift randomization (gifts project) keeps working: it changes the `Actor` parameter of that same action, which is still there.

### 4.3 Which scenes and conversations

- The existing list (`cutscenes.json`, 488 story flows plus the reviewed forced conversations) is extended to the whole game, with the same rules as §8 of the earlier design: forced conversations yes, player-started conversations no, `KEEP_TALKS` stay, minigames stay.
- NPCs who give an item or teach a song in a conversation the player starts (Saria, Malon, the windmill man…): the conversation itself is skipped and the item or song is received, as the user asked. Their entry points are listed explicitly in the data, reviewed by hand.
- The intro keeps its unlocked skip from today as a fallback, but its entry point is also rewritten, so nothing needs to be pressed.

## 5. Testing

- **Unit tests:**
  - the rewrite of synthetic flows (forks, joins, switches, subflows, loops);
  - for every targeted entry point of the real game, every kept action reachable before the rewrite is still reachable after it, in the same order along each path;
  - no fork or join is reachable after the rewrite;
  - same placement with the option on or off.
- **In-game rounds**, each with a test mod and a guide (Spanish for the user in `local/`, English in `docs/`). Each round checks that nothing freezes, nothing is missing (items, songs, stones, medallions, flags that open the way) and the player ends in the right place.

## 6. Rollout

1. **Spike (throwaway):** four representative scenes, rewritten by hand with the rule of §4.1 and tested in game: Saria's ocarina (`Dm_Kokiri_0155`), the Kokiri Forest scene with Saria, Mido and Navi (`Dm_Kokiri_0060`, a `FROZEN_LINK` scene), Zelda in the garden (`Dm_HrlCastle_0050`) and one song (Saria's Song or Epona's Song). It settles the "review" actions of §4.1 and whether the item-get presentation can be turned off. If the method fails, stop and come back to the user.
2. **Childhood** (Kokiri Forest, Deku Tree, Hyrule Field, Market, Castle, Lon Lon, Kakariko, Death Mountain, Goron City, Zora's Domain, Jabu-Jabu, Dodongo's Cavern).
3. **Adult** (Temple of Time, Sacred Forest Meadow, the temples, Gerudo Valley and Fortress, Desert, the sages).
4. **Ganon's Castle and the ending** (except the credits).

## 7. Done when

- A new game with the option on reaches the end without any story cutscene or forced conversation and without pressing skip, losing nothing and never freezing.
- Player-started conversations, shops, minigames and chest openings behave as in the original game.
- The tests pass and the acceptance seed is played with the option on.

## 8. Decisions after the builder check (my calls)

1. **Scenes that relinking cannot straighten.** The goal stays "every scene", so leftovers are fixed, not accepted. When relinking existing events is not enough (an event shared with an entry point that is not targeted, or a kept action that needs different "next" values on different paths), the rewriter may **duplicate events into new slots and grow the file**, updating the RSTB as is already done for the banc files. Events reachable from untargeted entry points (`KEEP_TALKS`, player-started talks) are never changed in place; the targeted path gets its own copies instead. Subflows into another flow file are kept as calls; that other file is rewritten too if its entry is targeted.
2. **Switches that read something a dropped action produced.** A switch is classified by its query:
   - reads the game state (flags, items, counts): kept, every case reduced;
   - reads a dialogue answer (`TalkChoice`, `Select`), an animation or camera state, or random chance: collapsed to one case, chosen per scene in the data. The default is the case that reaches the scene's kept effects (the "accept" path, the one that progresses the story). If no single case does, the scene goes to manual review;
   - a polling loop on a display state (switch → wait → switch) is dropped with its wait.
3. **Scenes that are not event flows** (boss intros, timeline-only or actor-coded scenes): not covered by this method. The spike and each round list the ones still seen; how to skip them, if possible, is decided with the user once they are known. "Done when" (§7) applies to event-flow scenes plus that list.
4. **Fork branches that depend on each other.** The tool flags a fork where one branch reads a flag, state or event value that a sibling branch sets; such a scene goes to manual review instead of using file order. The spike includes `Dm_Kokiri_0060`, a scene with waiting joins.
5. **Gift randomization and the rewrite** touch the same files independently: the rewrite only changes event indices (and, if it grows, appends events); the gift swap only changes the `Actor` string parameter of the pouch action, which the rewrite always keeps. Order: rewrite first, then the gift swap on the result.
6. **Spike gate.** After the spike, work stops until the user has played it and given a verdict. Building the keep/drop table and the rewriter with unit tests may go on in parallel, but nothing more goes to the user to test. A round passes only if nothing freezes **and** every expected item, song, reward and flag is there **and** the player ends in the right place.
7. **Item-get presentation for NPC gifts.** Preferred off ("the item is simply received"). If the pouch action has no parameter for it, the spike tries a silent alternative (the same action used for pouch changes without presentation, if one exists in other flows). If none exists, the presentation stays for now and that is reported to the user; it is not a blocker.

## 9. Left to the builder

- The exact keep/drop/review table and the full list of entry points, starting from §4.1, §4.3 and the data.
- How to order fork branches when their order matters (default: branch order in the file).
- How to detect the item-get and song play-along parameters.

## 10. Spike build notes (2026-11-11)

Built on branch `feat/full-skip` (plan `docs/superpowers/plans/2026-11-11-full-cutscene-skip-spike.md`); test mod `TestScenes4`, guide `docs/test-scenes-4.md`.

Decisions taken while building (each with what it costs if wrong):
- **Classification order:** action names with `GameData`, `EventBool` or `Pouch` are kept before the drop list is checked, and query names are checked against the state list before the collapse list. Cost: a few waits on flags stay in scenes.
- **Song play-along** (`EventPlayerPlayOcarina*`) is dropped. Cost: a song that needs that step to be granted would be lost; the spike checks Zelda's Lullaby.
- **Collapsed switches** skip cases that lead back to the switch (a re-asked question) and take the first case with its own effects; a kept node that can never reach the end is a `loop` error. Cost: a scene whose only effect was behind a re-asked question would lose it.
- **Fades:** a kept fade-out with no later fade-in is accepted only if the original scene also had none after it (the game fades back at event end). Cost: a black screen the test lets through.
- **The spike's song** is Zelda's Lullaby (`Dm_MelodyGet_Zelda`), not Saria's or Epona's, because it is on the same play path as Zelda's scene.
- **`Dm_Kokiri_0060`** is the Kokiri Forest scene with Saria, Mido and Navi, not the Deku Tree's death.

Must be done in phase 2, before rewriting more scenes:
- Check external callers (EventSetting entries, timelines, cross-file subflows) before relinking an entry point that a scene inlines; the spike relinks the cut entries of its four scenes (no cross-file callers exist for them).
- Assert "same order along each path" in the real-data tests (§5); the spike only checks that kept actions stay reachable.
- Implement the fork-dependency flag of §8.4 before scenes that keep waits or state switches (none of the four spike outputs keeps any).
- Small robustness gaps in the rewriter: a fork whose join is END, a branch jumping back to its own fork, a join that does not match the open fork; synthetic tests for the protected set and for `apply_rewrite` refusing a failed rewrite.

## 11. Spike verdict (2026-11-11)

Played by the user from a new game to Zelda's Lullaby with `TestScenes4` only.

**The method works on event-flow scenes.** No freeze, no black screen, nothing missing:
- `Dm_Kokiri_0155`: the Fairy Ocarina is received and the scene is gone, but a first part of Saria's scene on the bridge still plays. That part is `Dm_Kokiri_0150`, a timeline (see below).
- `Dm_HrlCastle_0050`: the conversation that gives Zelda's Letter is skipped and the letter is received.
- `Dm_MelodyGet_Zelda`: the song is skipped and received.
- `Dm_Kokiri_0060`: the user still saw "the conversation with Mido and Saria"; which file played it is not known yet (candidates: the timeline `Dm_Kokiri_0050`, or Saria's NPC flow `GuideToDekuTree_BeforeTalkMido`).

Everything else the user saw still plays, as expected, because it was not in the spike: the intro, the Deku Tree and Navi, the targeting and shield tutorials, Mido blocking the way, entering the Deku Tree, the Deku Tree after the boss, the Kokiri at the forest exit, Malon, Zelda's first scene and conversation, a second Zelda scene, and a scene with Zelda after the letter.

**Scenes that are not event flows (§8.3), now measured:**
- **261 of the 487 `Dm_*` flow files are timelines** (BFEVFL with one `TLIN` timeline and no flowchart), among them the intro `Dm_Kokiri_0000`, `Dm_Kokiri_0050`, `0070`, `0090`, `0140`, `0150`, `0158`, Impa after the letter `Dm_HrlCastle_0060`, and every boss intro and outro. The effects-only rewriter cannot touch them.
- **26 scenes are pre-rendered movies** (`Event/Movie/*.webm`, `RecordMovieTimelineEvent`), among them `Dm_Kokiri_0000`, `Dm_Kokiri_0095`, `Dm_Kokiri_0160` and `Dm_HrlCastle_0045`.
- Timelines hold presentation only: a scan of their action names finds no flag, game-data or pouch action. The exceptions with a lasting effect are 3 warps (`EventWarpToTargetPosAndRot` in `Dm_DeathMtTrail_0020`, `Dm_LakeHrl_0010`, `Dm_TimeTemple_0050`; `EventWarpToHomeMatrix` in `Dm_FinalBattle_BossIn`), boots changes and one loading fade-out (`Dm_DeathMtTrail_0030`).
- The timeline's length is a float in frames at `TLIN + 0x10` (for example 3014 in `Dm_HrlCastle_0060`), followed by the counts of actors, actions, clips, one-shots, subtimelines and triggers.

**Open for the user:** how to skip timelines and movies (proposal: shorten the timeline to almost no frames, keeping the warps, and test it on `Dm_Kokiri_0150`, `Dm_Kokiri_0050` and `Dm_HrlCastle_0060` before phase 2).

**Timeline spike (TestTimelines, built 2026-11-11):** `randomizer/timeline_skip.py` cuts a timeline right after a fade-in that starts in its first 60 frames (else after 1 frame) and moves the clips in `LASTING` (warps, boots, music, Navi's appearance and colour, NPC schedules, time of day, heart refill) to just before the new end; subtimelines (`_Effect`, `_Env`) are shortened too. Applied to `Dm_Kokiri_0150` (6108 → 60 frames), `Dm_Kokiri_0050` (1178 → 15) and `Dm_HrlCastle_0060` (3014 → 60), on top of the four TestScenes4 scenes. Guide: `docs/test-timelines.md`.

**Timeline verdict (2026-11-12):** shortening works. All three are cut, Link regains control, and music, Navi (with its colour) and positions are right afterwards. `Dm_Kokiri_0050` is a short scene with Navi just outside Link's house, before Saria. Timelines are settled: phase 2 shortens every timeline it reaches the same way. Movies remain open.

**Movies are timelines (2026-11-12):** each movie's EventSetting derives from `RecordMovieTimelineEvent`; 18 of the 26 have a timeline of their own with only voices, rumble, fades and (intro) the title card, launched by an `EventTransition` like any other scene. The other 8 have no flow: the Royal Family Tomb wall (`Dm_MelodyGet_Sun_*`, launched from `GimmickFlow_RoyalFamilyTomb`) and the title screen (`Dm_Title_*`). `Dm_Kokiri_0000_Effect` is referenced but not in the game. **Movie spike (TestMovies):** `Dm_Kokiri_0000` (intro, 9255 frames), `Dm_Kokiri_0095` (Deku Tree after Gohma, 7040) and `Dm_HrlCastle_0045` (Zelda's story, 2449) cut to 1 frame, on top of TestTimelines. Guide: `docs/test-movies.md`. **Verdict (2026-11-12): no.** The intro played in full, rumble included, so a movie runs on its own clock and ignores the timeline's length.

**Movie spike 2 (TestMovies2):** `randomizer/movie_skip.py` removes the `EventTransition` that starts the movie from the flow that calls it (`OpeningEvent` for the intro, `Dm_SY_BancChange_EscapeDungeon` for `Dm_Kokiri_0095`, `Goto_HyruleCastle` for `Dm_HrlCastle_0045`), relinking what pointed to it to what came after. Each movie sits in a chain of scenes, so the neighbours are skipped too: `Dm_Kokiri_0080` (the Deku Tree's speech) → movie → `Dm_Kokiri_0090` (Ganondorf vision, timeline), and `Dm_HrlCastle_0035` (Zelda's first scene) → movie → `Dm_HrlCastle_0050`. `0080` and `0035` are rewritten effects-only, `0090` shortened. Guide: `docs/test-movies-2.md`. **Verdict (2026-11-12): works.** The intro, the Deku Tree's speech (movie included) and Zelda's story are gone with no freeze; the letter and the Lullaby still arrive. The loading screen after the intro is longer, since the movie used to hide it. Scenes still seen were simply not in the batch (`Dm_Kokiri_0030`, `Dm_Kokiri_0130`, `Dm_Kokiri_0140`, `Dm_HrlCastle_0030`).

**Spike conclusion:** the three methods are proven in game: effects-only rewrite (event flows), shortening (timelines), removing the starting transition (movies). Phase 2 applies them to the whole childhood.

## 12. Phase 2 build notes (2026-11-12)

Childhood full skip built on branch `feat/full-skip` (`randomizer/full_skip.py`, data `randomizer/data/full_skip.json`, wired in `randomizer/generate.py`; the spoiler gets a "Cutscenes not skipped" section). Test mod `Rando_FullSkipChild1`, guide `docs/test-full-skip-child.md`.

**Counts (the real report for phase 1).** Targets: 93 flow files with 181 entry points, 31 timelines, 11 movies. Report: 108 applied, 16 unchanged, 29 fell back to the old trimming, 28 left untrimmed because the file was only partly rewritten, 14 files not written at all (the old trimming applies). 264 report lines; the full skip changes 335 files.

**Decisions taken while building (each with what it costs if wrong):**
- **Kind 5 = a subflow switch that runs its call; kind 6 = a result.** Cost: a scene follows the wrong case; the checker cannot see it, so the game test must.
- **Copies go into donor slots; the game data has no donors for some.** Growing a file needs a relocation-table writer, so every copy that found no donor falls back. Cost: shared paths stay unskipped.
- **Untargeted entries outside `Dm_*` are protected** (never changed in place). Cost: some forced talks stay.
- **Siblings are external:** a sibling file never relinks another sibling's entries.
- **New END cases are refused:** a rewrite that would add a case to END is rejected. Cost: 5 scene files stay (`Dm_DeathMtTrail_0010`, `Dm_DodongoCave_0010` and `.110`, `Dm_Goron_0028`, `Dm_Goron_0040.110`).
- **Chatter is excluded** except `FORCED_TALKS_ALLOW` (four forced talks).
- **Partly written files are not old-trimmed**, to avoid mixing two edits. They are reported as "untrimmed".

**Fell back or left alone:** dozens of forced conversations that share events with player-started ones (Kokiri blocking the exit, Mido's Talk, Zelda and Malon talks, castle guards; see the spoiler: 29 entries shortened as before, 28 playing in full); `Dm_Kokiri_0045` (fork dependency on `KokiriForest_LinkHouseDoor_Open`); `Dm_InsideJabu_Jabu_0050` (conflict); the Royal Family Tomb files; one "no result" case (event 28, hash `0xa6da0479`, in `SubEvent_GetEponaSong`).

**What the test batch must decide:**
1. Do the kind 5 and kind 6 readings hold (no scene takes a wrong branch)?
2. Navi's colour after `Dm_Kokiri_0030`, and whether the longer loading screen after the intro is acceptable.
3. Whether Link still raises gifted items (section 8.7).
4. Whether the fallback list is short enough, or the shared conversations need growing files or banc EventStarter indexing.

**Childhood test 1 verdict (2026-11-12, `docs/test-full-skip-child.md`):** nothing lost, nothing frozen; every item, song, stone and flag of the childhood arrived and the Door of Time opens. Still seen: the targeting and shield tutorials, Mido's first block, the exit Kokiri, some owl talks, the Great Fairy talk, King Zora not moving aside (animation dropped), a black-screen walk at Zora's Fountain. User decision: boss intros and defeats are kept. **Round 2 (`docs/test-full-skip-child-2.md`):** boss timelines and boss entries untargeted; King Zora keeps his EventPlayAS (`skip_actions.json` actor_actions); `Dm_ZoraFountain_0000` back to the old trimming; owl scenes, `Npc_Kaepora_LakeHylia`, Farore's Great Fairy and the Deku Shield tutorial targeted. Still failing the rewrite: Din's Great Fairy (conflict) and the targeting tutorial (`Npc_Kokiri_006_Child`: conflict, shared).

**Growth (round 3, 2026-11-12).** Forced conversations that share events with player-started ones now get private copies. Method: the BFEVFL is grown (event array moved to the end, RELT rebuilt, RSTB entry updated), the rewriter copies shared events into new slots, and `files_with_fallback` writes the grown file. Counts on seed `FullSkipChild3`: applied 106 -> 130, fallback to old trimming 35 -> 18, untrimmed 23 -> 16. Newly applied: all of `Npc_Kokiri_007_Child` (exit Kokiri), `Npc_Kokiri_Mido_Child/Talk`, two Zelda `Zelda_CanbeStopped` entries, `HyruleCastle_FoundBySecurity` Courtyard, all 16 `MelodyGet_Sun_SubEvent` targets (Royal Family Tomb; flow file 126 KB -> 276 KB) and `Goto_HyruleCastle/EggHatch`. Guide: `docs/test-full-skip-child-3.md`.

**What the test must decide:** (1) grown flow files load and run in game, especially the 276 KB Royal Family Tomb file (song received, no crash); (2) the exit Kokiri and Mido no longer stop Link and talking to them still works (some lines may be missing: accepted); (3) the castle egg/cucco with `Step03_01_Npc_Navi_StepStart` playing in full; (4) Zelda and the guards; (5) nothing lost vs round 2. Still failing: targeting tutorial `ActionTutorial_1st_Talk` (conflict), Din's fairy (conflict), `Dm_InsideJabu_Jabu_0050` (conflict).
