"""Reader for SARC files (little-endian)."""
import struct


def read(data: bytes) -> dict:
    if data[:4] != b'SARC':
        raise ValueError('Not a valid SARC file.')
    hlen, _bom = struct.unpack_from('<HH', data, 4)
    data_off = struct.unpack_from('<I', data, 0xC)[0]
    if data[hlen:hlen + 4] != b'SFAT':
        raise ValueError('Corrupt SARC: SFAT table missing.')
    n = struct.unpack_from('<H', data, hlen + 6)[0]
    nodes = [struct.unpack_from('<IIII', data, hlen + 0xC + 16 * i) for i in range(n)]
    names = hlen + 0xC + 16 * n + 8
    out = {}
    for _h, attr, s, e in nodes:
        noff = names + (attr & 0xFFFF) * 4
        nm = data[noff:data.index(b'\0', noff)].decode('utf-8')
        out[nm] = data[data_off + s:data_off + e]
    return out


def _name_hash(name: str, key: int = 0x65) -> int:
    h = 0
    for c in name.encode('utf-8'):
        h = (h * key + c) & 0xFFFFFFFF
    return h


def write(files: dict, align: int = 8, data_align: int = 0x20) -> bytes:
    """Write a little-endian SARC; nodes sorted by name hash."""
    names = sorted(files, key=_name_hash)
    sfnt = bytearray()
    offs = {}
    for n in names:
        offs[n] = len(sfnt)
        sfnt += n.encode('utf-8') + b'\0'
        sfnt += b'\0' * (-len(sfnt) % 4)
    hdr_len = 0x14 + 0xC + 16 * len(names) + 8 + len(sfnt)
    data_off = -(-hdr_len // data_align) * data_align
    data = bytearray()
    nodes = []
    for n in names:
        data += b'\0' * (-len(data) % align)
        start = len(data)
        data += files[n]
        nodes.append((_name_hash(n), 0x01000000 | (offs[n] // 4), start, len(data)))
    out = bytearray(b'SARC')
    out += struct.pack('<HHIIHH', 0x14, 0xFEFF, 0, data_off, 0x100, 0)
    out += b'SFAT' + struct.pack('<HHI', 0xC, len(names), 0x65)
    for nd in nodes:
        out += struct.pack('<IIII', *nd)
    out += b'SFNT' + struct.pack('<HH', 8, 0) + sfnt
    out += b'\0' * (data_off - len(out))
    out += data
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)
