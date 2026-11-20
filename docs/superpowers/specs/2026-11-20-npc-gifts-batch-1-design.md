# NPC gifts, batch 1, in the pool — Design

Status: the user approved batch 1 on 2026-11-15 (one-time gifts that give progress items, always on with "Any chest", as OoTR does) and added Zelda's Letter, the Weird Egg and the tunics on 2026-11-17. The research (`docs/npc-gifts-research.md`) and test batch 27 (`docs/test-batch-27.md`, every variant works) are done. The user approved this approach on 2026-11-20. This document is the design; the plan follows. It replaces the old gifts spec (2026-11-10, phases A and B) for batch 1, whose data it reuses.

## Why

OoTR always shuffles the NPC gifts with the other items. The goal of the project is to resemble OoTR. Today every NPC gift gives its own item, and the logic treats them as fixed. Batch 1 covers the one-time gifts. The minigames (batch 2) and OoTR's optional settings and the trade sequence (batch 3) come later.

## Goals, non-goals, anti-goals

- **Goal:** with key items set to "Any chest", the 14 batch 1 gifts become item locations and their items join the moving items. The seed stays beatable.
- **Goal:** with key items set to "Vanilla", nothing changes.
- **Non-goals:**
  - the models and texts of the items (a wrapper looks like the item with the token's glow; batch 27f);
  - the gift NPCs' own dialogue, which may still name their vanilla item;
  - the ocarinas, the Gold Skulltula rewards, the minigames and the trade items (batches 2 and 3).
- **Anti-goals:**
  - a gift that never gives its item, or gives it twice;
  - a moving item that the receiving site cannot hand over (a hang, or an item with no effect);
  - a logic rule that calls something reachable when the remake gates it more.

## What is known (research and batch 27)

| OoTR location | Remake content (site's vanilla) | Grant | Batch 27 |
|---|---|---|---|
| GC Darunias Joy | `Item_Gauntlet_Goron` | `Dm_Goron_0030`, `ActorName`; special entry `GetInEvent_Goron` | 27c works |
| HC Zeldas Letter | `Item_ZeldaLetter` | `Dm_HrlCastle_0050`, `ActorName`; special entry `GetInEvent_Zeldaletter` | 27d works (with the `SubFlowList` fix) |
| HC Malon Egg | `Item_WeirdEgg` | `Goto_HyruleCastle`, `ActorName` | 27a works |
| LW Skull Kid | `Obj_Heart_Piece` | `Npc_SkullKid_Child`, `ActorName` | same entry as 27a |
| ToT Light Arrows Cutscene | `Item_Arrow_Light` | `Dm_TimeTemple_0130`, `GetPouchContentByActorName` `ActorName` | the song scenes' grant (works) |
| GC Rolling Goron as Child | `Item_BombBag_Medium` | `Npc_Goron_006_Child`, `ReveiveItem` (Medium and Large); special entry `GetInEvent_NotTurn_BombBag` | 27b works |
| GC Rolling Goron as Adult | `Obj_Armor_Goron` | `SageOfFire`, `ActorName` | same entry as 27a |
| ZD King Zora Thawed | `Obj_Armor_Zora` | `SageOfWater`, `ActorName` | same entry family as 27a |
| Kak Anju as Child | `Item_Bottle` | `Minigame_CatchCucco`, `ReveiveItem` (`Item_Bottle` only; the red rupee of later rounds stays) | 27e works |
| Market Lost Dog | `Obj_Heart_Piece` | `SubEvent_FindRichard`, `ReveiveItem` (`Obj_Heart_Piece` only) | same hand-over as 27e |
| Kak Man on Roof | `Obj_Heart_Piece` | `Npc_Hylia_001_Adult`, `ActorName` | generic `GetInEvent` |
| Market 10 Big Poes | `Item_Bottle` | `Npc_Hylia_048_BottleShop`, `ActorName`; special entry `GetInEvent_Poeshop` | untested |
| LH Sun | `Item_Arrow_Fire` | world actor `Obj_Arrow_Fire`, `HyruleField_Adult_Static`, hash 4598657944866228526 | **untested** (batch 28a) |
| LH Underwater Item | `Item_Bottle_Letter` | world actor `Obj_Bottle_Letter`, `HyruleField_Child_Static`, hash 474136620438465634 | 27f works |

Further facts:

- **`SubFlowList` (27d):** when a grant's entry changes, the event's `SubFlowList` in `RSDB/GameAnalyzedEventInfo` must include every flow the new entry calls. Otherwise the game silently skips the call. NPC flows have no row there, so only `Dm_` scenes need it.
- **The egg (27a):** the egg hatches only after Malon's talk. Her talk moves the castle quest to `Step03`, and Navi's `Step03_01` schedule runs `EggHatch`, which removes the egg and gives the Cucco. That path does not check the egg. Talon wakes with the Cucco.
- **Bomb bags (27b):** a smaller bag never lowers the capacity, and the Medium bag alone works and comes with bombs. The order does not matter.
- **Nothing in batch 1 reads `IsGet.<own item>` before granting it**, unlike the Great Fairies, so no revisit patch is needed.
- **`Npc_SkullKid_Child_02`** (the stump near the bridge) gives the memory game's Piece of Heart. That is batch 2, so only `Npc_SkullKid_Child` is batch 1.

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| **A.** The 14 gifts join the fill as synthetic sites, as the Great Fairies do. Their progress items join the moving key items, and the Pieces of Heart move as minor items | Reuses the fill, exclusions, logic and spoiler. Same pattern as two working features | **Chosen** |
| **B.** A separate "Shuffle NPC gifts" setting | The user decided "always on with Any chest" | Rejected |
| **C.** Only the flow grants; the two world actors later | Simpler, but Ruto's Letter and the Fire Arrows are OoTR's, and 27f proved the wrapper | Rejected |

## Design

**Items** (`items.py`). These join `KEY_ITEMS` with OoTR's names, `LABELS` and `KEY_ITEM_HOME`:

| Actor | OoTR item | Label | Home |
|---|---|---|---|
| `Item_Gauntlet_Goron` | `Progressive Strength Upgrade` | Goron's Bracelet | GC Darunias Joy |
| `Item_ZeldaLetter` | `Zeldas Letter` | Zelda's Letter | HC Zeldas Letter |
| `Item_WeirdEgg` | `Weird Egg` | Weird Egg | HC Malon Egg |
| `Item_Arrow_Light` | `Light Arrows` | Light Arrows | ToT Light Arrows Cutscene |
| `Item_Arrow_Fire` | `Fire Arrows` | Fire Arrows | LH Sun |
| `Item_BombBag_Medium` | `Bomb Bag` | Big Bomb Bag | GC Rolling Goron as Child |
| `Obj_Armor_Goron` | `Goron Tunic` | Goron Tunic | GC Rolling Goron as Adult |
| `Obj_Armor_Zora` | `Zora Tunic` | Zora Tunic | ZD King Zora Thawed |
| `Item_Bottle` | `Bottle` | Bottle | Kak Anju as Child |
| `Item_Bottle_Letter` | `Rutos Letter` | Ruto's Letter | LH Underwater Item |

- `Item_Gauntlet_Goron` gets `ITEM_LEVEL` `('Progressive Strength Upgrade', 1)`. The comment that strength level 1 is fixed is removed.
- `Item_Bottle` appears at two sites (Anju and the Poes). Its home is Anju's, and the Poes' site keeps OoTR's `Bottle`.

**Logic** (`logic/world.py`). OoTR's rules stand, except for one `REMAKE_RULES` entry:

- `('Kak Odd Medicine Rooftop', 'locations', 'Kak Man on Roof')`: `({orig}) and is_adult`. Only `Npc_Hylia_001_Adult` has the grant.

The egg needs no rule. OoTR asks for `Weird_Egg or Chicken` at Hyrule Castle Grounds, where Malon is. A child there can talk to her, so the egg hatches. If her talk ever gives the Cucco without the egg, that only adds reach.

**Fill** (`fill.py`).

- **Sites:** with key items set to "Any chest", each gift becomes a site with a synthetic id (`-301` to `-314`, in table order). Its original content is the table's, and it maps to its OoTR location in `site_loc`. The base sets it to filler. Its item is moving if it is a key item and not excluded. The Pieces of Heart join `rest` as minor items.
- **What a site may receive:**
  - **Flow sites (12):** the fountains' forbidden set (`FOUNTAIN_FORBIDDEN`: the token, `Item_BulletBag_Small`, `TBox_DekuSeedBundle`, `Item_ScrubBusinessSeed`, the Bow, the Slingshot and the Small Bomb Bag). This is my call: the same `GetInEvent`-family grants, so the same known risks.
  - **World sites (2):** only contents that can be wrapped (`wrappers.can_wrap`), never a token. `generate` passes this set to the fill, as it does for the Skulltulas.
- `Placement` gains `gifts: dict[str, str]`, mapping each OoTR gift location to what it gives. It is empty with "Vanilla" key items.

**Patch** (`randomizer/gifts.py`, new). It mirrors `fairies.py`:

- `Gift(location, content, flow, key, vanilla, entry)` for the 12 flow grants:
  - `vanilla` is the tuple of values to rename;
  - `entry` is `(special, generic)` or `None`. The generic is `GetInEvent_Demo_NotLookatObjectEntry` for `Dm_` scenes and `GetInEvent_NotTurn` for NPC flows.
- `WorldGift(location, content, banc, hash)` for the 2 world actors.
- `gift_flow_patches(read, gifts) -> {flow: bytes}`:
  - every subflow call in the gift's flow whose `key` value is one of `vanilla` gets the placed item;
  - when the item changed and the gift has a special entry, those calls are pointed at the generic one;
  - a gift that keeps its own item is not touched;
  - zero matching calls raises `GiftPatchError`;
  - lookups are by value, never by event index.
- `gift_subflow_list(info, read, flows) -> bytes`: `ANALYZED_INFO` with each patched `Dm_` event's `SubFlowList` extended by the closure of its new entry (`test_start.subflow_closure`). Events with no row are skipped.
- `gift_actor_swaps(gifts) -> {hash: (banc, content)}`: the world gifts whose item changed.

**Generate.**

- It calls `gift_flow_patches` through `_with_flow_patches`, on top of the full skip and after the songs and the fairies.
- It patches `ANALYZED_INFO` on top of whatever the full skip wrote (a new `_with_file_patch` helper).
- It merges `gift_actor_swaps` with the boss-heart swaps into `patch.write_mod(actor_swaps=...)`.
- `_gs_forbidden` gets the new key items (they are in no chest) as `extra`.
- The world-site forbidden set is the pool's contents that `can_wrap` rejects, plus the token.

**Spoiler.** An "NPC Gifts" section lists the 14 locations and what each gives. The moving items appear under "Key items" with their labels and the zone "NPC gift".

**Site.** No new setting. The key items help says that with "Any chest" the NPC gifts (batch 1) are shuffled too.

## Before the plan: test batch 28

Three things are still untested and change the design if they fail:

| Variant | Question | If it fails |
|---|---|---|
| 28a | LH Sun: does the `Obj_Arrow_Fire` wrapper (the Boomerang) appear when the sun is shot, and can it be picked up? | LH Sun stays fixed (not a site); Fire Arrows do not move |
| 28b | Ruto's Letter from elsewhere (`Item_Bottle_Letter` from the start preset): does King Zora accept it? | Ruto's Letter stays fixed |
| 28c | Silver Gauntlets without the Goron's Bracelet: can Link throw bombs and lift bomb flowers? | The bracelet stays fixed at Darunia (the logic's level model would call bombs usable with Silver only) |

## Tests

- **Items and logic:**
  - the Kak Man on Roof rule needs an adult;
  - the vanilla placement stays beatable;
  - the bracelet counts as strength level 1.
- **Fill:**
  - with "Any chest", the 14 sites are filled and 20 seeds are beatable;
  - flow sites never get the fountains' forbidden contents, and world sites never get unwrappable contents or a token;
  - an excluded gift item stays at its site;
  - "Vanilla" key items give the same placement as today;
  - the songs and Tokensanity settings combine with this.
- **Patch, on the real game file** (needs `OOT_NUP`), vanilla and full-skip versions:
  - each gift's flow gives the new item, and only the matching calls change;
  - special entries go generic only when the item changed;
  - Zelda's `SubFlowList` gains `ActionGuide`;
  - the world swaps target the right hashes.
- **Generate:**
  - a mod contains the patched gift flows, the analysed-event table and the wrappers;
  - the spoiler has the NPC Gifts section.

## In-game acceptance

A seed with "Any chest" and the skip on. Its guide lists three gifts from the spoiler: one special entry (Darunia or Zelda), one NPC hand-over and one world actor.

## Decisions taken (mine, for review)

1. The flow gift sites use the fountains' forbidden set. 27b showed that the Medium Bomb Bag comes with bombs, but the set stays as it is until a batch tests the others.
2. The world gift sites take only wrappable items and never a token.
3. The Pieces of Heart move as minor items.
4. `Item_BombBag_Medium` is OoTR's `Bomb Bag`, a second copy next to the Dodongo's Cavern bag. The order does not matter (27b).
5. Only `Npc_SkullKid_Child` is batch 1. The stump's grant is the memory game (batch 2).
6. No rule for the egg (see Logic).
