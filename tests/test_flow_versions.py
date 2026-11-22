"""The game loads a versioned copy of some flows (`EventFlowFileEntry.Product.110`): a
patch must go to that file, or the game never sees it (Dampe's gift, the medallions)."""
import os
import unittest

from randomizer.formats import byml
from randomizer.game import FLOW_ENTRY, GameData
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')


class BigEndianTest(unittest.TestCase):
    def test_reads_a_big_endian_byml(self):
        # A minimal big-endian BYML v7: a dict {"a": 1}.
        keys = b'\xc2\x00\x00\x01' + (12).to_bytes(4, 'big') + (14).to_bytes(4, 'big') + b'a\x00'
        keys += b'\x00' * (-len(keys) % 4)
        root = b'\xc1\x00\x00\x01' + b'\x00\x00\x00' + b'\xd1' + (1).to_bytes(4, 'big')
        head = b'BY' + (7).to_bytes(2, 'big')
        ko = 16
        ro = ko + len(keys)
        data = head + ko.to_bytes(4, 'big') + (0).to_bytes(4, 'big') + ro.to_bytes(4, 'big')
        data += keys + root
        self.assertEqual(byml.load(data), (7, {'a': 1}))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class FlowPathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nup = NupArchive(NUP_PATH)
        cls.game = GameData(cls.nup)

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def test_entry_table(self):
        raw = self.game.codec.decompress(FLOW_ENTRY, self.nup.read(FLOW_ENTRY))
        versions = byml.load(raw)[1]['Versions']
        self.assertEqual(versions['Npc_Hylia_Dampe_001'], '110')
        self.assertEqual(versions['Dm_Awake_Fire_Get'], '110')

    def test_flow_path(self):
        self.assertEqual(self.game.flow_path('Npc_Hylia_Dampe_001'),
                         'Event/EventFlow/Npc_Hylia_Dampe_001.110.bfevfl.zs')
        self.assertEqual(self.game.flow_path('Dm_Awake_Water_Get'),
                         'Event/EventFlow/Dm_Awake_Water_Get.110.bfevfl.zs')
        self.assertEqual(self.game.flow_path('Dm_Kokiri_0130'),
                         'Event/EventFlow/Dm_Kokiri_0130.bfevfl.zs')
        for name in ('Npc_Hylia_Dampe_001', 'Dm_Kokiri_0130'):
            self.assertTrue(self.nup.has(self.game.flow_path(name)), name)

    def test_flow_patches_read_and_write_the_versioned_file(self):
        from randomizer.generate import _with_flow_patches
        dampe = self.game.flow_path('Npc_Hylia_Dampe_001')
        versioned = self.game.codec.decompress(dampe, self.nup.read(dampe))
        seen = {}

        def patches(read):
            seen['data'] = read('Npc_Hylia_Dampe_001')
            return {'Npc_Hylia_Dampe_001': seen['data']}

        files, _ = _with_flow_patches(self.game, patches, None, None)
        self.assertEqual(seen['data'], versioned)
        self.assertEqual(set(files), {dampe})


if __name__ == '__main__':
    unittest.main()
