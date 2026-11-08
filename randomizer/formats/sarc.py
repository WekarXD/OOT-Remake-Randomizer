"""Lector de archivos SARC (little-endian)."""
import struct


def read(data: bytes) -> dict:
    if data[:4] != b'SARC':
        raise ValueError('No es un archivo SARC válido.')
    hlen, _bom = struct.unpack_from('<HH', data, 4)
    data_off = struct.unpack_from('<I', data, 0xC)[0]
    if data[hlen:hlen + 4] != b'SFAT':
        raise ValueError('SARC dañado: falta la tabla SFAT.')
    n = struct.unpack_from('<H', data, hlen + 6)[0]
    nodes = [struct.unpack_from('<IIII', data, hlen + 0xC + 16 * i) for i in range(n)]
    names = hlen + 0xC + 16 * n + 8
    out = {}
    for _h, attr, s, e in nodes:
        noff = names + (attr & 0xFFFF) * 4
        nm = data[noff:data.index(b'\0', noff)].decode('utf-8')
        out[nm] = data[data_off + s:data_off + e]
    return out
