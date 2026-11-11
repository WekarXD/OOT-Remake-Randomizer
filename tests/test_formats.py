import os
import struct
import unittest
import zlib

from randomizer.formats import byml, sarc
from randomizer.formats.byml import U32, U64, F32
from randomizer.formats.rstb import Rstb, banc_rstb_size

NUP_PATH = os.environ.get('OOT_NUP')


def make_restbl(crcs, names, name_block=0xA0):
    out = bytearray(b'RESTBL')
    out += struct.pack('<IIII', 1, name_block, len(crcs), len(names))
    for crc, size in sorted(crcs):
        out += struct.pack('<II', crc, size)
    for name, size in names:
        out += name.encode().ljust(name_block, b'\0') + struct.pack('<I', size)
    return bytes(out)


class BymlTests(unittest.TestCase):
    def test_byml_roundtrip_synthetic(self):
        x = {'Actors': [
            {'Gyaml': 'Obj_TBox_A_01', 'Hash': U64(2 ** 63 + 5),
             'Dynamic': {'Drop__DropActor': 'TBox_Rupee_Blue'}},
            {'f': F32(1.5), 'i': -3, 'b': True, 'u': U32(7)}]}
        r = byml.load(byml.dump(x))[1]
        self.assertEqual(r, x)
        self.assertIs(type(r['Actors'][0]['Hash']), U64)
        self.assertIs(type(r['Actors'][1]['u']), U32)
        self.assertIs(type(r['Actors'][1]['f']), F32)

    def test_byml_shared_nodes_not_aliased(self):
        dyn = {'Drop__DropActor': 'TBox_Rupee_Blue'}
        x = {'Actors': [{'Dynamic': dict(dyn)}, {'Dynamic': dict(dyn)}]}
        data = byml.dump(x)
        # deduplicated: identical Dynamic nodes occupy less than distinct ones
        y = {'Actors': [{'Dynamic': {'Drop__DropActor': 'TBox_Rupee_Blue'}},
                        {'Dynamic': {'Drop__DropActor': 'TBox_Rupee_Red'}}]}
        self.assertLess(len(data), len(byml.dump(y)))
        r = byml.load(data)[1]
        r['Actors'][0]['Dynamic']['Drop__DropActor'] = 'Item_Hookshot'
        self.assertEqual(r['Actors'][1]['Dynamic']['Drop__DropActor'], 'TBox_Rupee_Blue')


class RstbTests(unittest.TestCase):
    def test_rstb_roundtrip_synthetic(self):
        p1, p2, p3 = 'Banc/A/A.bcett.byml', 'Banc/B/B.bcett.byml', 'Banc/C/C.bcett.byml'
        crcs = [(zlib.crc32(p.encode()), 100 + i) for i, p in enumerate((p1, p2, p3))]
        data = make_restbl(crcs, [('Some/Named.file', 55)])
        r = Rstb.load(data)
        self.assertEqual(r.get(p2), 101)
        self.assertEqual(r.get('Some/Named.file'), 55)
        self.assertIsNone(r.get('Nope'))
        r.set(p2, 999)
        r.set('Some/Named.file', 777)
        with self.assertRaises(KeyError):
            r.set('Nope', 1)
        r2 = Rstb.load(r.dump())
        self.assertEqual(r2.get(p2), 999)
        self.assertEqual(r2.get('Some/Named.file'), 777)
        self.assertEqual(r2.get(p1), 100)
        self.assertEqual(len(r.dump()), len(data))

    def test_banc_rstb_size(self):
        self.assertEqual(banc_rstb_size(510884), 511176)

    def test_rstb_add_sorted_and_duplicate(self):
        r = Rstb((1, 160), [[10, 1], [0xFFFFFFF0, 3]], [])
        r.add('x', 7)
        crcs = [c for c, _ in r._crcs]
        self.assertEqual(crcs, sorted(crcs))
        self.assertEqual(r.get('x'), 7)
        with self.assertRaises(ValueError):
            r.add('x', 8)


class SarcWriteTests(unittest.TestCase):
    def test_sarc_write_roundtrip_synthetic(self):
        files = {'b/x.bin': b'' * 5, 'a.txt': b'data', 'c': b''}
        self.assertEqual(sarc.read(sarc.write(files)), files)

    def test_sarc_write_node_order(self):
        raw = sarc.write({'zz': b'1', 'a': b'2'})
        hashes = [struct.unpack_from('<I', raw, 0x14 + 0xC + 16 * i)[0] for i in range(2)]
        self.assertEqual(hashes, sorted(hashes))


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class RealTests(unittest.TestCase):
    def test_real_all_banc_roundtrip(self):
        from randomizer.nup import NupArchive
        from randomizer.formats.zs import ZsCodec
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            rs_path = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs'
            rstb = Rstb.load(codec.decompress(rs_path, nup.read(rs_path)))
            files = [p for p in nup.list('Banc/') if p.endswith('.bcett.byml.zs')]
            self.assertEqual(len(files), 160)
            for p in files:
                raw = codec.decompress(p, nup.read(p))
                ver, root = byml.load(raw)
                new = byml.dump(root, ver)
                ver2, root2 = byml.load(new)
                self.assertEqual((ver, root), (ver2, root2), p)
                self.assertEqual(_types(root), _types(root2), p)
                self.assertEqual(rstb.get(p[:-3]), banc_rstb_size(len(raw)), p)
                self.assertEqual(codec.decompress(p, codec.compress(p, new)), new)

    def test_sarc_write_byte_exact_real_packs(self):
        from randomizer.nup import NupArchive
        from randomizer.formats.zs import ZsCodec
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for name in ('Obj_Bottle_Letter', 'Item_Hookshot', 'Obj_Heart_Piece'):
                p = f'Pack/Actor/{name}.pack.zs'
                raw = codec.decompress(p, nup.read(p))
                self.assertEqual(sarc.write(sarc.read(raw)), raw, name)


def _types(v):
    if isinstance(v, dict):
        return {k: _types(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_types(x) for x in v]
    return type(v)


if __name__ == '__main__':
    unittest.main()
