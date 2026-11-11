# Test scenes 4: full cutscene skip spike

Goal: check in-game that four cutscenes can be reduced to their effects only (items, flags, warps) with no scene at all, without freezing or breaking the game. If this works, the full skip is built on top of it; nothing else is built until you report.

## Setup

- Copy `test-mod/0400486024DEC000/TestScenes4` to Lichii's `load/0400486024DEC000/` folder.
- Keep **only this mod active**. Disable every other `Rando_*`, `TestBatch*` and `TestScenes*` mod.
- Start a **new game** with "Skip cutscenes" **off**: the mod carries the four scenes itself.
- The scenes play from vanilla save progress. In a new game you reach them in this order:
  1. Saria's ocarina scene, when you leave Kokiri Forest by the bridge after the Deku Tree.
  2. Hyrule Castle: Zelda in the garden (the letter), then Zelda's Lullaby.

## What should happen

| Scene | Expected |
| --- | --- |
| Saria gives the Fairy Ocarina (`Dm_Kokiri_0155`) | You get the Fairy Ocarina, with no scene and no item window. |
| The Deku Tree's death (`Dm_Kokiri_0060`) | No scene. Link is not frozen and can move right away. |
| Zelda in the castle garden (`Dm_HrlCastle_0050`) | You get Zelda's Letter, with no scene. |
| Zelda's Lullaby (`Dm_MelodyGet_Zelda`) | You learn the song with no play-along. The "You got" window may still show (spec section 8.7). |

## Checks

- [ ] Saria: Fairy Ocarina in the inventory? ______
- [ ] Saria: no scene and no item window? ______
- [ ] Deku Tree: no scene, Link free to move? ______
- [ ] Garden: Zelda's Letter in the inventory? ______
- [ ] Lullaby: song learned (shows in the ocarina menu, plays)? ______
- [ ] Does the "You got" window show for the Ocarina? ______
- [ ] Does the "You got" window show for the Lullaby? ______

Report any of the following, with the scene and where it happened:

- **Freeze:** the game or Link stops responding.
- **Missing item, song or flag:** something that should have been given is not there, or an event that should have been marked (for example, Saria still talking as if nothing happened) did not change.
- **Wrong position:** Link, Navi or an NPC ends up in a place different from where they were in the vanilla scene.
- **Black screen:** a fade that does not come back.
- **Leftovers:** any visible remainder of the scene (a dialogue box, camera movement, a character left posing).

## Results

Notes: ______
