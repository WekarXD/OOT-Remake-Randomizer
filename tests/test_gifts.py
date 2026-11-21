"""NPC gifts, batches 1 and 2 (designs docs/superpowers/specs/2026-11-20-npc-gifts-batch-1-design.md
and 2026-11-21-npc-gifts-batch-2-design.md; proven by test batches 27 to 30)."""
import os
import unittest

from randomizer import items
from randomizer.formats import byml
from randomizer.formats.bfevfl import SUBFLOW, EventFlow
from randomizer.formats.zs import ZsCodec
from randomizer.logic import ootr_data
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
FLOW_DIR, FLOW_EXT = 'Event/EventFlow/', '.bfevfl.zs'
NEW = 'Item_Boomerang'


def _gifts():
    from randomizer import gifts
    return gifts


def _calls(flow: EventFlow, key, values, via: str | None = None) -> list[int]:
    keys = (key,) if isinstance(key, str) else key
    return [i for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW
            and (via is None or ev.sub_entry == via)
            and any(flow.action_params(i).get(k) in values for k in keys)]


class GiftTableTest(unittest.TestCase):
    def test_table_matches_ootr(self):
        gifts = _gifts()
        locs = ootr_data.load_locations()
        self.assertEqual(len(gifts.GIFTS), 35)
        self.assertEqual(len({g.location for g in gifts.GIFTS}), 35)
        for g in gifts.GIFTS:
            with self.subTest(gift=g.location):
                self.assertIn(g.location, locs)
                self.assertTrue(items.content_matches(g.content, locs[g.location]['vanilla_item']))
        self.assertEqual(sum(isinstance(g, gifts.WorldGift) for g in gifts.GIFTS), 2)
        self.assertEqual(gifts.GIFT_ITEMS,
                         frozenset(g.content for g in gifts.GIFTS if g.content in items.KEY_ITEMS))
        self.assertEqual(gifts.FIXED_GIFTS, frozenset())  # batch 28: every gate passed

    def test_empty_placement_changes_nothing(self):
        self.assertEqual(_gifts().gift_flow_patches(lambda name: b'', {}), {})
        self.assertEqual(_gifts().gift_actor_swaps({}), {})

    def test_unknown_location_raises(self):
        with self.assertRaises(_gifts().GiftPatchError):
            _gifts().gift_flow_patches(lambda name: b'', {'Nowhere': NEW})

    def test_actor_swaps(self):
        gifts = _gifts()
        self.assertEqual(gifts.gift_actor_swaps({'LH Underwater Item': NEW}), {
            474136620438465634: ('Banc/HyruleField/HyruleField_Child_Static.bcett.byml.zs', NEW)})
        self.assertEqual(gifts.gift_actor_swaps({'LH Underwater Item': 'Item_Bottle_Letter'}), {})
        self.assertEqual(gifts.gift_actor_swaps({'LH Sun': NEW}), {
            4598657944866228526: ('Banc/HyruleField/HyruleField_Adult_Static.bcett.byml.zs', NEW)})


class _Base:
    """The flow patches on `cls.flows` (name -> decompressed bytes)."""
    flows: dict[str, bytes]

    def _flow_gifts(self):
        return [g for g in _gifts().GIFTS if isinstance(g, _gifts().Gift)]

    def test_every_gift_has_its_grant(self):
        for g in self._flow_gifts():
            with self.subTest(gift=g.location):
                self.assertTrue(_calls(EventFlow(self.flows[g.flow]), g.key, g.vanilla, g.via))

    def test_patch_gives_new_item(self):
        placement = {g.location: NEW for g in self._flow_gifts()}
        out = _gifts().gift_flow_patches(self.flows.__getitem__, placement)
        for g in self._flow_gifts():
            with self.subTest(gift=g.location):
                flow = EventFlow(out[g.flow])
                self.assertEqual(_calls(flow, g.key, g.vanilla, g.via), [])
                self.assertTrue(_calls(flow, g.key, (NEW,), g.via))

    def test_only_matching_calls_change(self):
        out = _gifts().gift_flow_patches(self.flows.__getitem__, {
            'Kak Anju as Child': NEW, 'Market Lost Dog': NEW})
        anju = EventFlow(out['Minigame_CatchCucco'])
        self.assertTrue(_calls(anju, 'ReveiveItem', ('Obj_Rupee_Red',)))
        dog = EventFlow(out['SubEvent_FindRichard'])
        self.assertTrue(_calls(dog, 'ReveiveItem', ('Obj_Rupee_Blue',)))

    def test_special_entry_goes_generic_only_when_changed(self):
        out = _gifts().gift_flow_patches(self.flows.__getitem__, {'GC Darunias Joy': NEW})
        darunia = EventFlow(out['Dm_Goron_0030'])
        self.assertFalse([e for e in darunia.events if e.sub_entry == 'GetInEvent_Goron'])
        self.assertTrue([e for e in darunia.events
                         if e.sub_entry == 'GetInEvent_Demo_NotLookatObjectEntry'])
        goron = _gifts().gift_flow_patches(self.flows.__getitem__,
                                           {'GC Rolling Goron as Child': NEW})
        roller = EventFlow(goron['Npc_Goron_006_Child'])
        self.assertFalse([e for e in roller.events if e.sub_entry == 'GetInEvent_NotTurn_BombBag'])

    def _swap(self, flow, key, a, b, loc_a, loc_b):
        before = EventFlow(self.flows[flow])
        calls_a, calls_b = _calls(before, key, (a,)), _calls(before, key, (b,))
        out = _gifts().gift_flow_patches(self.flows.__getitem__, {loc_a: b, loc_b: a})
        after = EventFlow(out[flow])
        self.assertEqual(_calls(after, key, (b,)), calls_a)
        self.assertEqual(_calls(after, key, (a,)), calls_b)

    def test_same_flow_swap(self):
        self._swap('GatheringTokenGold', 'TakenRewardActor', 'Item_Wallet_Medium',
                   'Item_Wallet_Large', 'Kak 10 Gold Skulltula Reward',
                   'Kak 30 Gold Skulltula Reward')
        self._swap('MiniGame_Fishing', ('ReveiveItem', 'ActorName'), 'Obj_Heart_Piece',
                   'Item_Scale_Gold', 'LH Child Fishing', 'LH Adult Fishing')

    def test_frogs_separate(self):
        flow = 'MiniGame_FrogTenors'
        for loc, changed, kept in (('ZR Frogs in the Rain', 'GetInEvent_NotTurn_NotNpc',
                                    'MushiToriGame'),
                                   ('ZR Frogs Ocarina Game', 'MushiToriGame',
                                    'GetInEvent_NotTurn_NotNpc')):
            with self.subTest(gift=loc):
                out = EventFlow(_gifts().gift_flow_patches(self.flows.__getitem__,
                                                           {loc: NEW})[flow])
                self.assertTrue(_calls(out, 'ActorName', (NEW,), changed))
                self.assertFalse(_calls(out, 'ActorName', ('Obj_Heart_Piece',), changed))
                self.assertFalse(_calls(out, 'ActorName', (NEW,), kept))
                self.assertTrue(_calls(out, 'ActorName', ('Obj_Heart_Piece',), kept))

    def test_two_keys_renamed(self):
        out = EventFlow(_gifts().gift_flow_patches(self.flows.__getitem__,
                                                   {'LH Child Fishing': NEW})['MiniGame_Fishing'])
        self.assertTrue(_calls(out, 'ReveiveItem', (NEW,)))
        self.assertTrue(_calls(out, 'ActorName', (NEW,)))

    def test_talon_repeat_untouched(self):
        out = EventFlow(_gifts().gift_flow_patches(
            self.flows.__getitem__, {'LLR Talons Chickens': NEW})['Minigame_FindOutCucco'])
        self.assertTrue(_calls(out, 'ReveiveItem', (NEW,)))
        self.assertTrue(_calls(out, 'ActorName', ('Item_Bottle_Milk',), 'GetInEventInBottle'))

    def test_dampe_entry_goes_generic_only_when_changed(self):
        flow = 'Npc_Hylia_Dampe_001'
        out = EventFlow(_gifts().gift_flow_patches(
            self.flows.__getitem__, {'Graveyard Dampe Gravedigging Tour': NEW})[flow])
        self.assertFalse([e for e in out.events
                          if e.sub_entry == 'GetInEvent_NotTurn_NotNpc_Dampe'])
        same = _gifts().gift_flow_patches(
            self.flows.__getitem__, {'Graveyard Dampe Gravedigging Tour': 'Obj_Heart_Piece'})
        self.assertEqual(same, {})

    def test_unchanged_gift_untouched(self):
        own = {g.location: g.content for g in self._flow_gifts()}
        self.assertEqual(_gifts().gift_flow_patches(self.flows.__getitem__, own), {})

    def test_missing_grant_raises(self):
        wrong = dict(self.flows)
        wrong['Dm_Goron_0030'] = self.flows['Dm_HrlCastle_0050']
        with self.assertRaises(_gifts().GiftPatchError):
            _gifts().gift_flow_patches(wrong.__getitem__, {'GC Darunias Joy': NEW})


def _flow_names():
    from randomizer.gifts import GIFTS, Gift
    return sorted({g.flow for g in GIFTS if isinstance(g, Gift)})


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class VanillaFlowsTest(_Base, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            cls.flows = {}
            for name in _flow_names():
                p = FLOW_DIR + name + FLOW_EXT
                cls.flows[name] = codec.decompress(p, nup.read(p))

    def test_subflow_list_adds_actionguide(self):
        from randomizer.test_start import ANALYZED_INFO
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            info = codec.decompress(ANALYZED_INFO, nup.read(ANALYZED_INFO))

            def load(name):
                p = FLOW_DIR + name + FLOW_EXT
                return EventFlow(codec.decompress(p, nup.read(p))) if nup.has(p) else None

            out = _gifts().gift_subflow_list(info, load, {'HC Zeldas Letter': NEW})
            same = _gifts().gift_subflow_list(info, load, {'HC Zeldas Letter': 'Item_ZeldaLetter'})
        rows = {r['__RowId']: r for r in byml.load(out)[1]}
        self.assertIn('ActionGuide', rows['Dm_HrlCastle_0050']['SubFlowList'])
        self.assertEqual(same, info)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class FullSkipFlowsTest(_Base, unittest.TestCase):
    """The same patches on the full skip's versions (copies of the grants)."""
    @classmethod
    def setUpClass(cls):
        from randomizer.full_skip import files_with_fallback
        from randomizer.game import GameData
        from randomizer.generate import FULL_SKIP_PHASE
        with NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
            cls.flows = {}
            for name in _flow_names():
                p = FLOW_DIR + name + FLOW_EXT
                cls.flows[name] = game.codec.decompress(p, skip.get(p) or nup.read(p))
            cls.skipped = {n for n in _flow_names() if FLOW_DIR + n + FLOW_EXT in skip}

    def test_skip_rewrote_some_gifts(self):
        self.assertIn('Goto_HyruleCastle', self.skipped)


if __name__ == '__main__':
    unittest.main()
