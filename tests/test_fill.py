import time
import unittest
from collections import Counter
from pathlib import Path

from randomizer import items, locations
from randomizer.fill import (AMMO_CONTAINER, NO_KEY_TARGET_ZONES, OOTR_TOKEN, TOKEN,
                              FillError, Settings, _settings_key, filler_sites, gs_sites, place,
                              place_all)
from randomizer.songs import BOSS_HEARTS, SONG_BY_ACTOR, SONGS
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


def _fixed_for(result, chests, loc_map, world, fairies=None) -> dict[str, str]:
    """The logic's view: eligible chests from `result`, and the Great Fairy fountains
    from `fairies` (they are sites too with key items shuffled)."""
    fixed = world.vanilla_fixed()
    for h in _eligible_hashes(chests, loc_map):
        drop = result[h]
        fixed[loc_map[h].location] = drop if drop in items.KEY_ITEMS else 'Rupees (5)'
    from randomizer.fill import MINOR_ONLY_GIFTS
    for loc, drop in (fairies or {}).items():
        if loc in MINOR_ONLY_GIFTS:
            continue  # the logic keeps its vanilla item (the Gerudo Card)
        fixed[loc] = (SONG_BY_ACTOR[drop].song if drop in SONG_BY_ACTOR
                      else drop if drop in items.KEY_ITEMS
                      else OOTR_TOKEN if drop == TOKEN else 'Rupees (5)')
    return fixed


def _fairy_rewards() -> Counter:
    from randomizer.fairies import FOUNTAINS
    return Counter(f.reward for f in FOUNTAINS)


def _scene_items(settings: Settings = Settings('x')) -> Counter:
    """What the synthetic sites (fountains and the NPC gifts active under `settings`) hold
    in the vanilla game."""
    from randomizer.gifts import active_gifts
    return _fairy_rewards() + Counter(g.content for g in active_gifts(settings))


class FillTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)

    def _place(self, **kw):
        return place(self.chests, self.loc_map, self.world, Settings(**kw))

    def _all(self, **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw))

    def test_deterministic(self):
        self.assertEqual(self._place(seed='ABC'), self._place(seed='ABC'))

    def test_different_seeds_differ(self):
        self.assertNotEqual(self._place(seed='A'), self._place(seed='B'))

    def test_all_hashes_returned(self):
        self.assertEqual(set(self._place(seed='ABC')), set(self.orig))

    def test_multiset_preserved(self):
        r = self._all(seed='ABC')
        self.assertEqual(Counter(r.chests.values()) + Counter(r.fairies.values())
                         + Counter(r.gifts.values()),
                         Counter(self.orig.values()) + _scene_items())

    def test_key_items_actually_move(self):
        moved = sum(self._place(seed=str(i)) != self.orig for i in range(5))
        self.assertEqual(moved, 5)

    def test_bomb_bag_can_leave_dodongo(self):
        # Batch 19: the Bomb Bag works from any chest once the Goron's
        # Bracelet is owned, so it is shuffled like the other key items.
        dodongo = 12161709650443144121
        homes = {h for seed in (f'B{i}' for i in range(1, 21))
                 for h, d in self._place(seed=seed).items() if d == 'Item_BombBag_Small'}
        self.assertTrue(homes - {dodongo})

    def test_beatable_many(self):
        start = time.perf_counter()
        for i in range(200):
            r = self._all(seed=str(i))
            fixed = _fixed_for(r.chests, self.chests, self.loc_map, self.world, {**r.fairies, **r.gifts})
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
        r = self._all(seed='ABC')
        self.assertEqual(Counter(r.chests.values()) + Counter(r.fairies.values())
                         + Counter(r.gifts.values()),
                         Counter(self.orig.values()) + _scene_items())

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


VANILLA_SONGS = {s.location: s.actor for s in SONGS}


class SongFillTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)

    def _all(self, **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw))

    def _fixed(self, result):
        fixed = _fixed_for(result.chests, self.chests, self.loc_map, self.world, {**result.fairies, **result.gifts})
        fixed.update((loc, SONG_BY_ACTOR[a].song) for loc, a in result.songs.items())
        return fixed

    def test_songs_off_identical(self):
        for seed in ('A', 'B'):
            result = self._all(seed=seed, shuffle_songs='off')
            self.assertEqual(result.chests, place(self.chests, self.loc_map, self.world,
                                                  Settings(seed=seed)))
            self.assertEqual(result.songs, VANILLA_SONGS)

    def test_songs_not_in_key_when_off(self):
        self.assertEqual(_settings_key(Settings(seed='A', shuffle_songs='off')),
                         _settings_key(Settings(seed='A')))
        self.assertNotIn('shuffle_songs', _settings_key(Settings(seed='A')))

    def test_settings_key_ignores_new_switches_when_off(self):
        # NPC gifts batch 3a: the three switches leave the RNG key alone when off.
        key = _settings_key(Settings(seed='A'))
        for name in ('shuffle_ocarinas', 'shuffle_gerudo_card', 'shuffle_expensive_merchants'):
            self.assertNotIn(name, key)
            self.assertIn(f'"{name}": true', _settings_key(Settings(seed='A', **{name: True})))

    def test_songs_permutation(self):
        moved = 0
        for i in range(5):
            result = self._all(seed=f'S{i}', shuffle_songs='song_locations')
            self.assertEqual(set(result.songs), set(VANILLA_SONGS))
            self.assertEqual(sorted(result.songs.values()), sorted(VANILLA_SONGS.values()))
            moved += result.songs != VANILLA_SONGS
            self.assertEqual(result, self._all(seed=f'S{i}', shuffle_songs='song_locations'))
        self.assertGreater(moved, 0)

    def test_songs_beatable_many(self):
        for i in range(20):
            result = self._all(seed=f'B{i}', shuffle_songs='song_locations')
            self.assertTrue(self.world.can_beat(self._fixed(result)), f'seed {i}')

    def test_songs_with_vanilla_key_items(self):
        # OoTR's key logic never calls the vanilla key placement beatable (world.py), so
        # the check here is that every song location can be reached.
        for i in range(5):
            result = self._all(seed=f'V{i}', key_items_mode='vanilla',
                               shuffle_songs='song_locations')
            self.assertEqual(result.chests, self.orig)
            self.assertEqual(sorted(result.songs.values()), sorted(VANILLA_SONGS.values()))
            reach = self.world.reachable_locations(self._fixed(result))
            self.assertLessEqual(set(VANILLA_SONGS), reach)

    def test_songs_unknown_value_raises(self):
        with self.assertRaises(FillError):
            self._all(seed='A', shuffle_songs='nope')


class AnywhereFillTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)

    def _all(self, **kw):
        return place_all(self.chests, self.loc_map, self.world,
                         Settings(shuffle_songs='anywhere', **kw))

    def _fixed(self, result):
        fixed = _fixed_for(result.chests, self.chests, self.loc_map, self.world, {**result.fairies, **result.gifts})
        for h, drop in result.chests.items():  # songs in chests
            if drop in SONG_BY_ACTOR and h in self.loc_map and self.loc_map[h].location:
                fixed[self.loc_map[h].location] = SONG_BY_ACTOR[drop].song
        for loc, drop in result.songs.items():
            fixed[loc] = (SONG_BY_ACTOR[drop].song if drop in SONG_BY_ACTOR
                          else drop if drop in items.KEY_ITEMS else 'Rupees (5)')
        return fixed

    def test_anywhere_moves_songs(self):
        in_chests = non_song_scenes = 0
        for i in range(10):
            r = self._all(seed=f'A{i}')
            in_chests += any(d in SONG_BY_ACTOR for d in r.chests.values())
            non_song_scenes += any(d not in SONG_BY_ACTOR for d in r.songs.values())
        self.assertGreater(in_chests, 0)
        self.assertGreater(non_song_scenes, 0)

    def test_anywhere_multiset(self):
        r = self._all(seed='M')
        self.assertEqual(set(r.chests), set(self.orig))
        self.assertEqual(set(r.songs), set(VANILLA_SONGS))
        self.assertEqual(Counter(r.chests.values()) + Counter(r.songs.values())
                         + Counter(r.fairies.values()) + Counter(r.gifts.values()),
                         Counter(self.orig.values()) + Counter(VANILLA_SONGS.values())
                         + _scene_items())
        self.assertEqual(r, self._all(seed='M'))

    def test_anywhere_beatable_many(self):
        for i in range(20):
            r = self._all(seed=f'B{i}')
            self.assertTrue(self.world.can_beat(self._fixed(r)), f'seed {i}')

    def test_anywhere_vanilla_keys_raises(self):
        with self.assertRaisesRegex(FillError, 'Anywhere needs key items shuffled'):
            self._all(seed='V', key_items_mode='vanilla')

    def test_anywhere_with_tokensanity_keeps_songs_off_skulltulas(self):
        skulltulas, gs_map = _gs_data()
        forbidden = frozenset(VANILLA_SONGS.values())
        sk = {s.hash for s in skulltulas}
        for i in range(5):
            r = place_all(self.chests, self.loc_map, self.world,
                          Settings(seed=f'T{i}', shuffle_songs='anywhere', tokensanity='all'),
                          skulltulas, gs_map, forbidden)
            self.assertFalse([h for h, d in r.chests.items() if h in sk and d in SONG_BY_ACTOR])

    def test_anywhere_no_token_from_a_song_scene(self):
        # A song scene giving a Gold Skulltula token is untested in game (review).
        skulltulas, gs_map = _gs_data()
        for i in range(15):
            r = place_all(self.chests, self.loc_map, self.world,
                          Settings(seed=f'T{i}', shuffle_songs='anywhere', tokensanity='all'),
                          skulltulas, gs_map, frozenset(VANILLA_SONGS.values()))
            self.assertNotIn(TOKEN, r.songs.values(), f'seed {i}')


class FairyFillTest(unittest.TestCase):
    """Great Fairy rewards in the pool (design 2026-11-15-great-fairies): with key items
    shuffled, the six fountains are sites and their rewards move."""
    def setUp(self):
        from randomizer.fairies import FOUNTAINS, FOUNTAIN_FORBIDDEN
        self.fountains, self.forbidden = FOUNTAINS, FOUNTAIN_FORBIDDEN
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)
        self.vanilla = {f.location: f.reward for f in FOUNTAINS}

    def _all(self, **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw))

    def _fixed(self, r):
        fixed = _fixed_for(r.chests, self.chests, self.loc_map, self.world, r.gifts)
        for loc, drop in r.fairies.items():
            fixed[loc] = drop if drop in items.KEY_ITEMS else 'Rupees (5)'
        return fixed

    def test_fountains_hold_six_items(self):
        r = self._all(seed='F')
        self.assertEqual(set(r.fairies), set(self.vanilla))
        self.assertEqual(set(r.chests), set(self.orig))
        self.assertEqual(Counter(r.chests.values()) + Counter(r.fairies.values())
                         + Counter(r.gifts.values()),
                         Counter(self.orig.values()) + _scene_items())
        self.assertEqual(r, self._all(seed='F'))

    def test_fairy_rewards_move(self):
        moved = 0
        for i in range(10):
            r = self._all(seed=f'M{i}')
            moved += any(r.fairies[loc] != a for loc, a in self.vanilla.items())
            reach = self.world.reachable_locations(self._fixed(r))
            for h, drop in r.chests.items():
                if drop in self.vanilla.values() and drop != self.orig[h]:
                    self.assertIn(self.loc_map[h].location, reach)
        self.assertGreater(moved, 0)

    def test_beatable_many(self):
        for i in range(20):
            r = self._all(seed=f'B{i}')
            self.assertTrue(self.world.can_beat(self._fixed(r)), f'seed {i}')

    def test_fountains_never_get_forbidden(self):
        skulltulas, gs_map = _gs_data()
        for i in range(20):
            r = place_all(self.chests, self.loc_map, self.world,
                          Settings(seed=f'T{i}', tokensanity='all'), skulltulas, gs_map)
            self.assertFalse(set(r.fairies.values()) & self.forbidden, f'seed {i}')

    def test_excluded_reward_stays(self):
        r = self._all(seed='X', excluded_items=frozenset({'Item_DinFire'}))
        self.assertEqual(r.fairies['DMT Great Fairy Reward'], 'Item_DinFire')

    def test_vanilla_keys_no_fountains(self):
        for songs in ('off', 'song_locations'):
            r = self._all(seed='V', key_items_mode='vanilla', shuffle_songs=songs)
            self.assertEqual(r.fairies, {})
            self.assertEqual(set(r.chests), set(self.orig))

    def test_with_songs_anywhere_and_dungeon_rewards(self):
        for songs in ('anywhere', 'dungeon_rewards'):
            r = self._all(seed='S', shuffle_songs=songs)
            self.assertEqual(set(r.fairies), set(self.vanilla))
            self.assertEqual(len(r.songs), 12)
            self.assertTrue(all(h >= 0 for h in r.chests))
            self.assertEqual(sum(d in SONG_BY_ACTOR for d in r.chests.values())
                             + sum(d in SONG_BY_ACTOR for d in r.songs.values())
                             + sum(d in SONG_BY_ACTOR for d in r.hearts.values())
                             + sum(d in SONG_BY_ACTOR for d in r.fairies.values())
                             + sum(d in SONG_BY_ACTOR for d in r.gifts.values()), 12)


class GiftFillTest(unittest.TestCase):
    """NPC gifts batch 1 in the pool (design 2026-11-20-npc-gifts-batch-1): with key items
    shuffled, the 14 gifts are sites and their items move."""
    def setUp(self):
        from randomizer.gifts import GIFT_FORBIDDEN, WorldGift, active_gifts
        self.forbidden = GIFT_FORBIDDEN
        active = active_gifts(Settings('x'))  # the defaults: batch 3a's switches off
        self.world_locs = {g.location for g in active if isinstance(g, WorldGift)}
        self.vanilla = {g.location: g.content for g in active}
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)

    def _all(self, skulltulas=(), gs_map=None, world_forbidden=frozenset(), **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw),
                         skulltulas, gs_map, world_forbidden=world_forbidden)

    def _fixed(self, r):
        return _fixed_for(r.chests, self.chests, self.loc_map, self.world,
                          {**r.fairies, **r.gifts})

    def test_gifts_are_sites(self):
        from randomizer.fairies import FOUNTAINS
        r = self._all(seed='G')
        self.assertEqual(set(r.gifts), set(self.vanilla))
        self.assertEqual(Counter(r.chests.values()) + Counter(r.fairies.values())
                         + Counter(r.gifts.values()),
                         Counter(self.orig.values()) + _fairy_rewards()
                         + Counter(self.vanilla.values()))
        self.assertEqual(len(FOUNTAINS), len(r.fairies))
        self.assertEqual(r, self._all(seed='G'))

    def test_gift_items_move(self):
        moved = sum(any(self._all(seed=f'M{i}').gifts[loc] != c
                        for loc, c in self.vanilla.items()) for i in range(5))
        self.assertGreater(moved, 0)

    def test_beatable_many(self):
        for i in range(20):
            r = self._all(seed=f'B{i}')
            self.assertTrue(self.world.can_beat(self._fixed(r)), f'seed {i}')

    def test_gift_forbidden(self):
        skulltulas, gs_map = _gs_data()
        unwrappable = frozenset({'Item_Hammer'})
        for i in range(20):
            r = self._all(skulltulas, gs_map, unwrappable, seed=f'T{i}', tokensanity='all')
            for loc, drop in r.gifts.items():
                bad = (unwrappable | {TOKEN}) if loc in self.world_locs else self.forbidden
                self.assertNotIn(drop, bad, f'seed {i}: {loc}')

    def test_ammo_never_on_forbidden_gift(self):
        # Generation: filler ammo goes to sites gated by its container in its own loop; it
        # must not land on a world gift that cannot wrap it (a Bombchu bundle did).
        ammo = frozenset(AMMO_CONTAINER)
        for i in range(30):
            r = self._all(world_forbidden=ammo, seed=f'A{i}')
            for loc in self.world_locs:
                self.assertNotIn(r.gifts[loc], ammo, f'seed {i}: {loc}')

    def test_excluded_gift_item_stays(self):
        r = self._all(seed='X', excluded_items=frozenset({'Item_ZeldaLetter'}))
        self.assertEqual(r.gifts['HC Zeldas Letter'], 'Item_ZeldaLetter')

    def test_vanilla_keys_no_gifts(self):
        for songs in ('off', 'song_locations'):
            r = self._all(seed='V', key_items_mode='vanilla', shuffle_songs=songs)
            self.assertEqual(r.gifts, {})
            self.assertEqual(set(r.chests), set(self.orig))

    def test_with_songs_and_tokens(self):
        skulltulas, gs_map = _gs_data()
        for songs in ('anywhere', 'dungeon_rewards'):
            r = self._all(skulltulas, gs_map, seed='S', shuffle_songs=songs, tokensanity='all')
            self.assertEqual(set(r.gifts), set(self.vanilla))
            self.assertTrue(all(h >= 0 for h in r.chests))


class Batch3aFillTest(unittest.TestCase):
    """NPC gifts batch 3a (design 2026-11-21-npc-gifts-batch-3a): the switches add their
    gifts as sites; the Gerudo Card's site only takes minor items."""
    SWITCHES = {'shuffle_ocarinas': ('LW Gift from Saria', 'HF Ocarina of Time Item'),
                'shuffle_expensive_merchants': ('GC Medigoron', 'Wasteland Bombchu Salesman'),
                'shuffle_gerudo_card': ('Hideout Gerudo Membership Card',)}
    CARD = 'Hideout Gerudo Membership Card'

    def setUp(self):
        self.chests, self.loc_map, self.world = _data()

    def _all(self, skulltulas=(), gs_map=None, **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw),
                         skulltulas, gs_map)

    def _beatable(self, r):
        return self.world.can_beat(_fixed_for(r.chests, self.chests, self.loc_map, self.world,
                                              {**r.fairies, **r.gifts}))

    def test_off_has_kak_100_only(self):
        r = self._all(seed='O')
        self.assertIn('Kak 100 Gold Skulltula Reward', r.gifts)
        for locs in self.SWITCHES.values():
            for loc in locs:
                self.assertNotIn(loc, r.gifts)

    def test_each_switch_adds_its_sites_and_stays_beatable(self):
        from randomizer.gifts import GIFT_FORBIDDEN
        for name, locs in self.SWITCHES.items():
            for i in range(20):
                with self.subTest(setting=name, seed=i):
                    r = self._all(seed=f'{name}{i}', **{name: True})
                    for loc in locs:
                        self.assertIn(loc, r.gifts)
                        self.assertNotIn(r.gifts[loc], GIFT_FORBIDDEN)
                    self.assertTrue(self._beatable(r))

    def test_card_site_takes_minor_items_only(self):
        from randomizer.songs import SONG_BY_ACTOR
        for i in range(20):
            r = self._all(seed=f'C{i}', shuffle_gerudo_card=True, shuffle_songs='anywhere')
            drop = r.gifts[self.CARD]
            self.assertNotIn(drop, items.KEY_ITEMS, i)
            self.assertNotIn(drop, SONG_BY_ACTOR, i)

    def test_all_switches_with_tokens(self):
        skulltulas, gs_map = _gs_data()
        on = dict.fromkeys(self.SWITCHES, True)
        gs = gs_sites(skulltulas, gs_map, 'all')
        for i in range(20):
            r = self._all(skulltulas, gs_map, seed=f'K{i}', tokensanity='all', **on)
            self.assertEqual(len([loc for locs in self.SWITCHES.values() for loc in locs
                                  if loc in r.gifts]), 5)
            fixed = _fixed_for({}, [], {}, self.world, {**r.fairies, **r.gifts})
            sites = ([(h, self.loc_map[h].location)
                      for h in _eligible_hashes(self.chests, self.loc_map)]
                     + [(h, gs_map[h].location) for h in gs])
            for h, loc in sites:
                drop = r.chests[h]
                fixed[loc] = (drop if drop in items.KEY_ITEMS
                              else OOTR_TOKEN if drop == TOKEN else 'Rupees (5)')
            self.assertTrue(self.world.can_beat(fixed), i)

    def test_excluded_ocarina(self):
        r = self._all(seed='E', shuffle_ocarinas=True,
                      excluded_items=frozenset({'Item_Ocarina_Time'}))
        self.assertEqual(r.gifts['HF Ocarina of Time Item'], 'Item_Ocarina_Time')
        off = self._all(seed='E', excluded_items=frozenset({'Item_Ocarina_Time'}))
        self.assertNotIn('HF Ocarina of Time Item', off.gifts)


class ScaleOrderTest(unittest.TestCase):
    """NPC gifts batch 2 (design 2026-11-21): a Silver Scale after the Golden one lowers
    the dive depth (test batch 29a2), so the Golden one only goes where the Silver one is
    needed; bombchus need any of the three bomb bags; upgrades never go to a song scene."""
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()

    def _all(self, skulltulas=(), gs_map=None, **kw):
        return place_all(self.chests, self.loc_map, self.world, Settings(**kw),
                         skulltulas, gs_map)

    def _where(self, r) -> dict[str, list[str]]:
        """Content -> OoTR locations holding it (chests, fountains, gifts, songs)."""
        out: dict[str, list[str]] = {}
        for h, drop in r.chests.items():
            if h in self.loc_map and self.loc_map[h].location:
                out.setdefault(drop, []).append(self.loc_map[h].location)
        for loc, drop in {**r.fairies, **r.gifts, **r.songs, **r.hearts}.items():
            out.setdefault(drop, []).append(loc)
        return out

    def _fixed(self, r):
        return _fixed_for(r.chests, self.chests, self.loc_map, self.world,
                          {**r.fairies, **r.gifts})

    def test_gold_needs_silver(self):
        for i in range(30):
            r = self._all(seed=f'S{i}')
            where = self._where(r)
            [gold], [silver] = where['Item_Scale_Gold'], where['Item_Scale_Silver']
            fixed = self._fixed(r)
            fixed[silver] = 'Rupees (5)'
            self.assertNotIn(gold, self.world.reachable_locations(fixed), f'seed {i}')

    def test_gold_needs_silver_with_dungeon_rewards(self):
        for i in range(5):
            r = self._all(seed=f'R{i}', shuffle_songs='dungeon_rewards')
            where = self._where(r)
            [gold], [silver] = where['Item_Scale_Gold'], where['Item_Scale_Silver']
            fixed = self._fixed(r)
            for loc, drop in list(r.songs.items()) + list(r.hearts.items()):
                fixed[loc] = (SONG_BY_ACTOR[drop].song if drop in SONG_BY_ACTOR
                              else drop if drop in items.KEY_ITEMS else 'Rupees (5)')
            fixed[silver] = 'Rupees (5)'
            self.assertNotIn(gold, self.world.reachable_locations(fixed), f'seed {i}')

    def test_excluding_one_scale_excludes_both(self):
        for scale in ('Item_Scale_Gold', 'Item_Scale_Silver'):
            r = self._all(seed='X', excluded_items=frozenset({scale}))
            self.assertEqual(r.gifts['LH Adult Fishing'], 'Item_Scale_Gold')
            self.assertEqual(r.gifts['ZD Diving Minigame'], 'Item_Scale_Silver')

    def test_bombchus_need_any_bag(self):
        for i in range(15):
            r = self._all(seed=f'C{i}')
            fixed = self._fixed(r)
            for loc, item in list(fixed.items()):
                if items.KEY_ITEMS.get(item, item) == 'Bomb Bag':
                    fixed[loc] = 'Rupees (5)'
            reach = self.world.reachable_locations(fixed)
            where = self._where(r)
            for chu in ('Item_BombchuBundle_Small', 'Item_BombchuBundle_Large'):
                for loc in where.get(chu, []):
                    self.assertNotIn(loc, reach, f'seed {i}: {chu} at {loc}')

    def test_upgrades_avoid_song_scenes(self):
        for i in range(10):
            r = self._all(seed=f'U{i}', shuffle_songs='anywhere')
            for loc, drop in r.songs.items():
                self.assertNotIn(drop, items.UPGRADES, f'seed {i}: {loc}')


REWARD_CHESTS = ('Gerudo Training Ground Maze Path Final Chest',
                 'Bottom of the Well Lens of Truth Chest')
REWARD_SCENES = ('Song from Impa', 'Sheik in Ice Cavern')


class DungeonRewardsFillTest(unittest.TestCase):
    def setUp(self):
        self.chests, self.loc_map, self.world = _data()
        self.orig = _original(self.chests)
        self.by_loc = {e.location: h for h, e in self.loc_map.items() if e.location}

    def _all(self, **kw):
        return place_all(self.chests, self.loc_map, self.world,
                         Settings(shuffle_songs='dungeon_rewards', **kw))

    def _fixed(self, r):
        fixed = _fixed_for(r.chests, self.chests, self.loc_map, self.world, {**r.fairies, **r.gifts})
        for h, drop in r.chests.items():
            if drop in SONG_BY_ACTOR and h in self.loc_map and self.loc_map[h].location:
                fixed[self.loc_map[h].location] = SONG_BY_ACTOR[drop].song
        for loc, drop in list(r.songs.items()) + list(r.hearts.items()):
            fixed[loc] = (SONG_BY_ACTOR[drop].song if drop in SONG_BY_ACTOR
                          else drop if drop in items.KEY_ITEMS else 'Rupees (5)')
        return fixed

    def test_songs_only_on_reward_sites(self):
        for i in range(10):
            r = self._all(seed=f'D{i}')
            self.assertEqual(set(r.hearts), set(BOSS_HEARTS.values()))
            self.assertTrue(all(a in SONG_BY_ACTOR for a in r.hearts.values()))
            for loc in REWARD_SCENES:
                self.assertIn(r.songs[loc], SONG_BY_ACTOR)
            for loc in REWARD_CHESTS:
                self.assertIn(r.chests[self.by_loc[loc]], SONG_BY_ACTOR)
            others = [a for loc, a in r.songs.items() if loc not in REWARD_SCENES]
            others += [d for h, d in r.chests.items()
                       if self.loc_map.get(h) is None or self.loc_map[h].location not in REWARD_CHESTS]
            self.assertFalse([a for a in others if a in SONG_BY_ACTOR], f'seed {i}')

    def test_multiset_and_hearts_moved(self):
        r = self._all(seed='M')
        got = (Counter(r.chests.values()) + Counter(r.songs.values())
               + Counter(r.hearts.values()) + Counter(r.fairies.values()) + Counter(r.gifts.values()))
        want = (Counter(self.orig.values()) + Counter(VANILLA_SONGS.values())
                + Counter({'Obj_Heart_Container': 8}) + _scene_items())
        self.assertEqual(got, want)
        self.assertEqual(r, self._all(seed='M'))

    def test_beatable_many(self):
        for i in range(20):
            self.assertTrue(self.world.can_beat(self._fixed(self._all(seed=f'B{i}'))), i)

    def test_vanilla_keys_raises(self):
        with self.assertRaisesRegex(FillError, 'needs key items shuffled'):
            self._all(seed='V', key_items_mode='vanilla')

    def test_excluding_a_reward_chest_item_raises(self):
        # Their chests are dungeon-reward sites and always get a song (review).
        for item in ('Item_GlassTruth', 'Item_Arrow_Ice'):
            with self.assertRaisesRegex(FillError, 'Dungeon Rewards'):
                self._all(seed='X', excluded_items=frozenset({item}))

    def test_other_modes_have_no_hearts(self):
        for mode in ('off', 'song_locations', 'anywhere'):
            r = place_all(self.chests, self.loc_map, self.world,
                          Settings(seed='H', shuffle_songs=mode))
            self.assertEqual(r.hearts, {}, mode)


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

    def PA(self, seed, mode, forbidden=frozenset()):
        return place_all(self.chests, self.loc_map, self.world,
                         Settings(seed=seed, tokensanity=mode), self.skulltulas,
                         self.gs_map, forbidden)

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
                    if items.KEY_ITEMS.get(item, item) == container:  # any bag of it
                        without[other] = 'Rupees (5)'
                reach = self.world.reachable_locations(without, owned=[OOTR_TOKEN] * 100)
                self.assertNotIn(loc, reach, (seed, r[h], loc))
                checked += 1
            self.assertGreater(checked, 0, seed)

    def test_tokensanity_off_identical(self):
        self.assertEqual(self._place(seed='ABC'), self.P('ABC', 'off'))

    def test_tokensanity_all_places_gs(self):
        pa = self.PA('T', 'all')
        r = pa.chests
        gs = self._gs('all')
        self.assertEqual(len(gs), 100)
        self.assertTrue(set(gs) <= set(r))
        self.assertEqual(set(r), set(self.orig) | set(gs))
        self.assertEqual(sum(1 for v in r.values() if v == TOKEN)
                         + sum(1 for v in pa.fairies.values() if v == TOKEN)
                         + sum(1 for v in pa.gifts.values() if v == TOKEN), 100)
        self.assertTrue(any(r[h] != TOKEN for h in gs))
        self.assertTrue(any(v == TOKEN for h, v in r.items() if h not in gs))
        expected = Counter(self.orig.values()) + Counter({TOKEN: 100}) + _scene_items()
        self.assertEqual(Counter(r.values()) + Counter(pa.fairies.values()) + Counter(pa.gifts.values()), expected)

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
        pa = self.PA('F', 'all', forbidden)
        r = pa.chests
        for h in self._gs('all'):
            self.assertNotIn(r[h], forbidden)
        # Forbidden contents are still in the fill (in chests or fountains).
        self.assertEqual(Counter(r.values()) + Counter(pa.fairies.values()) + Counter(pa.gifts.values()),
                         Counter(self.orig.values()) + Counter({TOKEN: 100}) + _scene_items())

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
            pa = self.PA(f'C{i}', 'all')
            r = pa.chests
            fixed = _fixed_for({}, [], {}, self.world, {**pa.fairies, **pa.gifts})
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
