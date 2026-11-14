import unittest

from randomizer.logic import ootr_data
from randomizer.songs import SHUFFLE_SONGS, SONG_BY_ACTOR, SONG_BY_LOCATION, SONGS


class SongTableTest(unittest.TestCase):
    def test_table_matches_ootr(self):
        locations = ootr_data.load_locations()
        for row in SONGS:
            self.assertEqual(locations[row.location]['vanilla_item'], row.song, row.location)

    def test_table_is_a_permutation(self):
        self.assertEqual(len(SONGS), 12)
        self.assertEqual(len({r.location for r in SONGS}), 12)
        self.assertEqual(len({r.actor for r in SONGS}), 12)
        self.assertEqual(sorted(r.melody for r in SONGS), list(range(12)))
        self.assertEqual(set(SONG_BY_LOCATION), {r.location for r in SONGS})
        self.assertEqual(set(SONG_BY_ACTOR), {r.actor for r in SONGS})
        self.assertTrue(all(r.actor.startswith('Item_Melody_') and r.flows for r in SONGS))

    def test_shuffle_values(self):
        self.assertEqual(SHUFFLE_SONGS, ('off', 'song_locations'))
