import os
import unittest
from unittest import mock

from randomizer import full_skip
from randomizer.cutscenes import FLOW_DIR, FLOW_EXT, build_cutscene_files
from randomizer.formats.bfevfl import ACTION, SUBFLOW, SUBFLOW_SWITCH, EventFlow
from randomizer.movie_skip import transitions_to
from randomizer.skipflow import SkipTable, check_rewrite, effects_only, inlined_entries, reachable
from tests.test_skipflow import A, SUB, FakeFlow, rewritten

NUP_PATH = os.environ.get('OOT_NUP')


def path_of(name):
    return FLOW_DIR + name + FLOW_EXT


def applied(report):
    """(flow, entry) pairs the report marks applied."""
    out = set()
    for line in report:
        if line.startswith('applied '):
            flow, entry = line[len('applied '):].split('/', 1)
            out.add((flow, entry))
    return out


class LoadTargetsTest(unittest.TestCase):
    def test_phase_filter_and_fields(self):
        t = full_skip.load_targets(1)
        self.assertIn('EntryPoint0', t.flows['Dm_Kokiri_0155'])
        self.assertIn('Dm_Kokiri_0150', t.timelines)
        self.assertEqual(t.movies['Dm_HrlCastle_0045'], ['Goto_HyruleCastle'])
        self.assertEqual(full_skip.load_targets(0).flows, {})
        self.assertNotIn('Dm_Kokiri_0045', t.reviewed_forks)


class FakeTable:
    """Keeps actions named K*; nothing collapses, no other-file subflow is dropped."""
    def keeps(self, actor, action):
        return action.startswith('K')

    def collapses(self, query):
        return False

    def drops_subflow(self, flow, entry):
        return False


class SkipFlowSiblingTests(unittest.TestCase):
    """skip_flow over synthetic flows: EventFlow, apply_rewrite and check_rewrite are
    stubbed so flows are lists of events keyed by fake "bytes"."""

    def run_skip(self, events, entries, targets):
        flows, calls = {b'v0': FakeFlow(events, entries, {})}, []

        def parse(data):
            return flows[data]

        def apply(data, flow, rw):
            ev, ent = rewritten(flow.events, flow.entry_points, rw)
            new = b'v%d' % len(flows)
            flows[new] = FakeFlow(ev, ent, {})
            return new

        def spy(flow, entry, table, choices, reviewed, external):
            calls.append((entry, external))
            return effects_only(flow, entry, table, choices, reviewed, external)

        with mock.patch.object(full_skip, 'EventFlow', parse),                 mock.patch.object(full_skip, 'apply_rewrite', apply),                 mock.patch.object(full_skip, 'check_rewrite', return_value=[]),                 mock.patch.object(full_skip, 'effects_only', spy):
            out = full_skip.skip_flow(b'v0', 'Dm_X', targets, set(), FakeTable(), {})
        return out, calls

    def test_second_target_cannot_inline_what_the_first_one_inlined(self):
        # A and B both call the untargeted C; A inlines it and relinks C's tail to A's own
        # continuation, so B must not walk through it.
        events = [A(0, 'K0', 1), SUB(1, '', 'C', 2), A(2, 'K2'),
                  A(3, 'K3', 4), SUB(4, '', 'C', 5), A(5, 'K5'),
                  A(6, 'D6', 7), A(7, 'K7'),
                  A(8, 'K8'), A(9, 'K9')]  # 8 and 9: free slots for private copies
        (data, steps, report), calls = self.run_skip(events, {'A': 0, 'B': 3, 'C': 6}, ['A', 'B'])
        self.assertEqual([s.entry for s in steps], ['A', 'B'], report)
        self.assertNotIn('C', calls[0][1])
        self.assertIn('C', calls[1][1])
        self.assertIn('C', steps[1].external)
        self.assertNotIn('C', steps[0].external)

    def test_entry_that_keeps_nothing_is_refused(self):
        (data, steps, report), _ = self.run_skip([A(0, 'D0', 1), A(1, 'D1')], {'E': 0}, ['E'])
        self.assertEqual(steps, [])
        self.assertEqual(data, b'v0')
        self.assertTrue(any(line.startswith('fallback to trimming Dm_X/E: empty entry')
                            for line in report), report)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class FullSkipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from randomizer.game import GameData
        from randomizer.nup import NupArchive
        cls.nup = NupArchive(NUP_PATH)
        cls.game = GameData(cls.nup)
        cls.cache = {}
        cls.files, cls.report = full_skip.build_full_skip_files(cls.game, 1, cls.cache)
        cls.applied = applied(cls.report)
        cls.targets = full_skip.load_targets(1)

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def original(self, name):
        p = path_of(name)
        return self.game.codec.decompress(p, self.nup.read(p))

    def output(self, name):
        p = path_of(name)
        return self.game.codec.decompress(p, self.files[p])

    def test_reports_applied_entries_and_wall_time(self):
        self.assertGreater(len(self.applied), 50)
        self.assertTrue(any(line.startswith('full skip built in ') for line in self.report))
        self.assertIn(('Dm_Kokiri_0155', 'EntryPoint0'), self.applied)
        # A fork dependency stays unreviewed: it falls back and is reported.
        self.assertNotIn(('Dm_Kokiri_0045', 'EntryPoint0'), self.applied)
        self.assertTrue(any(line.startswith('fallback to trimming Dm_Kokiri_0045/EntryPoint0: '
                                            'fork dependency') for line in self.report))

    def test_every_applied_entry_passes_the_checker(self):
        callers = full_skip.flow_callers(self.cache)
        table = SkipTable.load()
        seen = set()
        for name, entries in self.targets.flows.items():
            data, steps, _ = full_skip.skip_flow(
                self.original(name), name, entries, self.targets.movies_called_by(name), table,
                callers, self.targets.choices.get(name, {}),
                self.targets.reviewed_forks.get(name, frozenset()))
            for step in steps:
                problems = check_rewrite(EventFlow(step.before), step.after, step.entry, step.rw,
                                         step.external)
                self.assertEqual(problems, [], (name, step.entry))
                before = EventFlow(step.before)
                base = full_skip.protected_entries(callers, name, before, entries, step.entry)
                self.assertTrue(base <= step.external, (name, step.entry))
                self.assertNotIn(step.entry, step.external)
                # Siblings and (outside Dm_ scenes) untargeted entries are never inlined.
                self.assertTrue(set(entries) - {step.entry} <= step.external)
                if not name.startswith('Dm_'):
                    self.assertEqual(step.external, set(before.entry_points) - {step.entry})
                # ... and later targets never inline what an earlier step inlined.
                for earlier in steps[:steps.index(step)]:
                    self.assertTrue(inlined_entries(EventFlow(earlier.before), earlier.entry,
                                                    earlier.external) - {step.entry}
                                    <= step.external, (name, step.entry))
                self.assertEqual(full_skip.new_end_cases(before, step.rw), [], (name, step.entry))
                seen.add((name, step.entry))
            if path_of(name) in self.files:
                self.assertEqual(self.output(name), data, name)
            else:
                self.assertEqual(self.original(name), data, name)
            # In the final file every applied entry reaches exactly what its own step made.
            final = EventFlow(data)
            for step in steps:
                own = EventFlow(step.after)
                self.assertEqual(
                    reachable(final.events, final.entry_points, [final.entry_points[step.entry]]),
                    reachable(own.events, own.entry_points, [own.entry_points[step.entry]]),
                    (name, step.entry))
        self.assertEqual(seen, self.applied)

    def test_goto_hyrulecastle_is_written_once_with_all_methods(self):
        new = EventFlow(self.output('Goto_HyruleCastle'))
        old = EventFlow(self.original('Goto_HyruleCastle'))
        # The movie's transition is still in the file, but nothing reaches it any more.
        (t,) = transitions_to(old, {'Dm_HrlCastle_0045'})
        self.assertIn(t, reachable(old.events, old.entry_points, old.entry_points.values()))
        self.assertNotIn(t, reachable(new.events, new.entry_points, new.entry_points.values()))
        rewritten = [e for f, e in self.applied if f == 'Goto_HyruleCastle']
        self.assertTrue(rewritten)
        for e in rewritten:
            self.assertNotEqual(reachable(new.events, new.entry_points, [new.entry_points[e]]),
                                reachable(old.events, old.entry_points, [old.entry_points[e]]), e)

    def test_failed_scene_falls_back_to_old_trimming(self):
        name = 'Dm_InsideJabu_Jabu_0050'
        only = full_skip.Targets(flows={name: ['EntryPoint0']}, timelines=[], movies={},
                                 choices={}, reviewed_forks={})
        with mock.patch.object(full_skip, 'load_targets', return_value=only):
            files, report = full_skip.files_with_fallback(self.game, 1)
        self.assertTrue(any(line.startswith(f'fallback to trimming {name}/EntryPoint0: conflict')
                            for line in report))
        old = build_cutscene_files(self.game)
        self.assertEqual(files.get(path_of(name)), old.get(path_of(name)))
        self.assertEqual(set(files), set(old))

    def test_partly_rewritten_file_is_not_old_trimmed(self):
        files, report = full_skip.files_with_fallback(self.game, 1)
        p = path_of('Goto_HyruleCastle')
        self.assertEqual(files[p], self.files[p])
        self.assertTrue(any(line.startswith('full skip only Goto_HyruleCastle') for line in report))
        # Its failed entries are reported as untrimmed, not as falling back to trimming.
        self.assertTrue(any(line.startswith('untrimmed (file partly rewritten) Goto_HyruleCastle/')
                            for line in report))
        self.assertFalse(any(line.startswith('fallback to trimming Goto_HyruleCastle/')
                             for line in report))
        # The intro's unlocked skip (a component list) still comes from the old option.
        old = build_cutscene_files(self.game)
        for path in old:
            if not path.startswith(FLOW_DIR):
                self.assertEqual(files[path], old[path])

    def test_dropped_events_unreachable(self):
        table = SkipTable.load()
        for name, entry in sorted(self.applied):
            flow = EventFlow(self.output(name))
            for i in reachable(flow.events, flow.entry_points, [flow.entry_points[entry]]):
                ev = flow.events[i]
                if ev.kind == ACTION:
                    self.assertTrue(table.keeps(ev.actor, ev.action), (name, entry, i, ev.action))
                elif ev.kind in (SUBFLOW, SUBFLOW_SWITCH) and ev.sub_flow:
                    self.assertFalse(table.drops_subflow(ev.sub_flow, ev.sub_entry),
                                     (name, entry, i))

    def test_keep_talks_reach_the_same_events(self):
        from tools.build_cutscene_list import KEEP_TALKS
        for name, entries in KEEP_TALKS.items():
            if path_of(name) not in self.files:
                continue
            old, new = EventFlow(self.original(name)), EventFlow(self.output(name))
            for e in entries:
                self.assertEqual(
                    reachable(new.events, new.entry_points, [new.entry_points[e]]),
                    reachable(old.events, old.entry_points, [old.entry_points[e]]), (name, e))

    def test_new_end_case_is_refused(self):
        # Dm_Goron_0028's rewrite sends both cases of switch 28 to END (they were not).
        self.assertNotIn(('Dm_Goron_0028', 'EntryPoint0'), self.applied)
        self.assertTrue(any(line.startswith('fallback to trimming Dm_Goron_0028/EntryPoint0: '
                                            'new END case (switch 28 case 0')
                            for line in self.report))

    def test_timelines_are_shortened_with_their_subtimelines(self):
        from randomizer.formats.timeline import Timeline
        for name in ('Dm_Kokiri_0150', 'Dm_Kokiri_0030'):
            self.assertLess(Timeline(self.output(name)).duration,
                            Timeline(self.original(name)).duration, name)
        self.assertIn(path_of('Dm_Kokiri_0150_Effect'), self.files)

    def test_boss_scenes_are_kept(self):
        # User decision (2026-11-12): boss intros and defeats play.
        for name in ('Dm_Deku_BossIn', 'Dm_Deku_BossOut', 'Dm_DodongoCave_BossIn',
                     'Dm_InsideJabu_Jabu_BossOut'):
            self.assertNotIn(path_of(name), self.files, name)
        self.assertNotIn(('Get_StoneOfForest', 'Boss_Appear'), self.applied)
        self.assertNotIn(('Get_StoneOfWater', 'StoneOfWater_BossAppear'), self.applied)

    def test_shared_conversations_rewrite_into_new_slots(self):
        # Forced conversations that share events with player-started ones (spec 8.1).
        from randomizer.skipflow import apply_rewrite
        callers = full_skip.flow_callers(self.cache)
        table = SkipTable.load()
        # GoToDekuTree rewrites, but the untargeted Talk calls it by name (event 30), so
        # Talk would follow the moved entry slot: rule 4 refuses it (not about growing).
        for name, entry, problems in (
                ('Npc_Kokiri_007_Child', 'GoToDekuTree',
                 ['rule 4: entry Talk reaches other events than before']),
                ('Npc_Kokiri_007_Child', 'Talk', []),
                ('Npc_Kokiri_Mido_Child', 'Talk', [])):
            with self.subTest(name=name, entry=entry):
                data = self.original(name)
                flow = EventFlow(data)
                ext = full_skip.protected_entries(callers, name, flow, [entry], entry)
                self.assertEqual(effects_only(flow, entry, table, external=ext).error, 'shared')
                rw = effects_only(flow, entry, table, external=ext, grow=True)
                self.assertIsNone(rw.error, rw.detail)
                self.assertTrue(rw.grown)
                self.assertEqual(check_rewrite(flow, apply_rewrite(data, flow, rw), entry, rw,
                                               ext), problems)

    def test_king_zora_keeps_his_animation(self):
        flow = EventFlow(self.output('Dm_Zora_0010'))
        start = flow.entry_points['EntryPoint0']
        actions = {(flow.events[i].actor, flow.events[i].action)
                   for i in reachable(flow.events, flow.entry_points, [start])}
        self.assertIn(('Npc_Zora_KingZora_child', 'EventPlayAS'), actions)


if __name__ == '__main__':
    unittest.main()
