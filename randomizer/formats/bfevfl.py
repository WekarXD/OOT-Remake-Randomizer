"""Lector de BFEVFL (flujos de eventos) y parcheador de punteros in situ.

Solo se leen las estructuras necesarias para recorrer el grafo de eventos y
localizar cada u16 que referencia un índice de evento; el archivo no se
reconstruye, solo se reescriben esos u16 (la longitud no cambia).
"""
import struct
from dataclasses import dataclass, field

END = 0xFFFF
ACTION, SWITCH, FORK, JOIN, SUBFLOW = range(5)


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
            raise BfevflError(f'BFEVFL inválido: {e}') from e

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
        if self._u16(0x20) == 0:
            return  # archivo sin flowchart (marcador vacío)
        f = self._u64(self._u64(0x28))
        if d[f:f + 4] != b'EVFL':
            raise BfevflError('Falta la cabecera EVFL.')
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

        for i in range(n_events):
            e = events_p + 0x30 * i
            kind = d[e + 8]
            ev = Event(index=i, kind=kind)
            if kind in (ACTION, SWITCH):
                actor, actions, queries = actors[self._u16(e + 0xC)]
                ev.actor = actor
                sub = self._u16(e + 0xE)
                if kind == ACTION:
                    ev.action = actions[sub]
                    ev.next = slot(e + 0xA)
                else:
                    ev.query = queries[sub]
                    cases_p = self._u64(e + 0x18)  # casos de 8 bytes: u32 valor, u16 evento
                    ev.cases = [slot(cases_p + 8 * k + 4)
                                for k in range(self._u16(e + 0xA))]
            elif kind == FORK:
                forks_p = self._u64(e + 0x10)
                ev.forks = [slot(forks_p + 2 * k) for k in range(self._u16(e + 0xA))]
                ev.join = slot(e + 0xC)
            elif kind in (JOIN, SUBFLOW):
                ev.next = slot(e + 0xA)
            # Tipos 5 y 6: marcadores solo con nombre/hash; sin punteros a eventos.
            self.events.append(ev)

        n_dic = self._u32(dic_p + 4)
        names = [self._str(self._u64(dic_p + 8 + 0x10 * (i + 1) + 8)) for i in range(n_dic)]
        if n_dic != n_entries:
            raise BfevflError('El diccionario y las entradas no coinciden.')
        for i, name in enumerate(names):
            self.entry_points[name] = slot(entries_p + 0x20 * i + 0x1C)

    def pointer_slots(self) -> list[tuple[int, int]]:
        """(desplazamiento, índice actual) de cada u16 que referencia un evento."""
        return list(self._slots)


def patch_pointers(data: bytes, new_targets: dict[int, int]) -> bytes:
    """Reescribe cada u16 en `desplazamiento` con su nuevo índice."""
    out = bytearray(data)
    for off, idx in new_targets.items():
        if not 0 <= idx <= 0xFFFF:
            raise ValueError(f'Índice fuera de rango: {idx}')
        struct.pack_into('<H', out, off, idx)
    return bytes(out)
