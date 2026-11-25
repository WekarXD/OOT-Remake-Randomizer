"""Rainbow Bridge medallions and Ganon's Trials (design 2026-11-22-bridge-and-trials)."""
import itertools
import json
import os
import unittest

from randomizer import ganon
from randomizer.fill import FillError, Settings, _check_settings, _settings_key
from randomizer.formats.bfevfl import ACTION, END, SWITCH, EventFlow

NUP_PATH = os.environ.get('OOT_NUP')


def walk(flow: EventFlow, start: int, owned: set[str], stop: int,
         ints: dict[str, int] | None = None) -> list[dict]:
    """The params of the ChallengeSystemActor actions met from `start` until `stop`,
    taking each pouch switch's case 0 when its item is in `owned`, and each int
    comparison's case by `ints` (0 less, 1 equal, 2 greater)."""
    steps, i, seen = [], start, 0
    while i != stop:
        seen += 1
        assert seen < 200 and i != END, 'the check does not come back'
        e = flow.events[i]
        if e.kind == SWITCH and e.query == 'EventQueryIsGameDataInt':
            p = flow.action_params(i)
            v = (ints or {})[p['GameDataName']]
            i = e.cases[0 if v < p['Value'] else 1 if v == p['Value'] else 2]
            continue
        if e.kind == SWITCH:
            has = flow.action_params(i)['Actor'] in owned
            i = e.cases[0 if has else 1]
            continue
        assert e.kind == ACTION, e
        if e.actor == 'ChallengeSystemActor':
            steps.append(flow.action_params(i))
        i = e.next
    return steps


def _settings(**kw) -> Settings:
    return Settings(seed='TRIALS1', **kw)


class TrialTests(unittest.TestCase):
    def test_default_keeps_all_six(self):
        self.assertEqual(ganon.active_trials(_settings()), ganon.TRIALS)

    def test_count_and_determinism(self):
        for n in range(7):
            s = _settings(trials=n)
            active = ganon.active_trials(s)
            self.assertEqual(len(active), n)
            self.assertEqual(active, ganon.active_trials(s))
            self.assertEqual(list(active), [t for t in ganon.TRIALS if t in active])

    def test_random_count_in_range_and_varies(self):
        counts = {len(ganon.active_trials(Settings(seed=f'S{i}', trials_random=True)))
                  for i in range(60)}
        self.assertTrue(counts <= set(range(7)))
        self.assertGreater(len(counts), 2)

    def test_world_settings(self):
        s = _settings(bridge='medallions', bridge_medallions=4, trials=2)
        w = ganon.world_settings(s)
        self.assertEqual(w['bridge'], 'medallions')
        self.assertEqual(w['bridge_medallions'], 4)
        self.assertEqual(w['trials'], 2)
        active = ganon.active_trials(s)
        self.assertEqual(w['skipped_trials'], {t: t not in active for t in ganon.TRIALS})
        self.assertEqual(ganon.world_settings(_settings())['bridge'], 'vanilla')


class SettingsTests(unittest.TestCase):
    def test_defaults_keep_the_rng_key(self):
        key = json.loads(_settings_key(Settings(seed='X')))
        for name in ('bridge', 'bridge_medallions', 'trials', 'trials_random'):
            self.assertNotIn(name, key)

    def test_non_defaults_change_the_key(self):
        base = _settings_key(Settings(seed='X'))
        for kw in ({'bridge': 'medallions'}, {'bridge': 'medallions', 'bridge_medallions': 3},
                   {'trials': 0}, {'trials_random': True}):
            self.assertNotEqual(_settings_key(Settings(seed='X', **kw)), base, kw)
        # with the vanilla bridge the count does nothing
        self.assertEqual(_settings_key(Settings(seed='X', bridge_medallions=3)), base)

    def test_validation(self):
        for kw in ({'bridge': 'rings'}, {'bridge_medallions': 7}, {'bridge_medallions': -1},
                   {'bridge_stones': 4}, {'bridge_rewards': 10}, {'bridge_tokens': 101},
                   {'bridge_hearts': 3}, {'bridge_hearts': 21}, {'bridge_tokens': True},
                   {'trials': 9}, {'trials': True}, {'trials_random': 1}):
            with self.assertRaises(FillError, msg=kw):
                _check_settings(Settings(seed='X', **kw))
        for bridge in ('open', 'vanilla', 'stones', 'medallions', 'dungeons', 'tokens',
                       'hearts', 'random'):
            _check_settings(Settings(seed='X', bridge=bridge))

    def test_key_keeps_only_the_chosen_count(self):
        # Seeds made with 'medallions' before the other modes keep their key.
        self.assertEqual(
            {k: v for k, v in json.loads(_settings_key(
                Settings(seed='X', bridge='medallions', bridge_medallions=4))).items()
             if k.startswith('bridge')},
            {'bridge': 'medallions', 'bridge_medallions': 4})
        for bridge, field in (('stones', 'bridge_stones'), ('dungeons', 'bridge_rewards'),
                              ('tokens', 'bridge_tokens'), ('hearts', 'bridge_hearts')):
            key = json.loads(_settings_key(Settings(seed='X', bridge=bridge)))
            self.assertEqual({k for k in key if k.startswith('bridge')}, {'bridge', field})
        for bridge in ('open', 'random'):
            key = json.loads(_settings_key(Settings(seed='X', bridge=bridge)))
            self.assertEqual({k for k in key if k.startswith('bridge')}, {'bridge'})


class RequirementTests(unittest.TestCase):
    def test_each_mode(self):
        cases = {'vanilla': ('vanilla', 0), 'open': ('open', 0),
                 'stones': ('stones', 2), 'medallions': ('medallions', 5),
                 'dungeons': ('dungeons', 7), 'tokens': ('tokens', 30),
                 'hearts': ('hearts', 12)}
        for bridge, want in cases.items():
            s = Settings(seed='R', bridge=bridge, bridge_stones=2, bridge_medallions=5,
                         bridge_rewards=7, bridge_tokens=30, bridge_hearts=12)
            self.assertEqual(ganon.bridge_requirement(s), want, bridge)

    def test_random_never_tokens_and_in_range(self):
        seen = set()
        for i in range(80):
            mode, n = ganon.bridge_requirement(Settings(seed=f'R{i}', bridge='random'))
            seen.add(mode)
            self.assertNotEqual(mode, 'tokens')
            low, high = ganon.BRIDGE_RANGES.get(mode, (0, 0))
            self.assertTrue(low <= n <= high, (mode, n))
        self.assertGreater(len(seen), 3)
        s = Settings(seed='R1', bridge='random')
        self.assertEqual(ganon.bridge_requirement(s), ganon.bridge_requirement(s))

    def test_world_settings_per_mode(self):
        w = ganon.world_settings(Settings(seed='R', bridge='hearts', bridge_hearts=9))
        self.assertEqual((w['bridge'], w['bridge_hearts']), ('hearts', 9))
        w = ganon.world_settings(Settings(seed='R', bridge='dungeons', bridge_rewards=4))
        self.assertEqual((w['bridge'], w['bridge_rewards']), ('dungeons', 4))
        mode, n = ganon.bridge_requirement(Settings(seed='R3', bridge='random'))
        w = ganon.world_settings(Settings(seed='R3', bridge='random'))
        self.assertEqual(w['bridge'], mode)


class SpoilerTests(unittest.TestCase):
    def test_settings_and_active_trials(self):
        from randomizer import spoiler
        s = Settings(seed='T', bridge='medallions', bridge_medallions=4, trials=2)
        d = spoiler.build(s, {}, [], {}, '1.0')
        self.assertEqual(d['settings']['bridge_medallions'], 4)
        self.assertEqual(d['ganon_trials'], list(ganon.active_trials(s)))
        text = spoiler.to_text(d)
        self.assertIn('Rainbow Bridge Requirement: Medallions (4)', text)
        self.assertIn("Ganon's Trials Count: 2", text)
        trials = text.split("\nGanon's Trials\n", 1)[1].split('\n\n', 1)[0]
        self.assertEqual(trials.split(), list(ganon.active_trials(s)))

    def test_no_trials_and_vanilla_bridge(self):
        from randomizer import spoiler
        text = spoiler.to_text(spoiler.build(Settings(seed='T', trials=0), {}, [], {}, '1.0'))
        self.assertIn('Rainbow Bridge Requirement: Vanilla Requirements', text)
        self.assertIn("\nGanon's Trials\n  none\n", text)

    def test_every_mode_label(self):
        from randomizer import spoiler
        for kw, label in (({'bridge': 'open'}, 'Always Open'),
                          ({'bridge': 'stones', 'bridge_stones': 2}, 'Spiritual Stones (2)'),
                          ({'bridge': 'dungeons', 'bridge_rewards': 5}, 'Dungeon Rewards (5)'),
                          ({'bridge': 'tokens', 'bridge_tokens': 40}, 'Gold Skulltula Tokens (40)'),
                          ({'bridge': 'hearts', 'bridge_hearts': 9}, 'Hearts (9)')):
            text = spoiler.to_text(spoiler.build(Settings(seed='T', **kw), {}, [], {}, '1.0'))
            self.assertIn(f'Rainbow Bridge Requirement: {label}\n', text, kw)
        text = spoiler.to_text(spoiler.build(Settings(seed='T', bridge='random'), {}, [], {},
                                             '1.0'))
        self.assertIn('Rainbow Bridge Requirement: Random (', text)


class FillTests(unittest.TestCase):
    """The logic counts medallion items, so the fill must see where the rewards really are."""
    REWARDS = ('Queen Gohma', 'King Dodongo', 'Barinade', 'Phantom Ganon', 'Volvagia',
               'Morpha', 'Bongo Bongo', 'Twinrova', 'ToT Reward from Rauru')

    @classmethod
    def setUpClass(cls):
        from tests.test_fill import _data
        cls.chests, cls.loc_map, _ = _data()

    def _world(self, settings):
        from randomizer.logic.world import World, load_vanilla_settings
        return World({**load_vanilla_settings(), **ganon.world_settings(settings)})

    def _real_fixed(self, r, world):
        from randomizer.items import FAMILIES
        from tests.test_fill import _fixed_for
        fixed = _fixed_for(r.chests, self.chests, self.loc_map, world,
                           {**r.fairies, **r.gifts})
        fixed.update((loc, FAMILIES[r.gifts[loc]]) for loc in self.REWARDS)
        # the hearts too (only a hearts bridge counts them)
        from randomizer.fill import HEART_ACTORS
        from tests.test_fill import _eligible_hashes
        for h in _eligible_hashes(self.chests, self.loc_map):
            if r.chests[h] in HEART_ACTORS:
                fixed[self.loc_map[h].location] = HEART_ACTORS[r.chests[h]]
        for loc, drop in {**r.fairies, **r.gifts, **r.songs}.items():
            if drop in HEART_ACTORS:
                fixed[loc] = HEART_ACTORS[drop]
        return fixed

    def test_medallion_bridge_seeds_are_beatable_with_the_real_rewards(self):
        from randomizer.fill import place_all
        for i in range(4):
            s = Settings(seed=f'BRIDGE{i}', bridge='medallions', bridge_medallions=6, trials=0)
            world = self._world(s)
            r = place_all(self.chests, self.loc_map, world, s)
            fixed = self._real_fixed(r, world)
            self.assertTrue(world.can_beat(fixed), i)
            # the logic needs every medallion: losing one breaks the seed
            medal = next(loc for loc in self.REWARDS if r.gifts[loc] == 'Item_Medal_Water')
            self.assertFalse(world.can_beat({**fixed, medal: 'Rupees (5)'}), i)

    def test_the_fill_sees_the_shuffled_rewards(self):
        from unittest import mock

        from randomizer import fill
        from randomizer.items import FAMILIES
        s = Settings(seed='BRIDGE1', bridge='medallions')
        seen = {}
        real_run = fill._run

        def spy(settings, world, original, eligible, moving, site_loc, base, *a, **kw):
            seen.update(base)
            return real_run(settings, world, original, eligible, moving, site_loc, base,
                            *a, **kw)

        with mock.patch.object(fill, '_run', spy):
            r = fill.place_all(self.chests, self.loc_map, self._world(s), s)
        self.assertEqual({loc: seen[loc] for loc in self.REWARDS},
                         {loc: FAMILIES[r.gifts[loc]] for loc in self.REWARDS})
        self.assertTrue(any(seen[loc] != v for loc, v in
                            self._world(s).vanilla_fixed().items() if loc in self.REWARDS))

    def test_every_mode_is_beatable(self):
        from randomizer.fill import place_all
        for kw in ({'bridge': 'stones'}, {'bridge': 'dungeons'}, {'bridge': 'hearts'},
                   {'bridge': 'tokens', 'bridge_tokens': 30}, {'bridge': 'open'},
                   {'bridge': 'random'}):
            s = Settings(seed='MODES', trials=0, **kw)
            world = self._world(s)
            r = place_all(self.chests, self.loc_map, world, s)
            self.assertTrue(world.can_beat(self._real_fixed(r, world)), kw)

    def test_hearts_bridge_keeps_hearts_where_the_logic_sees_them(self):
        from randomizer.fill import filler_sites, place_all
        s = Settings(seed='HEARTS', bridge='hearts', bridge_hearts=20)
        r = place_all(self.chests, self.loc_map, self._world(s), s)
        filler = set(filler_sites(self.chests, self.loc_map))
        self.assertFalse([h for h in filler if r.chests.get(h) == 'Obj_Heart_Piece'])
        def pieces(res):
            return sum(d == 'Obj_Heart_Piece' for d in [*res.chests.values(), *res.gifts.values(),
                                                        *res.fairies.values(), *res.songs.values()])
        plain = Settings(seed='HEARTS')
        self.assertEqual(pieces(r), pieces(place_all(self.chests, self.loc_map,
                                                     self._world(plain), plain)))

    def test_zero_medallions_need_none(self):
        from randomizer.fill import place_all
        s = Settings(seed='BRIDGE0', bridge='medallions', bridge_medallions=0)
        world = self._world(s)
        r = place_all(self.chests, self.loc_map, world, s)
        fixed = self._real_fixed(r, world)
        medal = next(loc for loc in self.REWARDS if r.gifts[loc] == 'Item_Medal_Water')
        self.assertTrue(world.can_beat({**fixed, medal: 'Rupees (5)'}))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class RealFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from randomizer.game import GameData
        from randomizer.nup import NupArchive
        cls.nup = NupArchive(NUP_PATH)
        cls.game = GameData(cls.nup)

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def read(self, name):
        p = self.game.flow_path(name)
        return self.game.codec.decompress(p, self.nup.read(p))

    def _chain(self, flow, stop):
        params, i = [], flow.entry_points[ganon.RAINBOW_ENTRY]
        while i != stop:
            params.append(flow.action_params(i))
            i = flow.events[i].next
        return params

    def test_rainbow_sets_the_skipped_trials_first(self):
        data = self.read(ganon.TRIALS_FLOW)
        start = EventFlow(data).entry_points[ganon.RAINBOW_ENTRY]
        chain = self._chain(EventFlow(ganon.rainbow_patch(data, ('Fire', 'Light'))), start)
        names = [p['GameDataName'] for p in chain]
        self.assertEqual(names, [f'{ganon.BARRIER_REMOVE}{t}' for t in
                                 ('Forest', 'Water', 'Shadow', 'Spirit')] + [ganon.BARRIER_COUNT])
        self.assertEqual(chain[-1]['Value'], 2)

    def test_rainbow_with_no_trials_clears_the_barrier(self):
        data = self.read(ganon.TRIALS_FLOW)
        start = EventFlow(data).entry_points[ganon.RAINBOW_ENTRY]
        names = [p['GameDataName'] for p in
                 self._chain(EventFlow(ganon.rainbow_patch(data, ())), start)]
        self.assertIn(ganon.ALL_CLEAR, names)
        self.assertIn(ganon.BARRIER_MOVIE, names)

    def test_lacs_no_longer_moves_defeat_ganon(self):
        flow = EventFlow(ganon.lacs_patch(self.read(ganon.LACS_FLOW)))
        steps = [flow.action_params(e.index) for e in flow.events
                 if e.action == 'EventExecuteProgressChallengeStep']
        self.assertFalse([p for p in steps if p['ChallengeName'] == 'Defeat_Ganon'])
        self.assertEqual(sum(p['ChallengeName'] == 'AllSage' and p['StepName'] == 'Complete'
                             for p in steps), 2)

    def test_bridge_check_after_every_reward_grant(self):
        for n in (3, 6):  # 0 moves the quest on leaving home instead
            patches = ganon.flow_patches(self.read, Settings(seed='B', bridge='medallions',
                                                             bridge_medallions=n))
            for name in ganon.REWARD_FLOWS:
                data = self.read(name)
                old = EventFlow(data)
                grant = ganon.reward_grants(old)
                self.assertEqual(len(grant), 1, name)
                cont = old.events[grant[0]].next
                new = EventFlow(patches[name])
                first = new.events[grant[0]].next
                for owned in itertools.combinations(ganon.MEDALLION_ACTORS, 3):
                    steps = walk(new, first, set(owned), cont)
                    want = [('Defeat_Ganon', 'Ready'), ('Defeat_Ganon', 'Step01')] if n <= 3 else []
                    self.assertEqual([(p['ChallengeName'], p['StepName']) for p in steps], want,
                                     (name, n, owned))

    def test_bridge_check_every_count_and_combination(self):
        data = self.read('Dm_Awake_Forest_Get')
        old = EventFlow(data)
        grant = ganon.reward_grants(old)[0]
        cont = old.events[grant].next
        for n in range(7):
            new = EventFlow(ganon.with_bridge_check(data, grant, n))
            for owned in itertools.product((False, True), repeat=6):
                have = {a for a, o in zip(ganon.MEDALLION_ACTORS, owned) if o}
                hit = bool(walk(new, new.events[grant].next, have, cont))
                self.assertEqual(hit, len(have) >= n, (n, have))

    def test_zero_medallions_moves_the_quest_on_leaving_home(self):
        patches = ganon.flow_patches(self.read, Settings(seed='B', bridge='medallions',
                                                         bridge_medallions=0))
        old = EventFlow(self.read(ganon.START_FLOW))
        new = EventFlow(patches[ganon.START_FLOW])
        start = old.entry_points[ganon.START_ENTRY]
        steps = walk(new, new.entry_points[ganon.START_ENTRY], set(), start)
        self.assertEqual([p['StepName'] for p in steps], ['Ready', 'Step01'])
        self.assertNotIn(ganon.START_FLOW, ganon.flow_patches(
            self.read, Settings(seed='B', bridge='medallions', bridge_medallions=1)))

    def test_stones_and_dungeons_check_their_items(self):
        stones = ('Item_Stone_Forest', 'Item_Stone_Fire', 'Item_Stone_Water')
        for bridge, n, owned, hit in (
                ('stones', 2, stones[:2], True), ('stones', 2, stones[:1], False),
                ('stones', 2, ('Item_Medal_Forest', 'Item_Medal_Fire'), False),
                ('dungeons', 3, ('Item_Stone_Forest', 'Item_Medal_Light', 'Item_Medal_Fire'), True),
                ('dungeons', 3, ('Item_Stone_Forest', 'Item_Medal_Light'), False)):
            s = Settings(seed='B', bridge=bridge, bridge_stones=n, bridge_rewards=n)
            patches = ganon.flow_patches(self.read, s)
            for name in ganon.REWARD_FLOWS:
                old = EventFlow(self.read(name))
                grant = ganon.reward_grants(old)[0]
                new = EventFlow(patches[name])
                steps = walk(new, new.events[grant].next, set(owned), old.events[grant].next)
                self.assertEqual(bool(steps), hit, (bridge, owned, name))

    def _map_change(self, settings, ints):
        patches = ganon.flow_patches(self.read, settings)
        old = EventFlow(self.read(ganon.MAP_CHANGE_FLOW))
        new = EventFlow(patches[ganon.MAP_CHANGE_FLOW])
        start = old.entry_points[ganon.MAP_CHANGE_ENTRY]
        return walk(new, new.entry_points[ganon.MAP_CHANGE_ENTRY], set(), start, ints)

    def test_tokens_checked_before_each_map_change(self):
        s = Settings(seed='B', bridge='tokens', bridge_tokens=30)
        for count, hit in ((29, False), (30, True), (31, True), (100, True), (0, False)):
            steps = self._map_change(s, {ganon.TOKEN_COUNT: count})
            self.assertEqual([p['StepName'] for p in steps], ['Ready', 'Step01'] if hit else [],
                             count)

    def test_hearts_checked_before_each_map_change(self):
        s = Settings(seed='B', bridge='hearts', bridge_hearts=10)
        for life, hit in ((39, False), (40, True), (43, True), (80, True), (12, False)):
            steps = self._map_change(s, {ganon.MAX_LIFE: life})
            self.assertEqual(bool(steps), hit, life)

    def test_open_and_low_counts_move_the_quest_on_leaving_home(self):
        for kw in ({'bridge': 'open'}, {'bridge': 'stones', 'bridge_stones': 0},
                   {'bridge': 'tokens', 'bridge_tokens': 0}):
            patches = ganon.flow_patches(self.read, Settings(seed='B', **kw))
            self.assertIn(ganon.START_FLOW, patches, kw)
            self.assertNotIn(ganon.MAP_CHANGE_FLOW, patches, kw)
            self.assertFalse(set(ganon.REWARD_FLOWS) & set(patches), kw)

    def test_vanilla_bridge_patches_nothing(self):
        self.assertEqual(ganon.flow_patches(self.read, Settings(seed='B')), {})

if __name__ == '__main__':
    unittest.main()
