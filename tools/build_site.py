"""Builds the static web page into a folder (default `_site/`).

Copies `site/` and packs the `randomizer` package (code and data, without
caches) into `randomizer.zip`, which the page's worker unpacks into Pyodide.

    python tools/build_site.py [out_dir]
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'site'
PACKAGE = ROOT / 'randomizer'
SKIP_DIRS = {'__pycache__'}


def package_files() -> list[Path]:
    out = []
    for f in sorted(PACKAGE.rglob('*')):
        rel = f.relative_to(PACKAGE)
        if f.is_file() and not SKIP_DIRS & set(rel.parts[:-1]) and f.suffix != '.pyc':
            out.append(f)
    return out


def build(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(SITE, out_dir)
    zip_path = out_dir / 'randomizer.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in package_files():
            zf.write(f, f.relative_to(ROOT).as_posix())
    (out_dir / '.nojekyll').write_bytes(b'')
    return zip_path


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / '_site'
    path = build(target)
    print(f'{target} ({path.stat().st_size // 1024} KiB randomizer.zip)')
