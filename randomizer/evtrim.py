"""Pure computation of how to trim an event flow (no game data)."""
from randomizer.formats.bfevfl import ACTION, END, Event


def compute_trim(events: list[Event], removable: set[int],
                 roots: set[int] = frozenset()) -> tuple[set[int], dict[int, int]]:
    """Devuelve (removed, retarget).

    Only actions (kind 0) in `removable` are removed. `retarget[i]` is the first
    kept event found by following `next` from i (or 0xFFFF; a cycle of removed
    events ends at 0xFFFF). The following are kept (fixed point):
    - the first action of a fork branch that would resolve to the fork's join
      or to 0xFFFF;
    - the target of a switch case that would resolve to 0xFFFF;
    - the main event of an entry (`roots`) that would resolve to 0xFFFF.
    This way trimming never creates pointers to 0xFFFF that the original did not have.
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
