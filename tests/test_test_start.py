import os
import unittest
from pathlib import Path

from randomizer.formats.bfevfl import ACTION, SUBFLOW, EventFlow
from randomizer.formats.zs import ZsCodec
from randomizer.nup import NupArchive
from randomizer.formats import byml
from randomizer.test_start import (ANALYZED_INFO, HOOK_ENTRY, HOOK_FLAGS, HOOK_FLOW, START_POS,
                                   NewStartPos, StartPreset, apply_start, chain_calls,
                                   subflow_closure, with_start_pos, with_subflow_list)

NUP_PATH = os.environ.get('OOT_NUP')
PRESET = StartPreset('HyruleField_Child', 'HyruleField_FrontOfLostWoodBridge',
                     items=('Item_Ocarina_Fairy',), flags=(('Foo', True),))


def _shape(ev):
    return (ev.kind, ev.actor, ev.action, ev.query, ev.next, ev.cases, ev.forks, ev.join,
            ev.sub_flow, ev.sub_entry)


class NotInGenerateTest(unittest.TestCase):
    def test_not_used_by_generate(self):
        src = (Path(__file__).resolve().parent.parent / 'randomizer' / 'generate.py').read_text(
            encoding='utf-8')
        self.assertNotIn('test_start', src)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class ApplyStartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            p = f'Event/EventFlow/{HOOK_FLOW}.bfevfl.zs'
            cls.data = codec.decompress(p, nup.read(p))
        cls.flow = EventFlow(cls.data)

    def test_chain_order(self):
        new = EventFlow(apply_start(self.data, PRESET))
        i = new.entry_points[HOOK_ENTRY]
        seen = []
        while i != 0xFFFF:
            ev = new.events[i]
            seen.append((ev, new.action_params(i)))
            i = ev.next
        flags = [(p['GameDataName'], p['Value']) for ev, p in seen
                 if ev.kind == ACTION and ev.action == 'EventTriggerSetGameDataBool']
        self.assertEqual(flags, [(f, True) for f in HOOK_FLAGS] + [('Foo', True)])
        calls = [(ev.sub_flow, ev.sub_entry, p) for ev, p in seen if ev.kind == SUBFLOW]
        self.assertEqual(calls[0], ('Dm_SY_GetInEvent', 'GetInEvent',
                                    {'ActorName': 'Item_Ocarina_Fairy'}))
        flow, entry, params = calls[1]
        self.assertEqual((flow, entry), ('Dm_SY_BancChangeGo', 'EntryPoint0'))
        self.assertEqual(params['NextBanc'], 'HyruleField_Child')
        self.assertEqual(params['NextStartPos'], 'HyruleField_FrontOfLostWoodBridge')
        self.assertEqual(len(seen), len(HOOK_FLAGS) + 1 + 1 + 1)
        self.assertEqual((seen[-1][0].sub_flow, seen[-1][0].next), ('Dm_SY_BancChangeGo', 0xFFFF))

    def test_entry_lists_chain_subflows(self):
        # Every entry of the game lists the subflow events it reaches; without
        # that list the game hangs at the first call (batch 21).
        new = EventFlow(apply_start(self.data, PRESET))
        i = new.entry_points[HOOK_ENTRY]
        reached = []
        while i != 0xFFFF:
            if new.events[i].kind == SUBFLOW:
                reached.append(i)
            i = new.events[i].next
        self.assertEqual(len(reached), 2)
        self.assertEqual(new.entry_subflows(HOOK_ENTRY), reached)

    def test_subflow_closure_matches_game(self):
        # GameAnalyzedEventInfo lists, per event, every flow its entries reach
        # through subflow calls (recursively), sorted.
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            rows = byml.load(codec.decompress(ANALYZED_INFO, nup.read(ANALYZED_INFO)))[1]

            def load(name):
                p = f'Event/EventFlow/{name}.bfevfl.zs'
                return EventFlow(codec.decompress(p, nup.read(p))) if nup.has(p) else None

            for event in ('Dm_LostWood_0040', 'Dm_DeathMtTrail_0050', 'Dm_FairyFountain_Din'):
                row = next(r for r in rows if r['__RowId'] == event)
                flow = load(event)
                calls = [(event, e) for e in flow.entry_points]
                self.assertEqual(subflow_closure(load, calls, skip=event),
                                 row.get('SubFlowList', []), event)

    def test_with_subflow_list(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            raw = codec.decompress(ANALYZED_INFO, nup.read(ANALYZED_INFO))
        out = with_subflow_list(raw, HOOK_FLOW, ['B', 'A'])
        old, new = byml.load(raw)[1], byml.load(out)[1]
        self.assertEqual(len(old), len(new))
        for a, b in zip(old, new):
            if a['__RowId'] == HOOK_FLOW:
                self.assertEqual(b, {**a, 'SubFlowList': ['A', 'B']})
            else:
                self.assertEqual(a, b)
        with self.assertRaises(KeyError):
            with_subflow_list(raw, 'NoSuchEvent', ['A'])

    def test_with_start_pos(self):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            raw = codec.decompress(START_POS, nup.read(START_POS))
        pos = NewStartPos('RandoTest', (1.0, 2.0, 3.0), (0.0, 0.5, 0.0))
        out = with_start_pos(raw, 'HyruleCastle', pos)
        old, new = byml.load(raw)[1], byml.load(out)[1]
        self.assertEqual(new['HyruleCastle']['RandoTest'],
                         {'Rot': [0.0, 0.5, 0.0], 'Trans': [1.0, 2.0, 3.0]})
        self.assertEqual({k: v for k, v in new['HyruleCastle'].items() if k != 'RandoTest'},
                         old['HyruleCastle'])
        self.assertEqual({k: v for k, v in new.items() if k != 'HyruleCastle'},
                         {k: v for k, v in old.items() if k != 'HyruleCastle'})
        with self.assertRaises(KeyError):
            with_start_pos(raw, 'NoSuchBanc', pos)
        with self.assertRaises(ValueError):
            with_start_pos(raw, 'HyruleCastle', NewStartPos('EntrancePos', (0.0,) * 3, (0.0,) * 3))

    def test_chain_calls(self):
        self.assertEqual(chain_calls(PRESET), [('Dm_SY_GetInEvent', 'GetInEvent'),
                                               ('Dm_SY_BancChangeGo', 'EntryPoint0')])

    def test_original_events_untouched(self):
        new = EventFlow(apply_start(self.data, PRESET))
        for i in range(len(self.flow.events)):
            self.assertEqual(_shape(new.events[i]), _shape(self.flow.events[i]), i)
            self.assertEqual(new.action_params(i), self.flow.action_params(i), i)


if __name__ == '__main__':
    unittest.main()
