# Test batch 24: song scenes giving any item (Anywhere)

Part of "Shuffle Songs: Anywhere" (design `docs/superpowers/specs/2026-11-14-songs-anywhere-design.md`). When a song scene gives something that is not a song, the patch:

- **bypasses its lesson**, because the lesson's end adds the melody just played to the pouch. An emptied fork branch now points at its fork's join;
- in the crater, **bypasses the `IsGet.Item_Melody_FireBolero` set**.

Built with `tools/make_song_batch.py <nup> <out> 24a|24b`. Each variant teleports next to its scene, so each needs its own new game.

| Variant | Scene | Normally | In this batch | Full skip |
|---|---|---|---|---|
| `TestBatch24a` | Impa | Zelda's Lullaby | **Deku Shield** (`TBox_Shield_Deku`) | **off**, on purpose: the lesson bypass only happens without the skip |
| `TestBatch24b` | Sheik in the crater (adult) | Bolero of Fire | **Hookshot** | on |

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] **24a:**
  - Copy `TestBatch24a` to `load/0400486024DEC000/`, start a **new game** and leave the house: you get the Fairy Ocarina and appear in the castle courtyard.
  - Walk up to Zelda (her full scene plays, with no skip), then go to Impa.
- [ ] **24b:**
  - Replace it with `TestBatch24b`, start **another new game** and leave the house: you become an adult at the crater warp pad, with the Ocarina of Time and the Goron Tunic.
  - There is **no Hookshot** this time; Sheik should give it.

## Check

24a, Impa (without the skip):

- [ ] Does her scene play without a lesson (no notes to watch or repeat)? ______
- [ ] Does it end cleanly, with no hang? ______
- [ ] Do you get the **Deku Shield** (message, then equipped or in the inventory)? ______
- [ ] Do you **not** get Zelda's Lullaby (check the song list)? ______

24b, crater:

- [ ] Does Sheik appear and his scene play without a lesson? ______
- [ ] Do you get the **Hookshot**, and can you use it to leave the warp pad's ledge? ______
- [ ] Do you **not** get the Bolero of Fire? ______

In general:

- [ ] Did the game hang or show a black screen? When? ______

## Results

(To be filled in after testing.)
