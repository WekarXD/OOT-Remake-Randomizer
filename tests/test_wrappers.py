import os
import unittest
from pathlib import Path
from unittest import mock

from randomizer import wrappers
from randomizer.formats import byml, sarc
from randomizer.formats.rstb import Rstb
from randomizer.game import GameData, load_chests_fixture
from randomizer.items import DUNGEON_ITEM_PREFIXES
from randomizer.nup import NupArchive
from randomizer.wrappers import (RSDB_TABLES, WRAPPER_PREFIX, build_wrapper_files,
                                 can_wrap, drop_actor, pouch_rows, vanilla_drop,
                                 wrap_source, wrap_sources)

NUP_PATH = os.environ.get('OOT_NUP')
FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
RSTB_PATH = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs'


class TestDropActor(unittest.TestCase):
    ROWS = frozenset({'Obj_Rupee_Red', 'Obj_Token_Gold', 'Obj_MagicJar_Large', 'Obj_Heart_Piece'})

    def test_vanilla_drop_rules(self):
        self.assertEqual(vanilla_drop('Obj_Token_Gold', self.ROWS), 'Obj_Token_Gold')
        self.assertEqual(vanilla_drop('TBox_Rupee_Red', self.ROWS), 'Obj_Rupee_Red')
        self.assertEqual(vanilla_drop('Tbox_MagicJar_Large', self.ROWS), 'Obj_MagicJar_Large')
        self.assertIsNone(vanilla_drop('TBox_DekuNutBundle', self.ROWS))
        self.assertIsNone(vanilla_drop('Item_Hookshot', self.ROWS))

    def test_drop_actor_prefers_wrapper(self):
        wrappable = frozenset({'TBox_Rupee_Red', 'Item_Hookshot'})
        self.assertEqual(drop_actor('TBox_Rupee_Red', wrappable, self.ROWS),
                         'Obj_Rando_TBox_Rupee_Red')
        self.assertEqual(drop_actor('Item_Hookshot', wrappable, self.ROWS),
                         'Obj_Rando_Item_Hookshot')
        self.assertEqual(drop_actor('Tbox_MagicJar_Large', wrappable, self.ROWS),
                         'Obj_MagicJar_Large')
        with self.assertRaisesRegex(ValueError, 'TBox_DekuNutBundle'):
            drop_actor('TBox_DekuNutBundle', wrappable, self.ROWS)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class TestWrappers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nup = NupArchive(NUP_PATH)
        cls.game = GameData(cls.nup)

    @classmethod
    def tearDownClass(cls):
        cls.nup.close()

    def rstb(self):
        return Rstb.load(self.game.codec.decompress(RSTB_PATH, self.nup.read(RSTB_PATH)))

    def table(self, files, t):
        p = f'RSDB/{t}.Product.111.rstbl.byml.zs'
        return byml.load(self.game.codec.decompress(p, files[p]))[1]

    def build(self, contents, rstb):
        return build_wrapper_files(self.game, wrap_sources(self.game, contents), rstb)

    def pack(self, files, name):
        p = f'Pack/Actor/{WRAPPER_PREFIX}{name}.pack.zs'
        raw = self.game.codec.decompress(p, files[p])
        return raw, sarc.read(raw)

    def test_build_wrapper_boomerang(self):
        rstb = self.rstb()
        files = self.build(['Item_Boomerang', 'Item_Boomerang'], rstb)
        pack_path = 'Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs'
        self.assertEqual(sorted(files), sorted([pack_path] + [
            f'RSDB/{t}.Product.111.rstbl.byml.zs' for t in RSDB_TABLES]))
        raw, pack = self.pack(files, 'Item_Boomerang')
        _v, ap = byml.load(pack['Actor/Obj_Rando_Item_Boomerang.engine__actor__ActorParam.bgyml'])
        comp = ap['Components']
        self.assertEqual(comp['ActorNameRef'],
                         '?ActorSystem/ActorName/Item_Boomerang.engine__actor__ActorName.bgyml')
        _v, pc = byml.load(pack[comp['PouchContentRef'].lstrip('?')])
        self.assertIs(pc['DefaultAutoGet'], True)
        ai = self.table(files, 'ActorInfo')
        row = next(r for r in ai if r['__RowId'] == 'Obj_Rando_Item_Boomerang')
        self.assertEqual(row['ActorName'], 'Item_Boomerang')
        pa = self.table(files, 'PouchActorInfo')
        row = next(r for r in pa if r['__RowId'] == 'Obj_Rando_Item_Boomerang')
        self.assertEqual(row['AssignableItem'], 'Boomerang')
        for t in RSDB_TABLES:
            ids = [r['__RowId'] for r in self.table(files, t)]
            self.assertEqual(ids, sorted(ids))
        self.assertEqual(rstb.get(pack_path[:-3]), len(raw) + 0x1000)

    def test_rupee_wrapper_uses_world_rupee(self):
        # The chest content is a bundle; the wrapper takes the identity of
        # the world rupee, whose AnimationRef is inherited from Obj_Rupee_Green.
        self.assertEqual(wrap_source(self.game, 'TBox_Rupee_Purple'), 'Obj_Rupee_Purple')
        files = self.build(['TBox_Rupee_Purple'], self.rstb())
        _raw, pack = self.pack(files, 'TBox_Rupee_Purple')
        _v, ap = byml.load(pack['Actor/Obj_Rando_TBox_Rupee_Purple.engine__actor__ActorParam.bgyml'])
        comp = ap['Components']
        self.assertEqual(comp['ActorNameRef'],
                         '?ActorSystem/ActorName/Obj_Rupee_Purple.engine__actor__ActorName.bgyml')
        self.assertEqual(comp['AnimationRef'],
                         '?Component/AnimationParam/Obj_Rupee.engine__component__AnimationParam.bgyml')
        _v, pc = byml.load(pack[comp['PouchContentRef'].lstrip('?')])
        self.assertIs(pc['DefaultAutoGet'], True)
        self.assertEqual(pc['PickedUpEmitXlinkKey'], 'Item_PickedUp_Rupee_Purple')
        pa = {r['__RowId']: r for r in self.table(files, 'PouchActorInfo')}
        expected = dict(pa['Obj_Rupee_Purple'], __RowId='Obj_Rando_TBox_Rupee_Purple')
        self.assertEqual(pa['Obj_Rando_TBox_Rupee_Purple'], expected)

    def test_build_wrapper_none_needed(self):
        rstb = self.rstb()
        before = rstb.dump()
        self.assertEqual(self.build(['Obj_Token_Gold'], rstb), {})
        self.assertEqual(rstb.dump(), before)

    def test_build_wrapper_deterministic(self):
        a = self.build(['Item_Boomerang', 'Item_Hookshot', 'TBox_Rupee_Red'], self.rstb())
        b = self.build(['TBox_Rupee_Red', 'Item_Hookshot', 'Item_Boomerang'], self.rstb())
        self.assertEqual(a, b)

    def test_unwrappable_left_out(self):
        self.assertEqual(wrap_sources(self.game, ['Item_NoExiste', 'Item_Hookshot']),
                         {'Item_Hookshot': 'Item_Hookshot'})

    def test_can_wrap(self):
        self.assertTrue(can_wrap(self.game, 'Item_Hookshot'))
        self.assertTrue(can_wrap(self.game, 'TBox_Rupee_Blue'))
        self.assertFalse(can_wrap(self.game, 'Item_NoExiste'))

    def test_can_wrap_requires_game_actor_info_row(self):
        real = wrappers._load_table

        def no_row(game, t):
            n, v, rows = real(game, t)
            if t == 'GameActorInfo':
                rows = [r for r in rows if r['__RowId'] != 'Item_Hookshot']
            return n, v, rows
        with mock.patch.object(wrappers, '_load_table', no_row):
            self.assertFalse(can_wrap(self.game, 'Item_Hookshot'))

    def test_chest_contents_float_or_are_known_exceptions(self):
        rows = pouch_rows(self.game)
        contents = sorted({c.drop for c in load_chests_fixture(FIXTURE)
                           if not c.drop.startswith(DUNGEON_ITEM_PREFIXES)})
        sources = wrap_sources(self.game, contents)
        falling = [c for c in contents if c not in sources]
        # Only ammo bundles have no floating wrapper; none has a world actor.
        self.assertEqual(falling, ['Item_BombBundle_Small', 'Item_BombchuBundle_Small',
                                   'Item_DekuStickBundle_Small', 'TBox_DekuNutBundle'])
        self.assertTrue(all(vanilla_drop(c, rows) is None for c in falling))


if __name__ == '__main__':
    unittest.main()
