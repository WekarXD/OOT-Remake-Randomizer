import time
import unittest
from collections import Counter
from pathlib import Path

from randomizer import items, locations
from randomizer.fill import FillError, Settings, place
from randomizer.game import load_chests_fixture
from randomizer.logic.world import World, load_vanilla_settings

FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
HOOKSHOT_HASH = 16041366920820397198


def _data():
    if not hasattr(_data, 'cached'):
        _data.cached = (load_chests_fixture(FIXTURE), locations.load_map(),
                        World(load_vanilla_settings()))
    return _data.cached


def _original(chests) -> dict[int, str]:
    return {c.hash: c.drop for c in chests}


def _eligible_hashes(chests, loc_map) -> list[int]:
    """Rederivación independiente de los sitios elegibles (ver el brief)."""
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
        for h in self.orig:
            if h not in eligible:
                self.assertEqual(result[h], self.orig[h], h)

    def test_unknown_mode_raises(self):
        with self.assertRaises(FillError):
            self._place(seed='ABC', key_items_mode='nope')


class WorldOwnedTest(unittest.TestCase):
    def test_owned_items_extend_reach(self):
        w = _data()[2]
        fixed = w.vanilla_fixed()
        fixed['Deku Tree Slingshot Chest'] = 'Rupees (5)'
        self.assertNotIn('Deku Tree Queen Gohma Heart', w.reachable_locations(fixed))
        self.assertIn('Deku Tree Queen Gohma Heart',
                      w.reachable_locations(fixed, owned=['Item_Range_SlingShot']))
        # El parámetro no deja estado residual.
        self.assertNotIn('Deku Tree Queen Gohma Heart', w.reachable_locations(fixed))

    def test_owned_in_can_beat(self):
        w = _data()[2]
        fixed = w.vanilla_fixed()
        self.assertFalse(w.can_beat(fixed))
        self.assertTrue(w.can_beat(fixed, owned=['Small Key (Water Temple)',
                                                 'Small Key (Spirit Temple)']))


if __name__ == '__main__':
    unittest.main()
