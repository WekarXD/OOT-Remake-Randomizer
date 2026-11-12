"""Full cutscene skip: action table loader and effects-only event flow rewriter."""
import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

from randomizer.formats.bfevfl import (ACTION, END, FORK, JOIN, RESULT, SUBFLOW, SUBFLOW_SWITCH,
                                       SWITCH, Event, EventFlow, copy_event, patch_pointers)

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
    # copy slot -> original event: the copy (written over an unreachable action, the
    # donor) stands in for the original on the targeted path; `links` may name its slot.
    copies: dict[int, int] = field(default_factory=dict)


def reachable_chosen(events, entries, starts: Iterable[int],
                     chosen: Mapping[int, int]) -> set[int]:
    """Like `reachable`, but a switch listed in `chosen` only follows that case."""
    seen, todo = set(), list(starts)
    while todo:
        i = todo.pop()
        if i == END or i in seen:
            continue
        seen.add(i)
        todo += _successors(events, entries, i, chosen)
    return seen


def _successors(events, entries, i, chosen=None) -> list[int]:
    """Events reached in one step from i (`chosen` as in `reachable_chosen`)."""
    ev = events[i]
    if ev.kind in SWITCHES:
        out = [ev.cases[chosen[i]]] if chosen and i in chosen else list(ev.cases)
        if ev.kind == SUBFLOW_SWITCH and ev.sub_flow == '' and ev.sub_entry in entries:
            out.append(entries[ev.sub_entry])
        return out
    if ev.kind == FORK:
        return ev.forks + [ev.join]
    out = [ev.next] if ev.next is not None else []
    if ev.kind == SUBFLOW and ev.sub_flow == '' and ev.sub_entry in entries:
        out.append(entries[ev.sub_entry])
    return out


def reachable(events, entries, starts: Iterable[int]) -> set[int]:
    """Events reachable from `starts`: next, cases, forks, joins, same-file subflows
    (also those a subflow switch calls)."""
    return reachable_chosen(events, entries, starts, {})


def linearize(events: list[Event], entries: dict[str, int], entry: str,
              keep: Callable[[Event], bool], collapse: Callable[[Event], bool],
              choices: Mapping[int, int] = {}, protected: frozenset[int] = frozenset(),
              can_copy: Callable[[int, int], bool] | None = None) -> Rewrite:
    """Relink the walk from `entry` so that it only passes through kept nodes.

    The walk carries a continuation stack: ('sub', next, entry) frames for
    inlined same-file subflows and ('fork', fork, branch) frames for fork
    branches (branches run one after another, then what follows the join).
    Between two kept nodes the walk is a single path, so revisiting the same
    (event, stack) there is a loop. A kept node's successors depend only on
    (node, stack), which is expanded once.

    A subflow switch (kind 5) calls an entry and follows the case whose hash
    is the result that entry ends with. Same file: the call is inlined with a
    ('call', switch, entry) frame; a result pops it and continues at the
    matching case ('no result' if none matches or the entry ends without
    one). Other file: kept as a switch node (its call runs unchanged) when
    `keep` keeps the subflow; otherwise it collapses only to a case given in
    `choices` ('subflow switch' if none). A result outside a call frame: at
    the top level it is a kept terminal (the entry's own result); inside an
    inlined subflow or a fork branch it is refused (nothing could follow it).

    Events in `protected` (reached from untargeted entries) are never relinked:
    see `_private_copies`. `can_copy(src, dst)` says whether action `src` may be
    written over the slot of action `dst` (default: always).
    """
    collapsed: dict[int, int] = {}

    def is_kept(ev):
        if ev.kind == ACTION:
            return keep(ev)
        if ev.kind in (SUBFLOW, SUBFLOW_SWITCH):
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
                if top[0] == 'call':
                    raise _Fail('no result', f'{top[2]} ends without one (event {top[1]})')
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
                if not stack:
                    return i, stack
                top = stack[-1]
                if top[0] != 'call':
                    raise _Fail('result in call', f'event {i}')
                sw = events[top[1]]
                if ev.result not in sw.case_hashes:
                    raise _Fail('no result', f'event {i} result {ev.result:#x} is no case '
                                             f'of {top[1]}')
                i, stack = sw.cases[sw.case_hashes.index(ev.result)], stack[:-1]
                continue
            if ev.kind == ACTION:
                i = ev.next
            elif ev.kind in (SUBFLOW, SUBFLOW_SWITCH):
                if ev.sub_flow != '':
                    if ev.kind == SUBFLOW:
                        i = ev.next
                    elif i in choices:
                        i = ev.cases[choose(i)]
                    else:
                        raise _Fail('subflow switch', f'event {i}')
                    continue
                active = {entry} | {f[2] for f in stack if f[0] in ('sub', 'call')}
                if ev.sub_entry in active:
                    raise _Fail('recursive subflow', f'event {i} calls {ev.sub_entry}')
                if ev.sub_entry not in entries:
                    raise _Fail('missing entry', f'event {i} calls {ev.sub_entry}')
                frame = (('sub', ev.next, ev.sub_entry) if ev.kind == SUBFLOW
                         else ('call', i, ev.sub_entry))
                stack = stack + (frame,)
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
            elif ev.kind == SWITCH and ev.cases:  # collapsing
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
        links, copies = _private_copies(events, entries, links, protected, can_copy)
    except _Fail as e:
        return Rewrite({}, [], e.error, e.detail, collapsed)
    return Rewrite(links, kept, None, '', collapsed, copies)


def _private_copies(events, entries, links, protected, can_copy):
    """(links, copies): `links` with every protected event whose link changes
    replaced, on the targeted path, by a private copy (spec 8.1).

    Fixpoint: a protected action whose link differs from the original gets a copy
    that carries the new link, and every link of the rewrite that pointed at the
    original now points at the copy. That may change the link of a protected
    predecessor, which is then copied in turn. Switches, subflows and subflow
    switches are never copied ('shared').

    Copies first get placeholder slots (len(events) + j). Then each takes the slot
    of a donor: an action that nothing reaches after the rewrite (from any entry,
    through cases, forks, joins and same-file calls), that no link targets, that
    is not protected and that `can_copy` accepts; lowest index first ('no donor'
    when they run out). Overwriting a donor is safe because nothing reaches it.
    """
    links = dict(links)
    n_events = len(events)
    originals: dict[int, int] = {}  # placeholder -> original
    changed = True
    while changed:
        changed = False
        for key, target in links.items():
            if key[0] == 'entry' or key[1] not in protected:
                continue
            ev = events[key[1]]
            old = ev.next if key[0] == 'next' else ev.cases[key[2]]
            if old == target:
                continue
            if ev.kind != ACTION:
                raise _Fail('shared', f'{key}: {old} -> {target}')
            src, c = key[1], n_events + len(originals)
            originals[c] = src
            links[('next', c)] = links.pop(('next', src))
            for k, t in links.items():
                if t == src:
                    links[k] = c
            changed = True
            break
    if not originals:
        return links, {}

    def succ(i):
        if i >= n_events or ('next', i) in links:
            return [links[('next', i)]]
        if events[i].kind in SWITCHES and ('case', i, 0) in links:
            return [links[('case', i, k)] for k in range(len(events[i].cases))]
        return _successors(events, entries, i)

    seen, todo = set(), [links.get(('entry', e), i) for e, i in entries.items()]
    while todo:
        i = todo.pop()
        if i != END and i not in seen:
            seen.add(i)
            todo += succ(i)
    targets = set(links.values())
    free = [i for i, ev in enumerate(events) if ev.kind == ACTION and i not in seen
            and i not in targets and i not in protected]
    slot = {}
    for c, src in originals.items():
        d = next((d for d in free if can_copy is None or can_copy(src, d)), None)
        if d is None:
            raise _Fail('no donor', f'copy of event {src}')
        free.remove(d)
        slot[c] = d
    links = {(k if k[0] == 'entry' else (k[0], slot.get(k[1], k[1]), *k[2:])): slot.get(t, t)
             for k, t in links.items()}
    return links, {slot[c]: src for c, src in originals.items()}

# Parameter keys that name a game data flag (found by scanning the action and query
# parameters of every flow: GameDataName for the Set/Is/Add/Wait family, GameDataA/B
# for the compare and Sub queries, GameData for the pouch queries, Src/Dst for copies).
FLAG_KEYS = ('GameDataName', 'GameDataA', 'GameDataB', 'GameData', 'GameDataForActorName',
             'SrcGameDataName', 'DstGameDataName')


def _flags(flow, i):
    params = flow.action_params(i)
    return {v for k in FLAG_KEYS if isinstance(v := params.get(k), str) and v}


def fork_dependencies(flow: EventFlow, entry: str) -> list[tuple[int, str]]:
    """(fork, flag) for each fork reached from `entry` where a branch reads a flag
    (a switch naming it) that a sibling branch writes (an action named `...Set...`).

    Branches run one after another in the output, so a read that used to follow a
    concurrent write may see a different value. Same-file calls (subflows and subflow
    switches) are followed into the callee, which counts for the branch that calls it.
    """
    events, entries = flow.events, flow.entry_points
    if entry not in entries:
        return []

    def effects(start, stop):
        reads, writes, seen, todo = set(), set(), set(), [start]
        while todo:
            i = todo.pop()
            if i == END or i == stop or i in seen:
                continue
            seen.add(i)
            ev = events[i]
            if ev.kind == SWITCH:
                reads |= _flags(flow, i)
            elif ev.kind == ACTION and 'Set' in (ev.action or ''):
                writes |= _flags(flow, i)
            if ev.kind in SWITCHES:
                todo += ev.cases
            elif ev.kind == FORK:
                todo += ev.forks + [ev.join]
            elif ev.next is not None:
                todo.append(ev.next)
            if ev.kind in (SUBFLOW, SUBFLOW_SWITCH) and ev.sub_flow == '' and ev.sub_entry in entries:
                todo.append(entries[ev.sub_entry])
        return reads, writes

    found = set()
    for i in sorted(reachable(events, entries, [entries[entry]])):
        ev = events[i]
        if ev.kind != FORK or len(ev.forks) < 2:
            continue
        eff = [effects(b, ev.join) for b in ev.forks]
        for k, (reads, _) in enumerate(eff):
            for j, (_, writes) in enumerate(eff):
                if j != k:
                    found |= {(i, f) for f in reads & writes}
    return sorted(found)


def inlined_entries(flow: EventFlow, entry: str,
                    external: frozenset[str] = frozenset()) -> set[str]:
    """`entry` and the entry points it reaches through same-file subflows and subflow
    switches, except those in `external` (`entry` itself always counts)."""
    events, entries = flow.events, flow.entry_points
    inlined, todo = {entry}, [entry]
    external = external - {entry}
    while todo:
        e = todo.pop()
        if e not in entries:
            continue
        for i in reachable(events, {}, [entries[e]]):
            ev = events[i]
            if (ev.kind in (SUBFLOW, SUBFLOW_SWITCH) and ev.sub_flow == ''
                    and ev.sub_entry not in inlined and ev.sub_entry not in external):
                inlined.add(ev.sub_entry)
                todo.append(ev.sub_entry)
    return inlined


def effects_only(flow: EventFlow, entry: str, table: SkipTable,
                 choices: Mapping[int, int] = {},
                 reviewed_forks: frozenset[int] = frozenset(),
                 external: frozenset[str] = frozenset()) -> Rewrite:
    """`linearize` with the table's decisions; other entry points stay untouched.

    Fails with 'fork dependency' if a fork branch reads a flag that a sibling writes
    (see `fork_dependencies`), unless the fork is in `reviewed_forks`. Entry points in
    `external` (called from other files) are never inlined, whatever reaches them, and are
    protected like untargeted entries; the targeted entry itself is exempt."""
    deps = [(f, n) for f, n in fork_dependencies(flow, entry) if f not in reviewed_forks]
    if deps:
        return Rewrite({}, [], 'fork dependency', ', '.join(f'fork {f} flag {n}' for f, n in deps))

    def keep(ev):
        if ev.kind in (SUBFLOW, SUBFLOW_SWITCH):
            return not table.drops_subflow(ev.sub_flow, ev.sub_entry)
        return table.keeps(ev.actor, ev.action)

    def collapse(ev):
        return table.collapses(ev.query)

    events, entries = flow.events, flow.entry_points
    inlined = inlined_entries(flow, entry, external)
    protected = frozenset(reachable(events, entries,
                                    [i for e, i in entries.items() if e not in inlined]))
    return linearize(events, entries, entry, keep, collapse, choices, protected, flow.copyable)


def apply_rewrite(data: bytes, flow: EventFlow, rw: Rewrite) -> bytes:
    """The file with the rewrite's copies written, then its links patched in (same length)."""
    if rw.error:
        raise ValueError(f'Cannot apply a failed rewrite: {rw.error} ({rw.detail})')
    for dst, src in rw.copies.items():
        data = copy_event(data, src, dst)
    return patch_pointers(data, {flow.link_slots[k]: v for k, v in rw.links.items()})


# --- Rewrite checker -------------------------------------------------------

FADE_OUT = ('EventEventFadeOut', 'EventLoadingFadeOut')
FADE_IN = ('EventEventFadeIn',)


class _Graph:
    """Adjacency lists with memoized "reachable in one or more steps"."""
    def __init__(self, adj):
        self.adj, self._after = adj, {}

    def after(self, i) -> set[int]:
        if i not in self._after:
            seen, todo = set(), list(self.adj.get(i, ()))
            while todo:
                j = todo.pop()
                if j != END and j not in seen:
                    seen.add(j)
                    todo += self.adj.get(j, ())
            self._after[i] = seen
        return self._after[i]


def _old_graphs(flow) -> tuple[_Graph, _Graph]:
    """(plain, augmented) graphs of the old flow. Plain: `_successors`. Augmented adds an
    edge from each JOIN to every branch of the fork that uses it, from the end of each
    branch to the next branch (or the join after the last), from the RESULTs a same-file
    call can end with to the matching case of its subflow switch, and from where a called
    entry ends to what follows its SUBFLOW."""
    events, entries = flow.events, flow.entry_points
    plain = {i: _successors(events, entries, i) for i in range(len(events))}
    aug = {i: list(v) for i, v in plain.items()}
    for ev in events:
        if ev.kind != FORK:
            continue
        if ev.join in aug:
            aug[ev.join] += ev.forks
        for k, branch in enumerate(ev.forks):  # where a branch ends, the next one runs
            seen, todo = set(), [branch]
            while todo:
                n = todo.pop()
                if n == END or n == ev.join or n in seen:
                    continue
                seen.add(n)
                todo += plain[n]
                if END in plain[n] or ev.join in plain[n]:
                    aug[n] += ev.forks[k + 1:k + 2] or [ev.join]
    for i, ev in enumerate(events):
        if (ev.kind not in (SUBFLOW, SUBFLOW_SWITCH) or ev.sub_flow != ''
                or ev.sub_entry not in entries):
            continue
        for n in reachable(events, entries, [entries[ev.sub_entry]]):
            e = events[n]
            if ev.kind == SUBFLOW:
                ends = END in (e.cases if e.kind in SWITCHES else [e.next])
                if ends and ev.next not in (None, END):
                    aug[n].append(ev.next)
            elif e.kind == RESULT and e.result in ev.case_hashes:
                aug[n].append(ev.cases[ev.case_hashes.index(e.result)])
    return _Graph(plain), _Graph(aug)


def check_rewrite(old: EventFlow, new_data, entry: str, rw: Rewrite) -> list[str]:
    """Problems found in the rewritten file (empty means OK); `new_data` is the bytes
    `apply_rewrite` produced (or an already parsed flow). Each problem starts with its rule:

    1. the kept nodes reachable from `entry` are exactly `rw.kept` (copies count as
       their originals);
    2. no FORK or JOIN is reachable from `entry`;
    3. order: every new link a -> b between kept nodes follows the old flow (b after a,
       counting a join as leading back to its fork's branches) and does not reverse it
       (a not after b), unless a is on a cycle there;
    4. every entry other than `entry` and the inlined ones reaches the same events as
       before, walking the new flow through its own entry table (so a caller of a
       rewritten entry is caught);
    5. a kept fade-out with no later kept fade-in, where the old flow had one after it.
    """
    new = new_data if hasattr(new_data, 'events') else EventFlow(new_data)
    problems: list[str] = []
    if entry not in new.entry_points:
        return [f'rule 1: entry {entry} is missing from the new file']
    orig = lambda i: rw.copies.get(i, i)  # noqa: E731
    start = new.entry_points[entry]
    reach = reachable(new.events, new.entry_points, [start])
    kept_new = {i for i in reach if new.events[i].kind not in (FORK, JOIN)}
    # 1. kept nodes
    got, want = {orig(i) for i in kept_new}, {orig(i) for i in rw.kept}
    if got != want:
        problems.append(f'rule 1: reachable {sorted(got - want)} not kept, '
                        f'kept {sorted(want - got)} not reachable')
    # 2. forks and joins
    bad = sorted(i for i in reach if new.events[i].kind in (FORK, JOIN))
    if bad:
        problems.append(f'rule 2: fork/join reachable: {bad}')
    # 3. order
    plain, aug = _old_graphs(old)
    for a in sorted(kept_new):
        for b in _successors(new.events, {}, a):
            if b == END or b not in kept_new:
                continue
            a0, b0 = orig(a), orig(b)
            if b0 not in aug.after(a0):
                problems.append(f'rule 3: link {a} -> {b} does not follow the old flow')
            elif a0 in plain.after(b0) and a0 not in plain.after(a0):
                problems.append(f'rule 3: link {a} -> {b} reverses the old order')
    # 4. other entries
    skip = inlined_entries(old, entry)
    for other, i in old.entry_points.items():
        if other in skip:
            continue
        if other not in new.entry_points:
            problems.append(f'rule 4: entry {other} is missing from the new file')
        elif (reachable(new.events, new.entry_points, [new.entry_points[other]])
              != reachable(old.events, old.entry_points, [i])):
            problems.append(f'rule 4: entry {other} reaches other events than before')
    # 5. fades
    for a in sorted(kept_new):
        ev = new.events[a]
        if ev.kind != ACTION or ev.action not in FADE_OUT:
            continue
        later = reachable(new.events, new.entry_points, _successors(new.events, {}, a))
        if any(new.events[j].action in FADE_IN for j in later if new.events[j].kind == ACTION):
            continue
        if any(old.events[j].action in FADE_IN for j in aug.after(orig(a))
               if old.events[j].kind == ACTION):
            problems.append(f'rule 5: fade-out {a} has no fade-in after it')
    return problems


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
