"""Generates test mods with only the scene files (no bancs or RSTB).
Usage: python -I tools/make_cutscene_batch.py <nup> <out_dir> --only intro|flows|all
Only reads the .nup; writes to <out_dir>/romfs/...  If <out_dir> already exists and is not
empty, it is replaced atomically (built in <out_dir>.tmp).
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from randomizer.cutscenes import build_cutscene_files  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402

INTRO = 'Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml'
FLOWS = 'Event/EventFlow/'


def select(files: dict, only: str) -> dict:
    if only == 'intro':
        return {k: v for k, v in files.items() if k == INTRO}
    if only == 'flows':
        return {k: v for k, v in files.items() if k.startswith(FLOWS)}
    return dict(files)


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
    ap.add_argument('--only', choices=['intro', 'flows', 'all'], required=True)
    a = ap.parse_args()

    with NupArchive(a.nup) as nup:
        game = GameData(nup)
        files = select(build_cutscene_files(game), a.only)
    if not files:
        raise SystemExit('FAIL: no files to write')

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
    print(f'{len(files)} files in {out}')


if __name__ == '__main__':
    main()
