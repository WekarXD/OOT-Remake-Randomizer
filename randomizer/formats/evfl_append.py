"""Append new events with their own parameters to a BFEVFL flow.

`bfevfl.py` can change existing values and copy events within a file; this
module adds events that did not exist, each with a parameter container built
from scratch. That needs the container's `DIC ` dictionary, Nintendo's radix
tree (ResDic):

- `DIC `, u32 count, then count + 1 entries of 0x10 bytes: s32 bit index,
  u16 left, u16 right, u64 pointer to the name. Entry 0 is the root (bit -1,
  empty name); entry j + 1 names parameter item j.
- Bit i of a key is bit (i % 8) of the byte i // 8 counted from the END of the
  key, 0 past its length. A new key's bit is the lowest bit where it differs
  from the key its search reaches; it is inserted on the search path before the
  first node whose bit is higher (or before a back link). The child it goes to
  on its own bit points to itself, the other child to the replaced link.

`build_dic` reproduces every dictionary of the game byte for byte (see
tests/test_evfl_append.py).
"""
from __future__ import annotations

import struct
from collections.abc import Callable, Sequence


def _bit(key: bytes, i: int) -> int:
    k = i >> 3
    if k >= len(key):
        return 0
    return (key[len(key) - 1 - k] >> (i & 7)) & 1


def _first_diff(a: bytes, b: bytes) -> int:
    for k in range(max(len(a), len(b))):
        x = (a[len(a) - 1 - k] if k < len(a) else 0) ^ (b[len(b) - 1 - k] if k < len(b) else 0)
        if x:
            return 8 * k + ((x & -x).bit_length() - 1)
    raise ValueError('Duplicate key in a DIC.')


def build_dic(keys: Sequence[str], name_ptr: Callable[[str], int]) -> bytes:
    """The `DIC ` block for `keys` (in item order). `name_ptr(name)` gives the
    offset of each name's string; the root uses `name_ptr('')`."""
    names = [b''] + [k.encode('utf-8') for k in keys]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate key in a DIC.')
    bits = [-1]
    children = [[0, 0]]  # [left, right] per entry
    for idx in range(1, len(names)):
        key = names[idx]
        # Search: the entry the key reaches.
        prev, cur = 0, children[0][0]
        while bits[cur] > bits[prev]:
            prev, cur = cur, children[cur][_bit(key, bits[cur])]
        bit = _first_diff(key, names[cur])
        # Insert on the path before the first higher bit or back link.
        parent, side = 0, 0
        cur = children[0][0]
        while bits[cur] > bits[parent] and bits[cur] < bit:
            parent = cur
            side = _bit(key, bits[cur])
            cur = children[cur][side]
        own = _bit(key, bit)
        node = [0, 0]
        node[own], node[1 - own] = idx, cur
        bits.append(bit)
        children.append(node)
        children[parent][side] = idx
    out = bytearray(b'DIC ' + struct.pack('<I', len(keys)))
    for j, name in enumerate(names):
        out += struct.pack('<iHHQ', bits[j], children[j][0], children[j][1],
                           name_ptr(name.decode('utf-8')))
    return bytes(out)
