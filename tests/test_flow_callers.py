import unittest

from randomizer.flow_callers import entry_callers
from randomizer.formats.bfevfl import ACTION, END, Event
from randomizer.skipflow import SkipTable, effects_only
from tests.test_skipflow import A, SUB, fake


class EmptyFlow:
    events: list = []
    entry_points: dict = {}

    def action_params(self, index):
        return {}


class EntryCallersTests(unittest.TestCase):
    def test_subflow_and_transition(self):
        a = fake([SUB(0, 'B', 'C01', 1),
                  (Event(index=1, kind=ACTION, actor='Npc', action='EventTransition', next=END),
                   {1: {'EventName': 'B'}})],
                 {'EntryPoint0': 0})
        b = fake([A(0, 'K')], {'EntryPoint0': 0, 'C01': 0})
        self.assertEqual(entry_callers({'A': a, 'B': b}),
                         {('B', 'C01'): {'A'}, ('B', 'EntryPoint0'): {'A'}})

    def test_boot_event_name_and_unknown_names(self):
        a = fake([(Event(index=0, kind=ACTION, actor='Npc', action='X', next=1),
                   {0: {'BootEventName': 'B'}}),
                  (Event(index=1, kind=ACTION, actor='Npc', action='Y', next=END),
                   {1: {'EventName': 'NotAFlow'}})])
        b = fake([A(0, 'K')])
        self.assertEqual(entry_callers({'A': a, 'B': b}), {('B', 'EntryPoint0'): {'A'}})

    def test_same_file_calls_and_self_references_are_not_external(self):
        a = fake([SUB(0, '', 'Q', 1), SUB(1, 'A', 'Q', END), A(2, 'K')], {'E': 0, 'Q': 2})
        self.assertEqual(entry_callers({'A': a}), {})

    def test_hash_switch_call_counts(self):
        a = fake([Event(index=0, kind=5, sub_flow='B', sub_entry='Q', cases=[END],
                        case_hashes=[1])])
        b = fake([A(0, 'K')], {'Q': 0})
        self.assertEqual(entry_callers({'A': a, 'B': b}), {('B', 'Q'): {'A'}})

    def test_subflow_without_entry_name_means_entrypoint0(self):
        a = fake([SUB(0, 'B', None)])
        self.assertEqual(entry_callers({'A': a, 'B': fake([A(0, 'K')])}),
                         {('B', 'EntryPoint0'): {'A'}})

    def test_flow_without_flowchart_is_skipped(self):
        b = fake([A(0, 'K')])
        self.assertEqual(entry_callers({'A': EmptyFlow(), 'B': b}), {})


class ExternalEntryTests(unittest.TestCase):
    table = SkipTable({'actions': {'EventWait': 'drop'}})

    def flow(self):
        # E: 0 keep -> 1 calls C01.  C01: 2 keep -> 3 drop -> 4 keep.
        # Inlined into E, C01's own link 2 -> 3 would become 2 -> 4.
        return fake([A(0, 'KA', 1), SUB(1, '', 'C01', END), A(2, 'KB', 3),
                     A(3, 'EventWait', 4), A(4, 'KC')],
                    {'E': 0, 'C01': 2})

    def test_external_entry_is_not_inlined(self):
        flow = self.flow()
        self.assertIsNone(effects_only(flow, 'E', self.table).error)
        rw = effects_only(flow, 'E', self.table, external=frozenset({'C01'}))
        self.assertEqual(rw.error, 'shared')

    def test_targeted_entry_in_external_is_still_rewritten(self):
        flow = fake([A(0, 'KB', 1), A(1, 'EventWait', 2), A(2, 'KC')], {'C01': 0})
        self.assertIsNone(effects_only(flow, 'C01', self.table).error)
        rw = effects_only(flow, 'C01', self.table, external=frozenset({'C01'}))
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links[('next', 0)], 2)


if __name__ == '__main__':
    unittest.main()
