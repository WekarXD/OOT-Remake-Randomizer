import os
import struct
import unittest

from randomizer.formats.bfevfl import EventFlow
from randomizer.formats.evfl_append import build_dic
from randomizer.formats.zs import ZsCodec
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
FLOW_DIR = 'Event/EventFlow/'


def _dic_of(flow: EventFlow, index: int) -> tuple[int, list[str]]:
    """(DIC offset, keys in item order) of the event's parameter container."""
    c = flow._params[index]
    return flow._u64(c + 8), [k for k, _ in flow._items(index)]


class DicSmallTest(unittest.TestCase):
    def test_dic_small(self):
        ptrs = {'': 0x100, 'A': 0x200}
        dic = build_dic(['A'], ptrs.__getitem__)
        self.assertEqual(dic[:4], b'DIC ')
        self.assertEqual(struct.unpack_from('<I', dic, 4)[0], 1)
        self.assertEqual(len(dic), 8 + 0x10 * 2)
        # Root: bit -1, left -> entry 1; entry 1 points to 'A'.
        self.assertEqual(struct.unpack_from('<iHHQ', dic, 8), (-1, 1, 0, 0x100))
        self.assertEqual(struct.unpack_from('<Q', dic, 8 + 0x10 + 8)[0], 0x200)

    def test_known_container(self):
        # Dm_Kokiri_0045 event 45 (decoded by hand): GameDataName, Index, Value.
        ptrs = {'': 0x9dec, 'GameDataName': 0xae30, 'Index': 0x9ef6, 'Value': 0xad18}
        dic = build_dic(['GameDataName', 'Index', 'Value'], ptrs.__getitem__)
        self.assertEqual(dic.hex(), (
            '4449432003000000'
            'ffffffff01000000ec9d000000000000'
            '000000000200030030ae000000000000'
            '0300000000000200f69e000000000000'
            '0b0000000300010018ad000000000000'))

    def test_duplicate_key_raises(self):
        with self.assertRaises(ValueError):
            build_dic(['A', 'A'], lambda k: 0)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class DicOracleTest(unittest.TestCase):
    def test_dic_oracle(self):
        checked = 0
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for p in nup.list(FLOW_DIR):
                if not p.endswith('.bfevfl.zs'):
                    continue
                data = codec.decompress(p, nup.read(p))
                flow = EventFlow(data)
                for i in sorted(flow._params):
                    dic, keys = _dic_of(flow, i)
                    n = len(keys)
                    original = data[dic:dic + 8 + 0x10 * (n + 1)]
                    names = [''] + keys
                    ptrs = {names[j]: struct.unpack_from('<Q', original, 8 + 0x10 * j + 8)[0]
                            for j in range(n + 1)}
                    with self.subTest(flow=p, event=i):
                        self.assertEqual(build_dic(keys, ptrs.__getitem__), original)
                    checked += 1
        self.assertGreater(checked, 10000)


if __name__ == '__main__':
    unittest.main()
