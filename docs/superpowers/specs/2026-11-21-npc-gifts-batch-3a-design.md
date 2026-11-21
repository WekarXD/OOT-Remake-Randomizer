# NPC gifts, batch 3a: OoTR's optional switches — Design

Status: batches 1 and 2 are released (main `0f11649`). The batch 3a research (`docs/npc-gifts-research.md`, "Batch 3a") and test batch 31 (`docs/test-batch-27.md`) are done. Batch 2's design (`2026-11-21-npc-gifts-batch-2-design.md`) is the base: same `GIFTS` table, same patch path, same rules. This document only adds what batch 3a changes.

## Why

OoTR has four switches that put more NPC items in the pool: Shuffle Ocarinas, Shuffle Gerudo Card, Shuffle Expensive Merchants, and the Kak 100 Gold Skulltula Reward (always shuffled in OoTR). The remake keeps all of them fixed today. Batch 3a adds them as OoTR has them.

## Goals, non-goals, anti-goals

- **Goal:** three new settings, named and defaulting as in OoTR: `shuffle_ocarinas`, `shuffle_gerudo_card` and `shuffle_expensive_merchants`, all off. With key items set to "Any chest", each one turns its locations into item locations. The Kak 100 reward joins batch 2's house rewards, with no setting.
- **Goal:** with the three settings off, a seed is the same as before batch 3a, except that the Kak 100 reward moves.
- **Goal:** with key items set to "Vanilla", nothing changes.
- **Non-goals:**
  - the dialogue and the item models (as in batches 1 and 2): Medigoron's counter still shows the knife;
  - Granny's potion shop, the bean seller and the trade sequences (batch 3b);
  - new `GameDataList` flags (see Approaches).
- **Anti-goals:**
  - a merchant that sells a placed item twice (31d, 31e2: both resell today). With a progressive item this would hand out the next level;
  - a merchant that stops selling before the first sale: Medigoron's flow refuses when the Giant's Knife or Biggoron's Sword is already in the pouch;
  - a rule that needs the Gerudo Card when the card does nothing in the remake.

## What is known

| OoTR location | Site content | Grant (flow, events, key) | Proven |
|---|---|---|---|
| LW Gift from Saria | `Item_Ocarina_Fairy` | `Dm_Kokiri_0155` 51 (`EventTriggerAddOrRemovePouchContent`, `Actor`) and 52 (`GetPouchContent:DisplayGetByActorName`, `ActorName`) | 31a |
| HF Ocarina of Time Item | `Item_Ocarina_Time` | `Dm_MelodyGet_Time` 106 (`Actor`) and 255 (`ActorName`); the Song of Time (93) is separate | 31b (with the Fairy Ocarina in the pouch) |
| Hideout Gerudo Membership Card | `Item_Token_Gerudo` | `Dm_Gerudo_0025` 120, `GetInEvent_NotLookatObjectTurnOff`, `ActorName` | **untested** |
| GC Medigoron | `Shop_Sword_Giant` | `Npc_Goron_Medigoron_Adult` 6 (`SimpleShop:SimpleShopRoot_Npc_Goron_Medigoron_Adult`, `ActorName` by reference); special grant entry `SimpleShop` 112 `GetInEventItemSwordMedigoron` → `GetInEvent_NotTurn` | 31d |
| Wasteland Bombchu Salesman | `Shop_BombchuBundle_01` | `Npc_Hylia_044_Adult` 0 (`SimpleShop:SimpleShopRoot`, `ActorName` by reference), handed over by `SimpleShop` 39 (`NpcCommon_HandOver_NpcToPlayer_NoTurn_NoWaitAS`) | 31e2 |
| Kak 100 Gold Skulltula Reward | `Obj_Rupee_Gold` | `GatheringTokenGold` 250 (`TakenRewardActor`) and 573 (`ActorName`) | 31f |

Also found:
- **The two ocarinas are separate items (31c):** with both, Link has both and plays songs. Their order does not matter.
- **The full skip keeps every grant above.**
- **The Gerudo Card does nothing in the remake:** no flow reads `Item_Token_Gerudo`. The guards, the gate and the Training Ground follow `SageOfSpirit_IsAfter_Step01/Step03_Exp`, which the carpenters' rescue sets.
- **Merchants:**
  - **Both resell (31d, 31e2).** Medigoron refuses only when the Giant's Knife (event 2), the broken knife (3) or Biggoron's Sword (17) is in the pouch. The carpet salesman never refuses.
  - **`Npc_Hylia_044_Buy`**, which `SimpleShop` 84 sets after his sale, is not saved: `SaveFileIndex` -1, `ResetTypeValue` 1. It only picks his greeting.
- **`GameDataList` can now be read:** big-endian BYML v7, with each name stored as its MurmurHash3 (seed 0, big-endian). This tells whether a flag exists and whether it is saved (`SaveFileIndex` 0, `ResetTypeValue` 8, as `HavePlayedEvent.*`). Adding a flag would mean writing the file and its `MetaData` save sizes, which is untested.
- **`HaveTalked.<npc>`** exists for 156 of the 240 NPC flows. That pattern suggests the engine sets it on any talk, so it cannot mean "sold".
- **Case values:** a query's case value 0 is true and 1 is false. A query with no matching case ends the flow, or returns from a subflow.

## Approaches (the sold-out flag)

| Approach | Trade-off | Decision |
|---|---|---|
| **A.** Reuse three saved Medigoron flags that the patch makes dead. The patch sends Medigoron's talk straight to the sale, which skips his pouch checks (17, 2, 3) and his one-time comments (`SageOfFire_Check`). That leaves `HaveTalked_Special.Npc_Goron_Medigoron_Adult_Talk_Event26`, `_Event3` and `_Event8` with no setter. Event26 marks Medigoron as sold, and Event3 the carpet salesman | No new file format. Pointer and string edits, plus one appended action. Loses some cosmetic one-time lines | **Chosen** |
| **B.** Add two new saved Bool flags to `GameDataList` | Clean names, and reusable for 3b. But it needs a big-endian BYML writer and the `MetaData` save sizes, and if it fails, saves break | Later, if 3b needs more flags than A frees |
| **C.** Leave the merchants rebuyable | They could only hold non-progressive minor items; OoTR sells each once | Rejected |

## Design

**Settings.**
- `Settings` (fill.py) gets `shuffle_ocarinas: bool`, `shuffle_gerudo_card: bool` and `shuffle_expensive_merchants: bool`, all `False`.
- The CLI, `browser.py` (validated like `tokensanity`), the site's options and the spoiler's settings list show them, with OoTR's names and texts.
- The logic's `vanilla_settings` gets the same three values, so OoTR's rules see them.

**Items** (`items.py`). The new contents go in tables keyed by setting. When the setting is off they stay out of the pool, and the site keeps its vanilla item (`World.vanilla_fixed()`).

| Actor | OoTR item | Kind | Setting |
|---|---|---|---|
| `Item_Ocarina_Fairy` | `Ocarina` | key item, `ITEM_LEVEL` 1 | `shuffle_ocarinas` |
| `Item_Ocarina_Time` | `Ocarina` | key item, `ITEM_LEVEL` 2 | `shuffle_ocarinas` |
| `Item_Token_Gerudo` | `Gerudo Membership Card` | minor item (no logic effect, see below) | `shuffle_gerudo_card` |
| `Shop_Sword_Giant` | `Giants Knife` | minor item | `shuffle_expensive_merchants` |
| `Shop_BombchuBundle_01` | `Bombchus (10)` | minor item, `FAMILIES` `Bombchus` | `shuffle_expensive_merchants` |
| `Obj_Rupee_Gold` (Kak 100) | `Huge Rupee` | minor item | always |

- Each ocarina's `KEY_ITEM_HOME` is its OoTR location, with the `LABELS` "Fairy Ocarina" and "Ocarina of Time".
- **Pool twins.** When a merchant's item moves elsewhere, it goes as the `Item_` twin that test batch 32 proves works (32c, 32d). A `Shop_` actor may only work inside a shop.

**Logic** (`logic/world.py`).
- **Ocarina:** OoTR's progressive `Ocarina`, in the "direct" model. 31c shows the order does not matter, so no fill rule like the scales' is needed.
- **Gerudo Card:** with `shuffle_gerudo_card` on, the location "Hideout Gerudo Membership Card" also grants the logic event `Gerudo Membership Card`, whatever item it holds. The placed `Item_Token_Gerudo` grants nothing. OoTR's rules that need the card then need the rescue, which is what the remake checks. With the setting off, the vanilla card grants the same event at the same place.
- **HF Ocarina of Time Item:** if 32e shows that the scene needs an ocarina in the pouch, one `REMAKE_RULES` entry adds `Ocarina`.
- **Merchants:** OoTR's own rules, including the wallet. Kak 100: OoTR's `(Gold_Skulltula_Token, 100)`.

**Gifts** (`gifts.py`). New `GIFTS` rows, gated by their setting (`gifts_for(settings)`):
- **Action grants.** A grant can now be an action event with key `Actor` (`EventTriggerAddOrRemovePouchContent`) as well as a subflow call. `Gift.keys` covers both: the ocarinas rename `('Actor', 'ActorName')`.
- **Entry in another flow.** `Gift.entry` can name its flow: Medigoron's special entry is called from `SimpleShop` 112, not from his own flow.
- **Kak 100:** joins the house rows, with keys `('TakenRewardActor', 'ActorName')`.

**Sold-out patch** (`merchants.py`, new). It applies when `shuffle_expensive_merchants` is on, whatever item the fill placed, so a merchant always sells exactly once (as in OoTR).

- **Medigoron** (`Npc_Goron_Medigoron_Adult`):
  - event 50's next goes to 69. 69 is the existing query on Event26: true goes to 35 (his chatter after a sale), false goes to 15 (the sale path);
  - this leaves 2, 3, 14, 17 and their branches unreachable. A test proves that no entry reaches a setter of Event26, Event3 or Event8.
- **Medigoron's sale** (`SimpleShop`, entry `SimpleShopRoot_Npc_Goron_Medigoron_Adult`): a new action, `GameDataActor EventTriggerSetGameDataBool` with Event26 set to true, goes between the grant (112) and 53. Only the paid path reaches it: a refusal or too few rupees goes through `Sub_ShopCancel`.
- **The carpet salesman:**
  - `Npc_Hylia_044_Adult`: event 2's next goes to 11. 11's `GameDataName` becomes Event3. True goes to 13, whose message becomes `Talk_01` ("¡Tú aquí otra vez!") and whose next is the end. False goes to 14, his greeting;
  - 22's next goes to 12, the first-time pitch. The sold-out path never opens the rupee display;
  - `SimpleShop`: 84's `GameDataName` becomes Event3. 84 is on `Sub_SimpleShop_Buy`, which only the carpet salesman's `SimpleShopRoot` reaches.
- The patch works on whatever version `read(flow)` returns (the full skip's, or one the gift patch already wrote), as `gift_flow_patches` does.

**Generate, spoiler, site.**
- `generate` runs the merchants' patch after the gifts on the same flows.
- The spoiler lists the new locations under "NPC Gifts".
- The site and the README list the three settings.

## Before the plan: test batch 32 (gate)

| Variant | Question | If it fails |
|---|---|---|
| 32a | Medigoron with the sold-out patch: refuse once, then buy (the Boomerang), then talk again. Does he sell exactly once? | Medigoron stays fixed (`FIXED_GIFTS`); approach B for later |
| 32b | The carpet salesman, the same test. Is the rupee display closed afterwards? | The carpet stays fixed |
| 32c | The Giant's Knife from elsewhere (`Item_Sword_Giant`, then `Shop_Sword_Giant`): which one gives a working knife? Then, with the knife in the pouch, does the patched Medigoron still sell? | No twin works: the knife only stays at Medigoron (Medigoron's site takes the pool, the knife stays out) |
| 32d | Bombchus from `Shop_BombchuBundle_01` elsewhere, against `Item_BombchuBundle_Small` | The small bundle is the twin |
| 32e | Zelda's Ocarina of Time scene with no ocarina in the pouch: does it start, and give the item and the song? | `REMAKE_RULES`: the site needs `Ocarina` |
| 32f | The Gerudo Card scene (`Dm_Gerudo_0025`): does it give the Boomerang? | The card stays fixed |

## Tests

- **Settings:** the defaults are off; `browser.py` rejects non-bools; with all three off and key items "Any chest", the gifts are batch 2's plus Kak 100.
- **Items and logic:** the ocarinas' levels and homes; the card event at its location with the setting on; vanilla placements beatable with each setting on.
- **Gifts, on the real game file** (vanilla and full skip):
  - the ocarinas rename both their action and their subflow grant;
  - Medigoron's entry in `SimpleShop` changes only when his item changes;
  - Kak 100 renames both of its calls.
- **Sold-out patch, on the real game file:**
  - in Medigoron's flow, no path from any entry reaches events 2, 3, 17 or a setter of Event3/8/26;
  - his sale path sets Event26 after 112, and the cancel paths don't;
  - the carpet's flag is Event3 in both flows, and his sold-out path ends with no rupee display;
  - with the setting off, the three flows are untouched.
- **Fill:**
  - 20 seeds with each setting on are beatable;
  - neither ocarina goes where the logic needs it before it is reachable;
  - the merchants never get an item their site cannot hand over (`GIFT_FORBIDDEN`).
- **Generate:** a mod with the settings on contains the patched flows; the spoiler lists the new locations.

## In-game acceptance

A seed with "Any chest", the skip on and all three settings on. From the spoiler, the guide lists:
- Saria's gift;
- Zelda's ocarina;
- Medigoron and the carpet salesman (buy, then talk again);
- the Kak 100 reward (with the preset's 100 tokens).

## Decisions taken (mine, for review)

1. Sold-out flags by reuse (A): three of Medigoron's saved flags, freed by skipping his pouch checks and his one-time comments. The cost is cosmetic: his lines about Biggoron's Sword, the broken knife and the Fire Temple are gone.
2. The sold-out patch applies whenever `shuffle_expensive_merchants` is on, even if the fill puts the vanilla item back.
3. The Gerudo Card is a logic event at its site; the shuffled card is a minor item.
4. The ocarinas are progressive in the "direct" model, with no fill rule.
5. Kak 100 joins the always-shuffled house rewards (OoTR has no setting for it).
6. A merchant's item enters the pool as its `Item_` twin (from 32c and 32d).
