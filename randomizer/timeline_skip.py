"""Skipping timeline cutscenes by shortening them (spike, full-skip spec §11).

A timeline holds presentation only (camera, animation, voices, lighting).
It is cut right after its opening fade-in (one starting in the first
`FADE_WINDOW` frames), or after one frame if it has none; the few clips
with a lasting effect that would start later are moved to just before the
new end so they still run.
"""
from .formats.timeline import Clip, Timeline, retime

# Clips whose effect outlives the scene: they must still run.
LASTING = frozenset({
    'EventWarpToTargetPosAndRot', 'EventWarpToHomeMatrix',
    'EventTriggerPlayerRestoreBootsChange', 'EventTriggerEquipmentUserRequestChangeState',
    'EventTriggerAIScheduleSelectSchedule', 'EventTriggerSetNaviAppear', 'EventTriggerSetFairyColor',
    'EventTriggerStartInGameBgm', 'EventTriggerSoundStartAreaBgm', 'EventTriggerStartBgmSimple',
    'EventTrigger_SetTime', 'EventOpenHeartGaugeAndRecoverForTimeline',
})
FADE_IN = 'EventEventFadeInForTimeline'
MIN_FRAMES = 1.0
FADE_WINDOW = 60.0  # 2 s at 30 fps
# The spike's timelines: Saria on the bridge, Navi just outside Link's house (before Saria),
# the scene with Zelda and Impa after the letter.
SPIKE_TIMELINES: tuple[str, ...] = ('Dm_Kokiri_0150', 'Dm_Kokiri_0050', 'Dm_HrlCastle_0060')
# Movie spikes (TestMovies2, TestMovies3): timelines chained to the movies. The Deku Tree's vision
# of Ganondorf, Navi flying to Link's house after the intro, the Deku Tree after giving the
# Kokiri Emerald, Zelda meeting Link in the garden.
# (Movies are not shortened: their .webm plays on regardless, see movie_skip.py.)
MOVIE_SPIKE_TIMELINES: tuple[str, ...] = ('Dm_Kokiri_0090', 'Dm_Kokiri_0030', 'Dm_Kokiri_0140',
                                          'Dm_HrlCastle_0030')


def new_length(tl: Timeline) -> float:
    """End of the fade-in that opens the timeline, or one frame."""
    ends = [c.start + c.duration for c in tl.clips if c.action == FADE_IN and c.start <= FADE_WINDOW]
    return min(max(ends, default=MIN_FRAMES), tl.duration)


def moved_clips(tl: Timeline, length: float) -> list[Clip]:
    """Lasting clips that would start at or after the new end."""
    return [c for c in tl.clips if c.action in LASTING and c.start >= length]


def shorten(data: bytes) -> bytes:
    tl = Timeline(data)
    length = new_length(tl)
    last = max(length - 1.0, 0.0)
    return retime(data, length, {c.offset: (last, 1.0) for c in moved_clips(tl, length)})


def build_timeline_spike_files(nup, names=SPIKE_TIMELINES) -> dict[str, bytes]:
    """romfs path -> compressed bytes for the given timelines and their subtimelines, shortened."""
    from .formats.zs import ZsCodec
    codec = ZsCodec.from_archive(nup)
    files = {}
    todo = list(names)
    while todo:
        name = todo.pop(0)
        path = f'Event/EventFlow/{name}.bfevfl.zs'
        if path in files or not nup.has(path):
            continue
        data = codec.decompress(path, nup.read(path))
        todo += Timeline(data).subtimelines
        files[path] = codec.compress(path, shorten(data))
    return files
