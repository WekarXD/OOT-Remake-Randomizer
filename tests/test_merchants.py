import os
import unittest

from randomizer.formats.bfevfl import ACTION, END, FORK, SUBFLOW, SWITCH, EventFlow
from randomizer.formats.zs import ZsCodec
from randomizer.merchants import (CARPET, CARPET_SOLD, MEDIGORON, MEDIGORON_SOLD, SHOP,
                                  sold_out_patches)
from randomizer.nup import NupArchive

NUP_PATH = os.environ.get('OOT_NUP')
SETTERS = ('EventTriggerSetGameDataBool',)
FREED = (MEDIGORON_SOLD, CARPET_SOLD,
         'HaveTalked_Special.Npc_Goron_Medigoron_Adult_Talk_Event8')


def _reach(flow: EventFlow, start: int) -> set[int]:
    """Events reachable from `start`, following calls into this flow's own entries."""
    seen, todo = set(), [start]
    while todo:
        i = todo.pop()
        if i == END or i in seen:
            continue
        seen.add(i)
        ev = flow.events[i]
        todo += [ev.next] if ev.kind in (ACTION, SUBFLOW) else []
        todo += ev.cases if ev.kind == SWITCH else []
        todo += ev.forks + [ev.join] if ev.kind == FORK else []
        if ev.kind == SUBFLOW and not ev.sub_flow and ev.sub_entry in flow.entry_points:
            todo.append(flow.entry_points[ev.sub_entry])
        if ev.kind not in (ACTION, SUBFLOW, SWITCH, FORK) and ev.next is not None:
            todo.append(ev.next)
    return seen


def _sets(flow: EventFlow, i: int, name: str) -> bool:
    ev = flow.events[i]
    return ev.kind == ACTION and ev.action in SETTERS and \
        flow.action_params(i).get('GameDataName') == name


def _case(flow: EventFlow, i: int, value: int) -> int:
    e = flow._events_p + 0x30 * i
    cases_p = flow._u64(e + 0x18)
    for k, target in enumerate(flow.events[i].cases):
        if flow._u32(cases_p + 8 * k) == value:
            return target
    raise KeyError(value)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class SoldOutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {}
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for name in (MEDIGORON, CARPET, SHOP):
                p = f'Event/EventFlow/{name}.bfevfl.zs'
                cls.raw[name] = codec.decompress(p, nup.read(p))
        cls.out = sold_out_patches(cls.raw.__getitem__)
        cls.flows = {k: EventFlow(v) for k, v in cls.out.items()}

    def test_patches_the_three_flows(self):
        self.assertEqual(set(self.out), {MEDIGORON, CARPET, SHOP})

    def test_medigoron_skips_his_checks(self):
        # Batch 31d: he resold; his pouch checks (Giant's Knife, broken knife, Biggoron's
        # Sword) would refuse a sale when those items come from elsewhere.
        f = self.flows[MEDIGORON]
        # SageOfFire_Check is only called from inside the flow (event 14).
        starts = [i for name, i in f.entry_points.items() if name != 'SageOfFire_Check']
        reached = set().union(*(_reach(f, i) for i in starts))
        for i in reached:
            ev = f.events[i]
            if ev.kind == SWITCH and ev.query == 'EventQueryIsExistInPouch':
                self.fail(f'event {i} still checks {f.action_params(i)}')
            for name in FREED:
                self.assertFalse(_sets(f, i, name), (i, name))
        talk = f.entry_points['Talk']
        query = f.events[talk].next
        self.assertEqual(f.action_params(query)['GameDataName'], MEDIGORON_SOLD)
        sale = _reach(f, _case(f, query, 1))
        self.assertTrue(any(f.events[i].kind == SUBFLOW and f.events[i].sub_flow == SHOP
                            for i in sale))
        self.assertFalse(any(f.events[i].kind == SUBFLOW and f.events[i].sub_flow == SHOP
                             for i in _reach(f, _case(f, query, 0))))

    def test_medigoron_sale_sets_his_flag(self):
        f, old = self.flows[SHOP], EventFlow(self.raw[SHOP])
        grant = next(i for i, ev in enumerate(f.events)
                     if ev.kind == SUBFLOW and ev.sub_flow == 'Dm_SY_GetInEvent')
        setter = f.events[grant].next
        self.assertTrue(_sets(f, setter, MEDIGORON_SOLD))
        self.assertEqual(f.events[setter].next, old.events[grant].next)
        # The cancel paths (Sub_ShopCancel) never reach it.
        self.assertNotIn(setter, _reach(f, f.entry_points['Sub_ShopCancel']))
        root = _reach(f, f.entry_points['SimpleShopRoot_Npc_Goron_Medigoron_Adult'])
        self.assertIn(setter, root)

    def test_carpet_flag_is_saved_one(self):
        # Npc_Hylia_044_Buy is not saved (SaveFileIndex -1): the patch uses a saved flag.
        for name in (CARPET, SHOP):
            f = self.flows[name]
            names = {f.action_params(i).get('GameDataName') for i in range(len(f.events))
                     if f.events[i].kind in (ACTION, SWITCH)}
            self.assertNotIn('Npc_Hylia_044_Buy', names, name)
            self.assertIn(CARPET_SOLD, names, name)
        shop = self.flows[SHOP]
        setter = next(i for i in range(len(shop.events)) if _sets(shop, i, CARPET_SOLD))
        self.assertIn(setter, _reach(shop, shop.entry_points['SimpleShopRoot']))
        self.assertNotIn(setter, _reach(shop, shop.entry_points[
            'SimpleShopRoot_Npc_Goron_Medigoron_Adult']))

    def test_carpet_sold_out_path(self):
        f = self.flows[CARPET]
        query = next(i for i, ev in enumerate(f.events) if ev.kind == SWITCH
                     and f.action_params(i).get('GameDataName') == CARPET_SOLD)
        sold = _reach(f, _case(f, query, 0))
        self.assertEqual(len(sold), 1)
        (talk,) = sold
        self.assertEqual(f.action_params(talk)['MessageId'],
                         'EventFlowMsg/Npc_Hylia_044_Adult:Talk_01')
        for i in _reach(f, f.entry_points['Talk']) - _reach(f, _case(f, query, 1)):
            self.assertNotEqual(f.events[i].action, 'EventTriggerOpenRupeeDisplay', i)
            self.assertFalse(f.events[i].kind == SUBFLOW and f.events[i].sub_flow == SHOP, i)
        sale = _reach(f, _case(f, query, 1))
        self.assertTrue(any(f.events[i].action == 'EventTriggerOpenRupeeDisplay' for i in sale))
        self.assertTrue(any(f.events[i].kind == SUBFLOW and f.events[i].sub_flow == SHOP
                            for i in sale))

    def test_other_events_untouched(self):
        old, new = EventFlow(self.raw[SHOP]), self.flows[SHOP]
        self.assertEqual(len(new.events), len(old.events) + 1)
        changed = [i for i in range(len(old.events))
                   if (old.events[i].next, old.events[i].cases)
                   != (new.events[i].next, new.events[i].cases)
                   or old.action_params(i) != new.action_params(i)]
        self.assertEqual(len(changed), 2)  # the grant's next and the carpet's flag


if __name__ == '__main__':
    unittest.main()
