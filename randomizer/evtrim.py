"""Cálculo puro del recorte de un flujo de eventos (sin datos del juego)."""
from randomizer.formats.bfevfl import ACTION, END, Event


def compute_trim(events: list[Event], removable: set[int]) -> tuple[set[int], dict[int, int]]:
    """Devuelve (removed, retarget).

    Solo se quitan acciones (kind 0) de `removable`. `retarget[i]` es el primer
    evento conservado al seguir `next` desde i (o 0xFFFF; un ciclo de quitados
    acaba en 0xFFFF). La primera acción de una rama de fork que se resolvería
    al join del fork o a 0xFFFF se conserva (punto fijo).
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

    changed = True
    while changed:
        changed = False
        for ev in events:
            for b in ev.forks:
                if b in removed and resolve(b) in (ev.join, END):
                    removed.discard(b)
                    changed = True

    return removed, {i: resolve(i) for i in sorted(removed)}
