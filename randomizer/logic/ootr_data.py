"""Loaders for the vendored OoT Randomizer logic data (GPL-3.0, see ootr/SOURCE.md).

Only parses data; no OoTR code is imported or executed.
"""
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'ootr'


def parse_commented_json(text: str):
    """Parse OoTR's JSON dialect.

    Whole-line '#' comments are dropped (and, like OoTR's own reader, trailing
    '#' comments are cut). String values may span several lines, so newlines
    are folded into single spaces before json.loads.
    """
    kept = []
    for ln in text.splitlines():
        if ln.lstrip().startswith('#'):
            continue
        kept.append(ln.split('#')[0])
    return json.loads(re.sub(' +', ' ', ' '.join(kept)))


def _load(path: Path):
    return parse_commented_json(path.read_text(encoding='utf-8'))


def load_world_files() -> dict[str, list]:
    return {p.stem: _load(p) for p in sorted((DATA_DIR / 'World').glob('*.json'))}


def load_helpers() -> dict[str, str]:
    return _load(DATA_DIR / 'LogicHelpers.json')


def load_locations() -> dict[str, dict]:
    return json.loads((DATA_DIR / 'locations.json').read_text(encoding='utf-8'))
