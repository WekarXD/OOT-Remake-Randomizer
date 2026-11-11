# Tokensanity (Gold Skulltulas in the fill): design

Status: draft for approval. Part of project 2, the OoTR "Shuffle" options for items across the world. Branch: `feat/v1`, or a new branch from it, at the builder's discretion.

## 1. What it is and why

The user wants the **Tokensanity** option from the OoTR generator. In OoTR, each Gold Skulltula that enters the fill no longer always drops its token and becomes a location where any item can appear. Their tokens go into the pool of items being distributed.

Until now this could not be done, because key items (`Item_*`) dropped by the world cannot be picked up (batch 6). Batches 9 to 14 found a way to achieve it. Batch 14 was tested in Lichii on 2026-11-10 (`docs/test-batch-14.md`): a Skulltula drops a **wrapper actor** that is a copy of the Gold Skulltula Token with the identity of a key item. It floats where the Skulltula was, is picked up by walking over it or with the Boomerang or the Hookshot, and the item reaches the inventory and can be used.

## 2. Goals, non-goals and anti-goals

**Goals**

- A **Tokensanity** selector in the "Shuffle" section of the page, with the OoTR values:

  | Value (OoTR) | On the page | Which Skulltulas enter |
  |---|---|---|
  | `off` | Off (default) | None |
  | `dungeons` | Dungeons Only | The 44 in dungeons |
  | `overworld` | Overworld Only | The 56 outside |
  | `all` | All Tokens | All 100 |

- A Skulltula that enters the fill can contain any item from the pool: a key item, the contents of a chest (rupees, ammo, hearts…) or a token.
- The tokens of those Skulltulas go into the pool and can end up in a chest or in another Skulltula. The total number of tokens in the game remains 100.
- OoTR's logic, already in the repository, receives `tokensanity` with the chosen value and guarantees the seed can be completed. That includes what is needed to reach each Skulltula and how many tokens the Skulltula House rewards require.
- The spoiler log has a "Skulltulas" section with what is in each one.
- The same seed with the same settings always gives the same mod.

**Non-goals**

- Pots, crates, beehives, loose rupees and other world objects. They come later, with their own design. What is built here (wrappers, logs) should be reusable.
- Changing the wrapper's appearance. The item is seen with its model and with the token's golden glow. I decided this: the user saw it in batch 14 and did not ask to change it.
- OoTR options that depend on tokens, such as the token-based Ganon's bridge or castle. They do not exist in the randomizer today.

**Anti-goals**

- A game blocked because a Skulltula drops nothing, drops something that cannot be picked up, or drops it again every time you enter.
- Any mod file changing compared to today when Tokensanity is `off`.
- Writing to the `.nup` or putting game files in the repository.

## 3. Facts (exploration of 2026-11-10)

- **There are 100 Gold Skulltulas.** They are `Enemy_Skulltula_Gold` actors in the `*_Static.bcett.byml.zs` Banc files, with 100 distinct `Hash` values spread across 114 placements.
  - **14 Hash values appear in two Banc files,** for example the child and adult versions, or the "Alternative" map of Kakariko or Zora's Domain. When changing a Skulltula, all its copies must be changed, as with chests.
  - **The count per zone matches OoTR.** Dungeons: Deku Tree 4, Dodongo 5, Jabu-Jabu 4, Forest 5, Fire 5, Water 5, Shadow 5, Spirit 5, Well 3 and Ice Cavern 3. Overworld: 56. The remake merges zones: the `HyruleField` Banc (11) also contains those of Lake Hylia and Lon Lon Ranch.
  - **Data that helps identify them** (`Dynamic` keys): `Enemy_Skulltula_Gold_Nocturnal` (30), `Enemy_Skulltula_Gold_IsMagicBeanSoil` (10), `DefaultDungeonRoomIndex` (44, in dungeons) and others about how they appear.
- **The token is changed with `Dynamic.Drop__DropActor`** on the Skulltula actor. No Skulltula has it set: without it, it drops its token. Confirmed in the Deku Tree in batches 6 and 9 to 14. Regular `Obj_*` also work, such as the red rupee and the Piece of Heart from batch 6.
- **Recipe for the wrapper that works (batch 14).** The test script is `lote14.py`, in the scratchpad.
  1. **Pack.** `Pack/Actor/<New>.pack.zs` is a copy of the `Obj_Token_Gold` pack. In its ActorParam, `ActorNameRef`, `ModelInfoRef`, `AnimationRef`, `GameParameterTableRef` and `PouchContentRef` are replaced with those from the item's pack, and the item pack's missing files (outside `Actor/`) are added. The `PouchContentParam` is a copy of the item's with `DefaultAutoGet: True` (that makes it get picked up when walked over), with its own name.
  2. **RSTB.** A new entry `[crc32(path without .zs), size + 0x1000]`, inserted in order.
  3. **`RSDB/ActorInfo`.** A row copied from the `Obj_Token_Gold` one with:
     - a new `__RowId`;
     - `ActorName` equal to the `ActorName` of the item's row, or the item's name if it has none;
     - the item's model (`FmdbName`, `ModelProjectName`, `AnimationResources`, `ModelAabbMax/Min`);
     - heaps at the maximum of the two + 0x10000.
  4. **`RSDB/GameActorInfo`.** The token's row, plus the item's `ModelVariationAnims`.
  5. **`RSDB/PouchActorInfo`.** A row copied from the item's with the new `__RowId`. **Without this row the item can be picked up, but does not reach the inventory** (batches 11 to 13).
  6. **Order.** The three RSDB tables are sorted by `__RowId`. Their RSTB is new size + (original RSTB − original size) + 0x1000.
  7. **Format.** The pack is written with a SARC writer: file alignment 8 and data alignment 0x20. It is tested in the scratchpad (`sarcw.py`); today the repository only reads SARC.
- **Bomb Bag.** Outside its original chest it gives the bag and 20 bombs, but they cannot be thrown (known v1 problem, commit 2ad8165). That is why it stays fixed in its chest and does not enter the fill.
- **OoTR.** The vendored settings have `tokensanity: "off"` and `gold_skulls_ignore_daytime: false`. Locations are named "`<zone> GS <place>`" (for example "Kak GS Tree"). MQ does not apply, because the remake has no Master Quest.
- **How tokens are counted.** In `RSDB/PouchActorInfo`, `Obj_Token_Gold` and `Item_Token_Gold` are a stackable inventory item (`PouchStockable`, `FixedMaxNum: 100`). That is, the counter is global and there are no per-Skulltula marks. The Skulltula House rewards require `(Gold_Skulltula_Token, N)` in the logic (`World/Overworld.json`). It remains to be confirmed in game that a token away from its place counts (§4).
- **A Skulltula that is in two Banc files** (child and adult) is the same OoTR location. OoTR's logic already says with which age, time and item each one is reached. As with chests, that logic is accepted for the remake.

## 4. What remains to be known (tested in game at the start)

**Resolved in batch 15 (2026-11-11, `docs/test-batch-15.md`).**

- 1 and 3: tokens work in chests (`Obj_Token_Gold` or `Item_Token_Gold`) and as an explicit drop, and the counter goes up.
- 2: after picking up what it drops, the Skulltula does not come back.
- 4: the nocturnal one works; the soft-soil one remains untested.
- 5: if the item is not picked up, the Skulltula comes back and drops it again, so it is not lost.
- 6: the Boomerang, Hookshot, Iron Boots, Silver Gauntlets, Hammer and Mirror Shield were tested.

The original text follows.

1. **A token coming out of a chest** (`Drop__DropActor: Obj_Token_Gold` in a chest): does it appear, can it be picked up and does the counter go up? The token has a `GoldTokenGmdHash` field that could tie it to its Skulltula.
2. **A Skulltula that drops something else** (wrapper, rupee): does it stay "collected" on leaving and re-entering, and on loading the game, or does it reappear and drop the item again? If it reappears and the item can be picked up again, it does not block the game, but this needs to be known.
3. **A token coming out of another Skulltula:** does it count properly?
4. **A nocturnal Skulltula and a soft-soil one** that drop a wrapper: do they behave the same as those in the Deku Tree?
5. **Leaving without picking up what it drops:** if you kill the Skulltula and leave without picking up the item, is it still there on return or is it lost? If it is lost, a key item in a Skulltula could be lost forever.
6. **Wrappers for all the key items in the fill** (`KEY_ITEMS`, about 14 without the Bomb Bag): do they appear and reach the inventory? Only the Boomerang and the Hookshot have been tested. Songs and quest items are not distributed, so they are not needed.

If a token cannot be put in a chest (point 1), there are two ways out: tokens only go to Skulltulas, or a wrapper is also made for the token. Whoever builds it decides, depending on the result, and notes it down.

If in point 2 the Skulltula reappears and drops the item again, that does not block the game, but it clashes with an anti-goal. In that case, stop and ask the user. If in point 5 the item is lost, also stop and ask, because key items might have to be excluded from Skulltulas.

## 5. Behaviour

### 5.1 Identifying the Skulltulas

- A versioned data file (`randomizer/data/gs_map.json`, like `location_map.json` for chests) maps each `Hash` to its OoTR location, noting whether it is a dungeon or overworld one and its status (`confirmed` or `guessed`).
- It is built zone by zone: the count matches, and within each zone they are told apart by nocturnal, soft soil, dungeon room and position. Those that cannot be told apart are checked in game with a test batch. For example, each doubtful Skulltula drops a different, recognizable item.
- An unmapped Skulltula does not enter the fill even if the option is on, and keeps its token.

### 5.2 Fill

- The fill, which today is chests only, now handles locations of several types: chest and Skulltula. Nothing changes for chests. Phase B of the gifts (plan in `docs/superpowers/plans/2026-11-10-gifts-phase-b.md`) adds another type of location, so whoever builds it should generalize it once for all three.
- With Tokensanity on, the chosen Skulltulas are additional free locations. Their tokens (`Obj_Token_Gold`) go into the pool of content that is shuffled, along with the rest of the chest contents.
- Key items are placed with the same *assumed fill* as today, which already admits any reachable location. The rule of not putting key items in the `NO_KEY_TARGET_ZONES` zones (Water, Fire, Well, Training Grounds) also applies.
- OoTR's logic is loaded with `tokensanity` equal to the chosen value. The GS locations that do not enter (because of the option or because they are unmapped) keep their original token in `fixed`, and the logic counts them for the house rewards.
- **Tokens in the logic** (I decided this). Today non-key content is distributed blindly. Tokens, however, are placed in `fixed` as `Gold Skulltula Token`, so that the logic counts them. There are two cases:
  - **No house reward holds a key item** (as it is today, without gifts phase B): tokens are not needed to complete the game. It is enough to place them in the remaining free locations and validate with `can_beat`.
  - **Phase B puts key items in the rewards:** tokens become progression. They are placed with *assumed fill* after the key items, so that each key item is placed assuming they are held.
- `tokensanity` is part of the RNG key, because it changes the fill. With `off`, the result must be identical to today's.

### 5.3 What each Skulltula drops

- Content that is already a ground actor with a row in `PouchActorInfo` (`Obj_Rupee_*`, `Obj_Heart_Piece`, `Obj_Token_Gold`, etc.) is put as is in `Drop__DropActor`.
- Any other, key items and whatever cannot be dropped directly, receives a **wrapper** generated when assembling the mod with the recipe from §3: one per distinct item, with the fixed name `Obj_Rando_<Item>`. There are at most a few dozen, so no limit problems are expected. Whoever builds it decides which chest contents need a wrapper, by looking at whether they have a row in `PouchActorInfo` and whether they are `Obj_*`.
- The wrappers, their RSDB rows and their RSTB entries are only written if some Skulltula uses them. With `off`, no RSDB is touched.
- A chest that receives a token uses `Obj_Token_Gold`, or whatever the §4 test says.

### 5.4 Page and spoiler log

- In the "Shuffle" section of the Items tab: a "Gold Skulltula Tokens (Tokensanity)" selector with the four values from §2, off by default. If gifts phase B has not yet created the section, it is created here.
- The log adds a "Skulltulas" section listing each GS location that enters, with its content in English. Tokens that end up in chests appear in the usual chest section.

## 6. Phases (each with its Lichii test)

1. **Test of what is pending in §4,** with a hand-made test batch like the previous ones. If anything blocks the game, stop and rethink.
2. **Mapping the 100 Skulltulas** (`gs_map.json`), with its verification batch for the doubtful ones.
3. **Build.** Includes:
   - SARC writer with round-trip tests;
   - wrapper generator and RSDB/RSTB rows;
   - fill with Skulltula locations;
   - option on the page;
   - spoiler log;
   - a test seed with Tokensanity set to `all` that the user plays part of.

## 7. Done when

- The option exists on the page and is reflected in the spoiler log.
- Phases 1 to 3 have their batch passed in Lichii.
- The tests pass, including that with `off` the generated mod is identical to the previous one.
