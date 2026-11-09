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
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        for rel, data in sorted(files.items()):
            p = os.path.join(tmp, 'romfs', *rel.split('/'))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                f.write(data)
            print('wrote', rel, len(data))
        shutil.rmtree(out, ignore_errors=True)
        os.rename(tmp, out)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print(f'{len(files)} archivos en {out}')


if __name__ == '__main__':
    main()
