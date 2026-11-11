"""Entry points for the web page, which runs this package inside Pyodide.

The page calls `call(name, args_json)` and gets a JSON string back, so only
strings cross the JavaScript/Python boundary. The same functions work in a
normal Python, which is how the tests exercise them.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from . import locations
from .fill import MODES, TOKENSANITY, Settings
from .generate import GenerationError, generate
from .items import KEY_ITEM_HOME, KEY_ITEMS, LABELS, NON_EXCLUDABLE
from .nup import (SUPPORTED_DISPLAY_VERSION, SUPPORTED_UPDATE_VERSION, TITLE_ID,
                  NupArchive, NupError)


def movable_flags() -> dict[str, bool]:
    """Key item -> whether it can move (its home chest needs no event patch)."""
    entries = list(locations.load_map().values())
    return {actor: not any(e.needs_event_patch for e in entries if e.location == home)
            for actor, home in KEY_ITEM_HOME.items()}


def items() -> list[dict]:
    """The key items for the "Exclude items" list."""
    movable = movable_flags()
    return [{'actor': a, 'label': LABELS.get(a, a), 'movable': movable.get(a, True),
             'excludable': movable.get(a, True) and a not in NON_EXCLUDABLE}
            for a in KEY_ITEMS]


def check_nup(path: str) -> dict:
    """{'ok': True, 'version': ...} or {'ok': False, 'error': ...}."""
    try:
        nup = NupArchive(path)
    except NupError as e:
        return {'ok': False, 'error': str(e)}
    try:
        if nup.title_id != TITLE_ID:
            return {'ok': False, 'error': 'The file is not Zelda: Ocarina of Time '
                                          f'(title id 0x{nup.title_id:016X}).'}
        v = nup.update_version
        if v != SUPPORTED_UPDATE_VERSION:
            shown = f'update {v}' if v is not None else 'no update'
            return {'ok': False, 'error': f'Unsupported game version: {shown}. '
                                          f'Version {SUPPORTED_DISPLAY_VERSION} is required.'}
        return {'ok': True, 'version': SUPPORTED_DISPLAY_VERSION}
    finally:
        nup.close()


def parse_settings(options: dict) -> Settings:
    """Settings from the page's options; ValueError with a readable message."""
    if not isinstance(options, dict):
        raise ValueError('Invalid options.')
    seed = options.get('seed', '')
    if not isinstance(seed, str):
        raise ValueError('Invalid seed.')
    mode = options.get('key_items_mode', 'any_chest')
    if mode not in MODES:
        raise ValueError('Invalid key item mode.')
    excluded = options.get('excluded_items') or []
    if (not isinstance(excluded, list)
            or any(not isinstance(x, str) or x not in KEY_ITEMS for x in excluded)):
        raise ValueError('Invalid excluded items list.')
    flags = {}
    for key, default in (('spoiler', True), ('skip_cutscenes', False)):
        flags[key] = options.get(key, default)
        if not isinstance(flags[key], bool):
            raise ValueError(f'{key} must be true or false')
    tokensanity = options.get('tokensanity', 'off')
    if not isinstance(tokensanity, str) or tokensanity not in TOKENSANITY:
        raise ValueError('Invalid Tokensanity value.')
    bad = [x for x in excluded if x in NON_EXCLUDABLE]
    if bad:
        raise ValueError(f'Cannot exclude {LABELS.get(bad[0], bad[0])}: the logic '
                         'needs to move it for the game to be beatable.')
    movable = movable_flags()
    # Non-movable items never move: they must not alter the RNG key.
    effective = frozenset(x for x in excluded if movable.get(x, True))
    return Settings(seed=seed.strip(), key_items_mode=mode, excluded_items=effective,
                    spoiler=flags['spoiler'], skip_cutscenes=flags['skip_cutscenes'],
                    tokensanity=tokensanity)


def generate_zip(nup_path: str, options: dict, out_dir: str | None = None) -> dict:
    """Generates the mod and packs it as `Rando_<seed>.zip` in `out_dir`
    (a new temporary folder when omitted). The zip holds the `Rando_<seed>`
    folder, ready to copy into Lichii's mods folder, with the spoiler log
    inside it."""
    try:
        settings = parse_settings(options)
    except ValueError as e:
        return {'ok': False, 'error': str(e)}
    out = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix='rando-'))
    work = Path(tempfile.mkdtemp(prefix='rando-work-'))
    try:
        res = generate(nup_path, str(work), settings)
        if res.mod_dir is None:
            return {'ok': False, 'error': 'Nothing to download: Vanilla mode without '
                                          'the spoiler log changes nothing.'}
        mod_dir = Path(res.mod_dir)
        zip_path = out / f'{mod_dir.name}.zip'
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for f in sorted(p for p in mod_dir.rglob('*') if p.is_file()):
                zf.write(f, f.relative_to(work).as_posix())
    except GenerationError as e:
        return {'ok': False, 'error': str(e)}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {'ok': True, 'seed': res.seed, 'zip_path': str(zip_path),
            'zip_name': zip_path.name, 'changed_files': len(res.changed_files)}


_CALLS = {
    'items': lambda: items(),
    'check_nup': lambda path: check_nup(path),
    'generate_zip': lambda nup_path, options: generate_zip(nup_path, options),
}


def call(name: str, args_json: str = '[]') -> str:
    """JSON-in, JSON-out dispatcher used by the page's worker."""
    fn = _CALLS.get(name)
    if fn is None:
        return json.dumps({'ok': False, 'error': f'Unknown call: {name}'})
    return json.dumps(fn(*json.loads(args_json)), ensure_ascii=False)
