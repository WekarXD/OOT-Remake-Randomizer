"""Spike: put Item_Hookshot (absent from this map) into a Mido's-house chest via full BYML rewrite + RSTB update.
Usage: python hookshot_test.py <nup> <files.tsv> <mod_romfs_dir>
"""
import sys, os, struct, zlib
from compression import zstd
import peek, byml

BANC = 'Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml'
RSTB = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable'
CHEST_HASH = 4555665598794293658   # Mido's house, blue rupee chest
NEW_DROP = 'Item_Hookshot'

def rstb_size(n):
    return ((n + 31) & ~31) + 264   # matches all 160 vanilla Banc entries

def main():
    nup, tsv, mod = sys.argv[1:4]
    _, pk = peek.nup_read(nup, tsv, 'romfs/Pack/ZsDic.pack.zs')
    dic = zstd.ZstdDict(peek.sarc(zstd.decompress(pk))['bcett.byml.zsdic'])

    _, comp = peek.nup_read(nup, tsv, BANC + '.zs')
    raw = zstd.decompress(comp, zstd_dict=dic)
    ver, root = byml.load(raw)
    hits = [a for a in root['Actors'] if a.get('Hash') == CHEST_HASH]
    assert len(hits) == 1
    print('before:', hits[0]['Dynamic'])
    hits[0]['Dynamic']['Drop__DropActor'] = NEW_DROP
    print('after: ', hits[0]['Dynamic'])
    new = byml.dump(root, ver)
    v2, r2 = byml.load(new)
    assert [a for a in r2['Actors'] if a.get('Hash') == CHEST_HASH][0]['Dynamic']['Drop__DropActor'] == NEW_DROP
    newcomp = zstd.compress(new, level=19, zstd_dict=dic)
    assert zstd.decompress(newcomp, zstd_dict=dic) == new

    _, rc = peek.nup_read(nup, tsv, RSTB + '.zs')
    rs = bytearray(zstd.decompress(rc))
    _, sbs, cc, nc = struct.unpack_from('<IIII', rs, 6)
    crc = zlib.crc32(BANC.encode())
    lo, hi = 0, cc
    while lo < hi:
        mid = (lo + hi) // 2
        if struct.unpack_from('<I', rs, 22 + 8*mid)[0] < crc: lo = mid + 1
        else: hi = mid
    assert struct.unpack_from('<I', rs, 22 + 8*lo)[0] == crc
    old = struct.unpack_from('<I', rs, 22 + 8*lo + 4)[0]
    assert old == rstb_size(len(raw)), (old, len(raw))
    struct.pack_into('<I', rs, 22 + 8*lo + 4, rstb_size(len(new)))
    print('RSTB', old, '->', rstb_size(len(new)), '(byml', len(raw), '->', len(new), ')')

    for rel, data in ((BANC + '.zs', newcomp), (RSTB + '.zs', zstd.compress(bytes(rs), level=19))):
        p = os.path.join(mod, *rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        print('wrote', p, len(data))

if __name__ == '__main__':
    main()
