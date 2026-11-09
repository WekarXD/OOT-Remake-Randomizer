"""Genera mods de prueba con solo los archivos de escenas (sin bancs ni RSTB).
Uso: python -I tools/make_cutscene_batch.py <nup> <out_dir> --only intro|flows|all
Solo lee el .nup; escribe en <out_dir>/romfs/...  Si <out_dir> ya existe y no
esta vacio, se reemplaza de forma atomica (se construye en <out_dir>.tmp).
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
    """True si `path` es `d` o esta dentro de `d` (d es igual o ancestro de path)."""
    path, d = os.path.normcase(os.path.abspath(path)), os.path.normcase(os.path.abspath(d))
    return path == d or path.startswith(d.rstrip(os.sep) + os.sep)


def _check_replaceable(d):
    """Solo se reemplaza un directorio inexistente, vacio o con solo `romfs`."""
    if not os.path.exists(d):
        return
    if not os.path.isdir(d) or set(os.listdir(d)) - {'romfs'}:
        raise SystemExit(f'FALLO: {d} no esta vacio ni es una tanda anterior (solo romfs); no se toca')


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
        raise SystemExit('FALLO: no hay archivos para escribir')

    out = os.path.abspath(a.out_dir)
    tmp = out + '.tmp'
    old = out + '.old'
    cwd = os.getcwd()
    for guard in (cwd, os.path.abspath(a.nup)):
        if _inside(guard, out):
            raise SystemExit(f'FALLO: {out} es igual a un directorio que contiene {guard}')
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
        raise SystemExit(f'FALLO: no se pudo colocar {out}; se restauro el anterior')
    if had_old:
        shutil.rmtree(old)
    print(f'{len(files)} archivos en {out}')


if __name__ == '__main__':
    main()
