import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from randomizer.formats.bfevfl import (ACTION, END, FORK, JOIN, SUBFLOW, SWITCH, Event,
                                       EventFlow)
from randomizer.skipflow import (SPIKE_SCENES, Rewrite, SkipTable, _private_copies, apply_rewrite,
                                 build_spike_files,
                                 check_rewrite, effects_only, fork_dependencies, inlined_entries, linearize,
                                 reachable, reachable_chosen)

NUP_PATH = os.environ.get('OOT_NUP')

_spec = importlib.util.spec_from_file_location(
    'build_skip_actions', Path(__file__).resolve().parent.parent / 'tools' / 'build_skip_actions.py')
tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tool)

DROP = ['EventWait', 'EventTalk', 'EventMoveToTargetPosCamera',
        'EventMoveCameraAnimationInstructionsForFlowchart', 'EventPlayAS',
        'EventPlayerPlayASForFlowchart', 'EventPlayASWithClothWarp',
        'EventDemoProductSupportComment', 'EventSetAdvancedDoFForFlowchart',
        'EventTriggerEmitXLink', 'EventTriggerXLinkFadeByKey',
        'EventTriggerControllerRumble', 'EventNaviLookAtObject',
        'EventCloseMessageDialog', 'EventDoNothing']
KEEP = ['EventTriggerSetGameDataBool', 'EventTriggerSetEventBool',
        'EventTriggerAddOrRemovePouchContent', 'EventTransition',
        'EventWarpToTargetPosAndRot', 'EventPlayerWarpToTargetPosAndRot',
        'EventEventFadeOut', 'EventEventFadeIn', 'EventTriggerRequestAutoSave',
        'EventNotARealAction']


class TableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = SkipTable.load()

    def test_drop(self):
        for a in DROP:
            self.assertFalse(self.t.keeps(None, a), a)

    def test_keep(self):
        for a in KEEP:
            self.assertTrue(self.t.keeps(None, a), a)

    def test_state_keywords_win(self):
        self.assertTrue(self.t.keeps(None, 'EventGameDataBoolWaitChangeValue'))
        self.assertTrue(self.t.keeps(None, 'EventScrubBusinessWriteGameDataHaveTalked'))
        self.assertFalse(self.t.keeps(None, 'EventNaviWarpToPlayerHomePosition'))
        self.assertFalse(self.t.keeps(None, 'EventTriggerXLinkFadeByKey'))
        self.assertFalse(self.t.collapses('EventQueryPlayerCheckSelectedItem'))

    def test_play_ocarina_dropped(self):
        self.assertIs(self.t.keeps(None, 'EventPlayerPlayOcarinaFree'), False)

    def test_unknown_query(self):
        self.assertIs(self.t.collapses('NotARealQuery'), False)

    def test_subflows(self):
        for f, e in (('GetPouchContent', 'DisplayGetByActorName'),
                     ('Dm_SY_Ocarina', 'LearningOcarinaFollowExample'),
                     ('Common_Camera_Pln', 'CameraDoF_Default')):
            self.assertTrue(self.t.drops_subflow(f, e), (f, e))
        for f, e in (('GetPouchContent', 'GetPouchContentByActorName'),
                     ('Dm_SY_GetInEvent', 'GetInEvent_Zeldaletter')):
            self.assertFalse(self.t.drops_subflow(f, e), (f, e))

    def test_actor_override(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 't.json'
            p.write_text(json.dumps({
                'actions': {'EventX': 'drop', 'EventR': 'review'},
                'actor_actions': {'Npc.EventX': 'keep'},
                'queries': {'Q': 'collapse', 'S': 'state'},
                'subflows_drop': [], 'counts': {}}))
            t = SkipTable.load(p)
        self.assertTrue(t.keeps('Npc', 'EventX'))
        self.assertFalse(t.keeps('Other', 'EventX'))
        self.assertFalse(t.keeps(None, 'EventX'))
        self.assertTrue(t.keeps(None, 'EventR'))
        self.assertTrue(t.collapses('Q'))
        self.assertFalse(t.collapses('S'))


class ClassifierTests(unittest.TestCase):
    def test_actions(self):
        c = tool.classify_action
        self.assertEqual(c('EventGameDataBoolWaitChangeValue'), 'keep')  # state beats drop
        self.assertEqual(c('EventNaviWarpToPlayerHomePosition'), 'drop')  # drop beats warp keep
        self.assertEqual(c('EventTransition'), 'keep')
        self.assertEqual(c('EventSomethingElse'), 'review')

    def test_queries(self):
        c = tool.classify_query
        self.assertEqual(c('EventQueryPlayerCheckSelectedItem'), 'state')  # state beats collapse
        self.assertEqual(c('EventQueryTalkChoiceX'), 'collapse')
        self.assertEqual(c('EventQueryZzz'), 'review')


def A(i, name, nxt=END):
    return Event(index=i, kind=ACTION, actor='Npc', action=name, next=nxt)


def SW(i, query, cases):
    return Event(index=i, kind=SWITCH, actor='Npc', query=query, cases=list(cases))


def HS(i, cases, flow='Other', entry='Q', hashes=None):
    """Kind 5: a subflow call that switches on the called entry's result (hashes
    default to 100, 101, ...)."""
    hashes = list(hashes) if hashes is not None else [100 + k for k in range(len(cases))]
    return Event(index=i, kind=5, sub_flow=flow, sub_entry=entry, cases=list(cases),
                 case_hashes=hashes)


def RS(i, h=100):
    """Kind 6: ends the entry with result hash h (no event pointers)."""
    return Event(index=i, kind=6, result=h)


def SUB(i, flow, entry, nxt=END):
    return Event(index=i, kind=SUBFLOW, sub_flow=flow, sub_entry=entry, next=nxt)


def FK(i, forks, join):
    return Event(index=i, kind=FORK, forks=list(forks), join=join)


def JN(i, nxt=END):
    return Event(index=i, kind=JOIN, next=nxt)


def keep(ev):
    return (ev.action if ev.kind == ACTION else ev.sub_entry).startswith('K')


def collapse(ev):
    return ev.query.startswith('C')


def lin(events, entries=None, entry='E', **kw):
    return linearize(events, entries or {'E': 0}, entry, keep, collapse, **kw)


def rewritten(events, entries, rw):
    """(events, entries) as `apply_rewrite` would leave them: grown, copies written, links
    patched."""
    new = [copy.deepcopy(ev) for ev in events]
    for src in rw.grown:
        new.append(copy.deepcopy(events[src]))
        new[-1].index = len(new) - 1
    for dst, src in rw.copies.items():
        new[dst] = copy.deepcopy(events[src])
        new[dst].index = dst
    new_entries = dict(entries)
    for key, target in rw.links.items():
        if key[0] == 'entry':
            new_entries[key[1]] = target
        elif key[0] == 'next':
            new[key[1]].next = target
        else:
            new[key[1]].cases[key[2]] = target
    return new, new_entries


def walk(events, i):
    """Events visited from i following `next` only."""
    out = []
    while i != END:
        out.append(i)
        i = events[i].next
    return out


class LinearizeTests(unittest.TestCase):
    def test_linear(self):
        rw = lin([A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2')])
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 0, ('next', 0): 2, ('next', 2): END})
        self.assertEqual(rw.kept, [0, 2])

    def test_choice_out_of_range_is_a_refusal_not_an_exception(self):
        rw = lin([SW(0, 'C0', [1, 2]), A(1, 'K1'), A(2, 'K2')], choices={0: 5})
        self.assertEqual(rw.error, 'bad choice')
        self.assertIn('switch 0', rw.detail)

    def test_all_dropped(self):
        rw = lin([A(0, 'D0', 1), A(1, 'D1')])
        self.assertEqual(rw.links, {('entry', 'E'): END})
        self.assertEqual(rw.kept, [])

    def test_fork_flattened(self):
        ev = [FK(0, [1, 2], 4), A(1, 'K1', 4), A(2, 'D2', 3), A(3, 'K3', 4), JN(4, 5),
              A(5, 'K5')]
        rw = lin(ev)
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('next', 1): 3, ('next', 3): 5,
                                    ('next', 5): END})
        self.assertEqual(rw.kept, [1, 3, 5])
        self.assertFalse({0, 4} & set(rw.links.values()))

    def test_same_file_subflow_inlined(self):
        rw = lin([SUB(0, '', 'X', 1), A(1, 'K1'), A(2, 'K2')], {'E': 0, 'X': 2})
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 2, ('next', 2): 1, ('next', 1): END})
        self.assertEqual(rw.kept, [2, 1])

    def test_recursive_subflow(self):
        self.assertEqual(lin([SUB(0, '', 'E')]).error, 'recursive subflow')

    def test_cross_file_subflow(self):
        rw = lin([SUB(0, 'Other', 'Kx', 1), A(1, 'K1')])
        self.assertEqual(rw.links, {('entry', 'E'): 0, ('next', 0): 1, ('next', 1): END})
        rw = lin([SUB(0, 'Other', 'Dx', 1), A(1, 'K1')])
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('next', 1): END})

    def test_state_switch(self):
        ev = [SW(0, 'Q', [1, 2]), A(1, 'K1', 4), A(2, 'D2', 3), A(3, 'K3', 4), A(4, 'K4')]
        rw = lin(ev)
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 0, ('case', 0, 0): 1, ('case', 0, 1): 3,
                                    ('next', 1): 4, ('next', 3): 4, ('next', 4): END})
        self.assertEqual(rw.kept, [0, 1, 4, 3])

    def test_state_switch_after_join(self):
        # A kept switch inside a fork branch: each case continues past the join.
        ev = [FK(0, [1], 4), SW(1, 'Q', [2, 3]), A(2, 'K2', 4), A(3, 'D3', 4), JN(4, 5),
              A(5, 'K5')]
        rw = lin(ev)
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('case', 1, 0): 2, ('case', 1, 1): 5,
                                    ('next', 2): 5, ('next', 5): END})

    def test_collapse_default_and_choice(self):
        ev = [SW(0, 'C', [1, 2]), A(1, 'D1'), A(2, 'K2')]
        rw = lin(ev)
        self.assertEqual(rw.links, {('entry', 'E'): 2, ('next', 2): END})
        self.assertEqual(rw.collapsed, {0: 1})
        rw = lin(ev, choices={0: 0})
        self.assertEqual(rw.links, {('entry', 'E'): END})
        self.assertEqual(rw.collapsed, {0: 0})

    def test_kind5_same_file_runs_its_call(self):
        # 0 calls X; X keeps K1 and returns 101 -> case 1 (event 4).
        ev = [HS(0, [3, 4], '', 'X'), A(1, 'K1', 2), RS(2, 101), A(3, 'K3'), A(4, 'K4')]
        rw = lin(ev, {'E': 0, 'X': 1})
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('next', 1): 4, ('next', 4): END})
        self.assertEqual(rw.kept, [1, 4])

    def test_kind5_each_result_routes_to_its_case(self):
        # X: kept switch 1 -> result 100 (event 2) or 101 (event 3).
        ev = [HS(0, [4, 5], '', 'X'), SW(1, 'Q', [2, 3]), RS(2, 100), RS(3, 101),
              A(4, 'K4'), A(5, 'K5')]
        rw = lin(ev, {'E': 0, 'X': 1})
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('case', 1, 0): 4, ('case', 1, 1): 5,
                                    ('next', 4): END, ('next', 5): END})

    def test_kind5_without_matching_result(self):
        ev = [HS(0, [2], '', 'X'), RS(1, 999), A(2, 'K2')]
        self.assertEqual(lin(ev, {'E': 0, 'X': 1}).error, 'no result')
        ev = [HS(0, [2], '', 'X'), A(1, 'K1'), A(2, 'K2')]  # X ends without a result
        self.assertEqual(lin(ev, {'E': 0, 'X': 1}).error, 'no result')

    def test_kind5_recursive_call(self):
        self.assertEqual(lin([HS(0, [END], '', 'E')]).error, 'recursive subflow')

    def test_kind5_cross_file_kept(self):
        ev = [HS(0, [1, 2], 'Other', 'Kx'), A(1, 'K1'), A(2, 'D2')]
        rw = lin(ev)
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 0, ('case', 0, 0): 1, ('case', 0, 1): END,
                                    ('next', 1): END})
        self.assertEqual(rw.kept, [0, 1])

    def test_kind5_cross_file_dropped_needs_a_choice(self):
        ev = [HS(0, [1, 2], 'Other', 'Dx'), A(1, 'K1'), A(2, 'K2')]
        self.assertEqual(lin(ev).error, 'subflow switch')
        rw = lin(ev, choices={0: 1})
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 2, ('next', 2): END})
        self.assertEqual(rw.collapsed, {0: 1})

    def test_result_inside_a_fork_branch_is_refused(self):
        rw = lin([FK(0, [1], 2), RS(1), JN(2)])
        self.assertEqual(rw.error, 'result in call')

    def test_result_is_a_kept_terminal(self):
        # The entry's result is what its caller switches on: it stays.
        rw = lin([A(0, 'D0', 1), A(1, 'K1', 2), A(2, 'D2', 3), RS(3)])
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 1, ('next', 1): 3})
        self.assertEqual(rw.kept, [1, 3])

    def test_result_inside_an_inlined_call_is_refused(self):
        # The output could not continue after the result to the caller's next.
        rw = lin([SUB(0, '', 'X', 1), A(1, 'K1'), RS(2)], {'E': 0, 'X': 2})
        self.assertEqual(rw.error, 'result in call')

    def test_kind5_reachable_follows_cases(self):
        self.assertEqual(reachable([HS(0, [1, 2]), A(1, 'a'), A(2, 'b')], {}, [0]), {0, 1, 2})

    def test_collapse_prefers_distinct_effects(self):
        # Both cases reach K3; only case 1 has an effect of its own.
        ev = [SW(0, 'C', [1, 2]), A(1, 'D1', 3), A(2, 'K2', 3), A(3, 'K3')]
        self.assertEqual(lin(ev).links[('entry', 'E')], 2)

    def test_collapse_avoids_cases_that_come_back(self):
        # Case 0 asks the question again (back to the switch); case 1 moves on.
        ev = [SW(0, 'C', [1, 2]), A(1, 'K1', 0), A(2, 'K2')]
        rw = lin(ev)
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 2, ('next', 2): END})

    def test_cycle_without_exit_is_loop(self):
        # A kept switch whose cases all lead back: the output never ends.
        rw = lin([A(0, 'K0', 1), SW(1, 'Q', [0, 0])])
        self.assertEqual(rw.error, 'loop')

    def test_cycle_with_exit_is_kept(self):
        # A state polling loop: case 1 leaves it.
        rw = lin([SW(0, 'Q', [1, 2]), A(1, 'K1', 0), A(2, 'K2')])
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links[('next', 1)], 0)

    def test_conflict(self):
        # K3 (entry X) is called twice and must continue at 1, then at 2.
        ev = [SUB(0, '', 'X', 1), SUB(1, '', 'X', 2), A(2, 'K2'), A(3, 'K3')]
        rw = lin(ev, {'E': 0, 'X': 3})
        self.assertEqual(rw.error, 'conflict')

    def test_loop(self):
        self.assertEqual(lin([A(0, 'D0', 1), A(1, 'D1', 0)]).error, 'loop')

    def test_shared(self):
        # A kept subflow is never copied: relinking a protected one fails.
        rw = lin([SUB(0, 'Other', 'K0', 1), A(1, 'D1', 2), A(2, 'K2')], protected=frozenset({0}))
        self.assertEqual(rw.error, 'shared')
        rw = lin([A(0, 'K0', 1), A(1, 'K1')], protected=frozenset({0}))
        self.assertIsNone(rw.error)

    def test_fork_with_end_join_runs_all_branches(self):
        # 0 fork [1, 2] join END; 1 keep -> END; 2 keep -> END
        rw = lin([FK(0, [1, 2], END), A(1, 'K'), A(2, 'K')], {'E': 0})
        self.assertIsNone(rw.error)
        self.assertEqual(rw.kept, [1, 2])
        self.assertEqual(rw.links[('next', 1)], 2)
        self.assertEqual(rw.links[('next', 2)], END)

    def test_branch_back_to_own_fork_is_a_loop(self):
        rw = lin([FK(0, [1], 2), A(1, 'D', 0), JN(2)], {'E': 0})
        self.assertEqual(rw.error, 'loop')

    def test_join_of_another_fork_is_refused(self):
        # branch of fork 0 reaches join 4, which belongs to fork 3
        rw = lin([FK(0, [1], 2), A(1, 'K', 4), JN(2), FK(3, [], 4), JN(4)], {'E': 0})
        self.assertEqual(rw.error, 'join mismatch')

    def test_protected_event_gets_a_private_copy(self):
        # entry E: 0 keep -> 1 keep -> 2 drop -> 3 keep; entry F (untargeted) starts at 1;
        # 4 is reached by nothing: the donor slot for the copy of 1.
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K'), A(4, 'D')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3}))
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.copies, {4: 1})
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(walk(new, new_entries['F']), [1, 2, 3])
        self.assertEqual(walk(new, new_entries['E']), [0, 4, 3])
        self.assertEqual(new[4].action, 'K')

    def test_protected_event_without_a_donor(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K')]
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}))
        self.assertEqual(rw.error, 'no donor')

    def test_dropped_event_of_the_path_is_a_donor(self):
        # Task 1's flow: E starts at 0 (dropped), which nothing reaches after the rewrite.
        events = [A(0, 'D', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3}))
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.copies, {0: 1})
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(walk(new, new_entries['F']), [1, 2, 3])
        self.assertEqual(walk(new, new_entries['E']), [0, 3])

    def test_copied_event_redirects_its_protected_predecessor(self):
        # E: 0 keep -> 1 keep -> 2 keep -> 3 drop -> 4 keep; F starts at 1: 1 is copied
        # because 2 is, and the copy of 1 goes to the copy of 2. Donors: 5 and 6.
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'K', 3), A(3, 'D', 4), A(4, 'K'),
                  A(5, 'D'), A(6, 'D')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}))
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(sorted(rw.copies.values()), [1, 2])
        self.assertEqual(set(rw.copies), {5, 6})
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(walk(new, new_entries['F']), [1, 2, 3, 4])
        path = walk(new, new_entries['E'])
        self.assertEqual([new[i].action for i in path], ['K'] * 4)
        self.assertEqual(path[-1], 4)

    def test_protected_switch_is_still_shared(self):
        # E: 0 keep -> 1 switch (kept) -> [2 drop -> 3 keep]; F starts at 1.
        events = [A(0, 'K', 1), SW(1, 'S', [2]), A(2, 'D', 3), A(3, 'K'), A(4, 'D')]
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}))
        self.assertEqual(rw.error, 'shared')

    def test_donor_must_be_copyable(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K'), A(4, 'D'), A(5, 'D')]
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}),
                 can_copy=lambda src, dst: dst != 4)
        self.assertEqual(rw.copies, {5: 1})
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}),
                 can_copy=lambda src, dst: False)
        self.assertEqual(rw.error, 'no donor')

    def test_donor_must_be_an_action(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K'), JN(4)]
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}))
        self.assertEqual(rw.error, 'no donor')

    def test_protected_switch_grows_a_copy(self):
        # E: 0 keep -> 1 switch (kept) -> [2 drop -> 3 keep | 4 keep]; F starts at 1.
        events = [A(0, 'K', 1), SW(1, 'S', [2, 4]), A(2, 'D', 3), A(3, 'K'), A(4, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.grown, [1])
        self.assertEqual(rw.copies, {})
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(reachable(new, new_entries, [new_entries['F']]), {1, 2, 3, 4})
        self.assertEqual([ev.cases for ev in new[:5]], [[], [2, 4], [], [], []])
        self.assertEqual(new[0].next, 5)
        self.assertEqual(new[5].cases, [3, 4])
        self.assertEqual(reachable(new, new_entries, [new_entries['E']]), {0, 5, 3, 4})

    def test_switch_copy_carries_its_unchanged_cases(self):
        # Only case 0 changes; the copy still has case 1 (the original target).
        events = [A(0, 'K', 1), SW(1, 'S', [2, 3]), A(2, 'D', 3), A(3, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.grown, [1])
        self.assertEqual({k: v for k, v in rw.links.items() if k[0] == 'case'},
                         {('case', 4, 0): 3, ('case', 4, 1): 3})

    def test_switch_copy_case_without_a_link_keeps_its_target(self):
        # The rewrite links only case 0 of the protected switch 1; the copy (new slot 4)
        # falls back to the original target of case 1.
        events = [A(0, 'K', 1), SW(1, 'S', [2, 3]), A(2, 'D', 3), A(3, 'K')]
        entries = {'E': 0, 'F': 1}
        links = {('entry', 'E'): 0, ('next', 0): 1, ('case', 1, 0): 3}
        links, copies, grown = _private_copies(events, entries, links, frozenset({1, 2, 3}),
                                               None, grow=True)
        self.assertEqual((grown, copies), ([1], {}))
        self.assertEqual(links, {('entry', 'E'): 0, ('next', 0): 4, ('case', 4, 0): 3,
                                 ('case', 4, 1): 3})
        links, _, _ = _private_copies([A(0, 'K', 1), SW(1, 'S', [2, 2]), A(2, 'D', 3), A(3, 'K')],
                                      entries, {('entry', 'E'): 0, ('next', 0): 1,
                                                ('case', 1, 0): 3},
                                      frozenset({1, 2, 3}), None, grow=True)
        self.assertEqual(links[('case', 4, 1)], 2)

    def test_protected_subflow_grows_a_copy(self):
        # E: 0 keep -> 1 other-file subflow (kept) -> 2 drop -> 3 keep; F starts at 1.
        events = [A(0, 'K', 1), SUB(1, 'Other', 'KX', 2), A(2, 'D', 3), A(3, 'K')]
        entries = {'E': 0, 'F': 1}
        self.assertEqual(lin(events, entries, protected=frozenset({1, 2, 3})).error, 'shared')
        rw = lin(events, entries, protected=frozenset({1, 2, 3}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.grown, [1])
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(walk(new, new_entries['F']), [1, 2, 3])
        self.assertEqual(walk(new, new_entries['E']), [0, 4, 3])

    def test_action_without_a_donor_grows(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual((rw.grown, rw.copies), ([1], {}))
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(walk(new, new_entries['F']), [1, 2, 3])
        self.assertEqual(walk(new, new_entries['E']), [0, 4, 3])

    def test_actions_take_donors_before_new_slots(self):
        # E: 0 keep -> 1 keep -> 2 switch -> [3 drop -> 4 keep]; F starts at 1; donor 5.
        # 2 is copied first (new slot 6), then 1 (to the donor 5).
        events = [A(0, 'K', 1), A(1, 'K', 2), SW(2, 'S', [3]), A(3, 'D', 4), A(4, 'K'),
                  A(5, 'D')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual((rw.grown, rw.copies), ([2], {5: 1}))
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(reachable(new, new_entries, [new_entries['F']]), {1, 2, 3, 4})
        self.assertEqual(reachable(new, new_entries, [new_entries['E']]), {0, 5, 6, 4})

    def test_new_slots_follow_creation_order(self):
        # E: 0 keep -> 1 switch -> [2 switch -> [3 drop -> 4 keep]]; F starts at 1; no donor.
        events = [A(0, 'K', 1), SW(1, 'S', [2]), SW(2, 'S', [3]), A(3, 'D', 4), A(4, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}), grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(rw.grown, [2, 1])
        new, new_entries = rewritten(events, entries, rw)
        self.assertEqual(new[0].next, 6)
        self.assertEqual((new[6].cases, new[5].cases), ([5], [4]))
        self.assertEqual(reachable(new, new_entries, [new_entries['F']]), {1, 2, 3, 4})

    def test_without_grow_nothing_grows(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K'), A(4, 'D')]
        rw = lin(events, {'E': 0, 'F': 1}, protected=frozenset({1, 2, 3}), grow=False)
        self.assertEqual((rw.grown, rw.copies), ([], {4: 1}))

    def test_apply_rewrite_refuses_a_failed_rewrite(self):
        with self.assertRaises(ValueError):
            apply_rewrite(b'', None, Rewrite({}, [], 'loop', 'x'))


class CheckRewriteTests(unittest.TestCase):
    def check(self, events, entries, rw, entry='E'):
        new, new_entries = rewritten(events, entries, rw)
        return check_rewrite(FakeFlow(events, entries, {}), FakeFlow(new, new_entries, {}),
                             entry, rw)

    def ok(self, events, entries=None, **kw):
        entries = entries or {'E': 0}
        rw = lin(events, entries, **kw)
        self.assertIsNone(rw.error, rw.detail)
        self.assertEqual(self.check(events, entries, rw), [])

    def test_linearized_output_is_accepted(self):
        self.ok([A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2')])
        self.ok([FK(0, [1, 2], 4), A(1, 'K1', 4), A(2, 'D2', 3), A(3, 'K3', 4), JN(4, 5),
                 A(5, 'K5')])
        self.ok([SUB(0, '', 'X', 1), A(1, 'K1'), A(2, 'K2')], {'E': 0, 'X': 2})
        self.ok([HS(0, [3, 4], '', 'X'), A(1, 'K1', 2), RS(2, 101), A(3, 'K3'), A(4, 'K4')],
                {'E': 0, 'X': 1})
        self.ok([SW(0, 'Q', [1, 2]), A(1, 'K1'), A(2, 'K2')])

    def test_swapped_links_are_an_order_problem(self):
        events = [A(0, 'K0', 1), A(1, 'K1', 2), A(2, 'K2')]
        rw = Rewrite({('entry', 'E'): 2, ('next', 2): 1, ('next', 1): 0, ('next', 0): END},
                     [2, 1, 0])
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 3') for p in problems), problems)

    def test_link_to_an_unrelated_node_is_an_order_problem(self):
        events = [A(0, 'K0'), A(1, 'K1')]  # 1 does not follow 0
        rw = Rewrite({('entry', 'E'): 0, ('next', 0): 1, ('next', 1): END}, [0, 1])
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 3') for p in problems), problems)

    def test_reachable_join_is_reported(self):
        events = [FK(0, [1, 2], 3), A(1, 'K1', 3), A(2, 'K2', 3), JN(3, 4), A(4, 'K4')]
        rw = Rewrite({('entry', 'E'): 1}, [1, 4])  # 1 still goes to the join
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 2') for p in problems), problems)

    def test_kept_set_mismatch(self):
        events = [A(0, 'K0', 1), A(1, 'K1')]
        rw = Rewrite({('entry', 'E'): 0, ('next', 0): 1, ('next', 1): END}, [0])
        self.assertTrue(any(p.startswith('rule 1') for p in self.check(events, {'E': 0}, rw)))

    def test_caller_of_the_targeted_entry_is_reported(self):
        # F (untargeted) calls the targeted entry E by name, so it reaches the rewritten events.
        events = [A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2'), SUB(3, '', 'E')]
        entries = {'E': 0, 'F': 3}
        rw = lin(events, entries)
        self.assertIsNone(rw.error, rw.detail)
        problems = self.check(events, entries, rw)
        self.assertTrue(any(p.startswith('rule 4') and 'F' in p for p in problems), problems)

    def test_exclusive_cases_chained_in_a_fork_branch(self):
        events = [FK(0, [1, 4], 5), SW(1, 'Q', [2, 3]), A(2, 'K2'), A(3, 'K3'), A(4, 'K4'),
                  JN(5, 6), A(6, 'K6')]
        rw = Rewrite({('entry', 'E'): 1, ('next', 2): 3, ('next', 3): 4, ('next', 4): 6,
                      ('next', 6): END, ('case', 1, 0): 2, ('case', 1, 1): 3},
                     [1, 2, 3, 4, 6])
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 3') for p in problems), problems)

    def test_exclusivity_rule_alone_flags_chained_cases(self):
        # Branch 0 is a switch with cases 2 and 3; branch 1 is event 3, so the branch-end edge
        # makes 3 follow 2 in the augmented graph: only the exclusivity rule can object.
        events = [FK(0, [1, 3], 5), SW(1, 'Q', [2, 3]), A(2, 'K2'), A(3, 'K3'), A(4, 'D'),
                  JN(5, 6), A(6, 'K6')]
        rw = Rewrite({('entry', 'E'): 1, ('case', 1, 0): 2, ('case', 1, 1): 3, ('next', 2): 3,
                      ('next', 3): 6, ('next', 6): END}, [1, 2, 3, 6])
        problems = self.check(events, {'E': 0}, rw)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn('exclusive cases', problems[0])
        self.assertNotIn('does not follow', problems[0])

    def test_exclusive_cases_chained_outside_a_fork(self):
        events = [SW(0, 'Q', [1, 2]), A(1, 'K1'), A(2, 'K2')]
        rw = Rewrite({('entry', 'E'): 0, ('case', 0, 0): 1, ('case', 0, 1): 2,
                      ('next', 1): 2, ('next', 2): END}, [0, 1, 2])
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 3') for p in problems), problems)

    def test_external_entry_changed_by_the_rewrite(self):
        events = [SUB(0, '', 'X', 1), A(1, 'K1'), A(2, 'K2', 3), A(3, 'D3', 4), A(4, 'K4')]
        entries = {'E': 0, 'X': 2}
        rw = lin(events, entries)
        new, new_entries = rewritten(events, entries, rw)
        old, newf = FakeFlow(events, entries, {}), FakeFlow(new, new_entries, {})
        self.assertEqual(check_rewrite(old, newf, 'E', rw), [])
        problems = check_rewrite(old, newf, 'E', rw, external=frozenset({'X'}))
        self.assertTrue(any(p.startswith('rule 4') and 'X' in p for p in problems), problems)
        # An entry whose reachability may change (another target of the file) is tolerated.
        self.assertEqual(check_rewrite(old, newf, 'E', rw, external=frozenset({'X'}),
                                       tolerated=frozenset({'X'})), [])

    def test_untouched_other_entry_is_fine(self):
        events = [A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2'), A(3, 'K3', 4), A(4, 'K4')]
        entries = {'E': 0, 'F': 3}
        rw = lin(events, entries)
        self.assertEqual(self.check(events, entries, rw), [])

    def test_copies_stand_in_for_their_originals(self):
        events = [A(0, 'K', 1), A(1, 'K', 2), A(2, 'D', 3), A(3, 'K'), A(4, 'D')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3}))
        self.assertEqual(rw.copies, {4: 1})
        self.assertEqual(self.check(events, entries, rw), [])

    def test_new_slots_stand_in_for_their_sources(self):
        events = [A(0, 'K', 1), SW(1, 'S', [2, 4]), A(2, 'D', 3), A(3, 'K'), A(4, 'K')]
        entries = {'E': 0, 'F': 1}
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}), grow=True)
        self.assertEqual(rw.grown, [1])
        self.assertEqual(self.check(events, entries, rw), [])
        events = [A(0, 'K', 1), A(1, 'K', 2), SW(2, 'S', [3]), A(3, 'D', 4), A(4, 'K'),
                  A(5, 'D')]
        rw = lin(events, entries, protected=frozenset({1, 2, 3, 4}), grow=True)
        self.assertEqual((rw.grown, rw.copies), ([2], {5: 1}))
        self.assertEqual(self.check(events, entries, rw), [])

    def test_fade_out_without_a_later_fade_in(self):
        events = [A(0, 'EventEventFadeOut', 1), A(1, 'D1', 2), A(2, 'EventEventFadeIn')]
        rw = Rewrite({('entry', 'E'): 0, ('next', 0): END}, [0])
        problems = self.check(events, {'E': 0}, rw)
        self.assertTrue(any(p.startswith('rule 5') for p in problems), problems)
        rw = Rewrite({('entry', 'E'): 0, ('next', 0): 2, ('next', 2): END}, [0, 2])
        self.assertEqual(self.check(events, {'E': 0}, rw), [])

    def test_fade_out_ending_the_old_flow_too_is_fine(self):
        events = [A(0, 'EventLoadingFadeOut', 1), A(1, 'D1')]
        rw = Rewrite({('entry', 'E'): 0, ('next', 0): END}, [0])
        self.assertEqual(self.check(events, {'E': 0}, rw), [])


class ReachableTests(unittest.TestCase):
    def test_follows_everything(self):
        ev = [FK(0, [1], 2), SUB(1, '', 'X', 2), JN(2, 3), SW(3, 'Q', [4, 5]), A(4, 'a'),
              A(5, 'b'), A(6, 'x')]
        self.assertEqual(reachable(ev, {'E': 0, 'X': 6}, [0]), set(range(7)))
        self.assertEqual(reachable_chosen(ev, {'E': 0, 'X': 6}, [0], {3: 1}),
                         set(range(7)) - {4})


SPIKE = {'Dm_Kokiri_0155': ([51], [52]), 'Dm_Kokiri_0060': ([], []),
         'Dm_HrlCastle_0050': ([238], []), 'Dm_MelodyGet_Zelda': ([66], [4, 5, 6])}


class FakeFlow:
    """What the fork dependency check needs from an EventFlow."""
    def __init__(self, events, entry_points, params):
        self.events, self.entry_points, self._params = events, entry_points, params

    def action_params(self, index):
        return self._params.get(index, {})

    def copyable(self, src, dst):
        return True


def SETF(i, flag, nxt=END):
    return A(i, 'EventTriggerSetGameDataBool', nxt), {i: {'GameDataName': flag}}


def RDF(i, flag, cases):
    return SW(i, 'EventQueryIsGameDataBool', cases), {i: {'GameDataName': flag}}


def fake(parts, entries=None):
    events, params = [], {}
    for p in parts:
        ev, pr = p if isinstance(p, tuple) else (p, {})
        events.append(ev)
        params.update(pr)
    return FakeFlow(events, entries or {'E': 0}, params)


class ForkDependencyTests(unittest.TestCase):
    table = SkipTable({'actions': {'EventWait': 'drop'}})

    def dependent(self):
        # fork 0: branch 1 sets X; branch 3 reads X
        return fake([FK(0, [1, 3], 6), SETF(1, 'X', 6), A(2, 'KA', 6),
                     RDF(3, 'X', [4, 5]), A(4, 'K4', 6), A(5, 'K5', 6), JN(6)])

    def test_flagged(self):
        flow = self.dependent()
        self.assertEqual(fork_dependencies(flow, 'E'), [(0, 'X')])
        rw = effects_only(flow, 'E', self.table)
        self.assertEqual(rw.error, 'fork dependency')
        self.assertIn('X', rw.detail)

    def test_reviewed_fork_is_accepted(self):
        rw = effects_only(self.dependent(), 'E', self.table, reviewed_forks=frozenset({0}))
        self.assertNotEqual(rw.error, 'fork dependency')

    def test_independent_branches(self):
        flow = fake([FK(0, [1, 3], 6), SETF(1, 'X', 6), A(2, 'KA', 6),
                     RDF(3, 'Y', [4, 5]), A(4, 'K4', 6), A(5, 'K5', 6), JN(6)])
        self.assertEqual(fork_dependencies(flow, 'E'), [])
        self.assertIsNone(effects_only(flow, 'E', self.table).error)

    def test_read_in_same_branch_is_fine(self):
        flow = fake([FK(0, [1, 4], 5), SETF(1, 'X', 2), RDF(2, 'X', [3, 3]),
                     A(3, 'K3', 5), A(4, 'K4', 5), JN(5)])
        self.assertEqual(fork_dependencies(flow, 'E'), [])

    def test_read_through_same_file_call(self):
        # branch 1 calls entry Q (event 4) whose switch reads X; branch 2 sets X
        flow = fake([FK(0, [1, 2], 6), SUB(1, '', 'Q', 6), SETF(2, 'X', 6),
                     A(3, 'KA', 6), RDF(4, 'X', [5, 5]), A(5, 'K5', END), JN(6)],
                    {'E': 0, 'Q': 4})
        self.assertEqual(fork_dependencies(flow, 'E'), [(0, 'X')])

    def test_write_through_same_file_call(self):
        flow = fake([FK(0, [1, 2], 6), SUB(1, '', 'Q', 6), RDF(2, 'X', [3, 3]),
                     A(3, 'K3', 6), SETF(4, 'X', END), A(5, 'K5', 6), JN(6)],
                    {'E': 0, 'Q': 4})
        self.assertEqual(fork_dependencies(flow, 'E'), [(0, 'X')])

    def test_other_actions_do_not_write(self):
        flow = fake([FK(0, [1, 2], 4), (A(1, 'EventQueryNotAWriter', 4), {1: {'GameDataName': 'X'}}),
                     RDF(2, 'X', [3, 3]), A(3, 'K3', 4), JN(4)])
        self.assertEqual(fork_dependencies(flow, 'E'), [])


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class SpikeForkDependencyTests(unittest.TestCase):
    def test_spike_scenes_not_flagged(self):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for name in SPIKE_SCENES:
                path = f'Event/EventFlow/{name}.bfevfl.zs'
                flow = EventFlow(codec.decompress(path, nup.read(path)))
                with self.subTest(name):
                    self.assertEqual(fork_dependencies(flow, 'EntryPoint0'), [])


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class SpikeScenesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        cls.table = SkipTable.load()
        cls.data = {}
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for name in SPIKE:
                path = f'Event/EventFlow/{name}.bfevfl.zs'
                cls.data[name] = codec.decompress(path, nup.read(path))

    def test_scenes(self):
        for name, (yes, no) in SPIKE.items():
            with self.subTest(name):
                data = self.data[name]
                flow = EventFlow(data)
                rw = effects_only(flow, 'EntryPoint0', self.table)
                self.assertIsNone(rw.error, rw.detail)
                out = apply_rewrite(data, flow, rw)
                self.assertEqual(len(out), len(data))
                start = [flow.entry_points['EntryPoint0']]
                before = reachable_chosen(flow.events, flow.entry_points, start, rw.collapsed)
                new = EventFlow(out)
                after = reachable(new.events, new.entry_points,
                                  [new.entry_points['EntryPoint0']])
                self.assertFalse({new.events[i].kind for i in after} & {FORK, JOIN})
                for i in after:
                    ev = new.events[i]
                    if ev.kind == ACTION:
                        self.assertTrue(self.table.keeps(ev.actor, ev.action), (i, ev.action))
                kept_before = {i for i in before if flow.events[i].kind == ACTION
                               and self.table.keeps(flow.events[i].actor, flow.events[i].action)}
                self.assertEqual(kept_before - after, set())
                for i in yes:
                    self.assertIn(i, after)
                for i in no:
                    self.assertNotIn(i, after)

    def _fade_paths(self, flow, start):
        """Yields lists of events on each path from `start` (switch cases and subflows followed)."""
        events, entries = flow.events, flow.entry_points

        def walk(i, trail):
            while i != END:
                if i in trail:
                    yield trail
                    return
                trail = trail + [i]
                ev = events[i]
                if ev.kind == SWITCH:
                    for c in ev.cases:
                        yield from walk(c, trail)
                    return
                if ev.kind == FORK:
                    for c in ev.forks + [ev.join]:
                        yield from walk(c, trail)
                    return
                if ev.kind == SUBFLOW and ev.sub_flow == '' and ev.sub_entry in entries:
                    for p in walk(entries[ev.sub_entry], trail):
                        yield p
                if ev.next is None:
                    break
                i = ev.next
            yield trail
        return walk(start, [])

    def test_spike_fades(self):
        for name in SPIKE_SCENES:
            with self.subTest(name):
                data = self.data_for(name)
                flow = EventFlow(data)
                rw = effects_only(flow, 'EntryPoint0', self.table)
                self.assertIsNone(rw.error, rw.detail)
                new = EventFlow(apply_rewrite(data, flow, rw))
                # fade-outs of the original that some later fade-in follows
                orig_paths = list(self._fade_paths(flow, flow.entry_points['EntryPoint0']))

                def fades(ev):
                    return ev.kind == ACTION and ev.action

                guarded = set()
                for path in orig_paths:
                    for n, i in enumerate(path):
                        if fades(flow.events[i]) == 'EventEventFadeOut' and any(
                                fades(flow.events[j]) == 'EventEventFadeIn' for j in path[n + 1:]):
                            guarded.add(i)
                for path in self._fade_paths(new, new.entry_points['EntryPoint0']):
                    for n, i in enumerate(path):
                        if fades(new.events[i]) == 'EventEventFadeOut' and i in guarded:
                            self.assertTrue(
                                any(fades(new.events[j]) == 'EventEventFadeIn' for j in path[n + 1:]),
                                f'{name}: fade-out {i} has no kept fade-in after it: {path}')

    def data_for(self, name):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            path = f'Event/EventFlow/{name}.bfevfl.zs'
            return codec.decompress(path, nup.read(path))

    def test_build_spike_files(self):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        with NupArchive(NUP_PATH) as nup:
            files = build_spike_files(nup)
            codec = ZsCodec.from_archive(nup)
            self.assertEqual(set(files), {f'Event/EventFlow/{n}.bfevfl.zs' for n in SPIKE_SCENES})
            for path, comp in files.items():
                self.assertEqual(len(codec.decompress(path, comp)),
                                 len(codec.decompress(path, nup.read(path))))


# The childhood survey: flows of the story and NPCs of the childhood (entries from
# cutscenes.json story_flows, else all of them).
CHILD_FLOWS = ('OpeningEvent', 'Meet_DekuTree', 'Get_StoneOfForest', 'Goto_HyruleCastle',
               'Get_StoneOfFire', 'Get_StoneOfWater', 'SubEvent_GetEponaSong',
               'HyruleCastle_FoundBySecurity', 'Npc_Hylia_Zelda_Child', 'Npc_Kokiri_007_Child',
               'Npc_Kokiri_010_Child', 'Npc_Kokiri_011_Child', 'Npc_Kokiri_Mido_Child',
               'Npc_Hylia_052_Child', 'Npc_Hylia_ImperialSoldier_001_Child',
               'MelodyGet_Sun_SubEvent', 'DoorOfTime', 'NpcCommon')


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class PrivateCopyRealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from randomizer.formats.zs import ZsCodec
        from randomizer.nup import NupArchive
        cls.table = SkipTable.load()
        policy = json.loads((Path(__file__).resolve().parent.parent / 'randomizer' / 'data'
                             / 'cutscenes.json').read_text(encoding='utf-8'))['story_flows']
        cls.flows = {}
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for name in CHILD_FLOWS:
                path = f'Event/EventFlow/{name}.bfevfl.zs'
                cls.flows[name] = (codec.decompress(path, nup.read(path)), policy.get(name, '*'))

    def test_untargeted_entries_reach_the_same_events(self):
        rewrites = 0
        for name, (data, entries) in self.flows.items():
            flow = EventFlow(data)
            for entry in (list(flow.entry_points) if entries == '*' else entries):
                rw = effects_only(flow, entry, self.table)
                if rw.error:
                    continue
                rewrites += 1
                with self.subTest(name=name, entry=entry):
                    new = EventFlow(apply_rewrite(data, flow, rw))
                    inlined = inlined_entries(flow, entry)
                    for other, i in flow.entry_points.items():
                        before = reachable(flow.events, flow.entry_points, [i])
                        # Known gap (not about copies): an entry that calls the targeted
                        # entry by name follows its moved entry slot.
                        if other in inlined or any(
                                flow.events[j].kind in (SUBFLOW, 5)
                                and flow.events[j].sub_flow == ''
                                and flow.events[j].sub_entry in inlined for j in before):
                            continue
                        self.assertEqual(
                            reachable(new.events, new.entry_points, [new.entry_points[other]]),
                            before, other)
                    for dst, src in rw.copies.items():
                        self.assertEqual((new.events[dst].actor, new.events[dst].action),
                                         (flow.events[src].actor, flow.events[src].action))
                        self.assertEqual(new.action_params(dst), flow.action_params(src))
        self.assertGreaterEqual(rewrites, 100)

    def test_checker_accepts_rewrites_but_for_callers_of_the_targeted_entry(self):
        checked = 0
        for name, (data, entries) in self.flows.items():
            flow = EventFlow(data)
            for entry in (list(flow.entry_points) if entries == '*' else entries):
                rw = effects_only(flow, entry, self.table)
                if rw.error:
                    continue
                checked += 1
                problems = check_rewrite(flow, apply_rewrite(data, flow, rw), entry, rw)
                with self.subTest(name=name, entry=entry):
                    self.assertEqual([p for p in problems if not p.startswith('rule 4')], [])
        self.assertGreaterEqual(checked, 100)

    def test_checker_reports_an_untargeted_caller_of_the_targeted_entry(self):
        # Npc_Hylia_Zelda_Child: the untargeted entry Talk calls the targeted Intro by name.
        data, _ = self.flows['Npc_Hylia_Zelda_Child']
        flow = EventFlow(data)
        calls = [ev for ev in flow.events if ev.kind in (SUBFLOW, 5) and ev.sub_flow == ''
                 and ev.sub_entry == 'Intro']
        self.assertTrue(calls)
        rw = effects_only(flow, 'Intro', self.table)
        self.assertIsNone(rw.error, rw.detail)
        problems = check_rewrite(flow, apply_rewrite(data, flow, rw), 'Intro', rw)
        self.assertTrue(any(p.startswith('rule 4') for p in problems), problems)

    def test_grown_rewrite_of_the_exit_kokiri(self):
        # Npc_Kokiri_007_Child/Talk walks into GoToDekuTree and GoToMido, which the game
        # also starts on their own: their switches get copies in new slots, an action a donor.
        data, _ = self.flows['Npc_Kokiri_007_Child']
        flow = EventFlow(data)
        ext = frozenset(flow.entry_points) - {'Talk'}
        self.assertEqual(effects_only(flow, 'Talk', self.table, external=ext).error, 'shared')
        rw = effects_only(flow, 'Talk', self.table, external=ext, grow=True)
        self.assertIsNone(rw.error, rw.detail)
        self.assertTrue(rw.grown)
        self.assertTrue(rw.copies)
        new_data = apply_rewrite(data, flow, rw)
        new = EventFlow(new_data)
        n = len(flow.events)
        self.assertEqual(len(new.events), n + len(rw.grown))
        for j, src in enumerate(rw.grown):
            a, b = new.events[n + j], flow.events[src]
            self.assertEqual((a.kind, a.actor, a.action, a.query, a.sub_flow, a.sub_entry),
                             (b.kind, b.actor, b.action, b.query, b.sub_flow, b.sub_entry))
            self.assertEqual(new.action_params(n + j), flow.action_params(src))
        for other in ext:
            self.assertEqual(
                reachable(new.events, new.entry_points, [new.entry_points[other]]),
                reachable(flow.events, flow.entry_points, [flow.entry_points[other]]), other)
        self.assertEqual(check_rewrite(flow, new_data, 'Talk', rw, ext), [])

    def test_apply_rewrite_writes_copies_before_links(self):
        data, _ = self.flows['Get_StoneOfFire']
        flow = EventFlow(data)
        src, dst = [i for i, ev in enumerate(flow.events)
                    if ev.kind == ACTION and flow.action_params(i)][:2]
        rw = Rewrite({('next', dst): END}, [], copies={dst: src})
        new = EventFlow(apply_rewrite(data, flow, rw))
        self.assertEqual(new.events[dst].action, flow.events[src].action)
        self.assertEqual(new.action_params(dst), flow.action_params(src))
        self.assertEqual(new.events[dst].next, END)
        self.assertEqual(new.events[src], flow.events[src])


if __name__ == '__main__':
    unittest.main()
