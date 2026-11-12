import os
import struct
import unittest

from randomizer.formats.bfevfl import (BfevflError, Event, EventFlow, patch_pointers,
                                       set_string_param, string_param_owners)
from randomizer.formats.zs import ZsCodec
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
FLOW_DIR = 'Event/EventFlow/'


def _load(nup, codec, name):
    path = FLOW_DIR + name
    return codec.decompress(path, nup.read(path))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class BfevflTests(unittest.TestCase):
    def test_parse_get_stone_of_fire(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            flow = EventFlow(_load(nup, codec, 'Get_StoneOfFire.bfevfl.zs'))
        self.assertEqual(len(flow.events), 274)
        self.assertEqual(len(flow.entry_points), 33)
        chain = []
        i = flow.entry_points['Get_StoneOfFire_GetBombBag']
        while i != 0xFFFF:
            ev = flow.events[i]
            self.assertEqual(ev.kind, 0)
            chain.append(ev.action)
            i = ev.next
        self.assertEqual(chain, ['EventTriggerParticipateEvent', 'EventTransition',
                                 'EventNaviRequestBallonMessage'])

    def test_kind5_cases_are_parsed(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            flow = EventFlow(_load(nup, codec, 'SubEvent_GetEponaSong.bfevfl.zs'))
        self.assertEqual(flow.events[27].kind, 5)
        self.assertEqual(flow.events[27].cases, [28, 112])
        self.assertIn(28, [v for _, v in flow.pointer_slots()])
        self.assertEqual(flow.events[27].sub_flow, '')
        self.assertEqual(flow.events[27].sub_entry,
                         'Mask_Talk_Common_With_InitTalk_Malon_Child_Only')
        self.assertIn(('case', 27, 1), flow.link_slots)
        self.assertEqual(flow.events[27].case_hashes, [0xf7b0eeb8, 0xfab0f371])
        self.assertEqual(flow.events[28].kind, 6)
        self.assertEqual(flow.events[28].result, 0xa6da0479)
        self.assertEqual((flow.events[75].result, flow.events[76].result),
                         (0xf7b0eeb8, 0xfab0f371))
        self.assertEqual((flow.events[28].next, flow.events[28].cases), (None, []))

    def test_all_flows_parse(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            names = [p for p in nup.list(FLOW_DIR) if p.endswith('.bfevfl.zs')]
            self.assertEqual(len(names), 914)
            for p in names:
                flow = EventFlow(codec.decompress(p, nup.read(p)))
                n = len(flow.events)
                for off, idx in flow.pointer_slots():
                    self.assertTrue(idx < n or idx == 0xFFFF, (p, off, idx))
                for i in range(n):
                    flow.action_params(i)  # all containers are read

    def test_subflow_targets(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            flow = EventFlow(_load(nup, codec, 'Dm_Kokiri_0155.bfevfl.zs'))
        self.assertEqual(flow.events[2].sub_flow, '')
        self.assertEqual(flow.events[2].sub_entry, 'C01')
        self.assertEqual((flow.events[52].sub_flow, flow.events[52].sub_entry),
                         ('GetPouchContent', 'DisplayGetByActorName'))

    def test_link_slots(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            data = _load(nup, codec, 'Dm_Kokiri_0155.bfevfl.zs')
        flow = EventFlow(data)
        self.assertEqual(sorted(flow.link_slots.values()),
                         sorted(o for o, _ in flow.pointer_slots()))
        self.assertIn(('entry', 'EntryPoint0'), flow.link_slots)
        self.assertIn(('next', 51), flow.link_slots)
        patched = patch_pointers(data, {flow.link_slots[('next', 51)]: 0xFFFF})
        self.assertEqual(EventFlow(patched).events[51].next, 0xFFFF)

    def test_patch_roundtrip(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            d = _load(nup, codec, 'Get_StoneOfFire.bfevfl.zs')
        self.assertEqual(patch_pointers(d, {}), d)
        slots = EventFlow(d).pointer_slots()
        off, idx = slots[len(slots) // 2]
        new = 0xFFFF if idx != 0xFFFF else 0
        patched = patch_pointers(d, {off: new})
        self.assertEqual(len(patched), len(d))
        after = EventFlow(patched).pointer_slots()
        self.assertEqual([o for o, _ in after], [o for o, _ in slots])
        for (o, a), (_, b) in zip(after, slots):
            self.assertEqual(a, new if o == off else b)


# Keys found in Dm_Kokiri_0155: event 51 (action) and event 52 (subflow)
# carry Saria's ocarina in string parameters with different names.
GIFT_FLOW = 'Dm_Kokiri_0155.bfevfl.zs'
GIFT_KEYS = {51: 'Actor', 52: 'ActorName'}
GIFT_ITEM = 'Item_Ocarina_Fairy'
LONG_VALUE = 'Item_Ocarina_Fairy_Longer_Test'  # does not fit and does not exist


def _all_params(flow):
    return [flow.action_params(i) for i in range(len(flow.events))]


def _assert_valid(test, data):
    reloc, size = struct.unpack_from('<II', data, 0x18)
    test.assertEqual(size, len(data))
    test.assertEqual(data[reloc:reloc + 4], b'RELT')
    test.assertEqual(struct.unpack_from('<I', data, reloc + 4)[0], reloc)
    flow = EventFlow(data)
    _all_params(flow)  # it can be read entirely
    return flow


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class StringParamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            cls.data = _load(nup, codec, GIFT_FLOW)
            cls.gold = _load(nup, codec, 'GatheringTokenGold.bfevfl.zs')
        cls.flow = EventFlow(cls.data)

    def test_read_gift_params(self):
        for ev, key in GIFT_KEYS.items():
            params = self.flow.action_params(ev)
            keys = [k for k, v in params.items() if v == GIFT_ITEM]
            self.assertEqual(keys, [key], (ev, params))
        p51 = self.flow.action_params(51)
        self.assertEqual(p51['Num'], 1)
        self.assertIs(p51['IsGetEvent'], False)
        self.assertEqual(EventFlow(self.gold).action_params(250),
                         {'TakenRewardActor': 'Obj_Rupee_Gold'})

    def test_set_string_param_roundtrip(self):
        before = _all_params(self.flow)
        for ev, key in GIFT_KEYS.items():
            new = set_string_param(self.data, ev, key, 'Item_Hookshot')
            flow = _assert_valid(self, new)
            after = _all_params(flow)
            self.assertEqual(after[ev][key], 'Item_Hookshot')
            after[ev][key] = GIFT_ITEM
            self.assertEqual(after, before)
            self.assertEqual(flow.pointer_slots(), self.flow.pointer_slots())
            self.assertEqual(flow.entry_points, self.flow.entry_points)

    def test_inplace_when_fits(self):
        # Vanilla: each string is its own copy right after its parameter.
        for ev, key in GIFT_KEYS.items():
            slot = self.flow._string_slot(ev, key)
            s = struct.unpack_from('<Q', self.data, slot)[0]
            self.assertEqual(s, slot + 8)
            end = s + 3 + len(GIFT_ITEM)
            end += end & 1
            new = set_string_param(self.data, ev, key, 'Item_Hookshot')
            self.assertEqual(len(new), len(self.data))
            self.assertEqual(new[:s], self.data[:s])
            self.assertEqual(new[end:], self.data[end:])
            self.assertEqual(new[s:end],
                             (b'\x0d\x00Item_Hookshot').ljust(end - s, b'\0'))
            self.assertEqual(_assert_valid(self, new).action_params(ev)[key], 'Item_Hookshot')
            self.assertEqual(string_param_owners(new, ev, key), [ev])

    def test_reuse_existing_string(self):
        # They do not fit in the 18 bytes of 'Item_Ocarina_Fairy': it is repointed.
        # 'Dm_Item_Ocarina_Fairy_Saria' is in the pool; 'C02-Player_Child-A-0'
        # only in the ASCommand parameter of event 0.
        slot = self.flow._string_slot(52, 'ActorName')
        for value in ('Dm_Item_Ocarina_Fairy_Saria', 'C02-Player_Child-A-0'):
            new = set_string_param(self.data, 52, 'ActorName', value)
            self.assertEqual(len(new), len(self.data))
            self.assertNotEqual(new[slot:slot + 8], self.data[slot:slot + 8])
            self.assertEqual(_assert_valid(self, new).action_params(52)['ActorName'], value)

    def test_grow_file_valid(self):
        self.assertNotIn(LONG_VALUE.encode(), self.data)
        new = set_string_param(self.data, 51, 'Actor', LONG_VALUE)
        self.assertGreater(len(new), len(self.data))
        flow = _assert_valid(self, new)
        self.assertEqual(len(flow.events), len(self.flow.events))
        self.assertEqual(flow.pointer_slots(), self.flow.pointer_slots())
        self.assertEqual(flow.action_params(51)['Actor'], LONG_VALUE)
        # A second time it already reuses the added string.
        again = set_string_param(new, 52, 'ActorName', LONG_VALUE)
        self.assertEqual(len(again), len(new))
        self.assertEqual(EventFlow(again).action_params(52)['ActorName'], LONG_VALUE)

    def test_other_events_untouched(self):
        self.assertEqual(string_param_owners(self.data, 52, 'ActorName'), [52])
        self.assertEqual(string_param_owners(self.data, 0, 'ASCommand'), [0])
        shared = set_string_param(self.data, 52, 'ActorName', 'C02-Player_Child-A-0')
        self.assertEqual(string_param_owners(shared, 52, 'ActorName'), [0, 52])
        self.assertEqual(string_param_owners(shared, 0, 'ASCommand'), [0, 52])
        # The shared string is not edited in place even if the text fits.
        changed = set_string_param(shared, 52, 'ActorName', 'Item_Hookshot')
        flow = _assert_valid(self, changed)
        self.assertEqual(flow.action_params(52)['ActorName'], 'Item_Hookshot')
        self.assertEqual(flow.action_params(0)['ASCommand'], 'C02-Player_Child-A-0')
        self.assertEqual(string_param_owners(changed, 52, 'ActorName'), [52])

    def test_coexists_with_trim(self):
        off, idx = self.flow.pointer_slots()[0]
        trim = {off: 0xFFFF if idx != 0xFFFF else 0}
        for value in ('Item_Hookshot', LONG_VALUE):  # in place and growing
            a = set_string_param(patch_pointers(self.data, trim), 51, 'Actor', value)
            b = patch_pointers(set_string_param(self.data, 51, 'Actor', value), trim)
            self.assertEqual(a, b)
            flow = _assert_valid(self, a)
            self.assertEqual(flow.action_params(51)['Actor'], value)
            self.assertEqual(dict(flow.pointer_slots())[off], trim[off])

    def test_errors(self):
        with self.assertRaises(BfevflError):
            set_string_param(self.data, 51, 'Num', 'x')  # not a string
        with self.assertRaises(BfevflError):
            set_string_param(self.data, 51, 'NoSuchKey', 'x')
        with self.assertRaises(BfevflError):
            set_string_param(self.data, len(self.flow.events), 'Actor', 'x')
        with self.assertRaises(BfevflError):
            string_param_owners(self.data, 51, 'Num')


class EventTests(unittest.TestCase):
    def test_defaults(self):
        ev = Event(index=1, kind=0, next=2)
        self.assertEqual((ev.cases, ev.forks, ev.join, ev.actor), ([], [], None, None))
        ev = Event(0, 0)
        self.assertTrue(ev.sub_flow is None and ev.sub_entry is None)


if __name__ == '__main__':
    unittest.main()
