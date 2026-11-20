# Acceptance: NPC gifts (batch 1) in the pool

Design `docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md`; plan `docs/superpowers/plans/2026-11-20-npc-gifts-batch-1.md`. Test batches 27 and 28 (`docs/test-batch-27.md`) proved the patches with a teleport. This seed checks them in a normal generated game.

Seed `REGALOS1`: key items "Any chest", Skip cutscenes on, spoiler on. It is in `test-mod/0400486024DEC000/Rando_REGALOS1`.

Its gifts:

| Gift | Gives |
|---|---|
| HC Malon Egg | Goron's Bracelet |
| HC Zeldas Letter | Red rupees (`TBox_Rupee_Red`) |
| Kak Anju as Child | Ice Arrows |
| LH Underwater Item (Ruto's Letter) | Light Arrows (a floating wrapper) |
| GC Darunias Joy | Piece of Heart |
| GC Rolling Goron as Child | Bottle |
| Market 10 Big Poes | Nayru's Love |
| Market Lost Dog | Longshot |
| ZD King Zora Thawed | Fire Arrows |
| ToT Light Arrows Cutscene | Farore's Wind |

The Weird Egg is in the Dodongo's Cavern End of Bridge Chest and Zelda's Letter in the Graveyard Heart Piece Grave Chest.

## Check

- [ ] **Malon** (castle): she gives the Goron's Bracelet. Later, with the egg (Dodongo's Cavern), does it hatch and wake Talon? ______
- [ ] **Zelda**: she gives red rupees (special entry; her scene's `SubFlowList` gains `ActionGuide`). ______
- [ ] **Anju** (Kakariko, child): the Cuccos give the Ice Arrows. ______
- [ ] Optional, with the Silver Scale: Ruto's Letter is a floating Light Arrows. ______
- [ ] Any hang or black screen? ______
