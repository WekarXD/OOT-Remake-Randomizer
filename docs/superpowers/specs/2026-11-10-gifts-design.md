# Character and scene gifts in the fill — Design

Status: draft for approval. Project 1 of 2 for adding the "Shuffle" options of the OoTR generator (v9.1.0). Project 2 (minor items across the world) comes later, with its own design. Branch: `feat/v1` (or a new branch from it, at the builder's discretion).

## 1. What it is and why

The user wants the OoTR Shuffle options in the remake randomizer. Today key items are only distributed among chests.

Test `TestBatch6` showed that key items (`Item_*`) cannot be dropped into the world. They are drawn, but cannot be picked up (`docs/test-batch-6.md`). So the only way to get more locations for key items is **character and scene gifts**. The item a character hands over is a text parameter inside their event flow (`.bfevfl`), for example `{'ActorName': 'Item_Ocarina_Fairy'}`.

## 2. Goals, non-goals and anti-goals

**Goals.** Each of these OoTR options appears as a switch on the page, off by default. With the switch on, those locations enter the fill:

| Option (OoTR name) | Locations (exploration of 2026-11-10) |
|---|---|
| Shuffle Ocarinas | Fairy Ocarina (`Dm_Kokiri_0155`, events 51 and 52) and Ocarina of Time (`Dm_MelodyGet_Time`, events 106 and 255) |
| Shuffle Gerudo Card | `Dm_Gerudo_0025` event 120, `Item_Token_Gerudo` |
| Shuffle Magic Beans | Bean seller, `Npc_Hylia_047_Child` (with `SimpleShop`; can be bought several times) |
| Shuffle Expensive Merchants | Medigoron (`Shop_Sword_Giant`), carpet merchant (`Npc_Hylia_044_Adult`), potion granny (`Npc_Hylia_053_Adult`) |
| Shuffle 100 Skulltula Reward (+ the 10 to 50 ones) | `GatheringTokenGold` events 245 to 250 |
| Shuffle Hyrule Loach Reward | `MiniGame_Fishing` events 655 to 660 (Loach fish branch to be confirmed) |
| Frogs' Piece of Heart | `MiniGame_FrogTenors` event 247 |
| Shuffle Child / Adult Trade Sequence Items | See §4.4. Goes in the last phase. |

- The OoTR logic already vendored in the repository decides whether the seed can be completed, with those settings on.
- The same seed with the same settings always gives the same mod.

**Non-goals**
- Minor items across the world (Skulltulas, pots, crates, beehives, loose rupees, Deku scrubs): these are project 2.
- Cows, "wonder" items and loose ocarina notes: they cannot be done this way or the remake does not have them.
- Changing the model or the text shown by the scene: the item received is what counts, as with chests (accepted in v1).

**Anti-goals**
- A game blocked because a gift is not delivered, is delivered twice or takes away an item it should not.
- Anything changing compared to today when all the switches are off.
- Writing to the `.nup` or putting game files in the repository.

## 3. Known facts and risks

- Gifts are text parameters in actions such as `SUB Dm_SY_GetInEvent:* {'ActorName': ...}`, `PouchSystemActor.EventTriggerAddOrRemovePouchContent {'Actor': ...}` or `SimpleShop {'ActorName': ...}`. There is evidence in `scratchpad/shuffle-recon` (`flows_dump.txt`), which can be regenerated with the BFEVFL reader.
- Today we only know how to rewrite u16 indices in place. Changing a text may require:
  - pointing to a string that already exists in the file;
  - or adding it and moving whatever is needed, which changes the size. Then the flow's RSTB must be updated, and its formula is not known.
- Risks that the build must resolve or rule out:
  1. **Repeatable gifts** (beans, fishing): the fill's item is given only once.
  2. **Charges** (beans, merchants): the price is tied to the item (`PriceParam`).
  3. **Trades:** each delivery is paired with a `Num:-1` removal of the previous item.
  4. **Shared scenes** (`SimpleShop` event 63, `Dm_SY_GetInEvent`): something used by other scenes cannot be changed.
  5. **Whether an `Item_*` delivered by a scene works in game:** the Gerudo Card and the Ocarina do so in the original game, but a different item in that spot has to be tested.

## 4. Behaviour

### 4.1 Text parameter tool
- New module that rewrites the text parameter of a specific action (flow, event, key) and returns the new file, compressed like the others.
- If the size changes, it updates the flow's RSTB entry with a safe value, greater than or equal to what is needed.
- Round-trip tests: reading, changing and reading again gives the new text, and the rest of the flow stays the same.
- If the same flow is also modified by "Skip cutscenes", both changes are applied to the same bytes and a single file is written. Scene trimming only changes indices, so both cases can coexist.

### 4.2 Locations and logic
- Each new location is mapped to its OoTR location (`locations.json`) in a versioned data file: flow, event, parameter key and original item.
- OoTR's logic is loaded with the corresponding settings (`shuffle_ocarinas`, `shuffle_gerudo_card`, `shuffle_beans`, `shuffle_expensive_merchants`, `shuffle_100_skulltula_rupees` and similar for the Skulltula rewards, `shuffle_loach_reward`, `shuffle_frog_song_rupees`, `shuffle_child_trade` / `adult_trade_shuffle`; the exact names come from the vendored OoTR settings). With a setting off, its location keeps the original item.
- The original items of those locations enter the set of items to be distributed when their option is on.

### 4.3 Page and spoiler log
- New "Shuffle" section in the Items tab, with one switch per option, in English with the OoTR name in parentheses.
- The settings are part of the RNG key, because they change the fill.
- The spoiler log lists the new locations with their item.

### 4.4 Phases (each with its Lichii test before continuing)
- **A.** Text tool, plus an in-game test: the 10 Skulltulas reward gives a different key item. If an `Item_*` delivered this way does not work, stop and rethink.
- **B.** Ocarinas, Gerudo Card, Skulltula rewards, frogs' Piece of Heart and Loach.
- **C.** Beans and expensive merchants: repeatable gifts and charges.
- **D.** Child and adult trades.

## 5. Done when

- The options exist on the page and in the spoiler log.
- Each phase has its test batch passed in Lichii.
- The tests pass.
- A seed with everything on can be played through to Ganon following the logic.

## 6. Left to whoever builds it

- How to rewrite texts in BFEVFL (reuse strings or extend the file).
- The exact list of locations and the confirmation of each one in the data.
- How to make a repeatable gift give the fill's item only once, for example with a flag that already exists. If there is no safe way, that location is left out and documented.
- If an option turns out to be unviable in its phase, it is documented and left out without blocking the others.

## 7. Decisions after review (my decision, not the user's)

- **Which items can go in a gift:** only those delivered as `Item_*`:
  - the key items of the current fill;
  - the original `Item_*` of the enabled locations (ocarinas, Gerudo Card, Medigoron's sword…).

  The minor originals (rupees from fishing or from the 100 Skulltulas, frogs' Piece of Heart) are treated like the content of a rupee chest in v1: the location can receive a key item, and its minor item is resolved as the fill already does today. This is fixed in phase A with a test.
- **If phase A fails** (a different `Item_*` is not delivered properly by a scene), the project stops and goes back to the user. Phases B, C and D are planned but not built until A passes.
- **RSTB:** reusing a string that already exists in the flow is preferred, so the size does not change. If the file has to be extended, an RSTB value with a generous margin is used, because the table is an upper bound and larger values have already been shown to work.
- **Phases C and D** (repeatable gifts, charges and trades): they start with a short investigation. If there is no safe way (existing flag, per-character parameter), the location is left out and documented.
- **Shared scenes:** only what belongs to a single character or location is changed. If the parameter is in a shared event with no way to tell who calls it, that location is left out.
- **Logic:** each location must exist in the vendored `locations.json`, and each setting in the vendored OoTR settings. If any is missing, the location is left out and documented.
- **Compatibility:** with all the switches off, the RNG key and the generated mod are identical to today's. The new settings only enter the key when they are on. A test checks this.
