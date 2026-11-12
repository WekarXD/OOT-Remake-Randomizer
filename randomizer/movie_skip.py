"""Skipping movie cutscenes (spike, full-skip spec §11).

A movie (`Event/Movie/<name>.webm`, EventSetting derived from
`RecordMovieTimelineEvent`) plays for its own length: shortening its timeline
does not stop it (TestMovies, 2026-11-12). Its timeline only holds voices,
rumble and fades, so the scene is skipped by removing the `EventTransition`
that starts it from the flow that calls it; whatever came after it runs
straight away.
"""
from .evtrim import compute_trim
from .formats.bfevfl import END, EventFlow, patch_pointers

TRANSITION = 'EventTransition'
# Movie -> the flow that starts it: the intro, the Deku Tree after Gohma, Zelda's story.
SPIKE_MOVIES: dict[str, str] = {
    'Dm_Kokiri_0000': 'OpeningEvent',
    'Dm_Kokiri_0095': 'Dm_SY_BancChange_EscapeDungeon',
    'Dm_HrlCastle_0045': 'Goto_HyruleCastle',
}


def transitions_to(flow: EventFlow, names) -> set[int]:
    """Indices of the `EventTransition` events that start one of `names`."""
    return {i for i, ev in enumerate(flow.events)
            if ev.action == TRANSITION and flow.action_params(i).get('EventName') in names}


def drop_transitions(data: bytes, names) -> bytes:
    """The flow with every transition to `names` removed (same length).

    Raises ValueError if there is none, or if one cannot be removed (it is the
    only event of an entry or branch, which would leave a dangling pointer).
    """
    flow = EventFlow(data)
    wanted = transitions_to(flow, names)
    if not wanted:
        raise ValueError(f'No transition to {sorted(names)}.')
    roots = {i for i in flow.entry_points.values() if i != END}
    removed, retarget = compute_trim(flow.events, wanted, roots)
    if removed != wanted:
        raise ValueError(f'Cannot remove transitions {sorted(wanted - removed)}.')
    return patch_pointers(data, {off: retarget[i] for off, i in flow.pointer_slots() if i in removed})


def build_movie_spike_files(nup, movies=SPIKE_MOVIES) -> dict[str, bytes]:
    """romfs path -> compressed bytes of the calling flows with the movies removed."""
    from .formats.zs import ZsCodec
    codec = ZsCodec.from_archive(nup)
    by_flow: dict[str, set[str]] = {}
    for movie, flow in movies.items():
        by_flow.setdefault(flow, set()).add(movie)
    files = {}
    for flow, names in sorted(by_flow.items()):
        path = f'Event/EventFlow/{flow}.bfevfl.zs'
        files[path] = codec.compress(path, drop_transitions(codec.decompress(path, nup.read(path)), names))
    return files
