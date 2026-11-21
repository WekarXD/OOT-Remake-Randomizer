# NPC gifts, batch 2, in the pool — Design

Status: batch 1 is released (main `2bcfd1a`). The batch 2 research (`docs/npc-gifts-research.md`, "Batch 2") and test batch 29 (`docs/test-batch-27.md`) are done. The user asked for this design and its plan on 2026-11-21. Batch 1's design (`2026-11-20-npc-gifts-batch-1-design.md`) is the base: same sites, same patch module, same rules. This document only adds what batch 2 changes.

## Why

OoTR always shuffles the minigame prizes and the Gold Skulltula house rewards. Today the remake keeps them fixed. Batch 2 makes them item locations, as batch 1 did for the one-time gifts.

## Goals, non-goals, anti-goals

- **Goal:** with key items set to "Any chest", the 21 batch 2 prizes become item locations. Their key items join the moving items, and the rest move as minor items. The seed stays beatable.
- **Goal:** with key items set to "Vanilla", nothing changes.
- **Non-goals:**
  - the prize NPCs' dialogue and the item models (as in batch 1);
  - the repeat prizes (rupees after the first win), the Treasure Chest Game and the Deku Theater (batch 3);
  - Gold Skulltula tokens from gifts or scenes (29c suggests they count; a later step).
- **Anti-goals:**
  - a Silver Scale received after the Golden one (29a2: it lowers the dive depth, though the menu shows Gold);
  - two prizes in one flow that overwrite each other's item;
  - a prize that gives nothing, hangs, or gives an item with no effect.

## What is known

| OoTR location | Site content | Grant (flow, events, key) | Proven |
|---|---|---|---|
| Kak 10 Gold Skulltula Reward | `Item_Wallet_Medium` | `GatheringTokenGold` 245, `TakenRewardActor` (by reference) | 29c |
| Kak 20 Gold Skulltula Reward | `Item_AgonyStone` | 246, same | 29c |
| Kak 30 Gold Skulltula Reward | `Item_Wallet_Large` | 247, same | 29c |
| Kak 40 Gold Skulltula Reward | `Item_BombchuBundle_Large` | 248, same | 29c |
| Kak 50 Gold Skulltula Reward | `Obj_Heart_Piece` | 249, same | 29c |
| Market Shooting Gallery Reward | `Item_BulletBag_Medium` | `MiniGame_HitTarget` 291/292, `ReveiveItem` (Large, Medium) | NpcCommon (27e) |
| Kak Shooting Gallery Reward | `Item_Quiver_Medium` | `MiniGame_HitTarget` 293/294, `ReveiveItem` (Large, Medium) | NpcCommon (27e) |
| LW Target in Woods | `Item_BulletBag_Large` | `Dm_LostWood_0040` 84/85, `ActorName` (Large, Medium) | **untested**: a `Dm_` scene with a bag-specific animation |
| Market Bombchu Bowling First Prize | `Item_BombBag_Large` | `MiniGame_BombchuBowling` 297/298, `ReveiveItem` (Medium, Large) | NpcCommon (27e) |
| Market Bombchu Bowling Second Prize | `Obj_Heart_Piece` | 296, `ReveiveItem` | NpcCommon (27e) |
| LH Child Fishing | `Obj_Heart_Piece` | `MiniGame_Fishing` 482 (`ReveiveItem`) and 489 (`ActorName`) | NpcCommon, `GetInEvent_NotTurn` |
| LH Adult Fishing | `Item_Scale_Gold` | 483 (`ReveiveItem`) and 490 (`ActorName`) | same |
| LH Lab Dive | `Obj_Heart_Piece` | `Npc_Hylia_045_Child` 55, `ReveiveItem` | NpcCommon (27e) |
| ZD Diving Minigame | `Item_Scale_Silver` | `MiniGame_Diving` 316, `ActorName` | 29d |
| LW Ocarina Memory Game | `Obj_Heart_Piece` | `Npc_SkullKid_Child_02` 203, `ActorName` | `GetInEvent_NotTurn_NotNpc` (29d) |
| ZR Frogs Ocarina Game | `Obj_Heart_Piece` | `MiniGame_FrogTenors` 71/91, the `MushiToriGame` entry's `ActorName` (by reference, then 246) | by reference (29c) |
| ZR Frogs in the Rain | `Obj_Heart_Piece` | `MiniGame_FrogTenors` 247, `ActorName` (reached on the Song of Storms path) | `GetInEvent_NotTurn_NotNpc` (29d) |
| GF HBA 1000 Points | `Obj_Heart_Piece` | `Minigame_HorsebackArchery` 313, `ActorName` | `GetInEvent` family |
| GF HBA 1500 Points | `Item_Quiver_Large` | 311/312, `ActorName` (Large, Medium) | same |
| Graveyard Dampe Gravedigging Tour | `Obj_Heart_Piece` | `Npc_Hylia_Dampe_001` 602, `ActorName`; special entry `GetInEvent_NotTurn_NotNpc_Dampe` | **untested** entry change |
| LLR Talons Chickens | `Item_Bottle_Milk` | `Minigame_FindOutCucco` 261 (`ActorName`, special entry `GetInEventInBottle`) and 262 (`ReveiveItem`) | **untested** entry change and milk from elsewhere |

This corrects the research map: the frogs' two Pieces of Heart are both in `MiniGame_FrogTenors`. The ocarina game (the remake's butterfly game) passes its prize to `MushiToriGame`, and the Song of Storms path reaches event 247.

Test batch 29:
- **Upgrades out of order:** a smaller wallet or bomb bag after a bigger one never lowers the capacity (29a, 27b); a bullet bag before the Slingshot is kept (29b).
- **Scales are the exception (29a2):** the Silver Scale after the Golden one lowers the dive depth to silver's.
- **Grants:** the Skulltula house's `TakenRewardActor` and a minigame's `GetInEvent_NotTurn_NotNpc` can be renamed (29c, 29d).

## Approaches

| Approach | Trade-off | Decision |
|---|---|---|
| **A.** Append the 21 prizes to batch 1's `GIFTS` table (ids `-315`..`-335`). New key items join `KEY_ITEMS`; the Slingshot and Bow upgrades move as minor items; the Golden Scale only goes where the logic needs the Silver one | One table, one patch path, the fill unchanged except two rules | **Chosen** |
| **B.** Scales: patch the game so the Silver never lowers the Golden | Would need code, not data; nothing in the event flows sets the dive depth | Rejected |
| **C.** Scales: leave both fixed | Simple, but OoTR shuffles them and the fill can order them | Rejected |
| **D.** Upgrades as OoTR's progressive `Slingshot` and `Bow` | A bag alone would count as the weapon in the logic | Rejected: they are minor items |

## Design

**Items** (`items.py`). New `KEY_ITEMS`, with `LABELS` and `KEY_ITEM_HOME`:

| Actor | OoTR item | Label | Home | Level |
|---|---|---|---|---|
| `Item_Wallet_Medium` | `Progressive Wallet` | Adult's Wallet | Kak 10 Gold Skulltula Reward | 1 |
| `Item_Wallet_Large` | `Progressive Wallet` | Giant's Wallet | Kak 30 Gold Skulltula Reward | 2 |
| `Item_AgonyStone` | `Stone of Agony` | Stone of Agony | Kak 20 Gold Skulltula Reward | |
| `Item_BombBag_Large` | `Bomb Bag` | Biggest Bomb Bag | Market Bombchu Bowling First Prize | |
| `Item_Scale_Silver` | `Progressive Scale` | Silver Scale | ZD Diving Minigame | 1 |
| `Item_Scale_Gold` | `Progressive Scale` | Golden Scale | LH Adult Fishing | 2 |
| `Item_Bottle_Milk` | `Bottle with Milk` | Bottle with Milk | LLR Talons Chickens | |

- The levels go in `ITEM_LEVEL` (the "direct" model: the logic holds the highest level). For wallets it matches the game (29a). For scales it holds only because of the fill rule below.
- **Minor items** (not key items): `Item_BulletBag_Medium`, `Item_BulletBag_Large`, `Item_Quiver_Medium`, `Item_Quiver_Large` and `Item_BombchuBundle_Large`. In OoTR the upgrades are the progressive `Slingshot` and `Bow`. Here they only raise the capacity, so the logic ignores them. `FAMILIES` maps them to `Slingshot`, `Bow` and `Bombchus`, so the table checks against OoTR's vanilla items still hold.
- **Ammo:** `Item_BombchuBundle_Large` joins `AMMO_CONTAINER` (bombchus need a bomb bag, batch 17). The container check now uses the OoTR name (`Bomb Bag`, `Bow`), so all three bomb bags count as the container. Today only the Small bag is removed when computing the gated chests, so a Medium bag already in the pool can break that gating.

**Scales** (`fill.py`).
- The Golden Scale is only placed where the logic cannot reach without the Silver Scale. When the fill places it, it computes reach with the Silver Scale removed (placed or still to place). The candidates are the reachable sites outside that set. Higher levels are placed first, so the Golden one goes before the Silver one, which then lands where the Golden one is not needed.
- Excluding one scale excludes both. Both then stay at their minigames, where the game hands them out as in vanilla.

**Logic** (`logic/world.py`). One `REMAKE_RULES` entry: `('LH Lab', 'locations', 'LH Lab Dive')`: `({orig}) and is_child`. Only `Npc_Hylia_045_Child` has the grant; the adult's flow gives the Eyedrops. This is my call: it is conservative, so a wrong guess only loses reach.

**Gifts** (`gifts.py`).
- `GIFTS` gets the 21 rows after batch 1's. Ids `-301`..`-314` stay the same.
- `Gift` gets two optional fields:
  - `via: str | None`: a call matches only if its entry is `via`. This separates the frogs' two prizes: the ocarina game uses `MushiToriGame`, and the rain uses `GetInEvent_NotTurn_NotNpc`. Both give `Obj_Heart_Piece` in the same flow.
  - `key` may be a tuple of keys. Fishing and Talon give each prize twice: an `NpcCommon` `ReveiveItem` and a `GetInEvent` `ActorName`. Both calls are renamed.
- **Same-flow prizes:** five flows hold several prizes: the Skulltula house, the galleries, bowling, fishing and the frogs. `gift_flow_patches` finds every changed gift's calls on the unpatched flow first, then renames them. This avoids a later gift renaming a call that an earlier gift just gave its value to (for example the 10 and 30 rewards swapping wallets).
- **Special entries:**
  - Dampe: `GetInEvent_NotTurn_NotNpc_Dampe` → `GetInEvent_NotTurn_NotNpc`.
  - Talon: `GetInEventInBottle` → `GetInEvent_NotTurn`.
  - The `SubFlowList` rule applies when the flow has a row (batch 1's `gift_subflow_list`).
- `GIFT_ITEMS` covers the new key items as it is.

**What a site may receive.**
- Batch 1's rules stand: the flow sites use `GIFT_FORBIDDEN`, and the world sites only take wrappable, proven contents.
- `generate._gs_forbidden` gets every gift content, not only the key items, so a Skulltula never drops an upgrade it cannot hand over.
- The song scenes (Anywhere) also refuse the four upgrades. `GetPouchContentByActorName` with a bag is untested.

**Generate, spoiler, site.** No new code path: the new rows flow through batch 1's code. The spoiler's "NPC Gifts" section lists 35 locations. The key items help on the site and in the README says that the minigames and the Gold Skulltula rewards are shuffled too.

## Before the plan: test batch 30 (gate)

| Variant | Question | If it fails |
|---|---|---|
| 30a | Talon's Cucco game, with `GetInEventInBottle` → generic: does the win give the Boomerang? | Talon stays fixed (`FIXED_GIFTS`) |
| 30b | Milk from elsewhere (`Item_Bottle_Milk` from the start preset): is there a bottle of milk you can drink? | Milk stays fixed (Talon in `FIXED_GIFTS`) |
| 30c | Dampe's tour, with his entry → generic: does the heart spot give the Boomerang? | Dampe stays fixed |
| 30d | LW Target: does the scene give the Boomerang (its animation shows a bag)? | LW Target stays fixed |
| 30e | The biggest quiver, then the medium one, then the Bow: does the Bow hold 50 arrows? | Quivers move only where the logic needs the Bow (like the scale rule) |

`FIXED_GIFTS` takes any failure, as in batch 1.

## Tests

- **Items and logic:**
  - the 7 new key items, their homes in OoTR's `locations.json` and the levels;
  - LH Lab Dive needs a child;
  - the vanilla placement stays beatable.
- **Gifts table:** 35 rows, unique locations, contents matching OoTR's vanilla items.
- **Patch, on the real game file** (vanilla and full-skip versions):
  - every new gift's grant changes and only that one (the frogs' ocarina game against the rain, the house's five rewards);
  - two prizes in one flow can swap items without overwriting each other;
  - Dampe's and Talon's entries change only when the item changed;
  - fishing and Talon rename both of their calls.
- **Fill:**
  - in 30 seeds, whenever the Golden Scale moves, its location is unreachable without the Silver one;
  - excluding one scale excludes both;
  - bombchus never go where no bomb bag is needed, counting all three bags;
  - the upgrades never go to a Skulltula, a song scene or a world gift;
  - 20 seeds with Tokensanity and songs on are beatable.
- **Generate:** a mod has the patched batch 2 flows; the spoiler lists 35 NPC gifts.

## In-game acceptance

A seed with "Any chest" and the skip on. The guide lists four prizes from the spoiler: a Skulltula house reward, a minigame, the Golden Scale's location (to check that the Silver comes first), and Dampe or Talon if they moved.

## Decisions taken (mine, for review)

1. The Slingshot and Bow upgrades and the bombchus move as minor items (Approach D).
2. The Golden Scale only goes where the logic needs the Silver one, and the two scales are excluded together.
3. LH Lab Dive needs a child.
4. The bowling's first prize is `Item_BombBag_Large`, a third `Bomb Bag` (OoTR has three).
5. Tokens from gifts stay out of this batch.
