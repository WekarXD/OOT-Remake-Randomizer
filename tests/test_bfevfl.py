import os
import unittest

from randomizer.formats.bfevfl import Event, EventFlow, patch_pointers
from randomizer.formats.zs import ZsCodec
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
FLOW_DIR = 'Event/EventFlow/'


def _load(nup, codec, name):
    path = FLOW_DIR + name
    return codec.decompress(path, nup.read(path))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')
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


class EventTests(unittest.TestCase):
    def test_defaults(self):
        ev = Event(index=1, kind=0, next=2)
        self.assertEqual((ev.cases, ev.forks, ev.join, ev.actor), ([], [], None, None))


if __name__ == '__main__':
    unittest.main()
