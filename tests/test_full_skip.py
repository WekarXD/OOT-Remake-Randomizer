import os
import struct
import unittest
from unittest import mock

from randomizer import full_skip
from randomizer.cutscenes import FLOW_DIR, FLOW_EXT, build_cutscene_files
from randomizer.formats.bfevfl import (ACTION, END, SUBFLOW, SUBFLOW_SWITCH, SWITCH, BfevflError,
                                       EventFlow, relocation_table)
from randomizer.movie_skip import transitions_to
from randomizer.skipflow import (Rewrite, SkipTable, check_rewrite, effects_only, inlined_entries,
                                 reachable)
from tests.test_skipflow import A, SUB, SW, FakeFlow, rewritten

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

    def test_entry_phases_filter_single_entries(self):
        # A phase 1 flow may gain phase 2 entries (entry_phases); a phase 2 flow is dropped
        # whole before phase 2, and the choices of a dropped flow go with it.
        data = {'flows': {
            'F': {'phase': 1, 'entries': ['A', 'B'], 'entry_phases': {'B': 2}},
            'G': {'phase': 2, 'entries': ['C'], 'choices': {'3': 1}}}}
        import json
        import tempfile
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False,
                                         encoding='utf-8') as f:
            json.dump(data, f)
        try:
            one, two = full_skip.load_targets(1, f.name), full_skip.load_targets(2, f.name)
        finally:
            os.unlink(f.name)
        self.assertEqual(one.flows, {'F': ['A']})
        self.assertEqual(one.choices, {})
        self.assertEqual(two.flows, {'F': ['A', 'B'], 'G': ['C']})
        self.assertEqual(two.choices, {'G': {3: 1}})


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

        def spy(flow, entry, table, choices, reviewed, external, grow=False):
            calls.append((entry, external, grow))
            return effects_only(flow, entry, table, choices, reviewed, external, grow)

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
        # The builder lets the private copies take new slots.
        self.assertTrue(all(grow for _, _, grow in calls))
        # Each step tolerates the other targets of the file (rule 4), nothing else.
        self.assertEqual(steps[0].tolerated, {'B'})
        self.assertEqual(steps[1].tolerated, {'A'})

    def test_new_end_case_of_a_grown_slot(self):
        # Slot 2 is new (a copy of switch 0); its case 1 becomes END where switch 0's was not.
        flow = FakeFlow([SW(0, 'Q', [1, END]), A(1, 'K1')], {'E': 0}, {})
        rw = Rewrite({('case', 2, 1): END, ('case', 2, 0): END}, [2], grown=[0])
        self.assertEqual(full_skip.new_end_cases(flow, rw), [(2, 0)])

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
        cls.files, cls.report, cls.sizes = full_skip.build_full_skip_files(cls.game, 1, cls.cache)
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
                                         step.external, step.tolerated)
                self.assertEqual(step.tolerated, set(entries) - {step.entry})
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
        # Nothing reaches the movie's transition any more (its slot may have become a
        # donor for a private copy, so it is looked up by content, not by index).
        (t,) = transitions_to(old, {'Dm_HrlCastle_0045'})
        self.assertIn(t, reachable(old.events, old.entry_points, old.entry_points.values()))
        self.assertFalse(set(transitions_to(new, {'Dm_HrlCastle_0045'}))
                         & reachable(new.events, new.entry_points, new.entry_points.values()))
        rewritten = [e for f, e in self.applied if f == 'Goto_HyruleCastle']
        self.assertTrue(rewritten)
        for e in rewritten:
            self.assertNotEqual(reachable(new.events, new.entry_points, [new.entry_points[e]]),
                                reachable(old.events, old.entry_points, [old.entry_points[e]]), e)

    def test_failed_scene_falls_back_to_old_trimming(self):
        name = 'Dm_Goron_0028'  # refused: its rewrite adds END cases
        only = full_skip.Targets(flows={name: ['EntryPoint0']}, timelines=[], movies={},
                                 choices={}, reviewed_forks={})
        with mock.patch.object(full_skip, 'load_targets', return_value=only):
            files, report, sizes = full_skip.files_with_fallback(self.game, 1)
        self.assertEqual(sizes, {})
        self.assertTrue(any(line.startswith(f'fallback to trimming {name}/EntryPoint0: new END case')
                            for line in report))
        old = build_cutscene_files(self.game)
        self.assertEqual(files.get(path_of(name)), old.get(path_of(name)))
        self.assertEqual(set(files), set(old))

    def test_partly_rewritten_file_is_not_old_trimmed(self):
        files, report, sizes = full_skip.files_with_fallback(self.game, 1)
        self.assertEqual(sizes, self.sizes)
        name = 'HyruleCastle_FoundBySecurity'
        p = path_of(name)
        self.assertEqual(files[p], self.files[p])
        self.assertTrue(any(line.startswith(f'full skip only {name}') for line in report))
        # Its failed entries are reported as untrimmed, not as falling back to trimming.
        self.assertTrue(any(line.startswith(f'untrimmed (file partly rewritten) {name}/')
                            for line in report))
        self.assertFalse(any(line.startswith(f'fallback to trimming {name}/')
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

    def test_grown_flows_report_their_size_change(self):
        self.assertIn(path_of('Npc_Kokiri_007_Child'), self.sizes)
        for path, data in self.files.items():
            if not path.startswith(FLOW_DIR):
                continue
            name = path[len(FLOW_DIR):-len(FLOW_EXT)]
            delta = len(self.output(name)) - len(self.original(name))
            self.assertEqual(self.sizes.get(path, 0), delta, name)
            if delta:
                self.assertGreater(delta, 0, name)

    def skip(self, name):
        """skip_flow of one target flow, as build_full_skip_files runs it."""
        t = self.targets
        return full_skip.skip_flow(self.original(name), name, t.flows.get(name, ()),
                                   t.movies_called_by(name), SkipTable.load(),
                                   full_skip.flow_callers(self.cache), t.choices.get(name, {}),
                                   t.reviewed_forks.get(name, frozenset()))

    def assert_relocated(self, name, data):
        """Every non-null pointer field of every event is in the RELT and no two switches
        share a case array."""
        flow = EventFlow(data)
        pointers = relocation_table(data)[2]
        arrays = {}
        for i, ev in enumerate(flow.events):
            e = flow._events_p + 0x30 * i
            for o in (0x00, 0x10, 0x18, 0x20, 0x28):
                if struct.unpack_from('<Q', data, e + o)[0]:
                    self.assertIn(e + o, pointers, (name, i, o))
            if ev.kind in (SWITCH, SUBFLOW_SWITCH) and ev.cases:
                p = struct.unpack_from('<Q', data, e + 0x18)[0]
                self.assertNotIn(p, arrays, (name, i, arrays.get(p)))
                arrays[p] = i

    def test_repeated_growth_is_compacted(self):
        name = 'MelodyGet_Sun_SubEvent'
        orig, out = self.original(name), self.output(name)
        with mock.patch.object(full_skip, 'compact', lambda data, original: data):
            loose, steps, _ = self.skip(name)
        self.assertGreater(sum(1 for s in steps if s.rw.grown), 1)
        old, new, flat = EventFlow(orig), EventFlow(out), EventFlow(loose)
        n = len(old.events)
        # One moved array (live events only), the copies' case arrays and the RELT.
        size0 = relocation_table(orig)[1]
        cases = sum(8 * len(ev.cases) for ev in new.events[n:]
                    if ev.kind in (SWITCH, SUBFLOW_SWITCH))
        relt = len(out) - struct.unpack_from('<I', out, 0x18)[0]
        self.assertLess(len(out), size0 + 0x30 * len(new.events) + cases + relt + 64)
        self.assertLess(len(out), len(loose))
        # The compacted file reads exactly like the uncompacted one.
        self.assertEqual(len(new.events), len(flat.events))
        for i in range(len(new.events)):
            self.assertEqual(new.events[i], flat.events[i], i)
            self.assertEqual(new.action_params(i), flat.action_params(i), i)
        self.assertEqual(new.entry_points, flat.entry_points)
        # The RSTB delta is the final size change.
        self.assertEqual(self.sizes[path_of(name)], len(out) - len(orig))

    def test_grown_files_relocate_every_pointer(self):
        for path in self.sizes:
            name = path[len(FLOW_DIR):-len(FLOW_EXT)]
            self.assert_relocated(name, self.output(name))

    def test_growth_error_fails_the_entry_only(self):
        name = 'Npc_Kokiri_Mido_Child'
        with mock.patch('randomizer.skipflow.grow_events', side_effect=BfevflError('boom')):
            data, steps, report = self.skip(name)
        self.assertFalse(any(s.rw.grown for s in steps))
        self.assertTrue(any(line.endswith(f'{name}/Talk: cannot apply: boom')
                            for line in report), report)

    def test_shared_forced_conversations_are_applied(self):
        # The exit Kokiri, Mido and the targeting tutorial share events with the
        # player-started conversations: their rewrites take new slots.
        for flow, entry in (('Npc_Kokiri_007_Child', 'Talk'),
                            ('Npc_Kokiri_007_Child', 'GoToDekuTree'),
                            ('Npc_Kokiri_Mido_Child', 'Talk')):
            self.assertIn((flow, entry), self.applied)

    def test_adult_phase_keeps_the_childhood_and_adds_the_adult_game(self):
        from randomizer.generate import FULL_SKIP_PHASE
        self.assertEqual(FULL_SKIP_PHASE, 1)  # the adult phase is not released yet
        files, report, _ = full_skip.build_full_skip_files(self.game, 2, self.cache)
        adult = applied(report)
        self.assertEqual(self.applied - adult, set())
        self.assertIn(('Npc_Kokiri_Mido_Adult', 'SageOfForest_Blocker_Talk'), adult)
        # Boss scenes stay (user decision), Ganon's Castle is a later phase.
        targets = full_skip.load_targets(2)
        self.assertNotIn('ForestTemple_SageOfForest_PhantomGanonAppearance',
                         targets.flows['SageOfForest'])
        self.assertFalse(any(n.startswith(('Dm_InsideGanonCastle_', 'Dm_FinalBattle_'))
                             for n in list(targets.flows) + targets.timelines))
        # Not even a movie drop may touch the ending's flows.
        self.assertNotIn(path_of('Defeat_Ganon'), files)
        self.assertNotIn(path_of('EscapeFromCrumblingGanonCastle'), files)

    def test_conflicting_scenes_get_a_copy_per_call_site(self):
        # A kept event inside a same-file subflow called twice continued differently
        # after each call ('conflict'); now each call site gets its own copy (Din's
        # copies grow the file, Jabu-Jabu's fit in unreachable donor slots).
        for name in ('Dm_FairyFountain_Din', 'Dm_InsideJabu_Jabu_0050'):
            self.assertIn((name, 'EntryPoint0'), self.applied)
        self.assertIn(path_of('Dm_FairyFountain_Din'), self.sizes)
        self.assertNotIn(path_of('Dm_InsideJabu_Jabu_0050'), self.sizes)

    def test_exit_kokiri_lets_link_pass_without_talking(self):
        # After the Deku Tree the exit Kokiri stops Link, talks and steps aside
        # (round 3: the talk still played). The rewrite keeps stepping aside.
        name, entry = 'Npc_Kokiri_007_Child', 'Get_StoneOfForest_IsCompleted_Exp_Talk'
        self.assertIn((name, entry), self.applied)
        flow = EventFlow(self.output(name))
        actions = {flow.events[i].action
                   for i in reachable(flow.events, flow.entry_points,
                                      [flow.entry_points[entry]])}
        self.assertNotIn('EventTalk', actions)
        self.assertIn('EventNpcBlockerEndBlockerAI', actions)

    def test_entry_called_by_a_sibling_target_is_tolerated(self):
        # Talk calls GoToDekuTree by name: rewriting GoToDekuTree changes what Talk
        # reaches, which is allowed only when Talk is itself a target of the file.
        name = 'Npc_Kokiri_007_Child'
        callers = full_skip.flow_callers(self.cache)
        table = SkipTable.load()
        _, steps, _ = full_skip.skip_flow(self.original(name), name, ['GoToDekuTree', 'Talk'],
                                          set(), table, callers)
        self.assertIn('GoToDekuTree', [s.entry for s in steps])
        _, steps, report = full_skip.skip_flow(self.original(name), name, ['GoToDekuTree'],
                                               set(), table, callers)
        self.assertEqual(steps, [])
        self.assertTrue(any(line.startswith(f'fallback to trimming {name}/GoToDekuTree: check: '
                                            'rule 4: entry Talk') for line in report), report)

    def test_king_zora_keeps_his_animation(self):
        flow = EventFlow(self.output('Dm_Zora_0010'))
        start = flow.entry_points['EntryPoint0']
        actions = {(flow.events[i].actor, flow.events[i].action)
                   for i in reachable(flow.events, flow.entry_points, [start])}
        self.assertIn(('Npc_Zora_KingZora_child', 'EventPlayAS'), actions)


if __name__ == '__main__':
    unittest.main()
