"""Song locations ("Shuffle Songs") and the edits that make a song scene give another song.

Each song is taught by one scene (`Dm_MelodyGet_*`). In it, the lesson is a pair of
`Dm_SY_Ocarina:LearningOcarina*` calls with a `MelodyType` int (the notes shown and the
notes you repeat), and the grant is a `GetPouchContent:GetPouchContentByActorName` call
with an `ActorName`. Batch 20: a scene gives whatever its grant names, even when you
already own its original song.
"""
from collections.abc import Callable
from dataclasses import dataclass

from randomizer.formats.bfevfl import SUBFLOW, EventFlow, set_int_param, set_string_param

SHUFFLE_SONGS = ('off', 'song_locations')
GRANT_CALL = ('GetPouchContent', 'GetPouchContentByActorName')
LESSON_FLOW, LESSON_PREFIX = 'Dm_SY_Ocarina', 'LearningOcarina'
# The crater's scene sets its song's flag itself (event 0, entry C21).
CRATER_FLOW = 'Dm_MelodyGet_Fire'
# The windmill man reads Song of Storms' flag four times, and the song-not-owned branch
# is the one that leads to his scene (and, from his Talk, to the quest step that sets
# it up). With Storm elsewhere he must ask whether his own scene has played instead.
WINDMILL_FLOW = 'Npc_Hylia_009_Adult'
WINDMILL_QUERIES = 4
WINDMILL_FLAG = 'HavePlayedEvent.Dm_MelodyGet_Storm'


@dataclass(frozen=True)
class SongLocation:
    location: str  # OoTR location
    song: str  # OoTR item name of the original song
    actor: str  # remake actor of the original song
    melody: int  # MelodyType of the original song's lesson
    flows: tuple[str, ...]  # flows holding the scene's lessons and grant


SONGS: tuple[SongLocation, ...] = (
    SongLocation('Song from Impa', 'Zeldas Lullaby', 'Item_Melody_ZeldaLullaby', 0,
                 ('Dm_MelodyGet_Zelda',)),
    SongLocation('Song from Malon', 'Eponas Song', 'Item_Melody_EponaSong', 1,
                 ('Dm_MelodyGet_Epona',)),
    SongLocation('Song from Saria', 'Sarias Song', 'Item_Melody_SariaSong', 2,
                 ('Dm_MelodyGet_Saria',)),
    SongLocation('Song from Royal Familys Tomb', 'Suns Song', 'Item_Melody_SunSong', 3,
                 ('Dm_MelodyGet_Sun', 'Dm_MelodyGet_Sun_03')),
    SongLocation('Song from Ocarina of Time', 'Song of Time', 'Item_Melody_TimeSong', 4,
                 ('Dm_MelodyGet_Time',)),
    SongLocation('Song from Windmill', 'Song of Storms', 'Item_Melody_StormSong', 5,
                 ('Dm_MelodyGet_Storm',)),
    SongLocation('Sheik in Forest', 'Minuet of Forest', 'Item_Melody_ForestMinuet', 6,
                 ('Dm_MelodyGet_Forest',)),
    SongLocation('Sheik in Crater', 'Bolero of Fire', 'Item_Melody_FireBolero', 7,
                 ('Dm_MelodyGet_Fire',)),
    SongLocation('Sheik in Ice Cavern', 'Serenade of Water', 'Item_Melody_WaterSerenade', 8,
                 ('Dm_MelodyGet_Water',)),
    SongLocation('Sheik at Colossus', 'Requiem of Spirit', 'Item_Melody_SpiritRequiem', 9,
                 ('Dm_MelodyGet_Spilit',)),
    SongLocation('Sheik in Kakariko', 'Nocturne of Shadow', 'Item_Melody_ShadowNocturne', 10,
                 ('Dm_MelodyGet_Shadow',)),
    SongLocation('Sheik at Temple', 'Prelude of Light', 'Item_Melody_LightPrelude', 11,
                 ('Dm_MelodyGet_Shine',)),
)
SONG_BY_LOCATION: dict[str, SongLocation] = {s.location: s for s in SONGS}
SONG_BY_ACTOR: dict[str, SongLocation] = {s.actor: s for s in SONGS}


def _flag(actor: str) -> str:
    return 'IsGet.' + actor


def _swap_scene(data: bytes, old: SongLocation, new: SongLocation) -> tuple[bytes, int]:
    """The flow with `old`'s grants and lessons turned into `new`'s, and the number of
    grants found. Lessons are only the `Dm_SY_Ocarina:LearningOcarina*` calls."""
    flow = EventFlow(data)
    grants, lessons = [], []
    for i, ev in enumerate(flow.events):
        params = flow.action_params(i)
        if params.get('ActorName') == old.actor:
            grants.append(i)
        elif (ev.kind == SUBFLOW and ev.sub_flow == LESSON_FLOW
              and (ev.sub_entry or '').startswith(LESSON_PREFIX)
              and params.get('MelodyType') == old.melody):
            lessons.append(i)
    for i in lessons:
        data = set_int_param(data, i, 'MelodyType', new.melody)
    for i in grants:
        data = set_string_param(data, i, 'ActorName', new.actor)
    return data, len(grants)


def _rename_flag(data: bytes, kind: str, old: str, new: str) -> tuple[bytes, int]:
    """The flow with every `kind` event (action or query name) on flag `old` reading
    or writing `new` instead, and how many there were."""
    flow = EventFlow(data)
    hits = [i for i, ev in enumerate(flow.events)
            if kind in (ev.action, ev.query)
            and flow.action_params(i).get('GameDataName') == old]
    for i in hits:
        data = set_string_param(data, i, 'GameDataName', new)
    return data, len(hits)


def _check_placement(placement: dict[str, str]) -> None:
    if set(placement) != set(SONG_BY_LOCATION) or sorted(placement.values()) != sorted(
            SONG_BY_ACTOR):
        raise ValueError('The song placement must put each of the 12 songs on one of '
                         'the 12 song locations.')


def song_flow_patches(read: Callable[[str], bytes],
                      placement: dict[str, str]) -> dict[str, bytes]:
    """{flow name: new decompressed bytes} of the flows to change so that each song
    location (OoTR name) gives the song actor `placement` assigns to it. `read(name)`
    gives the current decompressed flow (the full skip's or the game's). Unchanged
    flows are left out. Raises ValueError for a placement that is not a permutation,
    a scene without its grant, or a windmill that does not read Storm's flag
    `WINDMILL_QUERIES` times."""
    _check_placement(placement)
    out: dict[str, bytes] = {}

    def current(name: str) -> bytes:
        return out[name] if name in out else read(name)

    for row in SONGS:
        new = SONG_BY_ACTOR[placement[row.location]]
        if new is row:
            continue
        found = 0
        for name in row.flows:
            data, grants = _swap_scene(current(name), row, new)
            found += grants
            out[name] = data
        if not found:
            raise ValueError(f'{row.location}: no grant of {row.actor} in {row.flows}.')
    bolero = SONG_BY_LOCATION['Sheik in Crater'].actor
    if placement['Sheik in Crater'] != bolero:
        out[CRATER_FLOW], _ = _rename_flag(current(CRATER_FLOW), 'EventTriggerSetGameDataBool',
                                           _flag(bolero), _flag(placement['Sheik in Crater']))
    storm = SONG_BY_LOCATION['Song from Windmill'].actor
    if placement['Song from Windmill'] != storm:
        data, n = _rename_flag(current(WINDMILL_FLOW), 'EventQueryIsGameDataBool',
                               _flag(storm), WINDMILL_FLAG)
        if n != WINDMILL_QUERIES:
            raise ValueError(f'{WINDMILL_FLOW} reads {_flag(storm)} {n} times, '
                             f'not {WINDMILL_QUERIES}.')
        out[WINDMILL_FLOW] = data
    return out
