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


@dataclass(frozen=True)
class SwitchSpec:
    """A query of an actor already in the flow (its query must be in the actor's list),
    with one case per value in `cases`, all starting at the end of the flow. A boolean
    query takes case value 0 when it holds and 1 when it does not; a comparison
    (`EventQueryIsGameDataInt`) gives 0 less, 1 equal, 2 greater (as in the game)."""
    actor: str
    query: str
    params: dict[str, ParamValue] = field(default_factory=dict)
    cases: tuple[int, ...] = (0, 1)


# The parameters every system actor (GameDataActor, ChallengeSystemActor, ...) has
# in the game's flows, in their order.
SYSTEM_ACTOR_PARAMS: dict[str, ParamValue] = {
    'EventMemberCreateMethod': 0, 'IsBindNearestActor': False, 'IsGrounding': False,
    'IsWorld': False, 'UseEventModelAnime': '使用しない', 'UseEventAS': '使用しない'}
_ACTOR = 0x38  # actor slot: name, secondary name, argument name, actions, queries,
#                parameters (u64 pointers), then u16 actions, u16 queries, u16 0xFFFF, u8 1, u8 0


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


def _action_indices(flow: EventFlow, spec: ActionSpec | SwitchSpec) -> tuple[int, int]:
    """(actor, action or query) indices of `spec`."""
    is_query = isinstance(spec, SwitchSpec)
    member = spec.query if is_query else spec.action
    for a, (name, actions, queries) in enumerate(flow.actors):
        if name == spec.actor:
            names = queries if is_query else actions
            if member not in names:
                kind = 'query' if is_query else 'action'
                raise BfevflError(f'Actor {spec.actor!r} has no {kind} {member!r}.')
            return a, names.index(member)
    raise BfevflError(f'The flow has no actor {spec.actor!r}.')


Spec = ActionSpec | SubflowSpec | SwitchSpec


def append_events(data: bytes, specs: Sequence[Spec]) -> tuple[bytes, list[int]]:
    """The file with one new event per spec (indices n, n+1, ...), each with its own
    parameter container. New events end the flow (`next` = 0xFFFF); link them with
    `bfevfl.patch_pointers`. The event array is grown like `grow_events` does; the
    containers, dictionaries, items and new strings go after it, and the RELT is
    rebuilt with every new pointer."""
    flow = EventFlow(data)
    if flow._flowchart is None:
        raise BfevflError('The file has no flowchart.')
    indices = [None if isinstance(s, SubflowSpec) else _action_indices(flow, s)
               for s in specs]
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
        elif isinstance(spec, SwitchSpec):
            actor, query = indices[j]
            struct.pack_into('<BBHHH', out, slot + 8, bfevfl.SWITCH, 0, len(spec.cases),
                             actor, query)
            _align(out, 8)
            cases = len(out)
            out += b''.join(struct.pack('<IHH', v, bfevfl.END, 0) for v in spec.cases)
            w.pointer(slot + 0x18, cases)
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


def set_entry_subflows(data: bytes, entry: str, indices: Sequence[int]) -> bytes:
    """The file with entry point `entry` listing the subflow events `indices`. The
    game only runs subflow calls an entry lists (see `EventFlow.entry_subflows`), so
    a chain with new calls needs this. The new list goes after the relocated data;
    an empty list is a null pointer, as in the game."""
    flow = EventFlow(data)
    e = flow._entry_offset(entry)
    for i in indices:
        if not 0 <= i < len(flow.events) or flow.events[i].kind not in (
                bfevfl.SUBFLOW, bfevfl.SUBFLOW_SWITCH):
            raise BfevflError(f'Event {i} is not a subflow call.')
    _, size, pointers = bfevfl.relocation_table(data)
    out = bytearray(data[:size])
    pointers = set(pointers)
    if indices:
        _align(out, 8)
        at = len(out)
        out += b''.join(struct.pack('<H', i) for i in indices)
        struct.pack_into('<Q', out, e, at)
        pointers.add(e)
    else:
        struct.pack_into('<Q', out, e, 0)
        pointers.discard(e)
    struct.pack_into('<H', out, e + 0x18, len(indices))
    end = len(out)
    reloc = (end + 0xF) & ~0xF
    out += bytes(reloc - end) + bfevfl.build_relocation_table(reloc, end, pointers)
    struct.pack_into('<II', out, 0x18, reloc, len(out))
    return bytes(out)


def _finish(out: bytearray, pointers: set[int]) -> bytes:
    """`out` with a rebuilt RELT after it and the header pointing to it."""
    end = len(out)
    reloc = (end + 0xF) & ~0xF
    out += bytes(reloc - end) + bfevfl.build_relocation_table(reloc, end, pointers)
    struct.pack_into('<II', out, 0x18, reloc, len(out))
    return bytes(out)


def add_actions(data: bytes, pairs: Sequence[tuple[str, str]]) -> bytes:
    """The file with each (actor, action) available to `ActionSpec`: the action is
    added to the first actor with that name, and an actor that is missing is added
    as a system actor (`SYSTEM_ACTOR_PARAMS`, no queries). Existing actor and event
    indices do not change; the file is returned unchanged if nothing is missing."""
    return _add_members(data, pairs, queries=False)


def add_queries(data: bytes, pairs: Sequence[tuple[str, str]]) -> bytes:
    """`add_actions` for queries: each (actor, query) becomes available to `SwitchSpec`."""
    return _add_members(data, pairs, queries=True)


def _add_members(data: bytes, pairs: Sequence[tuple[str, str]], queries: bool) -> bytes:
    # Actor slot: the actions array at +0x18 and count at +0x30, the queries' at +0x20
    # and +0x32; the flowchart's totals at +0x12 (actions) and +0x14 (queries).
    kind = 2 if queries else 1
    arr_at, count_at, total_at = (0x20, 0x32, 0x14) if queries else (0x18, 0x30, 0x12)
    flow = EventFlow(data)
    if flow._flowchart is None:
        raise BfevflError('The file has no flowchart.')
    names = [name for name, _, _ in flow.actors]
    need: dict[str, list[str]] = {}
    for actor, action in pairs:
        if actor in names and action in flow.actors[names.index(actor)][kind]:
            continue
        need.setdefault(actor, [])
        if action not in need[actor]:
            need[actor].append(action)
    if not need:
        return data
    _, size, pointers = bfevfl.relocation_table(data)
    out = bytearray(data[:size])
    pointers = set(pointers)
    w = _Writer(flow, out, pointers)
    fl, n = flow._flowchart, len(flow.actors)
    actors_p = flow._u64(fl + 0x28)
    added = [a for a in need if a not in names]
    if added:
        _align(out, 8)
        new_p = len(out)
        out += data[actors_p:actors_p + _ACTOR * n] + bytes(_ACTOR * len(added))
        for k in range(_ACTOR * n):
            if actors_p + k in pointers:
                pointers.add(new_p + k)
        w.pointer(fl + 0x28, new_p)
        struct.pack_into('<H', out, fl + 0x10, n + len(added))
        actors_p = new_p
    for actor, actions in need.items():
        i = names.index(actor) if actor in names else n + added.index(actor)
        a = actors_p + _ACTOR * i
        old = flow.actors[i][kind] if actor in names else []
        if actor not in names:
            w.pointer(a, w.string(actor))
            w.pointer(a + 0x08, w.string(''))
            w.pointer(a + 0x10, w.string(''))
            w.pointer(a + 0x28, w.container(SYSTEM_ACTOR_PARAMS))
            struct.pack_into('<HHHBB', out, a + 0x30, 0, 0, 0xFFFF, 1, 0)
        old_arr = struct.unpack_from('<Q', out, a + arr_at)[0]
        _align(out, 8)
        arr = len(out)
        out += bytes(8 * (len(old) + len(actions)))
        for j in range(len(old)):
            w.pointer(arr + 8 * j, struct.unpack_from('<Q', out, old_arr + 8 * j)[0])
        for j, action in enumerate(actions):
            w.pointer(arr + 8 * (len(old) + j), w.string(action))
        w.pointer(a + arr_at, arr)
        struct.pack_into('<H', out, a + count_at, len(old) + len(actions))
    total = flow._u16(fl + total_at) + sum(len(v) for v in need.values())
    struct.pack_into('<H', out, fl + total_at, total)
    return _finish(out, pointers)
