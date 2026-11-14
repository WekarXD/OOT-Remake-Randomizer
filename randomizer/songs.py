"""Song locations ("Shuffle Songs") and the edits that make a song scene give another song.

Each song is taught by one scene (`Dm_MelodyGet_*`). In it, the lesson is a pair of
`Dm_SY_Ocarina:LearningOcarina*` calls with a `MelodyType` int (the notes shown and the
notes you repeat), and the grant is a `GetPouchContent:GetPouchContentByActorName` call
with an `ActorName`. Batch 20: a scene gives whatever its grant names, even when you
already own its original song.
"""
from dataclasses import dataclass

SHUFFLE_SONGS = ('off', 'song_locations')


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
