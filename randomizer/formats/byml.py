"""Typed BYML v7 reader/writer (little-endian) for TotK-engine files.
Scalars keep their exact BYML type via wrapper classes so a round trip is lossless.
Writer lays nodes out post-order and dedups identical containers / 64-bit values.
"""
import struct

class U32(int): pass        # 0xD3
class I64(int): pass        # 0xD4
class U64(int): pass        # 0xD5
class F64(float): pass      # 0xD6
class F32(float): pass      # 0xD2 (plain python float is also written as F32)
class Bin(bytes): pass      # 0xA1

def _strtab(d, off):
    assert d[off] == 0xC2
    n = int.from_bytes(d[off+1:off+4], 'little')
    out = []
    for i in range(n):
        s = off + struct.unpack_from('<I', d, off + 4 + 4*i)[0]
        out.append(d[s:d.index(b'\0', s)].decode('utf-8'))
    return out

def load(d):
    if d[:2] != b'YB':
        raise ValueError('No es un archivo BYML válido.')
    ver, ko, so, ro = struct.unpack_from('<HIII', d, 2)
    keys = _strtab(d, ko) if ko else []
    strs = _strtab(d, so) if so else []
    def val(t, at):
        v = struct.unpack_from('<I', d, at)[0]
        if t in (0xC0, 0xC1): return node(v)
        if t == 0xA0: return strs[v]
        if t == 0xD0: return bool(v)
        if t == 0xD1: return struct.unpack_from('<i', d, at)[0]
        if t == 0xD2: return F32(struct.unpack_from('<f', d, at)[0])
        if t == 0xD3: return U32(v)
        if t == 0xD4: return I64(struct.unpack_from('<q', d, v)[0])
        if t == 0xD5: return U64(struct.unpack_from('<Q', d, v)[0])
        if t == 0xD6: return F64(struct.unpack_from('<d', d, v)[0])
        if t == 0xA1: return Bin(d[v+4:v+4+struct.unpack_from('<I', d, v)[0]])
        if t == 0xFF: return None
        raise ValueError(f'unknown type {t:#x}')
    def node(off):
        # shared nodes become separate python objects, so editing one actor never aliases another
        t = d[off]; n = int.from_bytes(d[off+1:off+4], 'little')
        if t == 0xC0:
            ts = d[off+4:off+4+n]; base = off + 4 + ((n + 3) & ~3)
            return [val(ts[i], base + 4*i) for i in range(n)]
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = off + 4 + 8*i
                out[keys[int.from_bytes(d[e:e+3], 'little')]] = val(d[e+3], e + 4)
            return out
        raise ValueError(f'unknown node {t:#x}')
    return ver, (node(ro) if ro else None)

def _type(v):
    if isinstance(v, bool): return 0xD0
    if isinstance(v, dict): return 0xC1
    if isinstance(v, list): return 0xC0
    if isinstance(v, str): return 0xA0
    if isinstance(v, U32): return 0xD3
    if isinstance(v, I64): return 0xD4
    if isinstance(v, U64): return 0xD5
    if isinstance(v, F64): return 0xD6
    if isinstance(v, Bin): return 0xA1
    if isinstance(v, float): return 0xD2
    if isinstance(v, int): return 0xD1
    if v is None: return 0xFF
    raise TypeError(type(v))

def _strtab_bytes(lst):
    n = len(lst)
    start = 4 + 4 * (n + 1)
    offs, blob = [], bytearray()
    for s in lst:
        offs.append(start + len(blob)); blob += s.encode() + b'\0'
    offs.append(start + len(blob))
    out = bytearray([0xC2]) + n.to_bytes(3, 'little')
    out += b''.join(struct.pack('<I', o) for o in offs) + blob
    while len(out) % 4: out.append(0)
    return bytes(out)

def dump(root, ver=7):
    keys, strs = set(), set()
    def collect(v):
        if isinstance(v, dict):
            for k, x in v.items(): keys.add(k); collect(x)
        elif isinstance(v, list):
            for x in v: collect(x)
        elif isinstance(v, str): strs.add(v)
    collect(root)
    keys = sorted(keys, key=lambda s: s.encode()); strs = sorted(strs, key=lambda s: s.encode())
    kidx = {k: i for i, k in enumerate(keys)}; sidx = {s: i for i, s in enumerate(strs)}

    out = bytearray(16)
    ko = len(out) if keys else 0
    if keys: out += _strtab_bytes(keys)
    so = len(out) if strs else 0
    if strs: out += _strtab_bytes(strs)
    cache = {}

    def put(blob, align=4):
        o = cache.get(blob)
        if o is None:
            while len(out) % align: out.append(0)
            o = len(out); out.extend(blob); cache[blob] = o
        return o

    def inline(v):
        t = _type(v)
        if t in (0xC0, 0xC1): return emit(v)
        if t == 0xA0: return sidx[v]
        if t == 0xD0: return int(v)
        if t == 0xD1: return struct.unpack('<I', struct.pack('<i', v))[0]
        if t == 0xD2: return struct.unpack('<I', struct.pack('<f', v))[0]
        if t == 0xD3: return int(v)
        if t == 0xD4: return put(struct.pack('<q', v), 8)
        if t == 0xD5: return put(struct.pack('<Q', v), 8)
        if t == 0xD6: return put(struct.pack('<d', v), 8)
        if t == 0xA1: return put(struct.pack('<I', len(v)) + bytes(v))
        if t == 0xFF: return 0
        raise TypeError(t)

    def emit(v):
        if isinstance(v, list):
            n = len(v)
            vals = [inline(x) for x in v]
            body = bytes([0xC0]) + n.to_bytes(3, 'little') + bytes(_type(x) for x in v)
            body += b'\0' * (((n + 3) & ~3) - n)
            body += b''.join(struct.pack('<I', x) for x in vals)
            return put(body)
        items = sorted(v.items(), key=lambda kv: kidx[kv[0]])
        ents = [(kidx[k], _type(x), inline(x)) for k, x in items]
        body = bytes([0xC1]) + len(ents).to_bytes(3, 'little')
        body += b''.join(k.to_bytes(3, 'little') + bytes([t]) + struct.pack('<I', x) for k, t, x in ents)
        return put(body)

    ro = emit(root) if root is not None else 0
    struct.pack_into('<2sHIII', out, 0, b'YB', ver, ko, so, ro)
    while len(out) % 4: out.append(0)
    return bytes(out)
