# Test: TestMovies2 (movies removed from the flows that start them)

Fourth spike of the full cutscene skip (spec `docs/superpowers/specs/2026-11-11-full-cutscene-skip-design.md` §11). Built with `python -I tools/make_skip_spike.py --movies <nup> test-mod/0400486024DEC000/TestMovies2`.

TestMovies showed that a movie ignores its timeline's length. This time the `EventTransition` that starts each movie is removed from the flow that calls it (`randomizer/movie_skip.py`), so the game goes straight to what came after. The scenes chained around two of the movies are skipped too.

It carries everything in TestTimelines plus:

| Scene | Where | How |
|---|---|---|
| `Dm_Kokiri_0000` (movie) | The intro of a new game | Removed from `OpeningEvent`. |
| `Dm_Kokiri_0080` | The Deku Tree's speech after Gohma (conversation) | Effects only. |
| `Dm_Kokiri_0095` (movie) | The rest of the Deku Tree's speech | Removed from `Dm_SY_BancChange_EscapeDungeon`. |
| `Dm_Kokiri_0090` | The Deku Tree's vision of Ganondorf (timeline) | Shortened. |
| `Dm_HrlCastle_0035` | Zelda's first scene in the garden | Effects only. |
| `Dm_HrlCastle_0045` (movie) | Zelda's story (the second Zelda scene) | Removed from `Goto_HyruleCastle`. |

## Setup

1. Copy `test-mod/0400486024DEC000/TestMovies2` to `load/0400486024DEC000/` and enable only that mod (disable TestMovies).
2. Start a new game with "Skip cutscenes" off.

## Checks

- [ ] New game: is the intro gone, and does Link wake up in his house as usual? ______
- [ ] After Gohma: is the Deku Tree's whole speech (conversation, movie, Ganondorf) gone? ______
- [ ] After Gohma: do you still get the Kokiri Emerald and end up outside the tree? ______
- [ ] Castle garden: are Zelda's first scene and her story gone, and does the Lullaby still come? ______
- [ ] Any freeze, black screen, or sound left playing? ______

## Results

Played 2026-11-12. **Verdict: removing the transition skips movies.**
- New game: the intro movie is gone; the loading screen is longer (the movie used to hide the forest loading). The next scene, `Dm_Kokiri_0030` (Navi flying to Link's house, a timeline), still plays: it was not in this batch.
- After Gohma: the speech, movie and Ganondorf vision are gone. Still left: `Dm_Kokiri_0130` (the conversation that gives the Kokiri Emerald) and `Dm_Kokiri_0140` (a timeline after it).
- Castle garden: one scene is gone, but `Dm_HrlCastle_0030` (Zelda meeting Link, a timeline before `0035`) still plays. The letter and the Lullaby are both received.
No freezes reported. The remaining scenes are in `MOVIE_SPIKE_TIMELINES` / `MOVIE_SPIKE_SCENES` (TestMovies3, built, not played).
