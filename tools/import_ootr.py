"""Vendor OoT Randomizer logic data. Usage: python -I tools/import_ootr.py <ootr_clone>

Parses only (json + ast); never imports or executes OoTR code.
"""
import ast
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

COMMIT = '526b4c8d81b7c4023ef4573ffbaf39344e270d5b'
REPO_URL = 'https://github.com/OoTRandomizer/OoT-Randomizer'
OUT = Path(__file__).resolve().parent.parent / 'randomizer' / 'logic' / 'ootr'


def _lit(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return None


def extract_locations(source: str) -> dict:
    tree = ast.parse(source)
    value = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                and node.target.id == 'location_table'):
            value = node.value
        elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == 'location_table' for t in node.targets):
            value = node.value
    if value is None:
        raise SystemExit('location_table not found in LocationList.py')
    if not (isinstance(value, ast.Call) and value.args and isinstance(value.args[0], ast.List)):
        raise SystemExit('location_table is not OrderedDict([...])')
    result = {}
    for entry in value.args[0].elts:
        if not (isinstance(entry, ast.Tuple) and len(entry.elts) == 2
                and isinstance(entry.elts[1], ast.Tuple)):
            continue
        name = _lit(entry.elts[0])
        fields = entry.elts[1].elts
        if not isinstance(name, str) or len(fields) < 6:
            continue
        typ, scene, vanilla, cats = _lit(fields[0]), _lit(fields[1]), _lit(fields[4]), _lit(fields[5])
        result[name] = {
            'type': typ if isinstance(typ, str) else None,
            'scene': scene if isinstance(scene, int) else None,
            'vanilla_item': vanilla if isinstance(vanilla, str) else None,
            'categories': list(cats) if isinstance(cats, (tuple, list)) else [],
        }
    return result


def main(argv):
    if len(argv) != 2:
        raise SystemExit(__doc__)
    clone = Path(argv[1])
    head = subprocess.run(['git', '-C', str(clone), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != COMMIT:
        raise SystemExit(f'clone is at {head}, expected {COMMIT}')
    world = clone / 'data' / 'World'
    helpers = clone / 'data' / 'LogicHelpers.json'
    loclist = clone / 'LocationList.py'
    for p in (world, helpers, loclist):
        if not p.exists():
            raise SystemExit(f'missing in clone: {p}')
    files = sorted(p for p in world.glob('*.json') if 'MQ' not in p.name)
    if not files:
        raise SystemExit(f'no logic files found in {world}')

    (OUT / 'World').mkdir(parents=True, exist_ok=True)
    for old in (OUT / 'World').glob('*.json'):
        old.unlink()
    for f in files:
        shutil.copyfile(f, OUT / 'World' / f.name)
    shutil.copyfile(helpers, OUT / 'LogicHelpers.json')
    locs = extract_locations(loclist.read_text(encoding='utf-8'))
    (OUT / 'locations.json').write_text(
        json.dumps(locs, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

    lines = [
        '# OoT Randomizer logic data (vendored)', '',
        f'- Repository: {REPO_URL}',
        f'- Commit: {COMMIT}',
        f'- Imported: {datetime.date.today().isoformat()}',
        '- License: GPL-3.0 (this project\'s logic is derived from OoTR)',
        '- No OoTR code is imported or executed; data files are parsed only (json + ast).', '',
        '## Copied files', '',
        *(f'- World/{f.name}' for f in files),
        '- LogicHelpers.json',
        '- locations.json (generated from LocationList.py `location_table` with ast.literal_eval)',
        '', '## Notes', '',
        '- Excluded: `* MQ.json` files and `Glitched World/`.',
        '- All 15 key-item chest names from the plan match this commit; no corrections needed.',
    ]
    (OUT / 'SOURCE.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'imported {len(files)} world files, {len(locs)} locations')


if __name__ == '__main__':
    main(sys.argv)
