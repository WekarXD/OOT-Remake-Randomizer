import os
import unittest
from collections import Counter

from randomizer import cutscenes
from randomizer.formats import byml
from randomizer.formats.bfevfl import ACTION, END, SWITCH, EventFlow
from randomizer.game import GameData
from randomizer.nup import NupArchive

NUP = os.environ.get('OOT_NUP')
FLOW_DIR = 'Event/EventFlow/'
INTRO = ('Event/EventSetting/EventSettingComponentList/'
         'Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml')


def _reach(events, start):
    """Índices alcanzables desde `start` (sin entrar en subflujos)."""
    seen, stack = set(), [start]
    while stack:
        i = stack.pop()
        if i is None or i == END or i in seen or i >= len(events):
            continue
        seen.add(i)
        ev = events[i]
        stack.append(ev.next)
        stack.extend(ev.cases)
        stack.extend(ev.forks)
        stack.append(ev.join)
    return seen


def _phase1(policy):
    return {tuple(p) for p in policy['actions']['1']}


def _is_phase1(ev, pairs):
    return ev.kind == ACTION and ((ev.actor, ev.action) in pairs
                                  or ('*', ev.action) in pairs)


def _key(ev):
    return (ev.kind, ev.actor, ev.action, ev.query)


class TestPolicyShape(unittest.TestCase):
    def test_policy_shape(self):
        self.assertEqual(cutscenes.ACTIVE_PHASE, 1)
        pol = cutscenes.load_policy()
        p1 = {tuple(p) for p in pol['actions']['1']}
        p2 = {tuple(p) for p in pol['actions']['2']}
        self.assertEqual(len(p1), 22)
        self.assertEqual(len(p2), 8)
        self.assertFalse(p1 & p2)
        self.assertFalse({a for _, a in p1} & {a for _, a in p2})
        self.assertEqual(pol['intro_component_lists'], ['Dm_Kokiri_0000'])
        self.assertTrue(pol['story_flows'])
        for name, spec in pol['story_flows'].items():
            self.assertFalse(name.startswith(('DmF_', 'Dm_StaffCredit_', 'Dm_Title_')), name)
            self.assertTrue(spec == '*' or (isinstance(spec, list) and spec), name)


@unittest.skipUnless(NUP, 'OOT_NUP no definido')
class TestCutsceneFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nup = NupArchive(NUP)
        cls.game = GameData(cls.nup)
        cls.policy = cutscenes.load_policy()
        cls.files = cutscenes.build_cutscene_files(cls.game)
        cls.flows = {}
        for path, data in cls.files.items():
            if path.startswith(FLOW_DIR):
                orig = cls.game.codec.decompress(path, cls.nup.read(path))
                new = cls.game.codec.decompress(path, data)
                cls.flows[path] = (orig, new)

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def test_output_shape(self):
        self.assertIn(INTRO, self.files)
        self.assertGreater(len(self.flows), 50)
        self.assertEqual(list(self.files), sorted(self.files))
        for path in self.files:
            self.assertFalse(path.startswith('romfs/'), path)
        for path in self.flows:
            name = path[len(FLOW_DIR):-len('.bfevfl.zs')]
            self.assertIn(name, self.policy['story_flows'])

    def test_intro_skip_removed(self):
        orig = self.nup.read(INTRO)
        new = self.files[INTRO]
        _ver, root = byml.load(new)
        self.assertNotIn('SkipSetting', root['Components'])
        self.assertLessEqual(len(new), len(orig))
        _ver, oroot = byml.load(orig)
        del oroot['Components']['SkipSetting']
        self.assertEqual(root, oroot)

    def test_flows_same_size(self):
        for path, (orig, new) in self.flows.items():
            self.assertEqual(len(orig), len(new), path)
            self.assertNotEqual(orig, new, path)

    def test_kept_actions_preserved(self):
        pairs = _phase1(self.policy)
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            self.assertEqual(set(fo.entry_points), set(fn.entry_points), path)
            for name, start in fo.entry_points.items():
                a = Counter(_key(fo.events[i]) for i in _reach(fo.events, start)
                            if not _is_phase1(fo.events[i], pairs))
                b = Counter(_key(fn.events[i])
                            for i in _reach(fn.events, fn.entry_points[name])
                            if not _is_phase1(fn.events[i], pairs))
                self.assertEqual(a, b, (path, name))

    def test_shared_events_untouched(self):
        cases = []
        for path, (orig, new) in self.flows.items():
            spec = self.policy['story_flows'][path[len(FLOW_DIR):-len('.bfevfl.zs')]]
            if spec != '*':
                cases.append((path, spec, orig, new))
        # Flujo de PNJ con entradas mixtas: una de historia, el resto charla.
        path = FLOW_DIR + 'Npc_Kokiri_Saria_Child.bfevfl.zs'
        orig = self.game.codec.decompress(path, self.nup.read(path))
        spec = ['GuideToDekuTree_BeforeTalkMido']
        new = cutscenes.trim_flow(orig, spec, cutscenes.active_actions(self.policy))
        self.assertIsNotNone(new)
        cases.append((path, spec, orig, new))
        checked = 0
        for path, spec, orig, new in cases:
            fo, fn = EventFlow(orig), EventFlow(new)
            for entry, start in fo.entry_points.items():
                if entry in spec:
                    continue
                self.assertEqual(fn.entry_points[entry], start, (path, entry))
                for i in _reach(fo.events, start):
                    eo, en = fo.events[i], fn.events[i]
                    self.assertEqual((eo.next, eo.cases, eo.forks, eo.join),
                                     (en.next, en.cases, en.forks, en.join), (path, entry, i))
                    checked += 1
        self.assertGreater(checked, 0)

    def test_choice_talk_kept(self):
        pairs = _phase1(self.policy)

        def leads_to_switch(events, i):
            # Salta acciones de fase 1 que no son diálogos (emoción, espera...).
            j, seen = events[i].next, set()
            while (j != END and j not in seen and _is_phase1(events[j], pairs)
                   and events[j].action != 'EventTalk'):
                seen.add(j)
                j = events[j].next
            return j != END and events[j].kind == SWITCH

        found = 0
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            for name, start in fo.entry_points.items():
                before = _reach(fo.events, start)
                after = _reach(fn.events, fn.entry_points[name])
                for i in before:
                    ev = fo.events[i]
                    if (ev.kind == ACTION and ev.action == 'EventTalk'
                            and leads_to_switch(fo.events, i)):
                        found += 1
                        self.assertIn(i, after, (path, name, i))
        self.assertGreater(found, 0)

    def test_choice_talk_behind_emotion(self):
        # Pregunta de Nabooru: EventTalk -> cambio de emoción -> TalkChoice2.
        path = FLOW_DIR + 'Dm_DesertColossus_0025.bfevfl.zs'
        fn = EventFlow(self.flows[path][1])
        reach = set()
        for start in fn.entry_points.values():
            reach |= _reach(fn.events, start)
        self.assertIn(32, reach)

    def test_deterministic(self):
        again = cutscenes.build_cutscene_files(self.game)
        self.assertEqual(list(again), list(self.files))
        self.assertEqual(again, self.files)


if __name__ == '__main__':
    unittest.main()
