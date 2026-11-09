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
                for i in range(n):
                    flow.action_params(i)  # todos los contenedores se leen

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


# Claves encontradas en Dm_Kokiri_0155: el evento 51 (acción) y el 52 (subflujo)
# llevan la ocarina de Saria en parámetros de texto con nombres distintos.
GIFT_FLOW = 'Dm_Kokiri_0155.bfevfl.zs'
GIFT_KEYS = {51: 'Actor', 52: 'ActorName'}
GIFT_ITEM = 'Item_Ocarina_Fairy'
LONG_VALUE = 'Item_Ocarina_Fairy_Longer_Test'  # no cabe y no existe


def _all_params(flow):
    return [flow.action_params(i) for i in range(len(flow.events))]


def _assert_valid(test, data):
    reloc, size = struct.unpack_from('<II', data, 0x18)
    test.assertEqual(size, len(data))
    test.assertEqual(data[reloc:reloc + 4], b'RELT')
    test.assertEqual(struct.unpack_from('<I', data, reloc + 4)[0], reloc)
    flow = EventFlow(data)
    _all_params(flow)  # se puede leer entero
    return flow


@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')
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
        # Vanilla: cada texto es una copia propia justo detrás de su parámetro.
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
        # No caben en los 18 bytes de 'Item_Ocarina_Fairy': se reapunta.
        # 'Dm_Item_Ocarina_Fairy_Saria' está en el pool; 'C02-Player_Child-A-0'
        # solo en el parámetro ASCommand del evento 0.
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
        # Una segunda vez ya reutiliza la cadena añadida.
        again = set_string_param(new, 52, 'ActorName', LONG_VALUE)
        self.assertEqual(len(again), len(new))
        self.assertEqual(EventFlow(again).action_params(52)['ActorName'], LONG_VALUE)

    def test_other_events_untouched(self):
        self.assertEqual(string_param_owners(self.data, 52, 'ActorName'), [52])
        self.assertEqual(string_param_owners(self.data, 0, 'ASCommand'), [0])
        shared = set_string_param(self.data, 52, 'ActorName', 'C02-Player_Child-A-0')
        self.assertEqual(string_param_owners(shared, 52, 'ActorName'), [0, 52])
        self.assertEqual(string_param_owners(shared, 0, 'ASCommand'), [0, 52])
        # La cadena compartida no se edita en sitio aunque el texto quepa.
        changed = set_string_param(shared, 52, 'ActorName', 'Item_Hookshot')
        flow = _assert_valid(self, changed)
        self.assertEqual(flow.action_params(52)['ActorName'], 'Item_Hookshot')
        self.assertEqual(flow.action_params(0)['ASCommand'], 'C02-Player_Child-A-0')
        self.assertEqual(string_param_owners(changed, 52, 'ActorName'), [52])

    def test_coexists_with_trim(self):
        off, idx = self.flow.pointer_slots()[0]
        trim = {off: 0xFFFF if idx != 0xFFFF else 0}
        for value in ('Item_Hookshot', LONG_VALUE):  # en sitio y ampliando
            a = set_string_param(patch_pointers(self.data, trim), 51, 'Actor', value)
            b = patch_pointers(set_string_param(self.data, 51, 'Actor', value), trim)
            self.assertEqual(a, b)
            flow = _assert_valid(self, a)
            self.assertEqual(flow.action_params(51)['Actor'], value)
            self.assertEqual(dict(flow.pointer_slots())[off], trim[off])

    def test_errors(self):
        with self.assertRaises(BfevflError):
            set_string_param(self.data, 51, 'Num', 'x')  # no es texto
        with self.assertRaises(BfevflError):
            set_string_param(self.data, 51, 'NoExiste', 'x')
        with self.assertRaises(BfevflError):
            set_string_param(self.data, len(self.flow.events), 'Actor', 'x')
        with self.assertRaises(BfevflError):
            string_param_owners(self.data, 51, 'Num')


class EventTests(unittest.TestCase):
    def test_defaults(self):
        ev = Event(index=1, kind=0, next=2)
        self.assertEqual((ev.cases, ev.forks, ev.join, ev.actor), ([], [], None, None))


if __name__ == '__main__':
    unittest.main()
