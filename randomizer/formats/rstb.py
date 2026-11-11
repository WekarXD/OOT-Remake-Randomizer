"""Resource size table (RESTBL)."""
import struct
import zlib


def banc_rstb_size(n: int) -> int:
    return ((n + 31) & ~31) + 264


class Rstb:
    def __init__(self, header, crcs, names):
        self._header = header          # (version, name_block_size)
        self._crcs = crcs              # list [crc, size] sorted by crc
        self._names = names            # list [name, size]

    @classmethod
    def load(cls, data: bytes) -> 'Rstb':
        if data[:6] != b'RESTBL':
            raise ValueError('Not a valid RESTBL table.')
        ver, nbs, cc, nc = struct.unpack_from('<IIII', data, 6)
        pos = 22
        crcs = [list(struct.unpack_from('<II', data, pos + 8 * i)) for i in range(cc)]
        pos += 8 * cc
        names = []
        for i in range(nc):
            o = pos + (nbs + 4) * i
            raw = data[o:o + nbs]
            names.append([raw.split(b'\0', 1)[0].decode('utf-8'),
                          struct.unpack_from('<I', data, o + nbs)[0]])
        return cls((ver, nbs), crcs, names)

    def _find(self, path):
        for e in self._names:
            if e[0] == path:
                return e
        crc = zlib.crc32(path.encode())
        lo, hi = 0, len(self._crcs)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._crcs[mid][0] < crc:
                lo = mid + 1
            else:
                hi = mid
        if lo < len(self._crcs) and self._crcs[lo][0] == crc:
            return self._crcs[lo]
        return None

    def get(self, path: str):
        e = self._find(path)
        return e[1] if e else None

    def set(self, path: str, size: int) -> None:
        e = self._find(path)
        if e is None:
            raise KeyError(path)
        e[1] = size

    def add(self, path: str, size: int) -> None:
        crc = zlib.crc32(path.encode())
        lo, hi = 0, len(self._crcs)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._crcs[mid][0] < crc:
                lo = mid + 1
            else:
                hi = mid
        if lo < len(self._crcs) and self._crcs[lo][0] == crc:
            raise ValueError(f'{path} already exists in the RSTB')
        self._crcs.insert(lo, [crc, size])

    def dump(self) -> bytes:
        ver, nbs = self._header
        out = bytearray(b'RESTBL')
        out += struct.pack('<IIII', ver, nbs, len(self._crcs), len(self._names))
        for crc, size in self._crcs:
            out += struct.pack('<II', crc, size)
        for name, size in self._names:
            out += name.encode().ljust(nbs, b'\0') + struct.pack('<I', size)
        return bytes(out)
