"""BFEVFL (event flow) reader, with pointer and string patchers.

Only the structures needed to walk the event graph are read: locating every
u16 that references an event index and reading the actions' parameters.
`patch_pointers` rewrites those u16s without changing the length;
`set_string_param` repoints a string parameter and, if needed, appends a
string to the end of the pool.

Format (little endian, absolute offsets from the start of the file):

Header (0x00): magic `BFEVFL` + 2 null bytes, u32 version (0x0400), u16 BOM `FF FE`,
u8 alignment (3 = 8 bytes), u8 0; 0x10 u32 offset of the file name
(points into the pool); 0x14 u16 flag (0); 0x16 u16 first block; 0x18 u32 offset
of the RELT table; 0x1C u32 file size; 0x20 u16 number of flowcharts
(0 in the 261 files that only have a timeline); 0x28 u64 pointer to the list
of flowcharts.

`EVFL` flowchart: +4 u32 distance (from the flowchart) to the string pool;
+0x30 u64 events. Events are 0x30 bytes, type at +8. Action (0), switch (1)
and subflow (4) have a u64 at +0x10 pointing to the parameter container (0 if
they have none); the fork (2) uses +0x10 for its list of branches.

Parameter container (type 1): u8 type, u8 0, u16 number of items, u32 0,
u64 `DIC ` dictionary with the names, then one u64 per item. Item j is named
like entry j+1 of the dictionary (entry 0 is the root).
Each item: u8 type, u8 0, u16 number of values, u32 0, u64 0, then the data:
  0 argument: u64 -> string (argument name)
  2 int: i32 (in 8 bytes)          3 bool: u32 (nonzero; true = 0x80000001)
  4 float: f32 (in 8 bytes)        5 string: u64 -> string
  7/8/9 int/bool/float arrays: n x 4 bytes (8-aligned)
  10 string array: n x u64 -> string
  12 actor identifier: u64 -> name, u64 -> subname
Only types 0, 2, 3, 4, 5, 9 and 12 occur in the game. The string of a string
parameter sits right after its item (not in the pool) and no other parameter
shares it; that is why `set_string_param` overwrites it in place when the new
text fits (the file layout stays identical).

String: u16 length, UTF-8 bytes, NUL, padding to 2 bytes.

`STR ` pool: 0x10-byte block header (all zeros), u32 number of strings, the
empty string at +0x14 (not counted) and the rest from +0x18, back to back.

`RELT` table (at the end of the file, 8-aligned): `RELT`, u32 its own
offset, u32 number of sections (1), u32 0; 0x18 section: u64 0, u32 0,
u32 size (= end of the pool), u32 first entry, u32 number of entries;
8-byte entries: u32 offset and u32 mask (bit i = there is a pointer at
offset + 8*i). All pointers lie before the pool, so appending a string to the
end of the pool moves none of them: only the string count, the section size,
the RELT offset (header and the table's own) and the file size need updating.
"""
import struct
from dataclasses import dataclass, field

END = 0xFFFF
ACTION, SWITCH, FORK, JOIN, SUBFLOW = range(5)
# Item types of a parameter container.
(ARG, CONTAINER, INT, BOOL, FLOAT, STRING, WSTRING, INT_ARRAY, BOOL_ARRAY,
 FLOAT_ARRAY, STRING_ARRAY, WSTRING_ARRAY, ACTOR_ID) = range(13)


class BfevflError(Exception):
    pass


@dataclass
class Event:
    index: int
    kind: int
    actor: str | None = None
    action: str | None = None
    query: str | None = None
    next: int | None = None
    cases: list[int] = field(default_factory=list)
    forks: list[int] = field(default_factory=list)
    join: int | None = None


class EventFlow:
    def __init__(self, data: bytes):
        self._d = data
        try:
            self._parse()
        except (struct.error, IndexError) as e:
            raise BfevflError(f'Invalid BFEVFL: {e}') from e

    def _u16(self, o):
        return struct.unpack_from('<H', self._d, o)[0]

    def _u32(self, o):
        return struct.unpack_from('<I', self._d, o)[0]

    def _u64(self, o):
        return struct.unpack_from('<Q', self._d, o)[0]

    def _str(self, p):
        if not p:
            return None
        n = self._u16(p)
        return self._d[p + 2:p + 2 + n].decode('utf-8', 'replace')

    def _parse(self):
        d = self._d
        self._slots: list[tuple[int, int]] = []
        self.events: list[Event] = []
        self.entry_points: dict[str, int] = {}
        self._params: dict[int, int] = {}  # event -> parameter container
        self._flowchart = None
        if self._u16(0x20) == 0:
            return  # file without a flowchart (empty marker)
        f = self._u64(self._u64(0x28))
        if d[f:f + 4] != b'EVFL':
            raise BfevflError('EVFL header missing.')
        n_actors, _, _, n_events, n_entries = (self._u16(f + 0x10 + 2 * i) for i in range(5))
        actors_p, events_p, dic_p, entries_p = (self._u64(f + 0x28 + 8 * i) for i in range(4))

        actors = []
        for i in range(n_actors):
            a = actors_p + 0x38 * i
            acts_p, qs_p = self._u64(a + 0x18), self._u64(a + 0x20)
            actors.append((
                self._str(self._u64(a)),
                [self._str(self._u64(acts_p + 8 * j)) for j in range(self._u16(a + 0x30))],
                [self._str(self._u64(qs_p + 8 * j)) for j in range(self._u16(a + 0x32))],
            ))

        def slot(off):
            v = self._u16(off)
            self._slots.append((off, v))
            return v

        self._flowchart = f
        for i in range(n_events):
            e = events_p + 0x30 * i
            kind = d[e + 8]
            ev = Event(index=i, kind=kind)
            if kind in (ACTION, SWITCH, SUBFLOW) and self._u64(e + 0x10):
                self._params[i] = self._u64(e + 0x10)
            if kind in (ACTION, SWITCH):
                actor, actions, queries = actors[self._u16(e + 0xC)]
                ev.actor = actor
                sub = self._u16(e + 0xE)
                if kind == ACTION:
                    ev.action = actions[sub]
                    ev.next = slot(e + 0xA)
                else:
                    ev.query = queries[sub]
                    cases_p = self._u64(e + 0x18)  # 8-byte cases: u32 value, u16 event
                    ev.cases = [slot(cases_p + 8 * k + 4)
                                for k in range(self._u16(e + 0xA))]
            elif kind == FORK:
                forks_p = self._u64(e + 0x10)
                ev.forks = [slot(forks_p + 2 * k) for k in range(self._u16(e + 0xA))]
                ev.join = slot(e + 0xC)
            elif kind in (JOIN, SUBFLOW):
                ev.next = slot(e + 0xA)
            # Types 5 and 6: markers with only a name/hash; no event pointers.
            self.events.append(ev)

        n_dic = self._u32(dic_p + 4)
        names = [self._str(self._u64(dic_p + 8 + 0x10 * (i + 1) + 8)) for i in range(n_dic)]
        if n_dic != n_entries:
            raise BfevflError('The dictionary and the entries do not match.')
        for i, name in enumerate(names):
            self.entry_points[name] = slot(entries_p + 0x20 * i + 0x1C)

    def pointer_slots(self) -> list[tuple[int, int]]:
        """(offset, current index) of every u16 that references an event."""
        return list(self._slots)

    def _check_index(self, index):
        if not 0 <= index < len(self.events):
            raise BfevflError(f'Event out of range: {index}')

    def _items(self, index) -> list[tuple[str, int]]:
        """(name, item offset) of each parameter of the event."""
        self._check_index(index)
        c = self._params.get(index)
        if c is None:
            return []
        if self._d[c] != CONTAINER:
            raise BfevflError(f'Invalid parameter container in event {index}.')
        n, dic = self._u16(c + 2), self._u64(c + 8)
        if self._u32(dic + 4) != n:
            raise BfevflError(f'Invalid parameter dictionary in event {index}.')
        return [(self._str(self._u64(dic + 8 + 0x10 * (j + 1) + 8)), self._u64(c + 0x10 + 8 * j))
                for j in range(n)]

    def _value(self, it):
        kind, n, v = self._d[it], self._u16(it + 2), it + 0x10
        if kind in (ARG, STRING):
            return self._str(self._u64(v))
        if kind == INT:
            return struct.unpack_from('<i', self._d, v)[0]
        if kind == BOOL:
            return self._u32(v) != 0
        if kind == FLOAT:
            return struct.unpack_from('<f', self._d, v)[0]
        if kind in (INT_ARRAY, BOOL_ARRAY, FLOAT_ARRAY):
            fmt = {INT_ARRAY: 'i', BOOL_ARRAY: 'I', FLOAT_ARRAY: 'f'}[kind]
            vals = struct.unpack_from('<' + fmt * n, self._d, v)
            return [x != 0 for x in vals] if kind == BOOL_ARRAY else list(vals)
        if kind == STRING_ARRAY:
            return [self._str(self._u64(v + 8 * k)) for k in range(n)]
        if kind == ACTOR_ID:
            return (self._str(self._u64(v)), self._str(self._u64(v + 8)))
        raise BfevflError(f'Unsupported parameter type: {kind}')

    def action_params(self, index: int) -> dict[str, object]:
        """Parameters of an action, switch or subflow ({} if it has none).

        Strings and arguments as `str`; int, bool and float as themselves; arrays
        as lists; actor identifier as (name, subname).
        """
        try:
            return {k: self._value(it) for k, it in self._items(index)}
        except (struct.error, IndexError) as e:
            raise BfevflError(f'Invalid parameters in event {index}: {e}') from e

    def _string_slot(self, index, key) -> int:
        """Offset of the u64 that points to the string of the string parameter `key`."""
        for k, it in self._items(index):
            if k == key:
                if self._d[it] != STRING:
                    raise BfevflError(f'Parameter {key!r} of event {index} is not a string.')
                return it + 0x10
        raise BfevflError(f'Event {index} has no parameter {key!r}.')

    def _string_slots(self) -> list[tuple[int, int]]:
        """(event, pointer offset) of all string parameters."""
        return [(i, it + 0x10) for i in sorted(self._params)
                for _, it in self._items(i) if self._d[it] == STRING]

    def _pool(self) -> tuple[int, int]:
        """(start of the pool, end of the pool aligned to 2)."""
        if self._flowchart is None:
            raise BfevflError('The file has no flowchart.')
        p = self._flowchart + self._u32(self._flowchart + 4)
        if self._d[p:p + 4] != b'STR ':
            raise BfevflError('String pool missing.')
        q = p + 0x18
        for _ in range(self._u32(p + 0x10)):
            q += 3 + self._u16(q)
            q += q & 1
        return p, q

    def _find_string(self, value: bytes) -> int | None:
        """An existing string with that text: the pool first, then parameters."""
        p, end = self._pool()
        q = p + 0x18
        while q < end:
            n = self._u16(q)
            if self._d[q + 2:q + 2 + n] == value:
                return q
            q += 3 + n
            q += q & 1
        for _, slot in self._string_slots():
            s = self._u64(slot)
            if self._u16(s) == len(value) and self._d[s + 2:s + 2 + len(value)] == value:
                return s
        return None


def set_string_param(data: bytes, event_index: int, key: str, value: str) -> bytes:
    """Return the file with the event's string parameter `key` changed.

    In order: (1) if the string is the parameter's own copy (as in the
    original game), nobody else points to it and the new text is not longer,
    it is overwritten in place (length, bytes and zeros up to the end of the
    original gap); (2) if an identical string already exists, the parameter is
    repointed to it; (3) otherwise it is appended to the end of the pool,
    repointed, and the string count, the RELT, its section size and the file
    size are adjusted. A shared or pool string is never edited in place.
    """
    flow = EventFlow(data)
    slot = flow._string_slot(event_index, key)
    raw = value.encode('utf-8')
    if len(raw) > 0xFFFF or b'\0' in raw:
        raise BfevflError(f'Invalid text: {value!r}')
    # 1) In place: the parameter's own copy (right after the item), if nobody
    #    else uses it and the new text fits. The file stays identical except
    #    for those bytes: same size, no RSTB update, no repointing.
    old = flow._u64(slot)
    old_len = flow._u16(old)
    sharers = [s for _, s in flow._string_slots() if flow._u64(s) == old]
    if old == slot + 8 and len(sharers) == 1 and len(raw) <= old_len:
        storage_end = old + 3 + old_len
        storage_end += storage_end & 1
        out = bytearray(data)
        out[old:storage_end] = (struct.pack('<H', len(raw)) + raw).ljust(storage_end - old, b'\0')
        return bytes(out)
    # 2) Repoint to an identical string that already exists.
    target = flow._find_string(raw)
    if target is not None:
        out = bytearray(data)
        struct.pack_into('<Q', out, slot, target)
        return bytes(out)

    pool, end = flow._pool()
    reloc = flow._u32(0x18)
    if (data[reloc:reloc + 4] != b'RELT' or reloc < end or any(data[end:reloc])
            or flow._u32(reloc + 0x10 + 0xC) != end):
        raise BfevflError('Unexpected structure between the pool and the RELT.')
    entry = struct.pack('<H', len(raw)) + raw + b'\0'
    entry += b'\0' * (len(entry) & 1)
    new_end = end + len(entry)
    new_reloc = (new_end + 7) & ~7
    out = bytearray(data[:end] + entry + bytes(new_reloc - new_end) + data[reloc:])
    struct.pack_into('<I', out, pool + 0x10, flow._u32(pool + 0x10) + 1)
    struct.pack_into('<II', out, 0x18, new_reloc, len(out))
    struct.pack_into('<I', out, new_reloc + 4, new_reloc)
    struct.pack_into('<I', out, new_reloc + 0x10 + 0xC, new_end)
    struct.pack_into('<Q', out, slot, end)
    return bytes(out)


def string_param_owners(data: bytes, event_index: int, key: str) -> list[int]:
    """Events with a string parameter that points to the same string.

    Includes the event itself. In the original game each string parameter has
    its own copy, so this gives [event_index]; after a string is reused it can
    give more. `set_string_param` only changes the requested event, but anyone
    editing the string in place would change all of them.
    """
    flow = EventFlow(data)
    target = flow._u64(flow._string_slot(event_index, key))
    return sorted({i for i, slot in flow._string_slots() if flow._u64(slot) == target})


def patch_pointers(data: bytes, new_targets: dict[int, int]) -> bytes:
    """Rewrite each u16 at its offset with its new index."""
    out = bytearray(data)
    for off, idx in new_targets.items():
        if not 0 <= idx <= 0xFFFF:
            raise ValueError(f'Index out of range: {idx}')
        struct.pack_into('<H', out, off, idx)
    return bytes(out)
