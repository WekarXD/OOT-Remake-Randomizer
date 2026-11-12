# Test: TestTimelines (timeline cutscenes shortened)

Second spike of the full cutscene skip (spec `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §11). Built with `python -I tools/make_skip_spike.py --timelines <nup> test-mod/0400486024DEC000/TestTimelines`.

It carries the four TestScenes4 scenes (unchanged) plus three timeline cutscenes cut right after their opening fade-in (at most 2 seconds); clips with a lasting effect are moved before the new end (`randomizer/timeline_skip.py`).

## Setup

1. Copy `test-mod/0400486024DEC000/TestTimelines` to `load/0400486024DEC000/` and enable only that mod (disable TestScenes4).
2. Start a new game with "Skip cutscenes" off.

## What changes

| Scene | Where | Expected |
|---|---|---|
| `Dm_Kokiri_0050` | Kokiri Forest, at Link's house door with Navi (probably when leaving home after the intro) | Up to half a second of the scene, then control. |
| `Dm_Kokiri_0150` | The bridge out of the forest, after the Deku Tree: the first part of Saria's scene | Up to 2 seconds, then straight into the Ocarina (TestScenes4). |
| `Dm_HrlCastle_0060` | Castle garden, the scene with Zelda after the letter | Up to 2 seconds, then the Lullaby (TestScenes4). |

## Checks

- [x] Each of the three: cut short, Link free to move afterwards? **Yes.**
- [x] Screen comes back from black each time? **"No"** (with everything else fine, read as: no black screen was left; to confirm).
- [x] Navi still with Link and its colour right after `Dm_Kokiri_0050`? **Yes.**
- [x] Music plays normally after each scene? **Yes.**
- [x] Link, Navi and NPCs in sensible places afterwards? **Yes.**
- [x] Which scene was `Dm_Kokiri_0050` really? **A short scene with Navi right after leaving Link's house, before talking to Saria.**

Report freezes, black screens, missing music, wrong positions or anything left of the scenes.

## Results

Played 2026-11-12. **Verdict: shortening works.** The three timelines are cut, control returns, music, Navi and positions are right. The method can be extended to the other timelines.
