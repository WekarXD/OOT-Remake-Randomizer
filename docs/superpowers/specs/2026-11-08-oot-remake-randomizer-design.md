# Randomizer for The Legend of Zelda: Ocarina of Time (Switch 2 remake) — Design v1

Date: 2026-11-08 · Status: draft for approval

## 1. What it is and why

An item randomizer for the Switch 2 remake of Ocarina of Time, played in the **Lichii** emulator. It changes which item each chest gives so that every playthrough is different. At the same time, a **logic engine guarantees the game can be completed** without glitches.

The user wants to play randomized runs of the remake in the style of the classic OoT randomizers (OoTR). None exists for the remake.

**How it is used:** a local application with a web interface. You pick your game dump, adjust what gets randomized, enter or generate a seed and press **Generate**. The output is a mod folder that Lichii loads, plus a spoiler log.

## 2. Goals, non-goals and anti-goals

**v1 goals**
- Randomize the **key items that are currently in chests** (list in §5.2) among **any chest in the game**, including rupee chests. User decision.
- Logic guarantees that every generated seed can be completed without glitches.
- Reproducibility: the same seed, the same settings and the same randomizer version give exactly the same result.
- Spoiler log showing where each item went.
- Local web interface with tabs, in the style of OoTR (mockup "B", chosen by the user).

**v1 non-goals** (the user wants to extend this later; the architecture must not prevent it)
- Items obtained from events or NPCs: ocarina, songs, bottles, Goron bracelet, scales, Fire and Light Arrows, magic, medallions and stones, minigame Pieces of Heart. They stay in their usual place.
- Small keys, boss keys, maps and compasses: they stay where they are.
- Pots, grass, rocks, enemies and other places that drop something but are not chests.
- Entrance randomization, hints, multiworld, logic with glitches, real console, modifying or repacking the `.nup`.

**Anti-goals** (even if it "works", it would be a failure)
- Generating a seed that cannot be completed.
- Modifying the user's `.nup`. It is only read.
- The application including or distributing game files. They are always derived from the user's own dump on their machine.

## 3. Constraints and already verified facts

Verified with working prototypes in `spikes/` and **tested in Lichii by the user**:

- **Input**: a single `.nup` (an open community format, see `a55uka/nup` SPEC.md). The user's is `The Legend of Zelda Ocarina of Time [0400486024DEC000][v131072].nup`, about 25 GB. It contains two packages: the base (1.0.0) and the v131072 update (1.1.1), each with a complete RomFS tree. **The update's files are always used** (`p1/` in `spikes/nuplist.py`). It is not encrypted. Each file is stored raw or compressed with zstd and can be read directly by its offset, without extracting the 24 GB.
- **Engine**: it is the same as Tears of the Kingdom, with the same formats.
- **Chest contents**: they are in `romfs/Banc/<Zone>/*.bcett.byml.zs`. These are BYML v7 files compressed with zstd using the dictionary `bcett.byml.zsdic`, which is inside `romfs/Pack/ZsDic.pack.zs` (a SARC compressed with zstd without a dictionary). Each chest is an entry of `Actors[]` with:
  - `Gyaml`: actor type (`Obj_TBox_A_01`, `Obj_TBox_A_02_NoBake`...),
  - `Hash`: u64 identifier of the location,
  - `Dynamic.Drop__DropActor`: **the item it gives**, as text (for example `Item_Hookshot` or `TBox_Rupee_Blue`),
  - `Dynamic.GetEventName`: an optional event that is triggered when the chest is opened.
- **Writing**: `spikes/byml.py` reads and writes BYML preserving the exact types. All 160 maps pass the round-trip test with no differences. The resulting file is recompressed with the same dictionary.
- **Size table**: if a map changes size, its entry must be updated in `romfs/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs`. It is a RESTBL v1 compressed with zstd without a dictionary, with sorted pairs of `crc32(path without .zs)` and u32, plus a small name table. For maps, the value is `round_up_32(uncompressed_size) + 264`, a formula that matches exactly on all 160 maps.
- **Output**: a LayeredFS folder `<ModName>/romfs/<same path as in the game>`, inside Lichii's mods folder `load/0400486024DEC000/`. It contains only the modified files: the touched maps and the size table.
- **Tested in game**:
  1. Swapping the contents of two chests in the same map works.
  2. Putting an item into a map that did not have it (the Hookshot in a blue chest in Mido's house) works, by rewriting the whole map and updating the size table.
- **Environment**: Windows and Python 3.14, which ships with `compression.zstd`. During the design session third-party packages could not be installed with pip, but the user can.

## 4. Chest inventory (real data)

- 238 chest actors with `Drop__DropActor` across the 160 maps, corresponding to **203 distinct `Hash` values**. The same physical chest can appear in several files (for example in the `*_Child_*` and `*_Adult_*` maps) with the **same `Hash`**. **A logical location is one `Hash`**, and all its copies must always receive the same item.
- Chest types: `Obj_TBox_A_01` (+`_NoBake`, `_memo11`), `Obj_TBox_A_02` (+`_NoBake`), `Obj_TBox_A_03` (+`_NoBake`), `Obj_TBox_A_06`, `Obj_TBox_GlassTruth_A_01` (invisible chests) and `Obj_HrlCity_Shop_TBox_A_01/_02` (the chest minigame in Market Square).
- The full dump of what each thing drops is in `spikes/drops.json`.

## 5. v1 behaviour

### 5.1 Locations
- **Locations that can receive key items**: all chests (one location per `Hash`), except:
  - the Market Square minigame chests (`Obj_HrlCity_Shop_TBox_*`), *(my decision: their content depends on the minigame)*;
  - chests whose original content is a dungeon item (`Item_Dungeon_SmallKey`, `Item_Dungeon_BossKey`, `Item_Dungeon_Map`, `Item_Dungeon_Compass`, `Obj_MiniGame_SmallKey`, `Obj_Dungeon_SmallKey_*`). *My decision: those items do not move in v1, so their chest cannot be taken either.*
  - If a location cannot be reliably mapped to a logic location (§6), it is left out of the fill and keeps its original content.
- For the user, the result is "key items in any chest, including rupee chests". The exceptions above are indicated in the interface and in the spoiler log.

### 5.2 Key items in the fill
Those currently in chests: `Item_Sword_Kokiri`, `Item_Range_SlingShot`, `Item_Boomerang`, `Item_Range_Bow`, `Item_Hookshot`, `Item_Longshot`, `Item_Hammer`, `Item_HeavyBoot`, `Item_HoverBoot`, `Item_Gauntlet_Silver`, `Item_Gauntlet_Gold`, `Item_GlassTruth`, `Item_Shield_Mirror`, `Item_Arrow_Ice` and `Item_BombBag_Small`. That makes 15 original locations.

### 5.3 Fill
- Key items are placed by the logic in any allowed location.
- **Nothing is lost or duplicated**: the rest of the contents of the fill locations (rupees, ammo, hearts, shields, etc.) is shuffled into the remaining slots, including the chests that originally held key items. The total number of items in the game does not change.
- Items tab: with "Excluded items", the user can mark key items that stay in their original chest.

### 5.4 Logic
- No glitches. The rest of the world behaves like the original game, with the forest closed, the normal Door of Time, songs in their places, etc. Event items are fixed and the logic treats them as obtained at their original location, with their requirements.
- The user confirms that **the way to progress in the remake is the same as in the original**. Therefore **the logic starts from OoTR's** (`OoTRandomizer/OoT-Randomizer`, region and rule files, Python, GPL-3.0), configured to reproduce the original game except for key items in chests.
- License consequence: if its files are reused, this project is published under GPL-3.0.
- Progressive items and items that depend on others must be taken into account: the Longshot and the Hookshot, the Silver/Golden Gauntlets and the Goron bracelet (which is fixed, from an event), and the Bomb Bag as a requirement for bombs. See risk R2.
- Every seed passes a final check: with the generated fill, simulate the game from the start and reach Ganon. If it fails, retry deterministically with the same seed, or abort with a clear error.

### 5.5 Output
- The mod folder is named `Rando_<seed>` and is written to the chosen output folder, by default Lichii's mods folder for this game.
- The spoiler log (human-readable, and also JSON) states the seed, the settings, the randomizer version, the detected game version and, for each location, the logic location, the map and the item. It marks which chests could not be mapped or were excluded.
- Generating never touches the `.nup`. If a folder with the same name already exists, the user is asked before overwriting it.

### 5.6 Interface (mockup B, with tabs)
It is a local application: the user starts it and it opens in the browser.
- **General**: path to the `.nup` (when chosen, it is validated and the detected game version is shown; v1 only supports 1.1.1 / v131072), output folder, seed with a 🎲 button and the **Generate** button.
- **Items**: "Key items" with the options *Vanilla* or *Any chest* (default *Any chest*) and "Excluded items" as checkboxes. Future categories (keys, maps and compasses, songs...) appear greyed out as "coming soon".
- **Logic**: "No glitches", fixed in v1 and informational only.
- **Spoiler**: enable or disable the log, and view the last one generated.
- On completion: a success message with the mod path, a link to the log and a reminder to disable other `Rando_*` mods for the same game, because they would conflict.

## 6. Mapping the remake's chests to OoTR locations

This is the largest data task. A versioned table `remake Hash → OoTR location name` (for example `Deku Tree Slingshot Chest`) is built semi-automatically from the map (`Banc/<Zone>`), the original content, the `GetEventName` and the position. It is then reviewed by hand and doubtful cases are marked to be checked by playing. Chests with no OoTR equivalent are handled as in §5.1.

## 7. Technical risks (check at the start of the build)

- **R1. Events tied to chests.** **14 of the 15** key item chests have a story `GetEventName`; the Boomerang's is the only one that does not. Some examples: `SageOfWater_MelodyGet_Water` (Iron Boots → Serenade of Water), `SageOfSpirit_NaboorIsTakenAway` (Silver Gauntlets), `SageOfShdawo_GetHoverBoots`, `Get_StoneOfForest_GetSword`, `MiniGame_DampeRace_OpenGoalTBox`. The **expected** behaviour is that the event stays tied to the chest (the location) and not to the item. It must be checked in game that (a) a chest with an event gives the new item and not the original one, and (b) the event still does its job, such as giving the song or advancing the story.
  - **User decision:** if an event hands out the original item on its own, **the event files are edited** (`Event/EventFlow/*.bfevfl.zs`) in v1 so that they give the new item, instead of leaving that chest fixed. This adds to v1 reading and writing BFEVFL and updating their entries in the size table.
  - **User decision:** if only the visuals fail (the scene or text shows the original item but you receive the new one), **it is accepted in v1** and there is no need to fix it or exclude the location.
- **R2. Progressive items and prerequisites.** We need to check what happens if the Longshot is obtained without the Hookshot, the Golden Gauntlets without the Silver ones, or the Mirror Shield or Ice Arrows ahead of time. The logic has to model what the game actually does, or the fill has to avoid those situations.
- **R3. Adult items in child locations and vice versa.** OoTR's logic handles this, but it should be checked in game that an adult item obtained as a child is saved correctly.
- **R4. Lichii mods.** The exact mods path and whether they need to be enabled in "Add-Ons" were deduced, not documented. It worked by copying `<Mod>/romfs/...` into the game's mods folder.

## 7b. In-game testing and audience

- **Only the user can play in Lichii.** *My decision:* the plan starts with a **batch of small test mods and a written checklist** that cover R1, R2 and R3 and the doubtful chests from §6. The results of that batch decide the scope before the logic and the fill are finalized. This avoids many rounds of testing a single chest.
- **Audience (user decision):** it is for personal use first; if it ends up working well, it may be published. For v1 that means:
  - it runs from source with Python 3.14 and as few external dependencies as possible, with no `.exe`;
  - the code has no hardcoded paths from the user's machine and validates the `.nup` (version and required files) with clear errors;
  - the GPL-3.0 license is prepared if OoTR's logic is reused, with the corresponding attribution;
  - the `Hash → location` table contains only identifiers and names, not game assets, so it can be distributed.

## 8. How we know it is done
- Automated tests: BYML passes the round trip on all 160 maps; the size table formula matches; the generator is deterministic (same seed, same result); and the check that the seed can be completed passes on hundreds of seeds.
- The user plays a complete seed in Lichii.

## 9. Left to whoever builds it
- The code structure, the local web server (standard library or a small dependency), the exact format of the spoiler log and the visual design of the tabs.
- How to incorporate OoTR's logic (copy its data or depend on it) and the fill algorithm (for example "assumed fill", like OoTR).
- The seed format.
- Whether to reuse or rewrite the code in `spikes/`. It works, but it was written as a prototype.
