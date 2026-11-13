# Test batch 19: OoTR item types from a chest

OoTR shuffles about 60 item types that this randomizer does not: songs, Great Fairy gifts, magic, bottles, scales, wallets, tunics and more. Almost none of them come from a chest in the original game. Before building their locations, this batch checks whether each type **works when it comes from a chest**, because the Bomb Bag does not.

It also tests a theory about the Bomb Bag: bombs cannot be thrown outside its original chest perhaps only because the **Goron's Bracelet** is not owned yet.

The rest of the game is vanilla.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch19` to `load/0400486024DEC000/`.
- [ ] Start a **new game**.

## What changes

| Chest | Gives | Normally |
|---|---|---|
| Mido's house, top left | **Song of Storms** | Blue rupee |
| Mido's house, top right | **Din's Fire** | Blue rupee |
| Mido's house, bottom right | **Magic meter** | Blue rupee |
| Mido's house, bottom left | **Bomb Bag**: do NOT open it until you have the Goron's Bracelet | Green rupee |
| Deku Tree, side chest in the Slingshot room | **Adult's Wallet** | Deku nuts |
| Deku Tree, side chest in the compass room | **Silver Scale** | Deku nuts |
| Deku Tree, basement chest | **Empty bottle** | Deku sticks |

## Check

Mido's house (before the Deku Tree):

- [ ] Open **Din's Fire first** (top right), before the magic. Is it in the inventory? Can you cast it with no magic meter? ______
- [ ] Open the **magic** (bottom right). Does the magic meter appear? Can Din's Fire be cast now? ______
- [ ] **Song of Storms** (top left): is it in the song list? Once you have the Fairy Ocarina, can you play it, and does it rain? ______

Deku Tree:

- [ ] **Wallet:** does the rupee limit go from 99 to 200? ______
- [ ] **Silver Scale:** is it in the inventory? Can you dive deeper (Zora's River or Zora's Domain)? ______
- [ ] **Bottle:** is it in the inventory? Can you catch a fairy or a bug and use it? ______

Bomb Bag (after the Goron's Bracelet: Zelda's Lullaby, then Darunia, **without entering Dodongo's Cavern**):

- [ ] Open the bottom left chest in Mido's house. Does the Bomb Bag appear? Can you **throw** bombs? ______

In general:

- [ ] Does the "you got it" message or animation show the right item, or the original one? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

In-game results (2026-11-13): **every type works from a chest.**

- **Din's Fire:** reaches the inventory and can be cast. In the remake, the first magic item also gives the magic meter.
- **`Item_FairyBless_MP`** is not the magic meter: it gives the **spin attack** (Great Fairy blessing).
- **Song of Storms:** the chest shows a rupee, but the song is learned and works (the known chest image issue).
- **Wallet:** works. The remake's wallets are larger: 200 at the start, 500 with the first upgrade.
- **Silver Scale** and **bottle:** reach the inventory and work.
- **Bomb Bag:** taken at the start; bombs could not be thrown until the **Goron's Bracelet** was obtained, and then they could. The v1 failure was not the chest: in the remake, bombs need the bracelet.

Consequences:

1. The Bomb Bag can be shuffled again, provided the logic requires the Goron's Bracelet to use bombs.
2. Magic: no item gives only the meter. The logic should treat any magic item (Din's, Farore's, Nayru's, the magic arrows) as also giving it.
3. Songs, Great Fairy gifts, wallets, scales and bottles can go in chests.
