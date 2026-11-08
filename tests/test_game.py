import json
import os
import unittest
from pathlib import Path

from randomizer.game import GameData, load_chests_fixture
from randomizer.nup import NupArchive

NUP = os.environ.get('OOT_NUP')
FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
SWORD_HASH = 16757992849254467386


@unittest.skipUnless(NUP, 'OOT_NUP no definido')
class TestGameData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nup = NupArchive(NUP)
        cls.chests = GameData(cls.nup).chests()

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def test_chest_counts(self):
        self.assertEqual(len(self.chests), 238)
        self.assertEqual(len({c.hash for c in self.chests}), 203)

    def test_kokiri_sword_chest(self):
        sw = [c for c in self.chests if c.hash == SWORD_HASH]
        self.assertEqual(len(sw), 2)
        self.assertEqual({c.banc.rsplit('/', 1)[1].split('.')[0] for c in sw},
                         {'KokiriForest_Child_Dynamic', 'KokiriForest_Adult_Dynamic'})
        for c in sw:
            self.assertEqual(c.drop, 'Item_Sword_Kokiri')
            self.assertEqual(c.event, 'Get_StoneOfForest_GetSword')

    def test_fixture_matches(self):
        self.assertEqual(load_chests_fixture(FIXTURE), self.chests)


class TestFixture(unittest.TestCase):
    def test_fixture_loads(self):
        chests = load_chests_fixture(FIXTURE)
        self.assertEqual(len(chests), 238)
        self.assertIsInstance(chests[0].hash, int)
        self.assertIsInstance(chests[0].pos, tuple)
        self.assertEqual(chests, sorted(chests, key=lambda c: (c.banc, c.hash)))


if __name__ == '__main__':
    unittest.main()
