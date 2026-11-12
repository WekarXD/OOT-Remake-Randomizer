import os
import unittest
from collections import Counter
from types import SimpleNamespace

from randomizer import cutscenes
from randomizer.cutscenes import on_cycle
from randomizer.formats import byml
from randomizer.formats.bfevfl import ACTION, END, FORK, JOIN, SWITCH, Event, EventFlow
from randomizer.game import GameData
from randomizer.nup import NupArchive

NUP = os.environ.get('OOT_NUP')
FLOW_DIR = 'Event/EventFlow/'
INTRO = ('Event/EventSetting/EventSettingComponentList/'
         'Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml')


def _reach(events, start):
    """Indices reachable from `start` (without entering subflows)."""
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


class TestPollingLoop(unittest.TestCase):
    def test_wait_in_polling_loop_kept(self):
        # 0: talk -> 1: switch [2 -> end, 3 -> wait] ; 3: wait -> 1
        events = [
            Event(0, ACTION, actor='Npc_A', action='EventTalk', next=1),
            Event(1, SWITCH, actor='GameDataActor', query='EventQueryIsGameDataBool',
                  cases=[2, 3]),
            Event(2, ACTION, actor='EventSystemActor', action='EventWait', next=END),
            Event(3, ACTION, actor='EventSystemActor', action='EventWait', next=1),
        ]
        flow = SimpleNamespace(events=events, entry_points={'E': 0})
        pairs = cutscenes.active_actions(cutscenes.load_policy())
        self.assertEqual(cutscenes.on_cycle(events), {1, 3})
        removable = cutscenes.removable_events(flow, '*', pairs)
        self.assertNotIn(3, removable)
        self.assertIn(2, removable)


def _talk(i, nxt, actor='Npc_A'):
    return Event(i, ACTION, actor=actor, action='EventTalk', next=nxt)


def _wait(i, nxt):
    return Event(i, ACTION, actor='EventSystemActor', action='EventWait', next=nxt)


class TestChoiceTalkFork(unittest.TestCase):
    def setUp(self):
        self.pairs = cutscenes.active_actions(cutscenes.load_policy())

    def _removable(self, events, entry=0):
        flow = SimpleNamespace(events=events, entry_points={'E': entry})
        return cutscenes.removable_events(flow, '*', self.pairs)

    def test_question_through_fork_join(self):
        # 0: question -> 1: fork [2] join 3 ; 2: Navi talks (end of branch)
        # 3: join -> 4: TalkChoice2 [5, 6]
        events = [
            _talk(0, 1),
            Event(1, FORK, forks=[2, 7], join=3),
            _talk(2, END, actor='Npc_Navi'),
            Event(3, JOIN, next=4),
            Event(4, SWITCH, actor='GameSystemActor', query='EventQueryTalkChoice2',
                  cases=[5, 6]),
            _wait(5, END), _wait(6, END), _wait(7, END),
        ]
        rem = self._removable(events)
        self.assertNotIn(0, rem)
        self.assertNotIn(2, rem)
        self.assertIn(7, rem)

    def test_other_talk_blocks(self):
        # 0: talk -> 1: talk -> 2: fork -> 3: join -> 4: TalkChoice2
        events = [
            _talk(0, 1), _talk(1, 2),
            Event(2, FORK, forks=[5], join=3),
            Event(3, JOIN, next=4),
            Event(4, SWITCH, actor='GameSystemActor', query='EventQueryTalkChoice3',
                  cases=[END]),
            _wait(5, END),
        ]
        rem = self._removable(events)
        self.assertIn(0, rem)
        self.assertNotIn(1, rem)

    def test_non_choice_switch_after_fork(self):
        events = [
            _talk(0, 1),
            Event(1, FORK, forks=[4], join=2),
            Event(2, JOIN, next=3),
            Event(3, SWITCH, actor='GameDataActor', query='EventQueryIsGameDataBool',
                  cases=[END]),
            _wait(4, END),
        ]
        self.assertIn(0, self._removable(events))


class TestLinearChoiceRule(unittest.TestCase):
    # Round 2b: a dialogue followed by a switch is only a question if the
    # switch reads the answer (TalkChoice or Select), not if it draws lots or
    # checks a flag.
    def _removable(self, query):
        events = [
            _talk(0, 1),
            Event(1, SWITCH, actor='GameSystemActor', query=query, cases=[2, 3]),
            _wait(2, END), _wait(3, END),
        ]
        flow = SimpleNamespace(events=events, entry_points={'E': 0})
        pairs = cutscenes.active_actions(cutscenes.load_policy())
        return cutscenes.removable_events(flow, '*', pairs)

    def test_talk_choice_kept(self):
        for q in ('EventQueryTalkChoice2', 'EventQueryTalkChoice4',
                  'EventQueryFairyFountainSelectSpecialAbility'):
            self.assertNotIn(0, self._removable(q), q)

    def test_non_answer_switch_removed(self):
        for q in ('EventQueryRandomChoice2', 'EventQueryAvoidDuplicationRandomChoice2',
                  'EventQueryIsGameDataBool', 'EventQueryPlayerIsChild'):
            self.assertIn(0, self._removable(q), q)


class TestSystemText(unittest.TestCase):
    def test_signs_and_system_text_kept(self):
        events = [
            _talk(0, 1, actor='SystemTextNPC'),
            _talk(1, 2, actor='SignBoard_EventStarter'),
            _talk(2, 3),
            _wait(3, END),
        ]
        flow = SimpleNamespace(events=events, entry_points={'E': 0})
        pairs = cutscenes.active_actions(cutscenes.load_policy())
        rem = cutscenes.removable_events(flow, '*', pairs)
        self.assertNotIn(0, rem)
        self.assertNotIn(1, rem)
        self.assertEqual(rem, {2, 3})


def _reaches_talk_choice(events, i):
    """Independent of the code: walks with a stack of joins.

    From the EventTalk `i`, is a TalkChoice switch reached without passing
    another EventTalk? An end of branch (0xFFFF) continues at the fork's join.
    """
    n = len(events)
    seen, stack = set(), [(events[i].next, ())]
    while stack:
        j, joins = stack.pop()
        if j is None or j == END:
            if joins:
                stack.append((joins[-1], joins[:-1]))
            continue
        if not 0 <= j < n or (j, joins) in seen:
            continue
        seen.add((j, joins))
        ev = events[j]
        if ev.kind == ACTION and ev.action == 'EventTalk':
            continue
        if ev.kind == SWITCH:
            if ev.query and 'TalkChoice' in ev.query:
                return True
            stack.extend((c, joins) for c in ev.cases)
        elif ev.kind == FORK:
            stack.extend((b, joins + (ev.join,)) for b in ev.forks)
        elif ev.kind == JOIN and joins and joins[-1] == j:
            stack.append((ev.next, joins[:-1]))
        else:
            stack.append((ev.next, joins))
    return False


def _non_action_cycle(events):
    """Some cycle made up only of events that are not actions."""
    sub = [e if e.kind != ACTION else Event(e.index, ACTION) for e in events]
    return {i for i in on_cycle(sub) if events[i].kind != ACTION}


@unittest.skipUnless(NUP, 'OOT_NUP not set')
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
        # NPC flow with mixed entries: one story entry, the rest chatter. The
        # chatter entries reach the story entry's events through subflow switch
        # (kind 5) cases, so nothing of it may be trimmed.
        path = FLOW_DIR + 'Npc_Kokiri_Saria_Child.bfevfl.zs'
        orig = self.game.codec.decompress(path, self.nup.read(path))
        spec = ['GuideToDekuTree_BeforeTalkMido']
        self.assertIsNone(cutscenes.trim_flow(orig, spec, cutscenes.active_actions(self.policy)))
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
            # Skips phase 1 actions that are not dialogues (emotion, wait...).
            j, seen = events[i].next, set()
            while (j != END and j not in seen and _is_phase1(events[j], pairs)
                   and events[j].action != 'EventTalk'):
                seen.add(j)
                j = events[j].next
            # Round 2b: only a switch that reads the answer counts.
            return (j != END and events[j].kind == SWITCH and events[j].query
                    and ('TalkChoice' in events[j].query or 'Select' in events[j].query))

        found = 0
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            for name, start in fo.entry_points.items():
                before = _reach(fo.events, start)
                after = _reach(fn.events, fn.entry_points[name])
                for i in before:
                    ev = fo.events[i]
                    if (ev.kind == ACTION and ev.action == 'EventTalk'
                            and (leads_to_switch(fo.events, i)
                                 or _reaches_talk_choice(fo.events, i))):
                        found += 1
                        self.assertIn(i, after, (path, name, i))
        self.assertGreater(found, 0)

    def test_choice_talk_behind_emotion(self):
        # Nabooru's question: EventTalk -> emotion change -> TalkChoice2.
        path = FLOW_DIR + 'Dm_DesertColossus_0025.bfevfl.zs'
        fn = EventFlow(self.flows[path][1])
        reach = set()
        for start in fn.entry_points.values():
            reach |= _reach(fn.events, start)
        self.assertIn(32, reach)

    def test_choice_talk_through_fork_join(self):
        # Ruto (42) and Navi (46) ask; the answer is read after fork 49
        # -> join 50 -> TalkChoice2 125.
        path = FLOW_DIR + 'Dm_InsideJabu_Jabu_0050.bfevfl.zs'
        self.assertIn(path, self.flows)
        fo, fn = (EventFlow(b) for b in self.flows[path])
        self.assertIn('TalkChoice', fo.events[125].query)
        reach = set()
        for start in fn.entry_points.values():
            reach |= _reach(fn.events, start)
        self.assertIn(42, reach)
        self.assertIn(46, reach)

    def test_no_new_end_pointers(self):
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            for name, start in fo.entry_points.items():
                if fn.entry_points[name] == END:
                    self.assertEqual(start, END, (path, name))
            for eo, en in zip(fo.events, fn.events):
                for co, cn in zip(eo.cases, en.cases):
                    if cn == END:
                        self.assertEqual(co, END, (path, eo.index))

    def test_signs_and_system_text_untouched(self):
        protected = {'SystemTextNPC', 'SignBoard_EventStarter'}
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            before, after = set(), set()
            for name, start in fo.entry_points.items():
                before |= _reach(fo.events, start)
                after |= _reach(fn.events, fn.entry_points[name])
            for i in before - after:
                self.assertNotIn(fo.events[i].actor, protected, (path, i))

    def test_no_action_free_cycles(self):
        for path, (_orig, new) in self.flows.items():
            fn = EventFlow(new)
            reach = set()
            for start in fn.entry_points.values():
                reach |= _reach(fn.events, start)
            self.assertFalse(_non_action_cycle(fn.events) & reach, path)

    def _trimmed(self, flow):
        path = FLOW_DIR + flow + '.bfevfl.zs'
        self.assertTrue(path in self.flows, f"{flow} is not trimmed")
        return (EventFlow(b) for b in self.flows[path])

    def test_forced_talks_listed(self):
        # Confirmed mandatory cases (extension 1): Mido blocking the way
        # and the target-locking tutorial. Each trim removes some EventTalk.
        cases = {
            'Npc_Kokiri_Mido_Child': 'Talk',
            'Npc_Kokiri_010_Child': 'FocusOnAttentionRock_ShieldDeku_Short',
        }
        for flow, entry in cases.items():
            spec = self.policy['story_flows'].get(flow)
            self.assertIsInstance(spec, list, flow)
            self.assertIn(entry, spec, flow)
            fo, fn = self._trimmed(flow)
            before = _reach(fo.events, fo.entry_points[entry])
            after = _reach(fn.events, fn.entry_points[entry])
            gone = [i for i in before - after if fo.events[i].action == 'EventTalk']
            self.assertTrue(gone, (flow, entry))
        # Navi's notice (NaviLockOnHint -> NaviHint:Hint_00) shares the
        # entry with the voluntary hint: it stays out.
        self.assertNotIn('NaviHint', self.policy['story_flows'])

    def test_voluntary_talks_untouched(self):
        # NPC/Navi flows listed by entries: what is reached from
        # an unlisted entry does not change, and each listed flow is trimmed.
        listed = {n: s for n, s in self.policy['story_flows'].items() if s != '*'}
        self.assertTrue(any(n.startswith('Npc_') for n in listed))
        checked = 0
        for name, spec in listed.items():
            fo, fn = self._trimmed(name)
            for entry, start in fo.entry_points.items():
                if entry in spec:
                    continue
                self.assertEqual(fn.entry_points[entry], start, (name, entry))
                for i in _reach(fo.events, start):
                    eo, en = fo.events[i], fn.events[i]
                    self.assertEqual((eo.next, eo.cases, eo.forks, eo.join),
                                     (en.next, en.cases, en.forks, en.join),
                                     (name, entry, i))
                    checked += 1
        self.assertGreater(checked, 0)

    def test_mido_gate_kept(self):
        # Mido: all switches and all actions that are not
        # phase 1 are kept (the blocking AI, the flags, the steps).
        pairs = _phase1(self.policy)
        fo, fn = self._trimmed('Npc_Kokiri_Mido_Child')
        for entry, start in fo.entry_points.items():
            before = _reach(fo.events, start)
            after = _reach(fn.events, fn.entry_points[entry])
            for i in before - after:
                self.assertTrue(_is_phase1(fo.events[i], pairs), (entry, i))
                self.assertNotEqual(fo.events[i].kind, SWITCH, (entry, i))
        talk = _reach(fn.events, fn.entry_points['Talk'])
        acts = Counter(fn.events[i].action for i in talk)
        self.assertGreater(acts['EventNpcBlockerEndBlockerAI'], 0)
        self.assertGreater(acts['EventTriggerSetGameDataBool'], 0)

    def test_zelda_garden_talk_kept_safe(self):
        # Chat with Zelda in the garden (requested by the user, extension 1b).
        # The garden scene (Goto_HyruleCastle_MeetZelda -> Dm_HrlCastle_0035
        # and _0050) is already full story; in addition, the entries of
        # the Zelda chat are listed (not the mask ones). All the
        # switches and all actions that are not phase 1 are kept (flags,
        # subflows, AI), and the chat loses some dialogue.
        # Round 2b: Dm_HrlCastle_0035/_0050 are no longer trimmed (Link frozen).
        self.assertEqual(self.policy['story_flows'].get('Goto_HyruleCastle'), '*')
        entries = {'Talk', 'Intro', 'aboutGeneral', 'ThatsAll', 'AboutFireStone',
                   'AboutWaterStone', 'InterestTalk_Zelda_Child',
                   'InterestTalk_Zelda_Child_ChangeTheTopic'}
        spec = self.policy['story_flows'].get('Npc_Hylia_Zelda_Child')
        self.assertIsInstance(spec, list)
        self.assertLessEqual(entries, set(spec))
        self.assertFalse({e for e in spec if e.startswith('Mask_')})
        pairs = _phase1(self.policy)
        fo, fn = self._trimmed('Npc_Hylia_Zelda_Child')
        for entry, start in fo.entry_points.items():
            before = _reach(fo.events, start)
            after = _reach(fn.events, fn.entry_points[entry])
            for i in before - after:
                self.assertTrue(_is_phase1(fo.events[i], pairs), (entry, i))
                self.assertNotEqual(fo.events[i].kind, SWITCH, (entry, i))
        before = _reach(fo.events, fo.entry_points['Talk'])
        after = _reach(fn.events, fn.entry_points['Talk'])
        self.assertTrue([i for i in before - after
                         if fo.events[i].action == 'EventTalk'])
        acts = Counter(fn.events[i].action for i in after)
        self.assertGreater(acts['EventTriggerSetGameDataBool'], 0)

    def _assert_entry_untouched(self, flow, entry):
        path = FLOW_DIR + flow + '.bfevfl.zs'
        orig = self.game.codec.decompress(path, self.nup.read(path))
        new = self.flows.get(path, (orig, orig))[1]
        fo, fn = EventFlow(orig), EventFlow(new)
        start = fo.entry_points[entry]
        self.assertEqual(fn.entry_points[entry], start, (flow, entry))
        for i in _reach(fo.events, start):
            eo, en = fo.events[i], fn.events[i]
            self.assertEqual((eo.next, eo.cases, eo.forks, eo.join),
                             (en.next, en.cases, en.forks, en.join), (flow, entry, i))
        return fo

    def test_gameplay_hints_untouched(self):
        # Round 2: the Deku Scrub in the Deku Tree who gives the order clue (and his
        # siblings) lost the chat because Get_StoneOfForest was "*". Gameplay
        # hints are never trimmed: their entry (and the subflows
        # of the same flow it calls) is left out of the list.
        hints = {
            'Get_StoneOfForest': ['Talk_Deku_01', 'Talk_Deku_02', 'Talk_Deku_03',
                                  'Talk_Deku_01_Attacked', 'Talk_Deku_02_Attacked',
                                  'Talk_Deku_03_Attacked', 'Disappear',
                                  'FocusFaceCamera', 'Focus_ForDeku', 'InitTalk_Attacked'],
            'Get_StoneOfFire': ['Check_DaruniaDoor', 'CarpetCam'],
            'DoorOfTime': ['Check_SpiritStoneBase'],
            'Get_StoneOfWater': ['StoneOfWater_ElevatedFloor_NaviTalk'],
            'Dm_LostWood_0040': ['C01', 'Dm_LostWood_0040_SecondTure',
                                 'Dm_LostWood_0040_SecondFalse',
                                 'HitTargetOfDekuScrub_WalletFull'],
        }
        talks = 0
        for flow, entries in hints.items():
            spec = self.policy['story_flows'].get(flow)
            self.assertIsInstance(spec, list, flow)
            for entry in entries:
                self.assertNotIn(entry, spec, (flow, entry))
                fo = self._assert_entry_untouched(flow, entry)
                talks += sum(1 for i in _reach(fo.events, fo.entry_points[entry])
                             if fo.events[i].action == 'EventTalk')
        self.assertGreater(talks, 10)
        # The rest of Get_StoneOfForest is still story and is trimmed.
        spec = self.policy['story_flows']['Get_StoneOfForest']
        self.assertIn('GetSword', spec)
        self.assertIn('Boss_Win', spec)
        self.assertIn(FLOW_DIR + 'Get_StoneOfForest.bfevfl.zs', self.flows)

    def test_kokiri_007_first_reaction_listed(self):
        # Round 2: the Kokiri who blocks the exit. Near_FirstReaction is his
        # forced reaction (EventRequestActor.RequestEventName in the banc
        # KokiriForest_Child_Static -> SubEvent row). It is listed and its trim
        # keeps the switches and everything that is not phase 1.
        flow = 'Npc_Kokiri_007_Child'
        spec = self.policy['story_flows'].get(flow)
        self.assertIsInstance(spec, list)
        self.assertLessEqual({'Near_FirstReaction', 'Talk', 'GoToDekuTree', 'GoToMido'},
                             set(spec))
        pairs = _phase1(self.policy)
        fo, fn = self._trimmed(flow)
        for entry, start in fo.entry_points.items():
            before = _reach(fo.events, start)
            after = _reach(fn.events, fn.entry_points[entry])
            for i in before - after:
                self.assertTrue(_is_phase1(fo.events[i], pairs), (entry, i))
                self.assertNotEqual(fo.events[i].kind, SWITCH, (entry, i))
        # A single-bubble entry that ends in "end" cannot be left
        # pointing to "end": it is kept (end-pointer rule).
        self.assertNotEqual(fn.entry_points['Near_FirstReaction'], END)

    def test_kokiri_007_talks_removed(self):
        # Round 2b: the dialogues of Kokiri 007 followed by a random switch
        # or flag switch no longer count as questions and are all removed.
        fo, fn = self._trimmed('Npc_Kokiri_007_Child')
        for entry in ('Talk', 'GoToDekuTree', 'GoToMido'):
            after = _reach(fn.events, fn.entry_points[entry])
            talks = [i for i in after if fn.events[i].action == 'EventTalk']
            self.assertEqual(talks, [], entry)

    def test_frozen_link_flows_not_trimmed(self):
        # Round 2b: scenes in which the join waits for animations that are not
        # removed; if trimmed, Link stands still. They are not touched.
        frozen = ['Dm_Kokiri_0060', 'Dm_Kokiri_0130', 'Dm_Kokiri_0145', 'Dm_Kokiri_0155',
                  'Dm_Deku_0003', 'Dm_HrlField_0020', 'Dm_HrlCastle_0000',
                  'Dm_HrlCastle_0020', 'Dm_HrlCastle_0020.110', 'Dm_HrlCastle_0035',
                  'Dm_HrlCastle_0050', 'Dm_LonLon_0020', 'Dm_Kakariko_0010']
        for flow in frozen:
            self.assertNotIn(flow, self.policy['story_flows'], flow)
            self.assertNotIn(FLOW_DIR + flow + '.bfevfl.zs', self.files, flow)

    def test_fork_branches_never_emptied(self):
        # Round 2b: the original game has no fork branch that goes
        # straight to the join (0 of 12369), so the rule holds: no
        # trimmed branch points to the join or to "end".
        for path, (orig, new) in self.flows.items():
            fo, fn = EventFlow(orig), EventFlow(new)
            for eo, en in zip(fo.events, fn.events):
                for bo, bn in zip(eo.forks, en.forks):
                    if bn != bo:
                        self.assertNotIn(bn, (en.join, END), (path, eo.index))

    def test_deterministic(self):
        again = cutscenes.build_cutscene_files(self.game)
        self.assertEqual(list(again), list(self.files))
        self.assertEqual(again, self.files)


if __name__ == '__main__':
    unittest.main()
