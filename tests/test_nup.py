import hashlib
import os
import struct
import tempfile
import unittest

from randomizer.nup import NupArchive, NupError


def build_minimal_nup(path):
    content = b'hola'
    pool = b'romfshello.bin'
    # string pool: 'romfs' @0 len5, 'hello.bin' @5 len9
    pk = struct.pack('<QIIIIBBHI', 0x0400486024DEC000, 0, 0xFFFFFFFF, 1, 131072, 1, 1, 0, 0)
    pk += b'\0' * (0x40 - len(pk))
    d_root = struct.pack('<IIIIQ', 0, 0, 0, 1, 0)       # child slot 0 -> romfs
    d_romfs = struct.pack('<IIIIQ', 0, 5, 1, 1, 0)      # child slot 1 -> file
    f = struct.pack('<IIQQQ', 5, 9, len(content), 0, len(content))
    f += hashlib.sha256(content).digest() + b'\0' * (0x50 - len(f) - 32)
    children = struct.pack('<II', 1, 2)                 # dir 1; file 0 (id=2+0)
    n_pk, n_dir, n_file = 1, 2, 1
    sp_off = 0x30 + 0x40 + 0x18 * n_dir + 0x50 * n_file + len(children)
    toc = struct.pack('<IIQQQQQ', 0x01434F54, n_pk, n_dir, n_file, sp_off, len(pool), 0)
    toc += pk + d_root + d_romfs + f + children + pool
    toc_off = 0x80
    blob_off = (toc_off + len(toc) + 15) & ~15
    # patch extent_offset to blob_off (absolute)
    # file record position inside toc
    fo = 0x30 + 0x40 + 0x18 * n_dir
    toc = toc[:fo + 0x10] + struct.pack('<Q', blob_off) + toc[fo + 0x18:]
    file_size = blob_off + len(content)
    sb = b'NUP\x01' + struct.pack('<HHQQ', 0x80, 1, toc_off, len(toc))
    sb += hashlib.sha256(toc).digest()
    sb += struct.pack('<QQII', blob_off, file_size, 1, 0)
    sb += b'\0' * (0x80 - len(sb))
    data = sb + toc + b'\0' * (blob_off - toc_off - len(toc)) + content
    with open(path, 'wb') as fh:
        fh.write(data)


class NupTests(unittest.TestCase):
    def test_rejects_non_nup(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'x.nup')
            with open(p, 'wb') as fh:
                fh.write(b'hello')
            with self.assertRaises(NupError) as cm:
                NupArchive(p)
            self.assertIn('no es un archivo .nup', str(cm.exception))

    def test_minimal_synthetic_nup(self):
        with tempfile.TemporaryDirectory() as d:
            sub = os.path.join(d, 'juego [x] y espacios')
            os.makedirs(sub)
            p = os.path.join(sub, 'g.nup')
            build_minimal_nup(p)
            with NupArchive(p) as a:
                self.assertEqual(a.read('hello.bin'), b'hola')
                self.assertTrue(a.has('hello.bin'))
                self.assertFalse(a.has('nope'))
                self.assertEqual(a.list(''), ['hello.bin'])
                self.assertEqual(a.update_version, 131072)

    def test_corrupt_toc_hash(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'g.nup')
            build_minimal_nup(p)
            with open(p, 'rb') as fh:
                raw = bytearray(fh.read())
            raw[0x90] ^= 0xFF
            with open(p, 'wb') as fh:
                fh.write(raw)
            with self.assertRaises(NupError):
                NupArchive(p)

    @unittest.skipUnless(os.environ.get('OOT_NUP'), 'OOT_NUP no definido')
    def test_real_game(self):
        with NupArchive(os.environ['OOT_NUP']) as a:
            self.assertEqual(a.title_id, 0x0400486024DEC000)
            self.assertEqual(a.update_version, 131072)
            self.assertEqual(len([p for p in a.list('Banc/') if p.endswith('.bcett.byml.zs')]), 160)
            self.assertEqual(a.read('Pack/ZsDic.pack.zs')[:4], b'\x28\xb5\x2f\xfd')


if __name__ == '__main__':
    unittest.main()
