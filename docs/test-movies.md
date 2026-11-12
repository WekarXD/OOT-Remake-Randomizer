# Test: TestMovies (movie cutscenes shortened)

Third spike of the full cutscene skip (spec `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §11). Built with `python -I tools/make_skip_spike.py --movies <nup> test-mod/0400486024DEC000/TestMovies`.

The 26 pre-rendered movies (`Event/Movie/*.webm`) are timelines too: their EventSetting derives from `RecordMovieTimelineEvent`, and their timeline holds only voices, rumble and fades. 18 have their own timeline; the 8 without one are the Royal Family Tomb wall (`Dm_MelodyGet_Sun_*`) and the title screen. This spike checks whether shortening the timeline also stops the movie.

It carries everything in TestTimelines (the four TestScenes4 scenes and the three timelines) plus three movies shortened the same way (`randomizer/timeline_skip.py`, `MOVIE_SPIKE_TIMELINES`). None of them has a fade-in at the start that lasts more than one frame, so each is cut to 1 frame.

## Setup

1. Copy `test-mod/0400486024DEC000/TestMovies` to `load/0400486024DEC000/` and enable only that mod (disable TestTimelines).
2. Start a new game with "Skip cutscenes" off.

## What changes

| Scene | Where | Original | Expected |
|---|---|---|---|
| `Dm_Kokiri_0000` | The intro of a new game (the Deku Tree, Navi flying to Link) | 5 min | Gone or a flash, then the game goes on. |
| `Dm_Kokiri_0095` | The Deku Tree's speech after beating Gohma | 3 min 55 s | Gone or a flash; the Kokiri Emerald and the exit still happen. |
| `Dm_HrlCastle_0045` | Zelda's story in the castle garden (the second Zelda scene) | 1 min 20 s | Gone or a flash, then the conversation goes on. |

## Checks

- [ ] Each of the three: does the movie stop (no picture, no voices left playing)? ______
- [ ] Does the game go on afterwards, with no freeze or black screen? ______
- [ ] After the intro: does Link wake up in his house as usual? ______
- [ ] After the Deku Tree: do you get the Kokiri Emerald and leave the tree as usual? ______
- [ ] Music and sound normal afterwards? ______

Report freezes, black screens, sound from the movie that keeps playing, or anything left of the scenes.

## Results

Notes: ______
