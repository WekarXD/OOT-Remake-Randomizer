"""Full cutscene skip: action table loader and effects-only event flow rewriter."""
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

from randomizer.formats.bfevfl import (ACTION, END, FORK, JOIN, RESULT, SUBFLOW, SUBFLOW_SWITCH,
                                       SWITCH, Event, EventFlow, patch_pointers)

SWITCHES = (SWITCH, SUBFLOW_SWITCH)  # kinds whose edges are `cases`

TABLE_PATH = Path(__file__).resolve().parent / 'data' / 'skip_actions.json'


class SkipTable:
    def __init__(self, data):
        self.actions = data.get('actions', {})
        self.actor_actions = data.get('actor_actions', {})
        self.queries = data.get('queries', {})
        self.subflows_drop = list(data.get('subflows_drop', []))

    @classmethod
    def load(cls, path=TABLE_PATH):
        with open(path, encoding='utf-8') as f:
            return cls(json.load(f))

    def keeps(self, actor, action):
        """True if the action must stay. Unknown and 'review' actions are kept."""
        cls = self.actor_actions.get(f'{actor}.{action}') if actor else None
        if cls is None:
            cls = self.actions.get(action)
        return cls != 'drop'

    def collapses(self, query):
        return self.queries.get(query) == 'collapse'

    def drops_subflow(self, flow, entry):
        name = f'{flow}/{entry}'
        return any(fnmatchcase(name, p) for p in self.subflows_drop)


# --- Effects-only rewriter -------------------------------------------------


class _Fail(Exception):
    def __init__(self, error, detail=''):
        super().__init__(error)
        self.error, self.detail = error, detail


@dataclass
class Rewrite:
    links: dict[tuple, int]
    kept: list[int]
    error: str | None = None
    detail: str = ''  # what failed, for reports (empty when error is None)
    collapsed: dict[int, int] = field(default_factory=dict)  # switch -> case followed


def reachable_chosen(events, entries, starts: Iterable[int],
                     chosen: Mapping[int, int]) -> set[int]:
    """Like `reachable`, but a switch listed in `chosen` only follows that case."""
    seen, todo = set(), list(starts)
    while todo:
        i = todo.pop()
        if i == END or i in seen:
            continue
        seen.add(i)
        ev = events[i]
        if ev.kind in SWITCHES:
            todo += [ev.cases[chosen[i]]] if i in chosen else ev.cases
            if ev.kind == SUBFLOW_SWITCH and ev.sub_flow == '' and ev.sub_entry in entries:
                todo.append(entries[ev.sub_entry])
        elif ev.kind == FORK:
            todo += ev.forks + [ev.join]
        else:
            if ev.next is not None:
                todo.append(ev.next)
            if ev.kind == SUBFLOW and ev.sub_flow == '' and ev.sub_entry in entries:
                todo.append(entries[ev.sub_entry])
    return seen


def reachable(events, entries, starts: Iterable[int]) -> set[int]:
    """Events reachable from `starts`: next, cases, forks, joins, same-file subflows
    (also those a subflow switch calls)."""
    return reachable_chosen(events, entries, starts, {})


def linearize(events: list[Event], entries: dict[str, int], entry: str,
              keep: Callable[[Event], bool], collapse: Callable[[Event], bool],
              choices: Mapping[int, int] = {}, protected: frozenset[int] = frozenset()
              ) -> Rewrite:
    """Relink the walk from `entry` so that it only passes through kept nodes.

    The walk carries a continuation stack: ('sub', next, entry) frames for
    inlined same-file subflows and ('fork', fork, branch) frames for fork
    branches (branches run one after another, then what follows the join).
    Between two kept nodes the walk is a single path, so revisiting the same
    (event, stack) there is a loop. A kept node's successors depend only on
    (node, stack), which is expanded once.

    A subflow switch is never kept: it collapses like a switch (`choose`), so
    the entry it calls does not run. A result ends the entry with the value
    its caller switches on: at the top level it is a kept terminal; inside an
    inlined call or a fork branch it is refused (nothing could follow it).
    """
    collapsed: dict[int, int] = {}

    def is_kept(ev):
        if ev.kind == ACTION:
            return keep(ev)
        if ev.kind == SUBFLOW:
            return ev.sub_flow != '' and keep(ev)
        return ev.kind == SWITCH and not collapse(ev)

    def choose(i):
        """Case a collapsing switch follows: the choice if given. Otherwise, among
        the cases that do not lead back to the switch (a question asked again)
        or all of them if every case does: the first with kept nodes of its own
        (not reached by every candidate), else the first with any kept node,
        else the first candidate."""
        if i in collapsed:
            return collapsed[i]
        ev = events[i]
        if i in choices:
            k = choices[i]
            if not 0 <= k < len(ev.cases):
                raise ValueError(f'Switch {i} has no case {k}.')
        else:
            reach = [reachable_chosen(events, entries, [c], collapsed) for c in ev.cases]
            cand = [k for k, r in enumerate(reach) if i not in r] or list(range(len(reach)))
            sets = {k: {j for j in reach[k] if is_kept(events[j])} for k in cand}
            common = set.intersection(*sets.values())
            k = next((k for k in cand if sets[k] - common), None)
            if k is None:
                k = next((k for k in cand if sets[k]), cand[0])
        collapsed[i] = k
        return k

    def advance(i, stack):
        """First kept node on the path from i (or END), with its stack."""
        seen = set()
        while True:
            if i == END:
                if not stack:
                    return END, ()
                top = stack[-1]
                if top[0] == 'sub':
                    i, stack = top[1], stack[:-1]
                    continue
                f = top[1]  # a branch that ends: as if it reached the join
                if events[f].join == END:  # no join event: next branch, else done
                    k = top[2] + 1
                    if k < len(events[f].forks):
                        stack = stack[:-1] + (('fork', f, k),)
                        i = events[f].forks[k]
                    else:
                        stack, i = stack[:-1], END
                    continue
                i = events[f].join
            if (i, stack) in seen:
                raise _Fail('loop', f'event {i}')
            seen.add((i, stack))
            ev = events[i]
            if is_kept(ev):
                return i, stack
            if ev.kind == RESULT:
                if stack:
                    raise _Fail('result in call', f'event {i}')
                return i, stack
            if ev.kind == ACTION:
                i = ev.next
            elif ev.kind == SUBFLOW:
                if ev.sub_flow != '':
                    i = ev.next
                    continue
                active = {entry} | {f[2] for f in stack if f[0] == 'sub'}
                if ev.sub_entry in active:
                    raise _Fail('recursive subflow', f'event {i} calls {ev.sub_entry}')
                if ev.sub_entry not in entries:
                    raise _Fail('missing entry', f'event {i} calls {ev.sub_entry}')
                stack = stack + (('sub', ev.next, ev.sub_entry),)
                i = entries[ev.sub_entry]
            elif ev.kind == FORK:
                if not ev.forks:
                    i = ev.join
                    continue
                if any(f[0] == 'fork' and f[1] == i for f in stack):
                    raise _Fail('loop', f'event {i} re-enters its own fork')
                stack = stack + (('fork', i, 0),)
                i = ev.forks[0]
            elif ev.kind == JOIN:
                top = stack[-1] if stack else None
                if top and top[0] == 'fork' and events[top[1]].join == i:
                    f, k = top[1], top[2] + 1
                    if k < len(events[f].forks):
                        stack = stack[:-1] + (('fork', f, k),)
                        i = events[f].forks[k]
                    else:
                        stack, i = stack[:-1], ev.next
                elif any(f[0] == 'fork' for f in stack):
                    raise _Fail('join mismatch', f'event {i}')
                else:
                    i = ev.next
            elif ev.kind in SWITCHES and ev.cases:  # collapsing
                i = ev.cases[choose(i)]
            else:
                raise _Fail('dead end', f'event {i} (kind {ev.kind})')

    links: dict[tuple, int] = {}
    kept: list[int] = []
    try:
        if entry not in entries:
            raise _Fail('missing entry', entry)
        expanded = set()
        todo = [(('entry', entry), entries[entry], ())]
        while todo:
            key, i, stack = todo.pop()
            n, stack = advance(i, stack)
            if links.get(key, n) != n:
                raise _Fail('conflict', f'{key}: {links[key]} or {n}')
            links[key] = n
            if n == END:
                continue
            if n not in kept:
                kept.append(n)
            if (n, stack) in expanded:
                continue
            expanded.add((n, stack))
            ev = events[n]
            if ev.kind == RESULT:
                continue
            if ev.kind in SWITCHES:
                todo += [(('case', n, k), c, stack)
                         for k, c in reversed(list(enumerate(ev.cases)))]
            else:
                todo.append((('next', n), ev.next, stack))
        # The output must be able to end from every kept node: a cycle through
        # kept nodes with no way out would hang the scene.
        preds: dict[int, set[int]] = {}
        for key, target in links.items():
            if key[0] != 'entry':
                preds.setdefault(target, set()).add(key[1])
        ends = {n for n in kept if events[n].kind == RESULT}
        todo2 = [END, *ends]
        while todo2:
            for p in preds.get(todo2.pop(), ()):
                if p not in ends:
                    ends.add(p)
                    todo2.append(p)
        stuck = [n for n in kept if n not in ends]
        if stuck:
            raise _Fail('loop', f'cannot end from {stuck[:10]}')
        for key, target in links.items():
            if key[0] == 'entry' or key[1] not in protected:
                continue
            ev = events[key[1]]
            old = ev.next if key[0] == 'next' else ev.cases[key[2]]
            if old != target:
                raise _Fail('shared', f'{key}: {old} -> {target}')
    except _Fail as e:
        return Rewrite({}, [], e.error, e.detail, collapsed)
    return Rewrite(links, kept, None, '', collapsed)


def effects_only(flow: EventFlow, entry: str, table: SkipTable,
                 choices: Mapping[int, int] = {}) -> Rewrite:
    """`linearize` with the table's decisions; other entry points stay untouched."""
    def keep(ev):
        if ev.kind == SUBFLOW:
            return not table.drops_subflow(ev.sub_flow, ev.sub_entry)
        return table.keeps(ev.actor, ev.action)

    def collapse(ev):
        return table.collapses(ev.query)

    events, entries = flow.events, flow.entry_points
    inlined, todo = {entry}, [entry]
    while todo:  # entry points this one reaches through same-file subflows
        e = todo.pop()
        if e not in entries:
            continue
        for i in reachable(events, {}, [entries[e]]):
            ev = events[i]
            if ev.kind == SUBFLOW and ev.sub_flow == '' and ev.sub_entry not in inlined:
                inlined.add(ev.sub_entry)
                todo.append(ev.sub_entry)
    protected = frozenset(reachable(events, entries,
                                    [i for e, i in entries.items() if e not in inlined]))
    return linearize(events, entries, entry, keep, collapse, choices, protected)


def apply_rewrite(data: bytes, flow: EventFlow, rw: Rewrite) -> bytes:
    """The file with the rewrite's links patched in (same length)."""
    if rw.error:
        raise ValueError(f'Cannot apply a failed rewrite: {rw.error} ({rw.detail})')
    return patch_pointers(data, {flow.link_slots[k]: v for k, v in rw.links.items()})


SPIKE_SCENES: tuple[str, ...] = ('Dm_Kokiri_0155', 'Dm_Kokiri_0060', 'Dm_HrlCastle_0050',
                                 'Dm_MelodyGet_Zelda')
# Movie spikes (TestMovies2, TestMovies3): the scenes around the movies, the Deku Tree's speech
# after Gohma, Zelda's first scene and the Deku Tree giving the Kokiri Emerald.
MOVIE_SPIKE_SCENES: tuple[str, ...] = ('Dm_Kokiri_0080', 'Dm_HrlCastle_0035', 'Dm_Kokiri_0130')


def build_spike_files(nup, names=SPIKE_SCENES) -> dict[str, bytes]:
    """romfs path -> compressed bytes for the spike scenes rewritten effects-only."""
    from randomizer.formats.zs import ZsCodec
    codec = ZsCodec.from_archive(nup)
    table = SkipTable.load()
    files = {}
    for name in names:
        path = f'Event/EventFlow/{name}.bfevfl.zs'
        data = codec.decompress(path, nup.read(path))
        flow = EventFlow(data)
        rw = effects_only(flow, 'EntryPoint0', table)
        if rw.error:
            raise ValueError(f'{name}: {rw.error} ({rw.detail})')
        files[path] = codec.compress(path, apply_rewrite(data, flow, rw))
    return files
