"""Spike: swap Drop__DropActor of two actors in a bcett BYML by patching string indices in place.
Usage: python swaptest.py <nup> <files.tsv> <banc-suffix> <hashA> <hashB> <out_file>
Same decompressed size -> no ResourceSizeTable change needed.
"""
import sys, struct
from compression import zstd
import peek

def find_drop_slots(b, hashes):
    """Return {hash: (offset_of_u32_value, current_string_index)} for Dynamic.Drop__DropActor."""
    d = b.d
    res = {}
    def dict_entries(off):
        n = int.from_bytes(d[off+1:off+4], 'little')
        for i in range(n):
            e = off + 4 + 8*i
            yield b.keys[int.from_bytes(d[e:e+3], 'little')], d[e+3], e + 4
    root = b.root_off
    for k, t, at in dict_entries(root):
        if k != 'Actors': continue
        arr = struct.unpack_from('<I', d, at)[0]
        n = int.from_bytes(d[arr+1:arr+4], 'little')
        base = arr + 4 + ((n + 3) & ~3)
        for i in range(n):
            aoff = struct.unpack_from('<I', d, base + 4*i)[0]
            h = dyn = None
            for k2, t2, at2 in dict_entries(aoff):
                if k2 == 'Hash': h = b.val(t2, at2)
                if k2 == 'Dynamic': dyn = struct.unpack_from('<I', d, at2)[0]
            if h in hashes and dyn is not None:
                for k3, t3, at3 in dict_entries(dyn):
                    if k3 == 'Drop__DropActor':
                        assert t3 == 0xA0
                        res[h] = (at3, struct.unpack_from('<I', d, at3)[0])
    return res

def main():
    nup, tsv, suffix, ha, hb, out = sys.argv[1:7]
    ha, hb = int(ha), int(hb)
    path, comp = peek.nup_read(nup, tsv, suffix)
    _, pk = peek.nup_read(nup, tsv, 'romfs/Pack/ZsDic.pack.zs')
    dic = zstd.ZstdDict(peek.sarc(zstd.decompress(pk))['bcett.byml.zsdic'])
    raw = zstd.decompress(comp, zstd_dict=dic)
    b = peek.Byml(raw)
    slots = find_drop_slots(b, {ha, hb})
    assert set(slots) == {ha, hb}, slots
    (oa, sa), (ob, sb) = slots[ha], slots[hb]
    print('before:', b.strs[sa], '<->', b.strs[sb])
    buf = bytearray(raw)
    struct.pack_into('<I', buf, oa, sb)
    struct.pack_into('<I', buf, ob, sa)
    assert len(buf) == len(raw)
    newcomp = zstd.compress(bytes(buf), level=19, zstd_dict=dic)
    back = zstd.decompress(newcomp, zstd_dict=dic)
    assert back == bytes(buf)
    b2 = peek.Byml(back)
    chk = find_drop_slots(b2, {ha, hb})
    print('after: ', b2.strs[chk[ha][1]], '<->', b2.strs[chk[hb][1]])
    open(out, 'wb').write(newcomp)
    print('wrote', out, len(newcomp), 'bytes (orig', len(comp), '), decompressed', len(back))
    print('orig dict id', zstd.get_frame_info(comp).dictionary_id, 'new dict id', zstd.get_frame_info(newcomp).dictionary_id)

if __name__ == '__main__':
    main()
