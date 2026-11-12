"""Who calls into an event flow from another file.

A flow entry that another file calls (a cross-file subflow or hash switch, or a scene
transition naming the flow) must not be rewritten as part of the caller's own entry:
its events are shared with the other callers."""
from collections.abc import Mapping

from randomizer.formats.bfevfl import ACTION, SUBFLOW, SUBFLOW_SWITCH, EventFlow

# kind 5 (hash switch) is SUBFLOW_SWITCH in bfevfl.py.
CALL_PARAMS = ('EventName', 'BootEventName')


def entry_callers(flows: Mapping[str, EventFlow]) -> dict[tuple[str, str], set[str]]:
    """(flow, entry) -> names of the other flows that call it.

    Cross-file SUBFLOW / SUBFLOW_SWITCH events call (sub_flow, sub_entry or
    'EntryPoint0'); an ACTION whose `EventName` / `BootEventName` parameter is the name
    of a flow starts that flow at 'EntryPoint0'. Flows without a flowchart are skipped."""
    callers: dict[tuple[str, str], set[str]] = {}
    for name, flow in flows.items():
        if not flow.events:
            continue
        for ev in flow.events:
            target = None
            if ev.kind in (SUBFLOW, SUBFLOW_SWITCH):
                if ev.sub_flow and ev.sub_flow != name:
                    target = (ev.sub_flow, ev.sub_entry or 'EntryPoint0')
            elif ev.kind == ACTION:
                params = flow.action_params(ev.index)
                for key in CALL_PARAMS:
                    value = params.get(key)
                    if isinstance(value, str) and value in flows and value != name:
                        callers.setdefault((value, 'EntryPoint0'), set()).add(name)
            if target:
                callers.setdefault(target, set()).add(name)
    return callers
