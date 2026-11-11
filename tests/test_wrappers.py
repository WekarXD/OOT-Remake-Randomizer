import os
import unittest
from pathlib import Path

from randomizer.formats import byml, sarc
from randomizer.formats.rstb import Rstb
from randomizer.game import GameData, load_chests_fixture
from randomizer.items import DUNGEON_ITEM_PREFIXES
from randomizer.nup import NupArchive
from randomizer.wrappers import (RSDB_TABLES, WRAPPER_PREFIX, build_wrapper_files,
                                 can_wrap, drop_actor, pouch_rows)

NUP_PATH = os.environ.get('OOT_NUP')
FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
RSTB_PATH = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs'


class TestDropActor(unittest.TestCase):
    def test_drop_actor_rules(self):
        rows = frozenset({'Obj_Rupee_Red', 'Obj_Token_Gold', 'Obj_MagicJar_Large', 'Obj_Heart_Piece'})
        self.assertEqual(drop_actor('Obj_Token_Gold', rows), 'Obj_Token_Gold')
        self.assertEqual(drop_actor('TBox_Rupee_Red', rows), 'Obj_Rupee_Red')
        self.assertEqual(drop_actor('Tbox_MagicJar_Large', rows), 'Obj_MagicJar_Large')
        self.assertEqual(drop_actor('TBox_DekuNutBundle', rows), 'Obj_Rando_TBox_DekuNutBundle')
        self.assertEqual(drop_actor('Item_Hookshot', rows), 'Obj_Rando_Item_Hookshot')


@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')
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

    def test_build_wrapper_boomerang(self):
        rstb = self.rstb()
        files = self.game_build(['Item_Boomerang', 'Item_Boomerang', 'TBox_Rupee_Red'], rstb)
        pack_path = 'Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs'
        self.assertEqual(sorted(files), sorted([pack_path] + [
            f'RSDB/{t}.Product.111.rstbl.byml.zs' for t in RSDB_TABLES]))
        raw = self.game.codec.decompress(pack_path, files[pack_path])
        pack = sarc.read(raw)
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

    def game_build(self, contents, rstb):
        return build_wrapper_files(self.game, contents, rstb)

    def test_build_wrapper_none_needed(self):
        rstb = self.rstb()
        before = rstb.dump()
        self.assertEqual(self.game_build(['TBox_Rupee_Red', 'Obj_Token_Gold'], rstb), {})
        self.assertEqual(rstb.dump(), before)

    def test_build_wrapper_deterministic(self):
        a = self.game_build(['Item_Boomerang', 'Item_Hookshot'], self.rstb())
        b = self.game_build(['Item_Hookshot', 'Item_Boomerang'], self.rstb())
        self.assertEqual(a, b)

    def test_build_wrapper_rejects_unwrappable(self):
        with self.assertRaisesRegex(ValueError, 'Item_NoExiste'):
            self.game_build(['Item_NoExiste'], self.rstb())

    def test_can_wrap(self):
        self.assertTrue(can_wrap(self.game, 'Item_Hookshot'))
        self.assertFalse(can_wrap(self.game, 'Item_NoExiste'))

    def test_can_wrap_requires_game_actor_info_row(self):
        from unittest import mock

        from randomizer import wrappers
        real = wrappers._load_table

        def no_row(game, t):
            n, v, rows = real(game, t)
            if t == 'GameActorInfo':
                rows = [r for r in rows if r['__RowId'] != 'Item_Hookshot']
            return n, v, rows
        with mock.patch.object(wrappers, '_load_table', no_row):
            self.assertFalse(can_wrap(self.game, 'Item_Hookshot'))

    def test_can_wrap_chest_contents(self):
        rows = pouch_rows(self.game)
        contents = sorted({c.drop for c in load_chests_fixture(FIXTURE)
                           if not c.drop.startswith(DUNGEON_ITEM_PREFIXES)})
        forbidden = []
        for c in contents:
            if not drop_actor(c, rows).startswith(WRAPPER_PREFIX):
                continue
            ok = can_wrap(self.game, c)
            self.assertIsInstance(ok, bool)
            if not ok:
                forbidden.append(c)
        self.assertEqual(len(forbidden), len(set(forbidden)))


if __name__ == '__main__':
    unittest.main()
