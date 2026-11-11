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
