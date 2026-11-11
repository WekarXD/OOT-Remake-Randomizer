import time
import unittest
from collections import Counter
from pathlib import Path

from randomizer import items, locations
from randomizer.fill import (AMMO_CONTAINER, NO_KEY_TARGET_ZONES, OOTR_TOKEN, TOKEN,
                              FillError, Settings, filler_sites, gs_sites, place)
from randomizer.game import load_chests_fixture, load_skulltulas_fixture
from randomizer.logic.world import World, load_vanilla_settings

FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
GS_FIXTURE = Path(__file__).parent / 'fixtures' / 'skulltulas.json'
HOOKSHOT_HASH = 16041366920820397198


def _data():
    if not hasattr(_data, 'cached'):
        _data.cached = (load_chests_fixture(FIXTURE), locations.load_map(),
                        World(load_vanilla_settings()))
    return _data.cached


def _original(chests) -> dict[int, str]:
    return {c.hash: c.drop for c in chests}


def _eligible_hashes(chests, loc_map) -> list[int]:
    """Independent re-derivation of the eligible sites (see the brief)."""
    shop = {c.hash for c in chests if 'HrlCity_Shop' in c.gyaml}
    orig = _original(chests)
    out = []
    for h in sorted(orig):
        e = loc_map.get(h)
        if (e is None or e.status == 'unmapped' or e.needs_event_patch or h in shop
                or orig[h].startswith(items.DUNGEON_ITEM_PREFIXES)):
            continue
        out.append(h)
    return out


def _fixed_for(result, chests, loc_map, world) -> dict[str, str]:
    fixed = world.vanilla_fixed()
    for h in _eligible_hashes(chests, loc_map):
        drop = result[h]
        fixed[loc_map[h].location] = drop if drop in items.KEY_ITEMS else 'Rupees (5)'
    return fixed


class FillTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)

    def _place(self, **kw):
        return place(self.chests, self.loc_map, self.world, Settings(**kw))

    def test_deterministic(self):
        self.assertEqual(self._place(seed='ABC'), self._place(seed='ABC'))

    def test_different_seeds_differ(self):
        self.assertNotEqual(self._place(seed='A'), self._place(seed='B'))

    def test_all_hashes_returned(self):
        self.assertEqual(set(self._place(seed='ABC')), set(self.orig))

    def test_multiset_preserved(self):
        result = self._place(seed='ABC')
        self.assertEqual(Counter(result.values()), Counter(self.orig.values()))

    def test_key_items_actually_move(self):
        moved = sum(self._place(seed=str(i)) != self.orig for i in range(5))
        self.assertEqual(moved, 5)

    def test_beatable_many(self):
        start = time.perf_counter()
        for i in range(200):
            result = self._place(seed=str(i))
            fixed = _fixed_for(result, self.chests, self.loc_map, self.world)
            self.assertTrue(self.world.can_beat(fixed), f'seed {i}')
        self.assertLess(time.perf_counter() - start, 60)

    def test_excluded_stays(self):
        result = self._place(seed='ABC', excluded_items=frozenset({'Item_Hookshot'}))
        self.assertEqual(result[HOOKSHOT_HASH], 'Item_Hookshot')

    def test_excluded_eligible_item_stays(self):
        bow_hash = 11082303891540711688
        for i in range(10):
            result = self._place(seed=str(i), excluded_items=frozenset({'Item_Range_Bow'}))
            self.assertEqual(result[bow_hash], 'Item_Range_Bow')

    def test_vanilla_mode_identity(self):
        self.assertEqual(self._place(seed='ABC', key_items_mode='vanilla'), self.orig)

    def test_dungeon_item_chests_untouched(self):
        result = self._place(seed='ABC')
        for h, drop in self.orig.items():
            if drop.startswith(items.DUNGEON_ITEM_PREFIXES):
                self.assertEqual(result[h], drop, h)

    def test_shop_chests_untouched(self):
        result = self._place(seed='ABC')
        shop = {c.hash for c in self.chests if 'HrlCity_Shop' in c.gyaml}
        self.assertTrue(shop)
        for h in shop:
            self.assertEqual(result[h], self.orig[h], h)

    def test_ineligible_sites_untouched(self):
        result = self._place(seed='ABC')
        eligible = set(_eligible_hashes(self.chests, self.loc_map))
        eligible |= set(filler_sites(self.chests, self.loc_map))
        for h in self.orig:
            if h not in eligible:
                self.assertEqual(result[h], self.orig[h], h)

    def test_filler_sites_selection(self):
        filler = set(filler_sites(self.chests, self.loc_map))
        self.assertGreater(len(filler), 50)
        by_hash = {}
        for c in self.chests:
            by_hash.setdefault(c.hash, []).append(c)
        for h in filler:
            self.assertEqual(self.loc_map[h].status, 'unmapped')
            self.assertFalse(self.orig[h].startswith(items.DUNGEON_ITEM_PREFIXES))
            for c in by_hash[h]:
                self.assertIsNone(c.event)
                self.assertNotIn('HrlCity_Shop', c.gyaml)
                self.assertNotIn('/DreamWorld/', c.banc)
        dream = {c.hash for c in self.chests if '/DreamWorld/' in c.banc}
        self.assertTrue(dream)
        result = self._place(seed='ABC')
        for h in dream:
            self.assertEqual(result[h], self.orig[h])

    def test_filler_sites_get_minor_items_only(self):
        filler = filler_sites(self.chests, self.loc_map)
        moved = 0
        for seed in ('F1', 'F2', 'F3'):
            r = self._place(seed=seed)
            for h in filler:
                self.assertNotIn(r[h], items.KEY_ITEMS, (seed, h))
                self.assertNotIn(r[h], AMMO_CONTAINER, (seed, h))
                moved += r[h] != self.orig[h]
        self.assertGreater(moved, 0)

    def test_filler_ammo_moves_to_gated_chests(self):
        # The ammo that sat in unmapped chests now joins the fill, which only
        # places it where its container is required.
        filler = filler_sites(self.chests, self.loc_map)
        ammo = [h for h in filler if self.orig[h] in AMMO_CONTAINER]
        self.assertTrue(ammo)
        r = self._place(seed='ABC')
        self.assertEqual(Counter(r.values()), Counter(self.orig.values()))

    def test_spoiler_toggle_does_not_change_placement(self):
        self.assertEqual(self._place(seed='X', spoiler=True),
                         self._place(seed='X', spoiler=False))

    def test_skip_cutscenes_not_in_key(self):
        self.assertEqual(self._place(seed='X', skip_cutscenes=True),
                         self._place(seed='X', skip_cutscenes=False))

    def test_non_excludable_raises(self):
        for actor in sorted(items.NON_EXCLUDABLE):
            with self.assertRaises(FillError) as cm:
                self._place(seed='A', excluded_items=frozenset({actor}))
            self.assertIn('Cannot exclude', str(cm.exception))
            self.assertIn('the logic needs to move it', str(cm.exception))

    def test_no_key_items_in_guarded_zones(self):
        zone = {c.hash: c.banc.split('/')[1] for c in self.chests}
        self.assertTrue(set(zone.values()) & NO_KEY_TARGET_ZONES)
        for i in range(50):
            result = self._place(seed=f'zona{i}')
            for h, drop in result.items():
                if zone[h] in NO_KEY_TARGET_ZONES and drop in items.KEY_ITEMS:
                    # only the original item can remain (ineligible site)
                    self.assertEqual(drop, self.orig[h], (i, h))

    def test_unknown_mode_raises(self):
        with self.assertRaises(FillError):
            self._place(seed='ABC', key_items_mode='nope')


def _gs_data():
    if not hasattr(_gs_data, 'cached'):
        _gs_data.cached = (load_skulltulas_fixture(GS_FIXTURE), locations.load_gs_map())
    return _gs_data.cached


class TokensanityTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.skulltulas, self.gs_map = _gs_data()
        self.orig = _original(self.chests)

    def _place(self, **kw):
        return place(self.chests, self.loc_map, self.world, Settings(**kw))

    def P(self, seed, mode, forbidden=frozenset()):
        return place(self.chests, self.loc_map, self.world,
                     Settings(seed=seed, tokensanity=mode), self.skulltulas,
                     self.gs_map, forbidden)

    def _gs(self, mode):
        return gs_sites(self.skulltulas, self.gs_map, mode)

    def test_ammo_only_where_container_is_required(self):
        # Batch 17: bombs from a chest before the Bomb Bag unlocked the bag in
        # the inventory without being usable. Ammo may only land on a site
        # that cannot be reached without its container.
        sites = {h: self.loc_map[h].location for h in _eligible_hashes(self.chests, self.loc_map)}
        sites.update((h, self.gs_map[h].location) for h in self._gs('all'))
        for seed, mode in (('A1', 'off'), ('A2', 'off'), ('A3', 'all'), ('A4', 'all')):
            r = self.P(seed, mode)
            fixed = self.world.vanilla_fixed()
            for h, loc in sites.items():
                if h in r:
                    drop = r[h]
                    fixed[loc] = (drop if drop in items.KEY_ITEMS
                                  else OOTR_TOKEN if drop == TOKEN else 'Rupees (5)')
            checked = 0
            for h, loc in sites.items():
                container = AMMO_CONTAINER.get(r.get(h))
                if container is None:
                    continue
                without = dict(fixed)
                for other, item in fixed.items():
                    if item == container:
                        without[other] = 'Rupees (5)'
                reach = self.world.reachable_locations(without, owned=[OOTR_TOKEN] * 100)
                self.assertNotIn(loc, reach, (seed, r[h], loc))
                checked += 1
            self.assertGreater(checked, 0, seed)

    def test_tokensanity_off_identical(self):
        self.assertEqual(self._place(seed='ABC'), self.P('ABC', 'off'))

    def test_tokensanity_all_places_gs(self):
        r = self.P('T', 'all')
        gs = self._gs('all')
        self.assertEqual(len(gs), 100)
        self.assertTrue(set(gs) <= set(r))
        self.assertEqual(set(r), set(self.orig) | set(gs))
        self.assertEqual(sum(1 for v in r.values() if v == TOKEN), 100)
        self.assertTrue(any(r[h] != TOKEN for h in gs))
        self.assertTrue(any(v == TOKEN for h, v in r.items() if h not in gs))
        expected = Counter(self.orig.values()) + Counter({TOKEN: 100})
        self.assertEqual(Counter(r.values()), expected)

    def test_tokensanity_modes_counts(self):
        self.assertEqual(len(self._gs('dungeons')), 44)
        self.assertEqual(len(self._gs('overworld')), 56)
        self.assertEqual(self._gs('off'), [])
        self.assertEqual(self._gs('all'), sorted(set(self._gs('all'))))

    def test_tokensanity_dungeons_only_dungeon_sites(self):
        r = self.P('D', 'dungeons')
        self.assertEqual(set(r), set(self.orig) | set(self._gs('dungeons')))

    def test_tokensanity_seed_differs_by_mode(self):
        self.assertNotEqual(self.P('S', 'all'), self.P('S', 'dungeons'))

    def test_tokensanity_forbidden_never_on_gs(self):
        forbidden = frozenset({'Item_ScrubBusinessSeed', 'TBox_DekuNutBundle'})
        r = self.P('F', 'all', forbidden)
        for h in self._gs('all'):
            self.assertNotIn(r[h], forbidden)
        # Forbidden contents are still in the fill (in chests).
        self.assertEqual(Counter(r.values()),
                         Counter(self.orig.values()) + Counter({TOKEN: 100}))

    def test_tokensanity_not_enough_allowed_raises(self):
        allowed_none = frozenset(self.orig.values()) | {TOKEN}
        with self.assertRaises(FillError) as cm:
            self.P('F', 'all', allowed_none)
        self.assertIn('Skulltulas', str(cm.exception))

    def test_tokensanity_no_key_in_forbidden_zones(self):
        zone = {s.hash: s.banc.split('/')[1] for s in self.skulltulas}
        guarded = {h for h in self._gs('all') if zone[h] in NO_KEY_TARGET_ZONES}
        self.assertTrue(guarded)
        for i in range(5):
            r = self.P(f'Z{i}', 'all')
            for h in guarded:
                self.assertNotIn(r[h], items.KEY_ITEMS, (i, h))

    def test_tokensanity_no_key_gs_map_flag(self):
        flagged = {h for h, e in self.gs_map.items() if e.no_key}
        self.assertTrue(flagged)
        for i in range(5):
            r = self.P(f'K{i}', 'all')
            for h in flagged:
                self.assertNotIn(r[h], items.KEY_ITEMS, (i, h))

    def test_tokensanity_no_key_on_guessed_gs(self):
        guessed = {h for h, e in self.gs_map.items() if e.status == 'guessed'}
        self.assertTrue(guessed)
        for i in range(5):
            r = self.P(f'G{i}', 'all')
            for h in guessed & set(r):
                self.assertNotIn(r[h], items.KEY_ITEMS, (i, h))

    def test_tokensanity_forbidden_key_item_not_on_gs(self):
        gs = set(self._gs('all'))
        forbidden = frozenset({'Item_Boomerang'})
        for i in range(5):
            r = self.P(f'B{i}', 'all', forbidden)
            for h in gs:
                self.assertNotIn(r[h], forbidden, (i, h))

    def test_tokensanity_completable(self):
        gs = self._gs('all')
        for i in range(5):
            r = self.P(f'C{i}', 'all')
            fixed = self.world.vanilla_fixed()
            sites = ([(h, self.loc_map[h].location)
                      for h in _eligible_hashes(self.chests, self.loc_map)]
                     + [(h, self.gs_map[h].location) for h in gs])
            for h, loc in sites:
                drop = r[h]
                if drop in items.KEY_ITEMS:
                    fixed[loc] = drop
                elif drop == TOKEN:
                    fixed[loc] = OOTR_TOKEN
                else:
                    fixed[loc] = 'Rupees (5)'
            self.assertTrue(self.world.can_beat(fixed), f'C{i}')

    def test_tokensanity_world_not_mutated(self):
        before = self.world.vanilla_fixed()
        self.P('W', 'all')
        self.assertEqual(self.world.vanilla_fixed(), before)

    def test_tokensanity_invalid_mode(self):
        with self.assertRaises(FillError):
            self.P('x', 'mucho')


class WorldOwnedTest(unittest.TestCase):
    def test_owned_items_extend_reach(self):
        w = _data()[2]
        fixed = w.vanilla_fixed()
        fixed['Deku Tree Slingshot Chest'] = 'Rupees (5)'
        self.assertNotIn('Deku Tree Queen Gohma Heart', w.reachable_locations(fixed))
        self.assertIn('Deku Tree Queen Gohma Heart',
                      w.reachable_locations(fixed, owned=['Item_Range_SlingShot']))
        # The parameter leaves no residual state.
        self.assertNotIn('Deku Tree Queen Gohma Heart', w.reachable_locations(fixed))

    def test_owned_in_can_beat(self):
        w = _data()[2]
        fixed = w.vanilla_fixed()
        self.assertFalse(w.can_beat(fixed))
        self.assertTrue(w.can_beat(fixed, owned=['Small Key (Water Temple)',
                                                 'Small Key (Spirit Temple)']))


if __name__ == '__main__':
    unittest.main()
