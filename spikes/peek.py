"""Spike: extract one romfs file from the NUP, undo TotK-style zstd(+dict), parse BYML/SARC.
Usage: python peek.py <nup> <files.tsv> <romfs-path-suffix> [out.json]
"""
import sys, struct, json, io
from compression import zstd

def nup_read(nup, tsv, suffix):
    for line in open(tsv, encoding='utf-8'):
        path, size, eo, es, codec = line.rstrip('\n').split('\t')
        if path.startswith('p1/') and path.endswith(suffix):
            break
    else:
        raise SystemExit('not found: ' + suffix)
    with open(nup, 'rb') as f:
        f.seek(int(eo)); data = f.read(int(es))
    if codec == '1':
        data = zstd.decompress(data)
    return path, data

def sarc(data):
    assert data[:4] == b'SARC'
    hlen, bom = struct.unpack_from('<HH', data, 4)
    data_off = struct.unpack_from('<I', data, 0xC)[0]
    o = hlen
    assert data[o:o+4] == b'SFAT'
    _, n, _ = struct.unpack_from('<HHI', data, o + 4)
    nodes = [struct.unpack_from('<IIII', data, o + 0xC + 16 * i) for i in range(n)]
    sfnt = o + 0xC + 16 * n
    names = sfnt + 8
    out = {}
    for h, attr, s, e in nodes:
        noff = names + (attr & 0xFFFF) * 4
        nm = data[noff:data.index(b'\0', noff)].decode()
        out[nm] = data[data_off + s:data_off + e]
    return out

class Byml:
    def __init__(self, d):
        self.d = d
        assert d[:2] == b'YB', d[:4]
        self.ver, self.keys_off, self.str_off, self.root_off = struct.unpack_from('<HIII', d, 2)
        self.keys = self.strtab(self.keys_off) if self.keys_off else []
        self.strs = self.strtab(self.str_off) if self.str_off else []
    def strtab(self, off):
        d = self.d; assert d[off] == 0xC2
        n = int.from_bytes(d[off+1:off+4], 'little')
        res = []
        for i in range(n):
            s = off + struct.unpack_from('<I', d, off + 4 + 4*i)[0]
            res.append(d[s:d.index(b'\0', s)].decode('utf-8', 'replace'))
        return res
    def root(self):
        return self.node(self.d[self.root_off], self.root_off) if self.root_off else None
    def val(self, t, raw_at):
        d = self.d
        v = struct.unpack_from('<I', d, raw_at)[0]
        if t in (0xC0, 0xC1, 0xC8, 0xC9, 0xC4, 0xC5): return self.node(d[v], v)
        if t == 0xA0: return self.strs[v]
        if t == 0xD0: return bool(v)
        if t == 0xD1: return struct.unpack_from('<i', d, raw_at)[0]
        if t == 0xD2: return struct.unpack_from('<f', d, raw_at)[0]
        if t == 0xD3: return v
        if t == 0xD4: return struct.unpack_from('<q', d, v)[0]
        if t == 0xD5: return struct.unpack_from('<Q', d, v)[0]
        if t == 0xD6: return struct.unpack_from('<d', d, v)[0]
        if t == 0xA1: return 'bin:' + d[v+4:v+4+struct.unpack_from('<I', d, v)[0]].hex()
        if t == 0xFF: return None
        return f'?type{t:02X}:{v}'
    def node(self, t, off):
        d = self.d
        n = int.from_bytes(d[off+1:off+4], 'little')
        if t == 0xC0:
            types = d[off+4:off+4+n]
            base = off + 4 + ((n + 3) & ~3)
            return [self.val(types[i], base + 4*i) for i in range(n)]
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = off + 4 + 8*i
                k = int.from_bytes(d[e:e+3], 'little'); vt = d[e+3]
                out[self.keys[k]] = self.val(vt, e + 4)
            return out
        return f'?node{t:02X}'

def main():
    nup, tsv, suffix = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    path, data = nup_read(nup, tsv, suffix)
    if path.endswith('.zs'):
        _, pk = nup_read(nup, tsv, 'romfs/Pack/ZsDic.pack.zs')
        dicts = sarc(zstd.decompress(pk))
        print('dicts:', list(dicts), file=sys.stderr)
        name = 'bcett.byml.zsdic' if path.endswith('.bcett.byml.zs') else ('pack.zsdic' if path.endswith('.pack.zs') else 'zs.zsdic')
        data = zstd.decompress(data, zstd_dict=zstd.ZstdDict(dicts[name]))
    print(path, len(data), data[:8], file=sys.stderr)
    if data[:2] == b'YB':
        obj = Byml(data).root()
        s = json.dumps(obj, ensure_ascii=False, indent=1)
        if out: open(out, 'w', encoding='utf-8').write(s)
        else: print(s[:3000])
    elif data[:4] == b'SARC':
        for k, v in sarc(data).items(): print(k, len(v), v[:4])

if __name__ == '__main__':
    main()
