"""Generates the test mods TestBatch1 and TestBatch2 (R1-R3).
Usage: python -I tools/make_test_batch.py <nup> <files.tsv> <out_dir>
Only reads the .nup; writes to <out_dir>/0400486024DEC000/<Mod>/romfs/...
"""
import os, shutil, struct, sys, zlib
from compression import zstd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'spikes'))
import peek, byml  # noqa: E402

TITLE = '0400486024DEC000'
RSTB = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable'
CHILD = 'Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml'
ADULT = 'Banc/KokiriForest/KokiriForest_Adult_Dynamic.bcett.byml'
ICE = 'Banc/IceCavern/IceCavern_Static.bcett.byml'

# mod -> banc -> [(hash, original, new)]
KOKIRI_SWORD = (16757992849254467386, 'Item_Sword_Kokiri', 'TBox_Rupee_Green')
MODS = {
    'TestBatch1': {
        CHILD: [
            KOKIRI_SWORD,
            (10831981390482426294, 'TBox_Rupee_Green', 'Item_Longshot'),
            (4555665598794293658, 'TBox_Rupee_Blue', 'Item_Gauntlet_Gold'),
            (9725242744547055868, 'TBox_Rupee_Blue', 'Item_Shield_Mirror'),
            (12786193094758345086, 'TBox_Rupee_Blue', 'Item_Arrow_Ice'),
        ],
        ADULT: [KOKIRI_SWORD],
    },
    'TestBatch2': {
        ICE: [(6859289214373847284, 'Item_HeavyBoot', 'TBox_Rupee_Blue')],
    },
}


def rstb_size(n):
    return ((n + 31) & ~31) + 264


def rstb_find(rs, path):
    _, _, cc, _ = struct.unpack_from('<IIII', rs, 6)
    crc = zlib.crc32(path.encode())
    lo, hi = 0, cc
    while lo < hi:
        mid = (lo + hi) // 2
        if struct.unpack_from('<I', rs, 22 + 8 * mid)[0] < crc:
            lo = mid + 1
        else:
            hi = mid
    if lo >= cc or struct.unpack_from('<I', rs, 22 + 8 * lo)[0] != crc:
        raise SystemExit(f'FAIL: {path} is not in the RSTB')
    return 22 + 8 * lo + 4


def write(out, mod, rel, data):
    p = os.path.join(out, TITLE, mod + '.tmp', 'romfs', *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as f:
        f.write(data)
    print('wrote', p, len(data))


def build(nup, tsv, out):
    _, pk = peek.nup_read(nup, tsv, 'romfs/Pack/ZsDic.pack.zs')
    dic = zstd.ZstdDict(peek.sarc(zstd.decompress(pk))['bcett.byml.zsdic'])
    _, rc = peek.nup_read(nup, tsv, RSTB + '.zs')
    rstb_raw = zstd.decompress(rc)

    applied = {}  # (hash, new) -> times applied in total
    for mod, bancs in MODS.items():
        rs = bytearray(rstb_raw)  # one RSTB per mod
        for banc, changes in bancs.items():
            _, comp = peek.nup_read(nup, tsv, banc + '.zs')
            raw = zstd.decompress(comp, zstd_dict=dic)
            ver, root = byml.load(raw)
            done = []
            for h, orig, new in changes:
                for a in root['Actors']:
                    if a.get('Hash') == h:
                        cur = a['Dynamic'].get('Drop__DropActor')
                        if cur != orig:
                            raise SystemExit(f'FAIL: {banc} {h}: original {cur!r}, expected {orig!r}')
                        a['Dynamic']['Drop__DropActor'] = new
                        done.append((h, new))
                        applied[(h, new)] = applied.get((h, new), 0) + 1
            newraw = byml.dump(root, ver)
            v2, r2 = byml.load(newraw)
            for h, new in done:
                hits = [a for a in r2['Actors'] if a.get('Hash') == h]
                assert hits and all(a['Dynamic']['Drop__DropActor'] == new for a in hits), (banc, h)
                print('OK', h, new, f'({banc})')
            if not done:
                print('(no applicable changes in', banc + ')')
                continue
            newcomp = zstd.compress(newraw, level=19, zstd_dict=dic)
            assert zstd.decompress(newcomp, zstd_dict=dic) == newraw
            off = rstb_find(rs, banc)
            old = struct.unpack_from('<I', rs, off)[0]
            if old != rstb_size(len(raw)):
                raise SystemExit(f'FAIL: RSTB {banc}: {old} != formula {rstb_size(len(raw))}')
            struct.pack_into('<I', rs, off, rstb_size(len(newraw)))
            print('RSTB', banc, old, '->', rstb_size(len(newraw)))
            write(out, mod, banc + '.zs', newcomp)
        write(out, mod, RSTB + '.zs', zstd.compress(bytes(rs), level=19))

    for bancs in MODS.values():
        for changes in bancs.values():
            for h, _, new in changes:
                if not applied.get((h, new)):
                    raise SystemExit(f'FAIL: the change {h} -> {new} was not applied in any map')
    print('All changes applied at least once.')


def main():
    nup, tsv, out = sys.argv[1:4]
    base = os.path.join(out, TITLE)
    for mod in MODS:
        shutil.rmtree(os.path.join(base, mod + '.tmp'), ignore_errors=True)
    try:
        build(nup, tsv, out)
    except BaseException:
        for mod in MODS:
            shutil.rmtree(os.path.join(base, mod + '.tmp'), ignore_errors=True)
        raise
    for mod in MODS:
        shutil.rmtree(os.path.join(base, mod), ignore_errors=True)
        os.rename(os.path.join(base, mod + '.tmp'), os.path.join(base, mod))


if __name__ == '__main__':
    main()
