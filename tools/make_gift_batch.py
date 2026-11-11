"""Test batch 7: Saria gives the Boomerang instead of the Fairy Ocarina.
Usage: python -I tools/make_gift_batch.py <nup> <out_dir>
Only reads the .nup; writes to <out_dir>/romfs/...  If <out_dir> already exists and is not
empty, it is replaced atomically (built in <out_dir>.tmp).
Changes 'Item_Ocarina_Fairy' to 'Item_Boomerang' in events 51 (Actor) and
52 (ActorName) of Dm_Kokiri_0155. If the file changes size, it also writes
the RSTB.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from randomizer.formats.bfevfl import EventFlow, set_string_param, string_param_owners  # noqa: E402
from randomizer.formats.rstb import Rstb  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.patch import RSTB_PATH  # noqa: E402
from randomizer.formats.zs import ZsCodec  # noqa: E402

FLOW = 'Event/EventFlow/Dm_Kokiri_0155.bfevfl'
FLOW_ZS = FLOW + '.zs'
OLD, NEW = 'Item_Ocarina_Fairy', 'Item_Boomerang'
EDITS = ((51, 'Actor'), (52, 'ActorName'))


def build(nup):
    """Returns (files {romfs_path: bytes}, original data, new data)."""
    codec = ZsCodec.from_archive(nup)
    raw = codec.decompress(FLOW_ZS, nup.read(FLOW_ZS))
    flow = EventFlow(raw)
    allowed = {i for i, _ in EDITS}
    for i, key in EDITS:
        if flow.action_params(i).get(key) != OLD:
            raise SystemExit(f'FAIL: event {i} does not have {key}={OLD!r}')
        owners = string_param_owners(raw, i, key)
        if set(owners) - allowed:
            raise SystemExit(f'FAIL: the string of event {i} ({key}) is shared by other events: {owners}')
    new = raw
    for i, key in EDITS:
        new = set_string_param(new, i, key, NEW)
    files = {FLOW_ZS: codec.compress(FLOW_ZS, new)}
    if len(new) != len(raw):
        rstb = Rstb.load(codec.decompress(RSTB_PATH, nup.read(RSTB_PATH)))
        orig = rstb.get(FLOW)
        if orig is None:
            raise SystemExit(f'FAIL: the RSTB does not have {FLOW}')
        delta = (len(new) - len(raw) + 0xFF) & ~0xFF
        rstb.set(FLOW, orig + delta + 0x1000)
        files[RSTB_PATH] = codec.compress(RSTB_PATH, rstb.dump())
    return files, raw, new


def verify(raw, new):
    a, b = EventFlow(raw), EventFlow(new)
    assert len(a.events) == len(b.events)
    for i in range(len(a.events)):
        pa, pb = a.action_params(i), b.action_params(i)
        if i == 51:
            assert pa.get('Actor') == OLD and pb.get('Actor') == NEW and                 {k: v for k, v in pa.items() if k != 'Actor'} == {k: v for k, v in pb.items() if k != 'Actor'}, i
        elif i == 52:
            assert pa.get('ActorName') == OLD and pb.get('ActorName') == NEW and                 {k: v for k, v in pa.items() if k != 'ActorName'} == {k: v for k, v in pb.items() if k != 'ActorName'}, i
        else:
            assert pa == pb, f'unexpected change in event {i}'
    for x, y in zip(a.events, b.events):
        assert (x.kind, x.next, x.cases, x.forks, x.join, x.actor, x.action) ==             (y.kind, y.next, y.cases, y.forks, y.join, y.actor, y.action)


def _inside(path, d):
    """True if `path` is `d` or is inside `d` (d is equal to or an ancestor of path)."""
    path, d = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(d))
    return path == d or path.startswith(d.rstrip(os.sep) + os.sep)


def _check_replaceable(d):
    """Only a nonexistent directory, an empty one, or one with only `romfs` is replaced."""
    if not os.path.exists(d):
        return
    if not os.path.isdir(d) or set(os.listdir(d)) - {'romfs'}:
        raise SystemExit(f'FAIL: {d} is not empty nor a previous batch (romfs only); not touching it')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nup')
    ap.add_argument('out_dir')
    a = ap.parse_args()

    with NupArchive(a.nup) as nup:
        files, raw, new = build(nup)
    verify(raw, new)

    out = os.path.abspath(a.out_dir)
    tmp = out + '.tmp'
    old = out + '.old'
    cwd = os.getcwd()
    for guard in (cwd, os.path.abspath(a.nup)):
        if _inside(guard, out):
            raise SystemExit(f'FAIL: {out} is equal to a directory that contains {guard}')
    for d in (out, tmp, old):
        _check_replaceable(d)
    shutil.rmtree(tmp) if os.path.isdir(tmp) else None
    shutil.rmtree(old) if os.path.isdir(old) else None
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
    print(f'size {"changed" if len(new) != len(raw) else "same"} ({len(raw)} -> {len(new)}); {len(files)} files in {out}')


if __name__ == '__main__':
    main()
