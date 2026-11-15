import os
import unittest

from randomizer import items
from randomizer.formats.bfevfl import SUBFLOW, SWITCH, EventFlow
from randomizer.formats.zs import ZsCodec
from randomizer.logic import ootr_data
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
FLOW_DIR, FLOW_EXT = 'Event/EventFlow/', '.bfevfl.zs'
GRANT_FLOW = 'Dm_SY_GetInEvent'
GENERIC = 'GetInEvent_Demo_NotLookatObjectEntry'
PAY_QUERIES = ('EventQueryTalkChoice2', 'EventQueryHasRuppe')
REFUSALS = ('DontPay1', 'DontPay2')


def _fairies():
    from randomizer import fairies
    return fairies


def _vanilla():
    return {f.location: f.reward for f in _fairies().FOUNTAINS}


def reachable(flow: EventFlow, name: str, entries) -> set[int]:
    """Events reachable from `entries`, following same-file subflow calls."""
    seen, stack = set(), [flow.entry_points[e] for e in entries]
    while stack:
        i = stack.pop()
        if i in seen or i >= len(flow.events):
            continue
        seen.add(i)
        ev = flow.events[i]
        nxt = [ev.next] if isinstance(ev.next, int) else []
        nxt += list(ev.cases) + list(ev.forks) + ([ev.join] if isinstance(ev.join, int) else [])
        if ev.sub_flow in ('', name) and ev.sub_entry in flow.entry_points:
            nxt.append(flow.entry_points[ev.sub_entry])
        stack += [n for n in nxt if n != 0xFFFF]
    return seen


def _grants(flow: EventFlow) -> list[int]:
    return [i for i, ev in enumerate(flow.events)
            if ev.kind == SUBFLOW and ev.sub_flow == GRANT_FLOW]


class FairyTableTest(unittest.TestCase):
    def test_table_matches_ootr(self):
        fairies = _fairies()
        locs = ootr_data.load_locations()
        self.assertEqual(len(fairies.FOUNTAINS), 6)
        for f in fairies.FOUNTAINS:
            with self.subTest(fountain=f.name):
                self.assertIn('Great Fairies', locs[f.location]['categories'])
                self.assertEqual(f.flow, 'Dm_FairyFountain_' + f.name)
                self.assertIn(f.reward, items.KEY_ITEMS)
                self.assertEqual(items.KEY_ITEM_HOME[f.reward], f.location)
        self.assertEqual(fairies.FAIRY_REWARDS, frozenset(f.reward for f in fairies.FOUNTAINS))

    def test_empty_placement_changes_nothing(self):
        self.assertEqual(_fairies().fairy_flow_patches(lambda name: b'', {}), {})

    def test_wrong_locations_raise(self):
        fairies = _fairies()
        five = dict(list(_vanilla().items())[:5])
        with self.assertRaises(fairies.FairyPatchError):
            fairies.fairy_flow_patches(lambda name: b'', five)
        with self.assertRaises(fairies.FairyPatchError):
            fairies.fairy_flow_patches(lambda name: b'', {**_vanilla(), 'Nowhere': 'Item_Hammer'})


class _Base:
    """The flow patches on `cls.flows` (name -> decompressed bytes)."""
    flows: dict[str, bytes]

    def _patch(self, changes=None):
        placement = {**_vanilla(), **(changes or {})}
        return _fairies().fairy_flow_patches(self.flows.__getitem__, placement)

    def test_grant_gives_new_item(self):
        out = self._patch({'HC Great Fairy Reward': 'Item_Boomerang',
                           'DMC Great Fairy Reward': 'Item_NayruLove'})
        power = EventFlow(out['Dm_FairyFountain_Power'])
        self.assertTrue(_grants(power))
        self.assertEqual({power.action_params(i)['ActorName'] for i in _grants(power)},
                         {'Item_Boomerang'})
        wisdom = EventFlow(out['Dm_FairyFountain_Wisdom'])
        self.assertTrue(_grants(wisdom))
        for i in _grants(wisdom):
            self.assertEqual(wisdom.action_params(i)['ActorName'], 'Item_NayruLove')
            self.assertEqual(wisdom.events[i].sub_entry, GENERIC)
        din = EventFlow(out['Dm_FairyFountain_Din'])
        self.assertTrue(all(din.events[i].sub_entry == 'GetInEvent_GreatFairyDin'
                            and din.action_params(i)['ActorName'] == 'Item_DinFire'
                            for i in _grants(din)))

    def test_spin_guide_only_when_changed(self):
        def guides(out):
            flow = EventFlow(out['Dm_FairyFountain_Power'])
            return [i for i in reachable(flow, 'Dm_FairyFountain_Power', ['EntryPoint0'])
                    if flow.events[i].kind == SUBFLOW and flow.events[i].sub_flow == 'ActionGuide']
        self.assertEqual(guides(self._patch({'HC Great Fairy Reward': 'Item_Boomerang'})), [])
        self.assertNotEqual(guides(self._patch()), [])

    def test_free_on_every_fountain(self):
        out = self._patch({'HC Great Fairy Reward': 'Item_Boomerang'})
        for f in _fairies().FOUNTAINS:
            with self.subTest(fountain=f.name):
                flow = EventFlow(out[f.flow])
                entries = ['EntryPoint0'] + (['Pay', 'DontPay1', 'DontPay2']
                                             if f.name == 'Din' else [])
                main = reachable(flow, f.flow, ['EntryPoint0'])
                bad = [i for i in reachable(flow, f.flow, entries)
                       if flow.events[i].query in PAY_QUERIES
                       or flow.events[i].action == 'EventTriggerIncreaseRupee']
                bad += [i for i in main if flow.events[i].sub_entry in REFUSALS]
                self.assertEqual(bad, [])
                self.assertTrue(set(_grants(flow)) & main)

    def test_revisit_reads_have_played(self):
        out = self._patch()
        for f in _fairies().FOUNTAINS:
            with self.subTest(fountain=f.name):
                before, after = EventFlow(self.flows[f.flow]), EventFlow(out[f.flow])

                def count(flow, name):
                    return sum(1 for i, ev in enumerate(flow.events)
                               if ev.query == 'EventQueryIsGameDataBool'
                               and flow.action_params(i).get('GameDataName') == name)
                played = 'HavePlayedEvent.' + f.flow
                self.assertEqual(count(after, played), count(before, played) + 1)
                self.assertEqual(count(after, 'IsGet.' + f.reward),
                                 count(before, 'IsGet.' + f.reward) - 1)

    def test_triforce_gate_removed(self):
        out = self._patch()
        flow = EventFlow(out['TriForcePoint'])
        entries = [e for e in flow.entry_points if e.startswith('Demo_FairyFountain_')]
        self.assertEqual(len(entries), 6)
        gates = [i for i in reachable(flow, 'TriForcePoint', entries)
                 if flow.events[i].kind == SWITCH and len(flow.events[i].cases) == 2
                 and flow.action_params(i).get('GameDataName') == 'IsGet.Item_DinFire']
        self.assertEqual(gates, [])
        before = EventFlow(self.flows['TriForcePoint'])
        self.assertTrue([i for i in reachable(before, 'TriForcePoint', entries)
                         if before.events[i].kind == SWITCH and len(before.events[i].cases) == 2
                         and before.action_params(i).get('GameDataName') == 'IsGet.Item_DinFire'])


def _names():
    from randomizer.fairies import FOUNTAINS, TRIFORCE_FLOW
    return [f.flow for f in FOUNTAINS] + [TRIFORCE_FLOW]


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class VanillaFlowsTest(_Base, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            cls.flows = {}
            for name in _names():
                p = FLOW_DIR + name + FLOW_EXT
                cls.flows[name] = codec.decompress(p, nup.read(p))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class FullSkipFlowsTest(_Base, unittest.TestCase):
    """The same patches on the full skip's versions (grown files, inlined copies of
    the payment; Din's flow is left whole and read from the game)."""
    @classmethod
    def setUpClass(cls):
        from randomizer.full_skip import files_with_fallback
        from randomizer.game import GameData
        from randomizer.generate import FULL_SKIP_PHASE
        with NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            skip, _, _ = files_with_fallback(game, FULL_SKIP_PHASE)
            cls.flows = {}
            for name in _names():
                p = FLOW_DIR + name + FLOW_EXT
                raw = skip.get(p) or nup.read(p)
                cls.flows[name] = game.codec.decompress(p, raw)
            cls.skipped = {n for n in _names() if FLOW_DIR + n + FLOW_EXT in skip}

    def test_skip_rewrote_some_fountains(self):
        self.assertIn('Dm_FairyFountain_Power', self.skipped)
        self.assertNotIn('Dm_FairyFountain_Din', self.skipped)


if __name__ == '__main__':
    unittest.main()
