# Acceptance: Great Fairy rewards in the pool

Design `docs/superpowers/specs/2026-11-15-great-fairies-design.md`; plan `docs/superpowers/plans/2026-11-15-great-fairies.md`. Test batch 26 (`docs/test-batch-26.md`) proved the patches with a teleport. This seed checks them in a normal generated game.

Seed `HADAS1`: key items "Any chest", Skip cutscenes on, spoiler on. It is in `test-mod/0400486024DEC000/Rando_HADAS1`. Its fountains:

| Fountain | Gives |
|---|---|
| Top of Death Mountain (Din's flow) | Blue rupees (`TBox_Rupee_Blue`), a minor item |
| Hyrule Castle (Power's flow) | Farore's Wind |
| Death Mountain Crater (Wisdom) | Din's Fire |
| Desert Colossus (Nayru) | Red rupees (`TBox_Rupee_Red`) |
| Outside Ganon's Castle (Courage) | Double Defense (its own) |
| Zora's Fountain (Frore) | Red rupees (`TBox_Rupee_Red`) |

The other rewards: Double Magic is in the Deku Tree Slingshot Chest, the Magic Meter in the Shadow Temple, and Nayru's Love in Ganon's Castle (Light Trial).

## Check

- [ ] Top of Death Mountain: does the fairy appear without Din's Fire, and give the blue rupees (message, rupee count) without charging? On a second visit, does she only heal? ______
- [ ] Hyrule Castle: Farore's Wind, with no spin attack guide; does the magic bar appear? ______
- [ ] Crater (adult), if reached: Din's Fire? ______
- [ ] Any hang or black screen at a fountain? ______
