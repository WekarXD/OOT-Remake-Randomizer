"""The analysed-event table (`RSDB/GameAnalyzedEventInfo`): each event's `SubFlowList`
names every flow it can call. The game skips a call to a flow missing from that list
(test batch 27d), so a patch that makes an event call a new flow must add it there.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable

from randomizer.formats.bfevfl import EventFlow

ANALYZED_INFO = 'RSDB/GameAnalyzedEventInfo.Product.111.rstbl.byml.zs'


def subflow_closure(load: Callable[[str], EventFlow | None],
                    calls: Iterable[tuple[str, str]], skip: str = '') -> list[str]:
    """Sorted names of every flow reached from `calls` ((flow, entry) pairs),
    following each entry's subflow list recursively; `load(name)` gives a flow
    (None if missing) and `skip` is left out (the event's own flow). This is the
    event's `SubFlowList` in `ANALYZED_INFO`."""
    flows: dict[str, EventFlow | None] = {}
    seen: set[tuple[str, str]] = set()
    stack = list(calls)
    while stack:
        name, entry = stack.pop()
        if (name, entry) in seen:
            continue
        seen.add((name, entry))
        if name not in flows:
            flows[name] = load(name)
        flow = flows[name]
        if flow is None or entry not in flow.entry_points:
            continue
        for i in flow.entry_subflows(entry):
            ev = flow.events[i]
            stack.append((ev.sub_flow or name, ev.sub_entry))
    return sorted({name for name, _ in seen} - {skip})
