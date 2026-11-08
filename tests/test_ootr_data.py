import unittest

from randomizer.logic import ootr_data

KEY_CHESTS = [
    'KF Kokiri Sword Chest', 'Deku Tree Slingshot Chest',
    'Dodongos Cavern Bomb Bag Chest', 'Jabu Jabus Belly Boomerang Chest',
    'Forest Temple Bow Chest', 'Fire Temple Megaton Hammer Chest',
    'Water Temple Longshot Chest', 'Shadow Temple Hover Boots Chest',
    'Ice Cavern Iron Boots Chest', 'Bottom of the Well Lens of Truth Chest',
    'Spirit Temple Silver Gauntlets Chest', 'Spirit Temple Mirror Shield Chest',
    'Graveyard Dampe Race Hookshot Chest',
    'Gerudo Training Ground Maze Path Final Chest',
    'Ganons Castle Shadow Trial Golden Gauntlets Chest',
]


class OotrDataTest(unittest.TestCase):
    def test_key_item_locations_exist(self):
        locs = ootr_data.load_locations()
        for name in KEY_CHESTS:
            self.assertIn(name, locs)
            self.assertEqual(locs[name]['type'], 'Chest', name)

    def test_special_locations(self):
        locs = ootr_data.load_locations()
        self.assertEqual(locs['Ganon']['type'], 'Event')
        self.assertEqual(locs['Ganon']['vanilla_item'], 'Triforce')
        self.assertIn('Deku Tree Queen Gohma Heart', locs)
        self.assertIsInstance(locs['Queen Gohma']['categories'], list)

    def test_world_files_parse(self):
        world = ootr_data.load_world_files()
        self.assertEqual(len(world), 14)
        self.assertIn('Overworld', world)
        self.assertIn('Bosses', world)
        self.assertFalse([n for n in world if 'MQ' in n])
        for name, regions in world.items():
            self.assertIsInstance(regions, list, name)
            self.assertTrue(regions, name)

    def test_helpers_parse(self):
        helpers = ootr_data.load_helpers()
        self.assertIsInstance(helpers, dict)
        self.assertTrue(helpers)


if __name__ == '__main__':
    unittest.main()
