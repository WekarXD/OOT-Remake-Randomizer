"""Lector de BFEVFL (flujos de eventos), parcheador de punteros y de textos.

Solo se leen las estructuras necesarias para recorrer el grafo de eventos,
localizar cada u16 que referencia un índice de evento y leer los parámetros de
las acciones. `patch_pointers` reescribe esos u16 sin cambiar la longitud;
`set_string_param` reapunta un parámetro de texto y, si hace falta, añade una
cadena al final del pool.

Formato (little endian, offsets absolutos desde el inicio del archivo):

Cabecera (0x00): magic `BFEVFL` + 2 bytes nulos, u32 versión (0x0400), u16 BOM `FF FE`,
u8 alineación (3 = 8 bytes), u8 0; 0x10 u32 offset del nombre del archivo
(apunta al pool); 0x14 u16 flag (0); 0x16 u16 primer bloque; 0x18 u32 offset
de la tabla RELT; 0x1C u32 tamaño del archivo; 0x20 u16 nº de flowcharts
(0 en los 261 archivos que solo tienen timeline); 0x28 u64 puntero a la lista
de flowcharts.

Flowchart `EVFL`: +4 u32 distancia (desde el flowchart) al pool de cadenas;
+0x30 u64 eventos. Eventos de 0x30 bytes, tipo en +8. Acción (0), switch (1)
y subflujo (4) tienen en +0x10 un u64 al contenedor de parámetros (0 si no
tienen); el fork (2) usa +0x10 para su lista de ramas.

Contenedor de parámetros (tipo 1): u8 tipo, u8 0, u16 nº de elementos, u32 0,
u64 diccionario `DIC ` con los nombres, y luego un u64 por elemento. El
elemento j se llama como la entrada j+1 del diccionario (la 0 es la raíz).
Cada elemento: u8 tipo, u8 0, u16 nº de valores, u32 0, u64 0, y los datos:
  0 argumento: u64 -> cadena (nombre del argumento)
  2 int: i32 (en 8 bytes)          3 bool: u32 (≠0; verdadero = 0x80000001)
  4 float: f32 (en 8 bytes)        5 texto: u64 -> cadena
  7/8/9 arrays de int/bool/float: n × 4 bytes (alineado a 8)
  10 array de textos: n × u64 -> cadena
  12 identificador de actor: u64 -> nombre, u64 -> subnombre
En el juego solo aparecen los tipos 0, 2, 3, 4, 5, 9 y 12. La cadena de un
parámetro de texto está justo detrás de su elemento (no en el pool) y ninguna
la comparte otro parámetro.

Cadena: u16 longitud, bytes UTF-8, NUL, relleno a 2 bytes.

Pool `STR `: cabecera de bloque de 0x10 (todo ceros), u32 nº de cadenas, la
cadena vacía en +0x14 (no se cuenta) y desde +0x18 las demás, seguidas.

Tabla `RELT` (al final del archivo, alineada a 8): `RELT`, u32 su propio
offset, u32 nº de secciones (1), u32 0; sección de 0x18: u64 0, u32 0,
u32 tamaño (= fin del pool), u32 primera entrada, u32 nº de entradas;
entradas de 8 bytes: u32 offset y u32 máscara (bit i = hay un puntero en
offset + 8·i). Todos los punteros están antes del pool, así que añadir una
cadena al final del pool no mueve ninguno: solo hay que actualizar el nº de
cadenas, el tamaño de la sección, el offset de la RELT (cabecera y propia
tabla) y el tamaño del archivo.
"""
import struct
from dataclasses import dataclass, field

END = 0xFFFF
ACTION, SWITCH, FORK, JOIN, SUBFLOW = range(5)
# Tipos de elemento de un contenedor de parámetros.
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
        self._params: dict[int, int] = {}  # evento -> contenedor de parámetros
        self._flowchart = None
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

    def _check_index(self, index):
        if not 0 <= index < len(self.events):
            raise BfevflError(f'Evento fuera de rango: {index}')

    def _items(self, index) -> list[tuple[str, int]]:
        """(nombre, offset del elemento) de cada parámetro del evento."""
        self._check_index(index)
        c = self._params.get(index)
        if c is None:
            return []
        if self._d[c] != CONTAINER:
            raise BfevflError(f'Contenedor de parámetros inválido en el evento {index}.')
        n, dic = self._u16(c + 2), self._u64(c + 8)
        if self._u32(dic + 4) != n:
            raise BfevflError(f'Diccionario de parámetros inválido en el evento {index}.')
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
        raise BfevflError(f'Tipo de parámetro no soportado: {kind}')

    def action_params(self, index: int) -> dict[str, object]:
        """Parámetros de una acción, switch o subflujo ({} si no tiene).

        Textos y argumentos como `str`; int, bool y float como tales; arrays
        como listas; identificador de actor como (nombre, subnombre).
        """
        try:
            return {k: self._value(it) for k, it in self._items(index)}
        except (struct.error, IndexError) as e:
            raise BfevflError(f'Parámetros inválidos en el evento {index}: {e}') from e

    def _string_slot(self, index, key) -> int:
        """Offset del u64 que apunta a la cadena del parámetro de texto `key`."""
        for k, it in self._items(index):
            if k == key:
                if self._d[it] != STRING:
                    raise BfevflError(f'El parámetro {key!r} del evento {index} no es texto.')
                return it + 0x10
        raise BfevflError(f'El evento {index} no tiene el parámetro {key!r}.')

    def _string_slots(self) -> list[tuple[int, int]]:
        """(evento, offset del puntero) de todos los parámetros de texto."""
        return [(i, it + 0x10) for i in sorted(self._params)
                for _, it in self._items(i) if self._d[it] == STRING]

    def _pool(self) -> tuple[int, int]:
        """(inicio del pool, fin del pool alineado a 2)."""
        if self._flowchart is None:
            raise BfevflError('El archivo no tiene flowchart.')
        p = self._flowchart + self._u32(self._flowchart + 4)
        if self._d[p:p + 4] != b'STR ':
            raise BfevflError('Falta el pool de cadenas.')
        q = p + 0x18
        for _ in range(self._u32(p + 0x10)):
            q += 3 + self._u16(q)
            q += q & 1
        return p, q

    def _find_string(self, value: bytes) -> int | None:
        """Una cadena ya existente con ese texto: primero el pool, luego parámetros."""
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
    """Devuelve el archivo con el parámetro de texto `key` del evento cambiado.

    Solo se reescribe el puntero de ese parámetro (nunca la cadena en sí, que
    podría compartir otro). Si ya hay una cadena igual se reapunta a ella y el
    tamaño no cambia; si no, se añade al final del pool y se ajustan el nº de
    cadenas, la RELT, el tamaño de su sección y el del archivo.
    """
    flow = EventFlow(data)
    slot = flow._string_slot(event_index, key)
    raw = value.encode('utf-8')
    if len(raw) > 0xFFFF or b'\0' in raw:
        raise BfevflError(f'Texto no válido: {value!r}')
    target = flow._find_string(raw)
    if target is not None:
        out = bytearray(data)
        struct.pack_into('<Q', out, slot, target)
        return bytes(out)

    pool, end = flow._pool()
    reloc = flow._u32(0x18)
    if (data[reloc:reloc + 4] != b'RELT' or reloc < end or any(data[end:reloc])
            or flow._u32(reloc + 0x10 + 0xC) != end):
        raise BfevflError('Estructura inesperada entre el pool y la RELT.')
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
    """Eventos con algún parámetro de texto que apunta a la misma cadena.

    Incluye el propio evento. En el juego original cada parámetro de texto
    tiene su propia copia, así que da [event_index]; tras reutilizar una cadena
    puede dar más. `set_string_param` solo cambia el evento pedido, pero quien
    editara la cadena en sitio cambiaría todos.
    """
    flow = EventFlow(data)
    target = flow._u64(flow._string_slot(event_index, key))
    return sorted({i for i, slot in flow._string_slots() if flow._u64(slot) == target})


def patch_pointers(data: bytes, new_targets: dict[int, int]) -> bytes:
    """Reescribe cada u16 en `desplazamiento` con su nuevo índice."""
    out = bytearray(data)
    for off, idx in new_targets.items():
        if not 0 <= idx <= 0xFFFF:
            raise ValueError(f'Índice fuera de rango: {idx}')
        struct.pack_into('<H', out, off, idx)
    return bytes(out)
