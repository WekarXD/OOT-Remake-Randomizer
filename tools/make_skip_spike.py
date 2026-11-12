"""Spike test mods: TestScenes4 (four cutscenes rewritten effects-only: no scene, same
effects) and, with --timelines, TestTimelines (the same plus three timeline cutscenes
shortened, see randomizer/timeline_skip.py) and, with --movies, TestMovies3 (TestTimelines plus
three movies removed from the flows that start them, see randomizer/movie_skip.py, and the scenes
around them: MOVIE_SPIKE_SCENES rewritten effects-only, MOVIE_SPIKE_TIMELINES shortened).
Usage: python -I tools/make_skip_spike.py [--timelines] [--movies] <nup> <out_dir>
Only reads the .nup; writes <out_dir>/romfs/Event/EventFlow/<name>.bfevfl.zs for each scene and
prints the kept events of each as `index actor.action`. If <out_dir> already exists it must be
empty or a previous batch (romfs only); it is replaced atomically (built in <out_dir>.tmp).
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from randomizer.formats.bfevfl import ACTION, SUBFLOW, EventFlow  # noqa: E402
from randomizer.formats.zs import ZsCodec  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.timeline_skip import (MOVIE_SPIKE_TIMELINES, SPIKE_TIMELINES,  # noqa: E402
                                      build_timeline_spike_files)
from randomizer.movie_skip import build_movie_spike_files  # noqa: E402
from randomizer.skipflow import (MOVIE_SPIKE_SCENES, SPIKE_SCENES, SkipTable, apply_rewrite, build_spike_files,  # noqa: E402
                                 effects_only, reachable)


def report(nup, scenes):
    codec = ZsCodec.from_archive(nup)
    table = SkipTable.load()
    for name in scenes:
        path = f'Event/EventFlow/{name}.bfevfl.zs'
        data = codec.decompress(path, nup.read(path))
        flow = EventFlow(data)
        rw = effects_only(flow, 'EntryPoint0', table)
        new = EventFlow(apply_rewrite(data, flow, rw))
        print(f'{name}: {len(rw.kept)} kept events')
        for i in sorted(reachable(new.events, new.entry_points, [new.entry_points['EntryPoint0']])):
            ev = new.events[i]
            if ev.kind == ACTION:
                print(f'  {i} {ev.actor}.{ev.action}')
            elif ev.kind == SUBFLOW:
                print(f'  {i} subflow {ev.sub_flow}/{ev.sub_entry}')


def _check_replaceable(d):
    if not os.path.exists(d):
        return
    if not os.path.isdir(d) or set(os.listdir(d)) - {'romfs'}:
        raise SystemExit(f'FAIL: {d} is not empty nor a previous batch (romfs only); not touching it')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--timelines', action='store_true', help='also shorten the spike timelines')
    ap.add_argument('--movies', action='store_true', help='also skip the spike movies (implies --timelines)')
    ap.add_argument('nup')
    ap.add_argument('out_dir')
    a = ap.parse_args()
    with NupArchive(a.nup) as nup:
        scenes = SPIKE_SCENES + MOVIE_SPIKE_SCENES * a.movies
        files = build_spike_files(nup, scenes)
        names = SPIKE_TIMELINES * (a.timelines or a.movies) + MOVIE_SPIKE_TIMELINES * a.movies
        files.update(build_timeline_spike_files(nup, names))
        if a.movies:
            files.update(build_movie_spike_files(nup))
        report(nup, scenes)
    out = os.path.abspath(a.out_dir)
    tmp, old = out + '.tmp', out + '.old'
    for d in (out, tmp, old):
        _check_replaceable(d)
    for d in (tmp, old):
        if os.path.isdir(d):
            shutil.rmtree(d)
    try:
        for rel, data in sorted(files.items()):
            p = os.path.join(tmp, 'romfs', *rel.split('/'))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                f.write(data)
            print('wrote', rel, len(data))
    except BaseException:
        shutil.rmtree(tmp)
        raise
    had_old = os.path.isdir(out)
    if had_old:
        os.rename(out, old)
    try:
        os.rename(tmp, out)
    except BaseException:
        if had_old:
            os.rename(old, out)
        raise SystemExit(f'FAIL: could not place {out}; the previous one was restored')
    if had_old:
        shutil.rmtree(old)
    print(f'{len(files)} files in {out}')


if __name__ == '__main__':
    main()
