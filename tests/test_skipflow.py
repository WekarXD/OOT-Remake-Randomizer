import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

from randomizer.formats.bfevfl import (ACTION, END, FORK, JOIN, SUBFLOW, SWITCH, Event,
                                       EventFlow)
from randomizer.skipflow import (SPIKE_SCENES, SkipTable, apply_rewrite, build_spike_files,
                                 effects_only, linearize, reachable, reachable_chosen)

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


class LinearizeTests(unittest.TestCase):
    def test_linear(self):
        rw = lin([A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2')])
        self.assertIsNone(rw.error)
        self.assertEqual(rw.links, {('entry', 'E'): 0, ('next', 0): 2, ('next', 2): END})
        self.assertEqual(rw.kept, [0, 2])

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
        rw = lin([A(0, 'K0', 1), A(1, 'D1', 2), A(2, 'K2')], protected=frozenset({0}))
        self.assertEqual(rw.error, 'shared')
        rw = lin([A(0, 'K0', 1), A(1, 'K1')], protected=frozenset({0}))
        self.assertIsNone(rw.error)


class ReachableTests(unittest.TestCase):
    def test_follows_everything(self):
        ev = [FK(0, [1], 2), SUB(1, '', 'X', 2), JN(2, 3), SW(3, 'Q', [4, 5]), A(4, 'a'),
              A(5, 'b'), A(6, 'x')]
        self.assertEqual(reachable(ev, {'E': 0, 'X': 6}, [0]), set(range(7)))
        self.assertEqual(reachable_chosen(ev, {'E': 0, 'X': 6}, [0], {3: 1}),
                         set(range(7)) - {4})


SPIKE = {'Dm_Kokiri_0155': ([51], [52]), 'Dm_Kokiri_0060': ([], []),
         'Dm_HrlCastle_0050': ([238], []), 'Dm_MelodyGet_Zelda': ([66], [4, 5, 6])}


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

    def _fade_paths(self, flow, entry_events, fade_kind, start):
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
                orig_paths = list(self._fade_paths(flow, None, None, flow.entry_points['EntryPoint0']))

                def fades(ev):
                    return ev.kind == ACTION and ev.action

                guarded = set()
                for path in orig_paths:
                    for n, i in enumerate(path):
                        if fades(flow.events[i]) == 'EventEventFadeOut' and any(
                                fades(flow.events[j]) == 'EventEventFadeIn' for j in path[n + 1:]):
                            guarded.add(i)
                for path in self._fade_paths(new, None, None, new.entry_points['EntryPoint0']):
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


if __name__ == '__main__':
    unittest.main()
