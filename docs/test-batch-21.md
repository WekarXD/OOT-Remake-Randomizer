# Test batch 21: teleport on leaving the house (start-preset spike)

First test of the test teleport (`docs/superpowers/specs/2026-11-13-test-teleport-design.md`). The scene that plays when Link leaves his house for the first time (`Dm_Kokiri_0045`) is replaced by a chain of new events:

1. it sets the two flags that scene sets itself (so it does not replay);
2. it gives the **Fairy Ocarina**;
3. it teleports you to **Hyrule Field, by the Lost Woods bridge**.

The events are built from scratch by the new tool (`randomizer/formats/evfl_append.py`). If this works, each future test can start right where it is needed.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Copy `test-mod/0400486024DEC000/TestBatch21` to `load/0400486024DEC000/`.
- [ ] Start a **new game**. Let Navi wake Link and walk out of the house.

## Check

- [ ] When you leave the house, do you get the **Fairy Ocarina** (message or animation)? ______
- [ ] Are you teleported to **Hyrule Field by the Lost Woods bridge**? ______
- [ ] Is the Fairy Ocarina in the inventory, and can you play it? ______
- [ ] Does the game keep working: walk around, enter the Market? ______
- [ ] Go back to Kokiri Forest, enter Link's house and leave it again: are you teleported **again**? (It should not happen.) ______
- [ ] Is the rest of Kokiri Forest normal (Mido, Saria, the Deku Tree path)? ______
- [ ] Did the game hang or show a black screen? When? ______

## Results

Attempt 1 (2026-11-14): the door opened, then Link froze (music and leaves kept moving). Cause: every entry point lists the subflow events it reaches (true for all 5512 entries of the game), and the chain's calls were not listed. Fixed with `set_entry_subflows`; the mod was rebuilt for attempt 2.

Attempt 2 (2026-11-14): pressing the button did not open the door, and nothing froze (the event did not start). Cause: each event's row in `RSDB/GameAnalyzedEventInfo` lists in `SubFlowList` every flow its entries reach (recursively, sorted; 340 of 350 rows match exactly), and the hook's row had none. The batch now also writes that table.

Attempt 3 (2026-11-14): **works.** Leaving the house gives the Fairy Ocarina and teleports to Hyrule Field by the Lost Woods bridge. The ocarina is in the inventory and plays. The game runs normally (Market included). Back in Kokiri Forest the door stays open and leaving the house again does not teleport. The rest of the forest is normal.
