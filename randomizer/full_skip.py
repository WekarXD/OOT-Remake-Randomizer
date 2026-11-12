"""Full cutscene skip: target list (randomizer/data/full_skip.json) and mod files.

Three methods (full-skip spec §11): event flows are rewritten effects-only
(`skipflow.effects_only`), timelines are shortened (`timeline_skip.shorten`) and movies
are skipped by removing the transition that starts them (`movie_skip.drop_transitions`).
Whatever the full skip cannot do falls back to the old trimming (`cutscenes`).
"""
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from .cutscenes import FLOW_DIR, FLOW_EXT, build_cutscene_files
from .flow_callers import entry_callers
from .formats.bfevfl import EventFlow
from .formats.timeline import Timeline
from .movie_skip import drop_transitions
from .skipflow import Rewrite, SkipTable, apply_rewrite, check_rewrite, effects_only
from .timeline_skip import shorten

TARGETS_PATH = Path(__file__).resolve().parent / 'data' / 'full_skip.json'


@dataclass
class Targets:
    flows: dict[str, list[str]]             # flow -> targeted entries
    timelines: list[str]
    movies: dict[str, list[str]]            # movie -> flows that start it
    choices: dict[str, dict[int, int]]      # flow -> {switch: case}
    reviewed_forks: dict[str, frozenset[int]]

    def movies_called_by(self, flow: str) -> set[str]:
        return {m for m, callers in self.movies.items() if flow in callers}


def load_targets(phase: int = 1, path=TARGETS_PATH) -> Targets:
    """The targets of phases 1..`phase`."""
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    flows = {n: list(r['entries']) for n, r in data.get('flows', {}).items()
             if r.get('phase', 1) <= phase}
    return Targets(
        flows=flows,
        timelines=sorted(n for n, p in data.get('timelines', {}).items() if p <= phase),
        movies={m: list(r['callers']) for m, r in data.get('movies', {}).items()
                if r.get('phase', 1) <= phase},
        choices={n: {int(k): v for k, v in data['flows'][n].get('choices', {}).items()}
                 for n in flows if data['flows'][n].get('choices')},
        reviewed_forks={n: frozenset(v) for n, v in data.get('reviewed_forks', {}).items()})


def external_entries(callers: Mapping[tuple[str, str], set[str]], flow: str,
                     entry: str) -> frozenset[str]:
    """Entries of `flow` that other files call (see `entry_callers`), except `entry`."""
    return frozenset(e for f, e in callers if f == flow and e != entry)


def flow_callers(raw: Mapping[str, bytes]) -> dict[tuple[str, str], set[str]]:
    """`entry_callers` over decompressed flows (name -> bytes)."""
    return entry_callers({n: EventFlow(d) for n, d in raw.items()})


@dataclass
class Step:
    """One entry rewritten: the file before and after it."""
    entry: str
    rw: Rewrite
    before: bytes
    after: bytes
    external: frozenset[str] = field(default_factory=frozenset)


def skip_flow(data: bytes, name: str, entries, movies, table: SkipTable,
              callers, choices: Mapping[int, int] = {},
              reviewed_forks: frozenset[int] = frozenset()
              ) -> tuple[bytes, list[Step], list[str]]:
    """(new data, applied steps, report lines) for one flow file.

    First the transitions to `movies` are removed; then each entry in turn is rewritten
    effects-only and applied only if `check_rewrite` finds nothing (each on the file as
    the previous steps left it, since copies use donors)."""
    report = []
    if movies:
        try:
            data = drop_transitions(data, movies)
            report.append(f'movie {", ".join(sorted(movies))} dropped from {name}')
        except ValueError as e:
            report.append(f'movie {", ".join(sorted(movies))} not dropped from {name}: {e}')
    steps = []
    for entry in sorted(entries):
        flow = EventFlow(data)
        ext = external_entries(callers, name, entry)
        rw = effects_only(flow, entry, table, choices, reviewed_forks, ext)
        if rw.error:
            report.append(f'fallback {name}/{entry}: {rw.error} ({rw.detail})')
            continue
        new = apply_rewrite(data, flow, rw)
        if new == data:
            report.append(f'unchanged {name}/{entry}: already effects-only')
            continue
        problems = check_rewrite(flow, new, entry, rw, ext)
        if problems:
            report.append(f'fallback {name}/{entry}: check: {"; ".join(problems)}')
            continue
        steps.append(Step(entry, rw, data, new, ext))
        report.append(f'applied {name}/{entry}')
        data = new
    return data, steps, report


def _all_flows(game, cache: dict[str, bytes]) -> dict[str, bytes]:
    """Every flow file decompressed once (name -> bytes), kept in `cache`."""
    if not cache:
        for p in game.nup.list(FLOW_DIR):
            if p.endswith(FLOW_EXT):
                cache[p[len(FLOW_DIR):-len(FLOW_EXT)]] = game.codec.decompress(p, game.nup.read(p))
    return cache


def build_full_skip_files(game, phase: int = 1, flows_cache=None
                          ) -> tuple[dict[str, bytes], list[str]]:
    """(romfs path -> compressed bytes of the files the full skip changes, report lines).

    `flows_cache` (name -> decompressed bytes) may be passed to share the decompressed
    flows between calls; it is filled on first use."""
    start = time.perf_counter()
    targets = load_targets(phase)
    raw = _all_flows(game, {} if flows_cache is None else flows_cache)
    callers = flow_callers(raw)
    table = SkipTable.load()
    files, report = {}, []
    names = set(targets.flows) | {c for cs in targets.movies.values() for c in cs}
    for name in sorted(names):
        if name not in raw:
            report.append(f'missing flow {name}')
            continue
        data, steps, lines = skip_flow(
            raw[name], name, targets.flows.get(name, ()), targets.movies_called_by(name),
            table, callers, targets.choices.get(name, {}),
            targets.reviewed_forks.get(name, frozenset()))
        report += lines
        if data == raw[name] and targets.flows.get(name):
            report.append(f'not written {name}: no targeted entry changed it '
                          '(the old trimming applies)')
        if data != raw[name]:
            path = FLOW_DIR + name + FLOW_EXT
            files[path] = game.codec.compress(path, data)
    todo = list(targets.timelines)
    while todo:
        name = todo.pop(0)
        path = FLOW_DIR + name + FLOW_EXT
        if path in files:
            continue
        if name not in raw:
            report.append(f'missing timeline {name}')
            continue
        data = raw[name]
        todo += Timeline(data).subtimelines
        new = shorten(data)
        if new != data:
            files[path] = game.codec.compress(path, new)
    report.append(f'full skip built in {time.perf_counter() - start:.2f} s')
    return {p: files[p] for p in sorted(files)}, report


def files_with_fallback(game, phase: int = 1, flows_cache=None
                        ) -> tuple[dict[str, bytes], list[str]]:
    """The full skip's files plus the old trimming (`build_cutscene_files`) of every path
    the full skip did not write. A flow where every targeted entry failed is not written
    by the full skip, so it keeps the old trimming; a file the full skip wrote is not
    trimmed as well (reported)."""
    files, report = build_full_skip_files(game, phase, flows_cache)
    old = build_cutscene_files(game)
    for path, data in old.items():
        if path in files:
            name = path[len(FLOW_DIR):-len(FLOW_EXT)]
            report.append(f'full skip only {name}: the old trimming is not applied on top')
        else:
            files[path] = data
    return {p: files[p] for p in sorted(files)}, report
