"""Song locations ("Shuffle Songs") and the edits that make a song scene give another song.

Each song is taught by one scene (`Dm_MelodyGet_*`). In it, the lesson is a pair of
`Dm_SY_Ocarina:LearningOcarina*` calls with a `MelodyType` int (the notes shown and the
notes you repeat), and the grant is a `GetPouchContent:GetPouchContentByActorName` call
with an `ActorName`. Batch 20: a scene gives whatever its grant names, even when you
already own its original song.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from randomizer.formats.bfevfl import (SUBFLOW, EventFlow, patch_pointers, set_int_param,
                                       set_string_param, set_subflow_entry)

SHUFFLE_SONGS = ('off', 'song_locations', 'anywhere', 'dungeon_rewards')
GRANT_CALL = ('GetPouchContent', 'GetPouchContentByActorName')
LESSON_FLOW, LESSON_PREFIX = 'Dm_SY_Ocarina', 'LearningOcarina'
AUTO_NORMAL, AUTO_WARP = 'LearningOcarinaPlayAuto', 'LearningOcarinaPlayAutoForSeek'
# Ends an ocarina sequence (success, the tune played back, the ocarina put away) without
# adding any song; the frogs' minigame uses it.
AUTO_PLAIN = 'PlayAuto'
FIRST_WARP_MELODY = 6  # Minuet; 6-11 are the warp songs
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
# Boss Heart Containers (dungeon zone -> OoTR location), dungeon-reward sites for
# Shuffle Songs: Dungeon Rewards. Each zone's *_Static banc has one Obj_Heart_Container.
BOSS_HEARTS: dict[str, str] = {
    'InsideTheDekuTree': 'Deku Tree Queen Gohma Heart',
    'DodongoCavern': 'Dodongos Cavern King Dodongo Heart',
    'InsideJabuJabuBelly': 'Jabu Jabus Belly Barinade Heart',
    'ForestTemple': 'Forest Temple Phantom Ganon Heart',
    'FireTemple': 'Fire Temple Volvagia Heart',
    'WaterTemple': 'Water Temple Morpha Heart',
    'SpiritTemple': 'Spirit Temple Twinrova Heart',
    'ShadowTemple': 'Shadow Temple Bongo Bongo Heart',
}
HEART_GYAML = 'Obj_Heart_Container'
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
    old_auto, new_auto = _auto_entry(old.melody), _auto_entry(new.melody)
    if old_auto != new_auto:
        for i, ev in enumerate(flow.events):
            if ev.kind == SUBFLOW and ev.sub_flow == LESSON_FLOW and ev.sub_entry == old_auto:
                data = set_subflow_entry(data, i, new_auto)
    return data, len(grants)


def _auto_entry(melody: int) -> str:
    """The `Dm_SY_Ocarina` entry that ends a lesson of `melody`: Link plays the song
    back and it is added. `PlayAuto` only has cases for melodies 0-5 (and the
    scarecrow's), `PlayAutoForSeek` only for the warp songs 6-11; a melody without its
    case hangs the game (batch 22)."""
    return AUTO_WARP if melody >= FIRST_WARP_MELODY else AUTO_NORMAL


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


END = 0xFFFF


def bypass(data: bytes, events: Iterable[int]) -> bytes:
    """The flow with `events` skipped: every pointer to one of them (next, case, fork,
    join, entry) goes to the first event after it that is not skipped, or to the end
    when there is none. Nothing else changes (same size, same events)."""
    skipped = set(events)
    if not skipped:
        return data
    flow = EventFlow(data)

    def after(i: int) -> int:
        seen = set()
        while i in skipped:
            if i in seen:
                return END  # a loop made only of skipped events
            seen.add(i)
            nxt = flow.events[i].next
            i = nxt if isinstance(nxt, int) else END
        return i

    links = {}
    for key, off in flow.link_slots.items():
        if flow._u16(off) not in skipped:
            continue
        target = after(flow._u16(off))
        if target == END and key[0] == 'fork':
            # An emptied branch goes straight to its fork's join, like the game's own
            # empty branches (Dm_MelodyGet_Storm fork 39 -> join 40).
            target = flow.events[key[1]].join
        links[off] = target
    return patch_pointers(data, links)


def _lesson_ends(flow: EventFlow) -> list[int]:
    """The lesson's `PlayAuto` / `PlayAutoForSeek` calls: the only part of a lesson that
    adds a song to the pouch (the melody just played)."""
    return [i for i, ev in enumerate(flow.events)
            if ev.kind == SUBFLOW and ev.sub_flow == LESSON_FLOW
            and ev.sub_entry in (AUTO_NORMAL, AUTO_WARP)]


def _give_item(data: bytes, old: SongLocation, actor: str) -> tuple[bytes, int]:
    """The flow giving `actor` (not a song) instead of `old`'s song, and the number of
    grants found. The lesson's end adds the melody just played to the pouch, so the
    original song would come along: it becomes the plain `PlayAuto`, which still closes
    the lesson and plays the tune back (without an end the scene froze, batch 24b).
    The teacher still plays the original notes and Link repeats them."""
    flow = EventFlow(data)
    grants = [i for i in range(len(flow.events))
              if flow.action_params(i).get('ActorName') == old.actor]
    for i in _lesson_ends(flow):
        data = set_subflow_entry(data, i, AUTO_PLAIN)
    for i in grants:
        data = set_string_param(data, i, 'ActorName', actor)
    return data, len(grants)


def _flag_events(data: bytes, kind: str, name: str) -> list[int]:
    flow = EventFlow(data)
    return [i for i, ev in enumerate(flow.events)
            if kind in (ev.action, ev.query) and flow.action_params(i).get('GameDataName') == name]


def _check_placement(placement: dict[str, str]) -> None:
    if set(placement) != set(SONG_BY_LOCATION):
        raise ValueError('The song placement must give an item to each of the 12 song '
                         'locations.')
    if any(not isinstance(a, str) or not a for a in placement.values()):
        raise ValueError('Every song location needs an item.')
    songs = [a for a in placement.values() if a in SONG_BY_ACTOR]
    if len(songs) != len(set(songs)):
        raise ValueError('A song is placed on two song locations.')


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
        actor = placement[row.location]
        if actor == row.actor:
            continue
        found = 0
        for name in row.flows:
            if actor in SONG_BY_ACTOR:
                data, grants = _swap_scene(current(name), row, SONG_BY_ACTOR[actor])
            else:
                data, grants = _give_item(current(name), row, actor)
            found += grants
            out[name] = data
        if not found:
            raise ValueError(f'{row.location}: no grant of {row.actor} in {row.flows}.')
    _patch_crater(placement['Sheik in Crater'], current, out)
    storm = SONG_BY_LOCATION['Song from Windmill'].actor
    if placement['Song from Windmill'] != storm:  # wherever Storm went
        data, n = _rename_flag(current(WINDMILL_FLOW), 'EventQueryIsGameDataBool',
                               _flag(storm), WINDMILL_FLAG)
        if n != WINDMILL_QUERIES:
            raise ValueError(f'{WINDMILL_FLOW} reads {_flag(storm)} {n} times, '
                             f'not {WINDMILL_QUERIES}.')
        out[WINDMILL_FLOW] = data
    return out


def _patch_crater(actor: str, current: Callable[[str], bytes], out: dict[str, bytes]) -> None:
    """The crater's scene sets its song's flag itself: it follows a new song, and is
    skipped for an item that is not a song. Raises ValueError unless the set is found
    exactly once."""
    bolero = SONG_BY_LOCATION['Sheik in Crater'].actor
    if actor == bolero:
        return
    data = current(CRATER_FLOW)
    sets = _flag_events(data, 'EventTriggerSetGameDataBool', _flag(bolero))
    if len(sets) != 1:
        raise ValueError(f'{CRATER_FLOW} sets {_flag(bolero)} {len(sets)} times, not once.')
    if actor in SONG_BY_ACTOR:
        out[CRATER_FLOW] = set_string_param(data, sets[0], 'GameDataName', _flag(actor))
    else:
        out[CRATER_FLOW] = bypass(data, sets)
