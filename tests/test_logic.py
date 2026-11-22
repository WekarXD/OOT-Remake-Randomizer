import time
import unittest

from randomizer.items import KEY_ITEM_HOME
from randomizer.logic import ootr_data, rules, world
from randomizer.logic.rules import RuleError, State, compile_rule
from randomizer.logic.world import World


def _vanilla_world():
    if not hasattr(_vanilla_world, 'cached'):
        _vanilla_world.cached = World(world.load_vanilla_settings())
    return _vanilla_world.cached


class RuleCompileTest(unittest.TestCase):
    def test_all_rules_compile(self):
        helpers = ootr_data.load_helpers()
        settings = world.load_vanilla_settings()
        compiler = rules.Compiler(helpers, settings)
        count = 0
        for stem, regions in ootr_data.load_world_files().items():
            for region in regions:
                for key in ('events', 'locations', 'exits'):
                    for name, rule in (region.get(key) or {}).items():
                        with self.subTest(file=stem, spot=name):
                            fn = compiler.compile(rule, region=region['region_name'])
                            self.assertTrue(callable(fn))
                            count += 1
        compiler.compile_pending_subrules()
        self.assertGreater(count, 2000)

    def test_unknown_identifier_raises(self):
        with self.assertRaises(RuleError):
            compile_rule('Foo_Bar_Baz', {}, {})

    def test_unknown_string_event_raises(self):
        with self.assertRaises(RuleError):
            compile_rule("'Foo Bar Baz'", {}, {})

    def test_unknown_function_raises(self):
        with self.assertRaises(RuleError):
            compile_rule('frobnicate(Bow)', {}, {})

    def test_basic_semantics(self):
        rule = compile_rule('Kokiri_Sword and (Progressive_Hookshot, 2)', {}, {})
        s = State()
        self.assertFalse(rule(s, 'child'))
        s.collect('Kokiri Sword')
        s.collect('Item_Longshot')
        self.assertTrue(rule(s, 'child'))
        age_rule = compile_rule('is_adult', {'is_adult': "age == 'adult'"}, {})
        self.assertTrue(age_rule(s, 'adult'))
        self.assertFalse(age_rule(s, 'child'))
        setting_rule = compile_rule("open_forest == 'closed'", {}, {'open_forest': 'closed'})
        self.assertTrue(setting_rule(s, 'child'))

    def test_helper_with_parameter(self):
        helpers = {'can_use(item)': '(item == Bow and is_adult and item)',
                   'is_adult': "age == 'adult'"}
        rule = compile_rule('can_use(Bow)', helpers, {})
        s = State()
        s.collect('Bow')
        self.assertTrue(rule(s, 'adult'))
        self.assertFalse(rule(s, 'child'))
        self.assertFalse(compile_rule('can_use(Slingshot)', helpers, {})(s, 'adult'))


class StateTest(unittest.TestCase):
    def test_longshot_alone_counts_as_hookshot(self):
        s = State()
        s.collect('Item_Longshot')
        self.assertTrue(s.has('Progressive Hookshot', 1))
        self.assertTrue(s.has('Progressive Hookshot', 2))

    def test_hookshot_alone_is_not_longshot(self):
        s = State()
        s.collect('Item_Hookshot')
        self.assertTrue(s.has('Progressive Hookshot', 1))
        self.assertFalse(s.has('Progressive Hookshot', 2))

    def test_bracelet_after_silver_does_not_upgrade(self):
        s = State()
        s.collect('Item_Gauntlet_Silver')
        s.collect('Progressive Strength Upgrade')
        self.assertTrue(s.has('Progressive Strength Upgrade', 2))
        self.assertFalse(s.has('Progressive Strength Upgrade', 3))

    def test_bracelet_is_strength_one(self):
        # NPC gifts batch 1: the Goron's Bracelet moves; it is strength level 1, and a
        # later Silver Gauntlets raise it (batch 28c: any level lifts and throws bombs).
        s = State()
        s.collect('Item_Gauntlet_Goron')
        self.assertTrue(s.has('Progressive Strength Upgrade', 1))
        self.assertFalse(s.has('Progressive Strength Upgrade', 2))
        s.collect('Item_Gauntlet_Silver')
        self.assertTrue(s.has('Progressive Strength Upgrade', 2))

    def test_scale_levels(self):
        # NPC gifts batch 2: the direct model holds the highest scale (the fill keeps
        # the Silver Scale before the Golden one, test batch 29a2).
        s = State()
        s.collect('Item_Scale_Gold')
        self.assertTrue(s.has('Progressive Scale', 2))
        s.collect('Item_Scale_Silver')
        self.assertEqual(s.items['Progressive Scale'], 2)

    def test_wallet_levels(self):
        # Test batch 29a: a smaller wallet after a bigger one keeps the capacity.
        s = State()
        s.collect('Item_Wallet_Large')
        s.collect('Item_Wallet_Medium')
        self.assertEqual(s.items['Progressive Wallet'], 2)

    def test_ocarina_levels(self):
        # NPC gifts batch 3a: the two ocarinas are separate items in the game (31c); the
        # direct model holds the highest, so the Ocarina of Time alone counts as both.
        s = State()
        s.collect('Item_Ocarina_Time')
        self.assertEqual(s.items['Ocarina'], 2)
        s.collect('Item_Ocarina_Fairy')
        self.assertEqual(s.items['Ocarina'], 2)

    def test_unknown_item_raises(self):
        with self.assertRaises(KeyError):
            State().collect('Not An Item')


# Vanilla with four key items swapped: OoTR's key logic (worst case) does not
# accept the vanilla placement of the Water Temple or the Spirit Temple, but
# it does accept this one, so it serves as a base for the negative cases.
LOGIC_BASELINE_SWAPS = {
    'Graveyard Dampe Race Hookshot Chest': 'Item_Longshot',
    'Water Temple Longshot Chest': 'Item_Hookshot',
    'Shadow Temple Hover Boots Chest': 'Item_Gauntlet_Silver',
    'Spirit Temple Silver Gauntlets Chest': 'Item_HoverBoot',
}


def _baseline_fixed():
    fixed = _vanilla_world().vanilla_fixed()
    fixed.update(LOGIC_BASELINE_SWAPS)
    return fixed


class ReachabilityTest(unittest.TestCase):
    @unittest.expectedFailure
    def test_vanilla_is_beatable(self):
        # Fails by OoTR's design: its key logic counts the worst door-opening
        # order, and with the keys and items in their vanilla spots it
        # requires 5 Water Temple keys before the Longshot (only 4 without it) and
        # 3 Spirit Temple keys as a child for the Silver Gauntlets (only 2).
        # Ver test_vanilla_blocked_only_by_key_logic.
        w = _vanilla_world()
        self.assertTrue(w.can_beat(w.vanilla_fixed()))

    def test_vanilla_blocked_only_by_key_logic(self):
        settings = world.load_vanilla_settings()
        w = World(settings)
        fixed = w.vanilla_fixed()
        self.assertFalse(w.can_beat(fixed))
        w.starting_items = w.starting_items + ['Small Key (Water Temple)',
                                               'Small Key (Spirit Temple)']
        self.assertTrue(w.can_beat(fixed))

    def test_baseline_is_beatable(self):
        self.assertTrue(_vanilla_world().can_beat(_baseline_fixed()))

    def test_vanilla_fixed_uses_remake_actors(self):
        fixed = _vanilla_world().vanilla_fixed()
        self.assertEqual(fixed['Water Temple Longshot Chest'], 'Item_Longshot')
        self.assertEqual(fixed['KF Kokiri Sword Chest'], 'Item_Sword_Kokiri')
        self.assertEqual(fixed['Ganon'], 'Triforce')

    def test_no_sword_not_beatable(self):
        fixed = _baseline_fixed()
        fixed['KF Kokiri Sword Chest'] = 'Rupees (5)'
        self.assertFalse(_vanilla_world().can_beat(fixed))

    def test_slingshot_gates_deku(self):
        w = _vanilla_world()
        fixed = w.vanilla_fixed()
        fixed['Deku Tree Slingshot Chest'] = 'Rupees (5)'
        reach = w.reachable_locations(fixed)
        self.assertNotIn('Deku Tree Queen Gohma Heart', reach)
        self.assertIn('KF Kokiri Sword Chest', reach)
        self.assertIn('Deku Tree Queen Gohma Heart',
                      w.reachable_locations(w.vanilla_fixed()))

    def test_remake_rules_target_existing_spots(self):
        w = _vanilla_world()
        for region, kind, spot in world.REMAKE_RULES:
            spots = [s for s, _ in getattr(w.regions[region], kind)]
            self.assertIn(spot, spots, (region, kind))

    def test_deku_upper_floor_needs_ranged_weapon(self):
        # Remake: to climb to the floor of the compass room you have to kill
        # the vine Skulltulas (batch 17: the Slingshot in the side chest
        # of the compass room left the game softlocked).
        w = _vanilla_world()
        fixed = w.vanilla_fixed()
        fixed['Deku Tree Slingshot Chest'], fixed['Deku Tree Compass Room Side Chest'] = (
            fixed['Deku Tree Compass Room Side Chest'], fixed['Deku Tree Slingshot Chest'])
        reach = w.reachable_locations(fixed)
        self.assertIn('Deku Tree Slingshot Chest', reach)
        for loc in ('Deku Tree Compass Room Side Chest', 'Deku Tree Compass Chest',
                    'Deku Tree GS Compass Room', 'Deku Tree Basement Chest'):
            self.assertNotIn(loc, reach)
        reach = w.reachable_locations(w.vanilla_fixed())
        for loc in ('Deku Tree Compass Room Side Chest', 'Deku Tree Compass Chest',
                    'Deku Tree GS Compass Room', 'Deku Tree Basement Chest'):
            self.assertIn(loc, reach)

    def test_baseline_reaches_all_key_chests(self):
        reach = _vanilla_world().reachable_locations(_baseline_fixed())
        for loc in list(KEY_ITEM_HOME.values()) + ['Ganon']:
            self.assertIn(loc, reach)

    def test_no_light_arrows_not_beatable(self):
        fixed = _baseline_fixed()
        fixed['ToT Light Arrows Cutscene'] = 'Rupees (5)'
        self.assertFalse(_vanilla_world().can_beat(fixed))

    def test_unknown_item_in_fixed_raises(self):
        fixed = _baseline_fixed()
        fixed['KF Kokiri Sword Chest'] = 'Not An Item'
        with self.assertRaises(KeyError):
            _vanilla_world().can_beat(fixed)

    def test_can_beat_is_fast(self):
        w = _vanilla_world()
        fixed = _baseline_fixed()
        start = time.perf_counter()
        for _ in range(20):
            self.assertTrue(w.can_beat(fixed))
        self.assertLess((time.perf_counter() - start) / 20, 0.1)


class BombBagTest(unittest.TestCase):
    # Batch 19: in the remake, bombs cannot be thrown until the Goron's
    # Bracelet is owned, wherever the Bomb Bag comes from.
    def _compiler(self):
        return rules.Compiler(world.load_helpers(), world.load_vanilla_settings())

    def test_bombs_need_bracelet(self):
        compiler = self._compiler()
        # has_bombchus also needs can_refill_bombchus; it reaches the bag
        # through Bomb_Bag, so checking that name covers it.
        for text in ('Bombs', 'Bomb_Bag'):
            with self.subTest(rule=text):
                fn = compiler.compile(text)
                s = State()
                s.collect('Bomb Bag')
                self.assertFalse(fn(s, 'child'))
                s.collect('Progressive Strength Upgrade')
                self.assertTrue(fn(s, 'child'))

    def test_no_count_check_on_bomb_bag(self):
        texts = list(ootr_data.load_helpers().values())
        for regions in ootr_data.load_world_files().values():
            for region in regions:
                for kind in ('events', 'locations', 'exits'):
                    texts.extend((region.get(kind) or {}).values())
        for text in texts:
            self.assertNotIn('(Bomb_Bag,', text.replace(' ', ''))

    def test_magic_meter_from_any_magic_item(self):
        # Batch 26: every spell and fairy magic reward brings the meter in the remake
        # (PouchActorInfo MPMaxUP), so OoTR's Magic_Meter accepts any of them.
        compiler = self._compiler()
        for text in ('Magic_Meter', 'can_use(Lens_of_Truth)'):
            fn = compiler.compile(text)
            for actor in ('Item_DinFire', 'Item_FaroreWind', 'Item_NayruLove',
                          'Item_FairyBless_MP', 'Item_FairyBless_MPDouble'):
                with self.subTest(rule=text, item=actor):
                    s = State()
                    s.collect(actor)
                    s.collect('Item_GlassTruth')
                    self.assertTrue(fn(s, 'child'))
            s = State()
            s.collect('Item_GlassTruth')
            self.assertFalse(fn(s, 'child'))

    def test_man_on_roof_needs_adult(self):
        # Only Npc_Hylia_001_Adult hands over the Piece of Heart (NPC gifts research).
        region = _vanilla_world().regions['Kak Odd Medicine Rooftop']
        fn = dict(region.locations)['Kak Man on Roof']
        self.assertFalse(fn(State(), 'child'))
        self.assertTrue(fn(State(), 'adult'))

    def test_lab_dive_needs_child(self):
        # Only Npc_Hylia_045_Child hands over the Piece of Heart (the adult's flow gives
        # the Eyedrops; NPC gifts batch 2 design).
        region = _vanilla_world().regions['LH Lab']
        fn = dict(region.locations)['LH Lab Dive']
        s = State()
        s.collect('Item_Scale_Silver')
        s.collect('Item_Scale_Gold')
        self.assertFalse(fn(s, 'adult'))
        self.assertTrue(fn(s, 'child'))

    def test_lh_sun_needs_water_temple(self):
        # Batch 28a: the remake's Fire Arrows quest depends on the Water Temple being done
        # (SageOfWater_IsAfter_Step08); OoTR's scarecrow path does not apply.
        region = _vanilla_world().regions['Lake Hylia']
        fn = dict(region.locations)['LH Sun']
        s = State()
        for item in ('Item_Range_Bow', 'Item_Longshot', 'Scarecrow Song', 'Ocarina',
                     'Ocarina A Button', 'Ocarina C up Button', 'Ocarina C down Button',
                     'Ocarina C left Button', 'Ocarina C right Button'):
            s.collect(item)
        self.assertFalse(fn(s, 'adult'))
        s.collect('Water Temple Clear')
        self.assertTrue(fn(s, 'adult'))

    def test_vanilla_fixed_has_remake_fairy_rewards(self):
        # The remake swaps two rewards against the N64 (batch 26): the castle fairy
        # gives the magic, the mountain one Din's Fire.
        fixed = _vanilla_world().vanilla_fixed()
        self.assertEqual(fixed['HC Great Fairy Reward'], 'Item_FairyBless_MP')
        self.assertEqual(fixed['DMT Great Fairy Reward'], 'Item_DinFire')
        self.assertEqual(fixed['DMC Great Fairy Reward'], 'Item_FairyBless_MPDouble')
        self.assertEqual(fixed['OGC Great Fairy Reward'], 'Item_FairyBless_DefenseDouble')

    def test_early_bag_needs_bracelet(self):
        # Bag in Mido's house: a bomb grotto stays out of reach until
        # Darunia hands over the bracelet.
        w = _vanilla_world()
        fixed = w.vanilla_fixed()
        fixed['KF Midos Top Left Chest'] = 'Item_BombBag_Small'
        fixed['Dodongos Cavern Bomb Bag Chest'] = 'Rupees (5)'
        self.assertIn('HF Southeast Grotto Chest', w.reachable_locations(fixed))
        fixed['GC Darunias Joy'] = 'Rupees (5)'
        self.assertNotIn('HF Southeast Grotto Chest', w.reachable_locations(fixed))


if __name__ == '__main__':
    unittest.main()
