import os
import struct
import unittest

from randomizer.formats.bfevfl import (ACTION, SUBFLOW, BfevflError, EventFlow, grow_events,
                                       relocation_table)
from randomizer.formats.evfl_append import (ActionSpec, SubflowSpec, append_events, build_dic,
                                            set_entry_subflows)
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


FLAG = ActionSpec('GameDataActor', 'EventTriggerSetGameDataBool',
                  {'GameDataName': 'X_Test', 'Index': -1, 'Value': True})
GIFT = SubflowSpec('Dm_SY_GetInEvent', 'GetInEvent', {'ActorName': 'Item_Ocarina_Fairy'})
TELEPORT = SubflowSpec('Dm_SY_BancChangeGo', 'EntryPoint0', {
    'NextBanc': 'HyruleField_Child', 'NextStartPos': 'HyruleField_FrontOfLostWoodBridge',
    'BootEventName': '', 'IsCheckAir': False,
    'NextStartPosAir': 'HyruleField_FrontOfLostWoodBridge'})


def _valid(test, data):
    reloc, size = struct.unpack_from('<II', data, 0x18)
    test.assertEqual(size, len(data))
    test.assertEqual(data[reloc:reloc + 4], b'RELT')
    test.assertEqual(struct.unpack_from('<I', data, reloc + 4)[0], reloc)
    flow = EventFlow(data)
    for i in range(len(flow.events)):
        flow.action_params(i)
    return flow


def _shape(ev):
    return (ev.kind, ev.actor, ev.action, ev.query, ev.next, ev.cases, ev.forks, ev.join,
            ev.sub_flow, ev.sub_entry)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class AppendEventsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            p = FLOW_DIR + 'Dm_Kokiri_0045.bfevfl.zs'
            cls.data = codec.decompress(p, nup.read(p))
        cls.flow = EventFlow(cls.data)

    def _check_original(self, new):
        old = self.flow
        for i in range(len(old.events)):
            self.assertEqual(_shape(new.events[i]), _shape(old.events[i]), i)
            self.assertEqual(new.action_params(i), old.action_params(i), i)
        self.assertEqual(new.entry_points, old.entry_points)

    def test_append_action_and_subflow(self):
        out, idx = append_events(self.data, [FLAG, GIFT, TELEPORT])
        n = len(self.flow.events)
        self.assertEqual(idx, [n, n + 1, n + 2])
        new = _valid(self, out)
        self._check_original(new)
        flag, gift, tp = (new.events[i] for i in idx)
        self.assertEqual((flag.kind, flag.actor, flag.action, flag.next),
                         (ACTION, 'GameDataActor', 'EventTriggerSetGameDataBool', 0xFFFF))
        self.assertEqual(new.action_params(idx[0]), FLAG.params)
        self.assertEqual((gift.kind, gift.sub_flow, gift.sub_entry, gift.next),
                         (SUBFLOW, 'Dm_SY_GetInEvent', 'GetInEvent', 0xFFFF))
        self.assertEqual(new.action_params(idx[1]), GIFT.params)
        self.assertEqual((tp.kind, tp.sub_flow, tp.sub_entry), (SUBFLOW, 'Dm_SY_BancChangeGo', 'EntryPoint0'))
        self.assertEqual(new.action_params(idx[2]), TELEPORT.params)

    def test_append_to_grown_flow(self):
        action = next(i for i, e in enumerate(self.flow.events) if e.kind == ACTION)
        grown = grow_events(self.data, [action])
        out, idx = append_events(grown, [FLAG, GIFT])
        new = _valid(self, out)
        self.assertEqual(idx, [len(self.flow.events) + 1, len(self.flow.events) + 2])
        self.assertEqual(new.action_params(idx[1]), GIFT.params)

    def test_unknown_actor_or_action_raises(self):
        for spec in (ActionSpec('NoSuchActor', 'EventWait', {}),
                     ActionSpec('GameDataActor', 'NoSuchAction', {})):
            with self.subTest(spec=spec), self.assertRaises(BfevflError):
                append_events(self.data, [spec])

    def test_dic_root_uses_pool_empty_string(self):
        # As in the game: the root of each DIC names the pool's empty string.
        out, idx = append_events(self.data, [FLAG])
        new = EventFlow(out)
        pool, _ = new._pool()
        dic = new._u64(new._params[idx[0]] + 8)
        self.assertEqual(new._u64(dic + 8 + 8), pool + 0x14)

    def test_relt_covers_new_pointers(self):
        out, idx = append_events(self.data, [FLAG, TELEPORT])
        new = EventFlow(out)
        pointers = relocation_table(out)[2]
        for i in idx:
            slot = new._events_p + 0x30 * i
            for off in (0x00, 0x10, 0x18, 0x20):
                if new._u64(slot + off):
                    self.assertIn(slot + off, pointers, (i, off))
            c = new._params[i]
            items = new._items(i)
            self.assertIn(c + 8, pointers)
            for j in range(len(items)):
                self.assertIn(c + 0x10 + 8 * j, pointers)
            dic = new._u64(c + 8)
            for j in range(len(items) + 1):
                self.assertIn(dic + 8 + 0x10 * j + 8, pointers)
            for _, it in items:
                if out[it] == 5:
                    self.assertIn(it + 0x10, pointers)

    def test_set_entry_subflows(self):
        out, idx = append_events(self.data, [FLAG, GIFT, TELEPORT])
        self.assertEqual(EventFlow(out).entry_subflows('EntryPoint0'), [])
        out = set_entry_subflows(out, 'EntryPoint0', idx[1:])
        new = _valid(self, out)
        self.assertEqual(new.entry_subflows('EntryPoint0'), idx[1:])
        self._check_original(new)
        entry = new._entry_offset('EntryPoint0')
        self.assertIn(entry, relocation_table(out)[2])

    def test_set_entry_subflows_empty_is_null(self):
        out, idx = append_events(self.data, [GIFT])
        out = set_entry_subflows(set_entry_subflows(out, 'EntryPoint0', idx), 'EntryPoint0', [])
        new = _valid(self, out)
        self.assertEqual(new.entry_subflows('EntryPoint0'), [])
        entry = new._entry_offset('EntryPoint0')
        self.assertEqual(new._u64(entry), 0)
        self.assertNotIn(entry, relocation_table(out)[2])

    def test_set_entry_subflows_unknown_entry_raises(self):
        with self.assertRaises(BfevflError):
            set_entry_subflows(self.data, 'Nope', [])


if __name__ == '__main__':
    unittest.main()
