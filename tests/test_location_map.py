import json
import unittest
from pathlib import Path

from randomizer import items, locations
from randomizer.game import load_chests_fixture
from randomizer.logic.ootr_data import load_locations

FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'

KEY_ITEM_LOCATIONS = {
    16757992849254467386: 'KF Kokiri Sword Chest',
    821372075822700622: 'Deku Tree Slingshot Chest',
    12161709650443144121: 'Dodongos Cavern Bomb Bag Chest',
    5527401621172639818: 'Jabu Jabus Belly Boomerang Chest',
    11082303891540711688: 'Forest Temple Bow Chest',
    12083259659219538030: 'Fire Temple Megaton Hammer Chest',
    18059711820131847165: 'Water Temple Longshot Chest',
    14535080241831873137: 'Shadow Temple Hover Boots Chest',
    6859289214373847284: 'Ice Cavern Iron Boots Chest',
    16654774376625985726: 'Bottom of the Well Lens of Truth Chest',
    2490063409521505179: 'Spirit Temple Silver Gauntlets Chest',
    10012167258643363548: 'Spirit Temple Mirror Shield Chest',
    16041366920820397198: 'Graveyard Dampe Race Hookshot Chest',
    1941083939696166170: 'Gerudo Training Ground Maze Path Final Chest',
    17657623307936361670: 'Ganons Castle Shadow Trial Golden Gauntlets Chest',
}

# GATE results (docs/test-batch-1.md, Results section):
# - TestBatch1: the Kokiri Sword chest gave the green rupee, but its event
#   Get_StoneOfForest_GetSword still gave the sword.
# - TestBatch3: removing GetEventName from that chest gave the Boomerang and not the sword.
# So key item chests whose event only hands over the item lose
# the event (STRIP_EVENT_HASHES). Those with an event with more effects
# (song, sage, Ruto, Dampe race) need an event patch and stay
# vanilla (EVENT_PATCH_HASHES).
STRIP_EVENT_HASHES: set[int] = {
    16757992849254467386,  # Kokiri Sword
    821372075822700622,    # Slingshot
    11082303891540711688,  # Bow
    12083259659219538030,  # Hammer
    16654774376625985726,  # Lens of Truth
    1941083939696166170,   # Ice Arrows
    17657623307936361670,  # Golden Gauntlets
    18059711820131847165,  # Longshot
    12161709650443144121,  # Bomb Bag (batch 19: bombs need the Goron's Bracelet)
}
EVENT_PATCH_HASHES: set[int] = {
    6859289214373847284,   # Iron Boots (SageOfWater_MelodyGet_Water)
    2490063409521505179,   # Silver Gauntlets
    10012167258643363548,  # Mirror Shield
    14535080241831873137,  # Hover Boots
    16041366920820397198,  # Hookshot (Dampe race)
    5527401621172639818,   # Boomerang (Ruto)
}


# Homes of the NPC gift items (design 2026-11-20); Item_Bottle's is Anju's.
NPC_GIFT_HOMES = {
    'GC Darunias Joy', 'HC Zeldas Letter', 'HC Malon Egg', 'ToT Light Arrows Cutscene',
    'LH Sun', 'GC Rolling Goron as Child', 'GC Rolling Goron as Adult', 'ZD King Zora Thawed',
    'Kak Anju as Child', 'LH Underwater Item',
    # batch 2 (design 2026-11-21)
    'Kak 10 Gold Skulltula Reward', 'Kak 20 Gold Skulltula Reward',
    'Kak 30 Gold Skulltula Reward', 'Market Bombchu Bowling First Prize',
    'ZD Diving Minigame', 'LH Adult Fishing', 'LLR Talons Chickens',
    # batch 3a (design 2026-11-21-npc-gifts-batch-3a): Shuffle Ocarinas
    'LW Gift from Saria', 'HF Ocarina of Time Item',
    # OoTR parity (design 2026-11-22): the adult trade's first item
    'Kak Anju as Adult'}


class LocationMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = locations.load_map()
        cls.ootr = load_locations()

    def test_map_covers_all_hashes(self):
        hashes = {c.hash for c in load_chests_fixture(FIXTURE)}
        self.assertEqual(len(hashes), 203)
        self.assertEqual(set(self.map), hashes)

    def test_key_item_hashes_mapped(self):
        for h, name in KEY_ITEM_LOCATIONS.items():
            e = self.map[h]
            self.assertNotEqual(e.status, 'unmapped', h)
            self.assertEqual(e.location, name, h)

    def test_no_duplicate_locations(self):
        locs = [e.location for e in self.map.values() if e.location]
        self.assertEqual(len(locs), len(set(locs)))

    def test_mapped_locations_are_chests(self):
        for e in self.map.values():
            if e.location is not None:
                self.assertIn(e.location, self.ootr, e.hash)
                self.assertEqual(self.ootr[e.location]['type'], 'Chest', e.location)

    def test_needs_event_patch_from_batch(self):
        # OoTR parity design: these six move and keep their story event (batch 33a/33b).
        self.assertEqual({h for h, e in self.map.items() if e.needs_event_patch}, set())
        for h in EVENT_PATCH_HASHES:
            self.assertFalse(self.map[h].strip_event, h)

    def test_strip_event_from_batch(self):
        got = {h for h, e in self.map.items() if e.strip_event}
        self.assertEqual(got, STRIP_EVENT_HASHES)
        self.assertFalse(STRIP_EVENT_HASHES & EVENT_PATCH_HASHES)
        self.assertLessEqual(STRIP_EVENT_HASHES | EVENT_PATCH_HASHES,
                             set(KEY_ITEM_LOCATIONS))

    def test_strip_event_explicit_in_json(self):
        raw = json.loads(locations.MAP_PATH.read_text(encoding='utf-8'))
        for h, e in raw.items():
            self.assertIsInstance(e.get('strip_event'), bool, h)

    def test_strip_event_defaults_false(self):
        e = locations.LocationEntry(1, None, 'unmapped', False)
        self.assertFalse(e.strip_event)

    def test_status_consistent(self):
        for e in self.map.values():
            self.assertIn(e.status, ('auto', 'manual', 'unmapped'))
            self.assertEqual(e.location is None, e.status == 'unmapped', e.hash)

    def test_file_is_deterministic(self):
        raw = locations.MAP_PATH.read_text(encoding='utf-8')
        data = json.loads(raw)
        again = json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + '\n'
        self.assertEqual(raw, again)


class ItemsTest(unittest.TestCase):
    def test_key_items(self):
        # 15 from chests, the six Great Fairy rewards (design 2026-11-15) and the ten
        # NPC gift items of batch 1 (design 2026-11-20) and the seven of batch 2
        # (design 2026-11-21), the two ocarinas of batch 3a and the Pocket Egg (OoTR parity).
        self.assertEqual(len(items.KEY_ITEMS), 41)
        self.assertEqual(items.KEY_ITEMS['Item_PocketEgg'], 'Pocket Egg')
        self.assertEqual(items.KEY_ITEMS['Item_Ocarina_Fairy'], 'Ocarina')
        self.assertEqual(items.KEY_ITEMS['Item_Ocarina_Time'], 'Ocarina')
        self.assertEqual(items.KEY_ITEMS['Item_Scale_Gold'], 'Progressive Scale')
        self.assertEqual(items.KEY_ITEMS['Item_Wallet_Large'], 'Progressive Wallet')
        self.assertEqual(items.KEY_ITEMS['Item_Bottle_Milk'], 'Bottle with Milk')
        self.assertEqual(items.KEY_ITEMS['Item_Gauntlet_Goron'], 'Progressive Strength Upgrade')
        self.assertEqual(items.KEY_ITEMS['Item_Bottle_Letter'], 'Rutos Letter')
        self.assertEqual(items.KEY_ITEMS['Item_Longshot'], 'Progressive Hookshot')
        self.assertEqual(items.KEY_ITEMS['Item_BombBag_Small'], 'Bomb Bag')
        self.assertEqual(set(items.LABELS), set(items.KEY_ITEMS))
        self.assertEqual(items.LABELS['Item_GlassTruth'], 'Lens of Truth')

    def test_item_level(self):
        self.assertEqual(items.ITEM_LEVEL['Item_Longshot'], ('Progressive Hookshot', 2))
        self.assertEqual(items.ITEM_LEVEL['Item_Gauntlet_Goron'],
                         ('Progressive Strength Upgrade', 1))
        self.assertEqual(items.ITEM_LEVEL['Item_Gauntlet_Gold'],
                         ('Progressive Strength Upgrade', 3))
        self.assertEqual(items.ITEM_LEVEL['Item_Scale_Gold'], ('Progressive Scale', 2))
        self.assertEqual(items.ITEM_LEVEL['Item_Wallet_Medium'], ('Progressive Wallet', 1))

    def test_batch_2_homes_hold_their_items(self):
        from randomizer.logic import ootr_data
        locs = ootr_data.load_locations()
        for actor in ('Item_Wallet_Medium', 'Item_Wallet_Large', 'Item_AgonyStone',
                      'Item_BombBag_Large', 'Item_Scale_Silver', 'Item_Scale_Gold',
                      'Item_Bottle_Milk'):
            with self.subTest(actor=actor):
                home = items.KEY_ITEM_HOME[actor]
                self.assertEqual(locs[home]['vanilla_item'], items.KEY_ITEMS[actor])

    def test_upgrades_are_minor(self):
        self.assertEqual(items.UPGRADES, frozenset({
            'Item_BulletBag_Medium', 'Item_BulletBag_Large',
            'Item_Quiver_Medium', 'Item_Quiver_Large'}))
        self.assertFalse(items.UPGRADES & set(items.KEY_ITEMS))
        self.assertTrue(items.content_matches('Item_BulletBag_Medium', 'Slingshot'))
        self.assertTrue(items.content_matches('Item_Quiver_Large', 'Bow'))
        self.assertTrue(items.content_matches('Item_BombchuBundle_Large', 'Bombchus (10)'))

    def test_batch_3a_homes_and_contents(self):
        from randomizer.logic import ootr_data
        locs = ootr_data.load_locations()
        for actor in ('Item_Ocarina_Fairy', 'Item_Ocarina_Time'):
            with self.subTest(actor=actor):
                self.assertEqual(locs[items.KEY_ITEM_HOME[actor]]['vanilla_item'], 'Ocarina')
        self.assertEqual(items.ITEM_LEVEL['Item_Ocarina_Fairy'], ('Ocarina', 1))
        self.assertEqual(items.ITEM_LEVEL['Item_Ocarina_Time'], ('Ocarina', 2))
        for content, location in (('Shop_Sword_Giant', 'GC Medigoron'),
                                  ('Shop_BombchuBundle_01', 'Wasteland Bombchu Salesman'),
                                  ('Obj_Rupee_Gold', 'Kak 100 Gold Skulltula Reward'),
                                  ('Item_Token_Gerudo', 'Hideout Gerudo Membership Card')):
            with self.subTest(content=content):
                self.assertNotIn(content, items.KEY_ITEMS)
                self.assertTrue(items.content_matches(content, locs[location]['vanilla_item']))

    def test_key_item_home(self):
        self.assertEqual(set(items.KEY_ITEM_HOME), set(items.KEY_ITEMS))
        from randomizer.fairies import FOUNTAINS
        self.assertEqual(set(items.KEY_ITEM_HOME.values()),
                         set(KEY_ITEM_LOCATIONS.values()) | {f.location for f in FOUNTAINS}
                         | NPC_GIFT_HOMES)
        self.assertEqual(items.KEY_ITEM_HOME['Item_Longshot'],
                         'Water Temple Longshot Chest')

    def test_key_item_home_matches_fixture(self):
        drops = {c.hash: c.drop for c in load_chests_fixture(FIXTURE)}
        for h, name in KEY_ITEM_LOCATIONS.items():
            self.assertEqual(items.KEY_ITEM_HOME[drops[h]], name)

    def test_dungeon_prefixes(self):
        self.assertEqual(items.DUNGEON_ITEM_PREFIXES,
                         ('Item_Dungeon_', 'Obj_MiniGame_SmallKey', 'Obj_Dungeon_SmallKey_'))


if __name__ == '__main__':
    unittest.main()
