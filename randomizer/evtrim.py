"""Cálculo puro del recorte de un flujo de eventos (sin datos del juego)."""
from randomizer.formats.bfevfl import ACTION, END, Event


def compute_trim(events: list[Event], removable: set[int],
                 roots: set[int] = frozenset()) -> tuple[set[int], dict[int, int]]:
    """Devuelve (removed, retarget).

    Solo se quitan acciones (kind 0) de `removable`. `retarget[i]` es el primer
    evento conservado al seguir `next` desde i (o 0xFFFF; un ciclo de quitados
    acaba en 0xFFFF). Se conserva (punto fijo):
    - la primera acción de una rama de fork que se resolvería al join del
      fork o a 0xFFFF;
    - el destino de un caso de switch que se resolvería a 0xFFFF;
    - el evento principal de una entrada (`roots`) que se resolvería a 0xFFFF.
    Así el recorte nunca crea punteros a 0xFFFF que el original no tenía.
    """
    removed = {i for i in removable
               if 0 <= i < len(events) and events[i].kind == ACTION}

    def resolve(i: int) -> int:
        seen = set()
        while i in removed:
            if i in seen:
                return END
            seen.add(i)
            nxt = events[i].next
            i = END if nxt is None else nxt
        return i

    def keep_if(i: int, bad: tuple[int, ...]) -> bool:
        if i in removed and resolve(i) in bad:
            removed.discard(i)
            return True
        return False

    changed = True
    while changed:
        changed = False
        for i in roots:
            changed |= keep_if(i, (END,))
        for ev in events:
            for b in ev.forks:
                changed |= keep_if(b, (ev.join, END))
            for c in ev.cases:
                changed |= keep_if(c, (END,))

    return removed, {i: resolve(i) for i in sorted(removed)}
