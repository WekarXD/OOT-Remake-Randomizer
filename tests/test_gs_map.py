import json
import unittest
from pathlib import Path

from randomizer import locations
from randomizer.game import load_skulltulas_fixture
from randomizer.logic.world import World, load_vanilla_settings

FIX = Path(__file__).parent / 'fixtures' / 'skulltulas.json'

# Confirmadas en el juego (lote 15).
IN_GAME = {
    17067594426901953848: 'KF GS Know It All House',
    9623998892552467148: 'KF GS Bean Patch',
    13609975487234437568: 'Deku Tree GS Compass Room',
    17501688996789643983: 'Deku Tree GS Basement Back Room',
}


class GsMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = locations.load_gs_map()

    def test_gs_map_complete(self):
        m = self.map
        fixture_hashes = {x.hash for x in load_skulltulas_fixture(FIX)}
        self.assertEqual(set(m), fixture_hashes)
        w = World(load_vanilla_settings())
        names = {loc for _, loc, _ in w._all_locations}
        gs = {n for n, v in w.locations.items()
              if v['vanilla_item'] == 'Gold Skulltula Token' and n in names}
        self.assertEqual({e.location for e in m.values()}, gs)  # 100 distintas, biyección
        self.assertEqual(len(m), 100)
        self.assertEqual(sum(e.dungeon for e in m.values()), 44)
        self.assertTrue(all(e.status in ('confirmed', 'guessed') for e in m.values()))

    def test_in_game_confirmed(self):
        for h, name in IN_GAME.items():
            self.assertEqual(self.map[h].location, name, h)
            self.assertEqual(self.map[h].status, 'confirmed', h)

    def test_no_key_where_remake_contradicts_ootr(self):
        # Cow Grotto: solo en el Banc de adulto, OoTR la permite de niño.
        # ZR Tree: tierra blanda en el remake, OoTR pide can_bonk.
        got = {h for h, e in self.map.items() if e.no_key}
        self.assertEqual(got, {9047381233010434881, 12370559827741970774})

    def test_every_entry_has_note(self):
        for e in self.map.values():
            self.assertTrue(e.note, e.hash)

    def test_file_is_deterministic(self):
        raw = locations.GS_MAP_PATH.read_text(encoding='utf-8')
        again = json.dumps(json.loads(raw), indent=1, ensure_ascii=False,
                           sort_keys=True) + '\n'
        self.assertEqual(raw, again)


if __name__ == '__main__':
    unittest.main()
