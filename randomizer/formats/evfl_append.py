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
from dataclasses import dataclass, field

from randomizer.formats import bfevfl
from randomizer.formats.bfevfl import BfevflError, EventFlow


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


# ---- appending events -------------------------------------------------------

ParamValue = str | int | bool | float
_STRING, _INT, _BOOL, _FLOAT = bfevfl.STRING, bfevfl.INT, bfevfl.BOOL, bfevfl.FLOAT
_BOOL_TRUE = 0x80000001


@dataclass(frozen=True)
class ActionSpec:
    """An action of an actor already in the flow (its action must be in the
    actor's list)."""
    actor: str
    action: str
    params: dict[str, ParamValue] = field(default_factory=dict)


@dataclass(frozen=True)
class SubflowSpec:
    """A call to `entry` of flow `flow` ('' = the same file) with literal params."""
    flow: str
    entry: str
    params: dict[str, ParamValue] = field(default_factory=dict)


def _string_bytes(text: str) -> bytes:
    raw = text.encode('utf-8')
    if len(raw) > 0xFFFF or b'\0' in raw:
        raise BfevflError(f'Invalid text: {text!r}')
    out = struct.pack('<H', len(raw)) + raw + b'\0'
    return out + b'\0' * (len(out) & 1)


def _align(out: bytearray, n: int) -> None:
    out += bytes(-len(out) % n)


class _Writer:
    """Appends blobs after the relocated data and records the new pointers."""

    def __init__(self, flow: EventFlow, out: bytearray, pointers: set[int]) -> None:
        self.flow, self.out, self.pointers = flow, out, pointers
        self._strings: dict[str, int] = {}

    def string(self, text: str) -> int:
        """Offset of a string with that text: an existing one, or a new one."""
        if text in self._strings:
            return self._strings[text]
        if text == '':  # the pool's empty string, as the game's DIC roots use
            return self.flow._pool()[0] + 0x14
        found = self.flow._find_string(text.encode('utf-8'))
        if found is None:
            _align(self.out, 2)
            found = len(self.out)
            self.out += _string_bytes(text)
        self._strings[text] = found
        return found

    def pointer(self, at: int, target: int) -> None:
        struct.pack_into('<Q', self.out, at, target)
        self.pointers.add(at)

    def container(self, params: dict[str, ParamValue]) -> int:
        keys = list(params)
        names = {k: self.string(k) for k in [''] + keys}
        _align(self.out, 8)
        c = len(self.out)
        n = len(keys)
        self.out += struct.pack('<BBHI', bfevfl.CONTAINER, 0, n, 0) + bytes(8 + 8 * n)
        dic = len(self.out)
        self.out += build_dic(keys, names.__getitem__)
        self.pointer(c + 8, dic)
        for j in range(n + 1):
            self.pointers.add(dic + 8 + 0x10 * j + 8)
        for j, key in enumerate(keys):
            _align(self.out, 8)
            it = len(self.out)
            self.pointer(c + 0x10 + 8 * j, it)
            self.out += self._item(it, params[key])
            if self.out[it] == _STRING:
                self.pointers.add(it + 0x10)
        return c

    def _item(self, it: int, value: ParamValue) -> bytes:
        head = struct.pack('<BBHIQ', 0, 0, 1, 0, 0)
        if isinstance(value, bool):
            return bytes([_BOOL]) + head[1:] + struct.pack('<II', _BOOL_TRUE if value else 0, 0)
        if isinstance(value, int):
            return bytes([_INT]) + head[1:] + struct.pack('<iI', value, 0)
        if isinstance(value, float):
            return bytes([_FLOAT]) + head[1:] + struct.pack('<fI', value, 0)
        if isinstance(value, str):
            text = it + 0x18
            return bytes([_STRING]) + head[1:] + struct.pack('<Q', text) + _string_bytes(value)
        raise BfevflError(f'Unsupported parameter value: {value!r}')


def _action_indices(flow: EventFlow, spec: ActionSpec) -> tuple[int, int]:
    for a, (name, actions, _) in enumerate(flow.actors):
        if name == spec.actor:
            if spec.action not in actions:
                raise BfevflError(f'Actor {spec.actor!r} has no action {spec.action!r}.')
            return a, actions.index(spec.action)
    raise BfevflError(f'The flow has no actor {spec.actor!r}.')


def append_events(data: bytes, specs: Sequence[ActionSpec | SubflowSpec]) -> tuple[bytes, list[int]]:
    """The file with one new event per spec (indices n, n+1, ...), each with its own
    parameter container. New events end the flow (`next` = 0xFFFF); link them with
    `bfevfl.patch_pointers`. The event array is grown like `grow_events` does; the
    containers, dictionaries, items and new strings go after it, and the RELT is
    rebuilt with every new pointer."""
    flow = EventFlow(data)
    if flow._flowchart is None:
        raise BfevflError('The file has no flowchart.')
    indices = [_action_indices(flow, s) if isinstance(s, ActionSpec) else None for s in specs]
    template = next((i for i, e in enumerate(flow.events)
                     if e.kind == bfevfl.ACTION and i in flow._params), None)
    if template is None:
        raise BfevflError('The flow has no action with parameters to grow from.')
    n = len(flow.events)
    grown = bfevfl.grow_events(data, [template] * len(specs))
    at, size, pointers = bfevfl.relocation_table(grown)
    gflow = EventFlow(grown)
    out = bytearray(grown[:size])
    pointers = set(pointers)
    w = _Writer(gflow, out, pointers)
    for j, spec in enumerate(specs):
        slot = gflow._events_p + 0x30 * (n + j)
        for off in (0x00, 0x10, 0x18, 0x20):
            pointers.discard(slot + off)
        out[slot:slot + 0x30] = bytes(0x30)
        w.pointer(slot, w.string(f'RandoEvent{n + j}'))
        if isinstance(spec, ActionSpec):
            actor, action = indices[j]
            struct.pack_into('<BBHHH', out, slot + 8, bfevfl.ACTION, 0, bfevfl.END, actor, action)
        else:
            struct.pack_into('<BBHHH', out, slot + 8, bfevfl.SUBFLOW, 0, bfevfl.END, 0, 0)
            w.pointer(slot + 0x18, w.string(spec.flow))
            w.pointer(slot + 0x20, w.string(spec.entry))
        if spec.params:
            w.pointer(slot + 0x10, w.container(spec.params))
    end = len(out)
    reloc = (end + 0xF) & ~0xF
    out += bytes(reloc - end) + bfevfl.build_relocation_table(reloc, end, pointers)
    struct.pack_into('<II', out, 0x18, reloc, len(out))
    return bytes(out), [n + j for j in range(len(specs))]
