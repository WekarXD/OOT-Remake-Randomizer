# Randomizer OOT Remake

A local Python randomizer for the Switch 2 remake of Ocarina of Time (TotK engine), meant to be played in the Lichii emulator. It is a web application that runs on your machine and generates a mod that moves key items around.

It includes no game files: you need your own dump.

## Requirements

- Python 3.14 or later (uses `compression.zstd` from the standard library).
- Your own dump of the game in `.nup` format, version 1.1.1 (v131072).
- The Lichii emulator.

## Usage

```
python -m randomizer
```

This opens the interface in your browser. Options: `--port <number>` (default 8765) and `--no-browser` (do not open the browser). Choose the `.nup`, the seed and the settings, then click generate. The mod is created in a `Rando_<seed>` folder.

- **Skip cutscenes**: removes the visual steps of the cutscenes in phase 1 (the rest of the game is unchanged).
- **Gold Skulltula Tokens (Tokensanity)**: Off, Dungeons Only, Overworld Only or All Tokens. The Gold Skulltulas in that area join the fill: they can drop key items (which stay floating and are picked up by walking over them or with the Hookshot or Boomerang) or minor items, and their tokens are spread across chests and Skulltulas. The 27 Skulltulas that are not yet identified with certainty do not receive key items.

Source code: https://github.com/WekarXD/OOT-Remake-Randomizer

## Installing the mod in Lichii

1. Copy the `Rando_<seed>` folder (with its `romfs`) to `load/0400486024DEC000/Rando_<seed>/romfs/...` inside Lichii's data folder. If Lichii offers an option to open the game's mod folder (right-click the game), use it; otherwise look for the load/0400486024DEC000/ folder inside Lichii's data folder (its location depends on your installation).
2. Keep **only one** `Rando_*` mod active at a time; remove or disable the others.
3. Start a new game (an existing save will not reflect the change).

To play it following a checklist, see `docs/acceptance.md`.

## v1 limitations

- **8 key items are moved:** Kokiri Sword, Slingshot, Bow, Megaton Hammer, Lens of Truth, Ice Arrows, Golden Gauntlets and Longshot.
- **7 stay in place:** Boomerang, Hookshot, Iron Boots, Hover Boots, Silver Gauntlets and Mirror Shield, because their chests carry story events, and the Bomb Bag, because bombs cannot be thrown outside its own chest (under investigation).
- Only 104 of the 203 chests are mapped to the logic; the rest keep their original contents.
- Keys, maps, compasses, songs and NPC items are not randomized.
- The chest image and text may still show the original item (accepted in v1); what you receive is the new item.
- Ice Arrows also unlock the magic meter.
- Key items are not placed in the Water Temple, the Fire Temple, the Well or the Gerudo Training Ground in this version.
- The logic is OoTR's glitchless logic, with some remake-specific rules where the remake is stricter (`REMAKE_RULES` in `randomizer/logic/world.py`; for example, the upper floor of the Deku Tree compass room requires a ranged weapon).

## Tests

```
REM cmd:
set OOT_NUP=C:\path\to\game.nup
# PowerShell:
$env:OOT_NUP="C:\path\to\game.nup"
python -m unittest
```

With `OOT_NUP` set, no test is skipped. There is one documented expected failure: `test_vanilla_is_beatable`, because OoTR's glitchless logic cannot prove the fully vanilla key distribution beatable; it is not a bug.

## Test mod batch

```
python -I spikes/nuplist.py "<game.nup>" output/files.tsv
python -I tools/make_test_batch.py "<game.nup>" output/files.tsv test-mod
```

Creates `test-mod/0400486024DEC000/TestBatch1` and `TestBatch2`. Instructions: `docs/test-batch-1.md`.

## Attribution and license

The location and item logic comes from the Ocarina of Time Randomizer (OoTR), commit 526b4c8, and is used under GPL-3.0. This project is distributed under GPL-3.0 (see LICENSE).
