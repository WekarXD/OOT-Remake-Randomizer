import os
import unittest

from randomizer.formats.bfevfl import EventFlow
from randomizer.movie_skip import SPIKE_MOVIES, build_movie_spike_files, drop_transitions, transitions_to

NUP_PATH = os.environ.get('OOT_NUP')


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class MovieSkipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            cls.old, cls.new = {}, {}
            for path, data in build_movie_spike_files(nup).items():
                cls.old[path] = codec.decompress(path, nup.read(path))
                cls.new[path] = codec.decompress(path, data)

    def flows(self, movie):
        path = f'Event/EventFlow/{SPIKE_MOVIES[movie]}.bfevfl.zs'
        return EventFlow(self.old[path]), EventFlow(self.new[path]), self.old[path], self.new[path]

    def test_links_into_the_movie_skip_it(self):
        for movie in SPIKE_MOVIES:
            old, new, old_data, new_data = self.flows(movie)
            self.assertEqual(len(new_data), len(old_data))
            (t,) = transitions_to(old, {movie})
            after = old.events[t].next
            for (off, before), (_, now) in zip(old.pointer_slots(), new.pointer_slots()):
                self.assertEqual(now, after if before == t else before, (movie, off))

    def test_intro_entry_starts_after_the_movie(self):
        old, new, _, _ = self.flows('Dm_Kokiri_0000')
        self.assertEqual(old.entry_points['Opening_LoadingKokiriForest'], 7)
        self.assertEqual(new.entry_points['Opening_LoadingKokiriForest'], 14)

    def test_unknown_movie_is_an_error(self):
        _, _, old_data, _ = self.flows('Dm_HrlCastle_0045')
        with self.assertRaises(ValueError):
            drop_transitions(old_data, {'Dm_NotAMovie'})


if __name__ == '__main__':
    unittest.main()
