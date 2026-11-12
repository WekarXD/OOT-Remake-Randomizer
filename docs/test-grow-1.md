# Test: TestGrow1 (growing an event flow file)

Spike for the forced conversations that share events with player-started ones (spec §8.1, §12): their rewrite needs private copies of shared events, and the game files have no free slots, so the file must grow.

This mod changes no behaviour. Three Kokiri Forest NPC flows (`Npc_Kokiri_006_Child` targeting tutorial, `Npc_Kokiri_007_Child` exit Kokiri, `Npc_Kokiri_Mido_Child` Mido) are grown: the event array is moved to the end of the file with 8 extra unused event slots, the relocation table (RELT) is rebuilt to cover the moved pointers, and the RSTB entries get the new sizes. The RELT format was confirmed by rebuilding the originals byte for byte. Built with a scratch script (not committed).

If the game accepts these files, the next step uses the new slots for the rewrite's copies.

## Setup

1. Copy `test-mod/0400486024DEC000/TestGrow1` to `load/0400486024DEC000/` (Lichii) and enable **only** that mod.
2. Start a new game (the intro plays; this mod skips nothing).

## Checks

- [ ] The game loads Kokiri Forest without crashing? ______
- [ ] Targeting tutorial Kokiri: talks as in the original game? ______
- [ ] Mido blocking the Deku Tree: talks as in the original game, and lets you pass with sword and shield? ______
- [ ] Kokiri at the forest exit: talks as in the original game? ______

## Results

Played 2026-11-12. **Verdict: the game accepts grown flow files.** Kokiri Forest loads, the targeting tutorial Kokiri and Mido talk as in the original game (the exit Kokiri was not reached). Next: use the new slots for the rewrite's copies.
