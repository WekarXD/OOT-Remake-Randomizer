# Song Locations: acceptance seed

The first seed with **Shuffle Songs: Song Locations** (plan `docs/superpowers/plans/2026-11-14-song-locations.md`). Batch 22 (`docs/test-batch-22.md`) already confirmed the two scene patches (windmill, crater), the lesson-end retarget for a song of the other group, and the adult start preset. This seed checks the full option as the site builds it.

## Setup

- [ ] Remove any other `Rando_*`, `TestBatch*` or `TestScenes*` mod.
- [ ] Generate (or copy from `output/`) `Rando_CANCIONES1`: seed `CANCIONES1`, key items Any chest, **Skip cutscenes on**, **Shuffle Songs: Song Locations**. Copy it to `load/0400486024DEC000/` and start a **new game**.

## Where each song is (from the spoiler log)

| Location | Gives |
|---|---|
| Song from Impa | Zelda's Lullaby (unchanged) |
| Song from Saria | **Serenade of Water** |
| Song from Malon | **Song of Time** |
| Song from Royal Family's Tomb | **Requiem of Spirit** |
| Song from Ocarina of Time | **Song of Storms** |
| Song from Windmill | **Sun's Song** |
| Sheik in Forest | Minuet of Forest (unchanged) |
| Sheik in Crater | **Epona's Song** |
| Sheik in Ice Cavern | **Saria's Song** |
| Sheik at Colossus | **Bolero of Fire** |
| Sheik in Kakariko | **Prelude of Light** |
| Sheik at Temple | **Nocturne of Shadow** |

## Check

As far as is practical. The childhood ones come first:

- [x] Saria gives the **Serenade of Water**, a warp song from a normal-song scene. No hang? Does it warp to Lake Hylia? Yes, no hang, and it warps to the lake.
- [x] Malon gives the **Song of Time**. Yes.
- [x] The Royal Family's Tomb gives the **Requiem of Spirit**. Does it warp to the Colossus? Yes, and it warps to the Colossus.
- [ ] The Ocarina of Time scene gives **Song of Storms** (plus the Ocarina of Time). ______
- [ ] Any scene that did not start, or hung? Which, and what had you done just before? ______
- [ ] As an adult, if you get there: the windmill gives **Sun's Song**, and the Sheik scenes give the songs above. ______
- [ ] Does any song stop working, or appear twice? ______

## Results

Partial (2026-11-14): the three childhood swaps work (Saria → Serenade, Malon → Song of Time, Royal Family's Tomb → Requiem), including warp songs taught by normal-song scenes. The Ocarina of Time scene and the adult scenes are still to be checked.

**Accepted** by the user on 2026-11-14 without checking the rest (batch 22 covers the adult patches); released on `main` (8496244).
