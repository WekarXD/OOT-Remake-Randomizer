"""Orchestrator: .nup + settings -> mod with spoiler log."""
import dataclasses
import json
import re
import secrets
import shutil
import string
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import locations, patch, spoiler
from .formats.bfevfl import BfevflError
from .formats.timeline import TimelineError
from .fill import FillError, Settings, _eligible, place
from .full_skip import files_with_fallback
from .game import GameData
from . import wrappers
from .logic.world import World, load_vanilla_settings
from .nup import SUPPORTED_DISPLAY_VERSION, SUPPORTED_UPDATE_VERSION, NupArchive, NupError, TITLE_ID


class GenerationError(Exception):
    def __init__(self, message: str, exists: bool = False, mod_dir: str | None = None):
        super().__init__(message)
        self.exists = exists
        self.mod_dir = mod_dir


@dataclass
class GenerateResult:
    seed: str
    mod_dir: str | None
    spoiler_txt: str | None
    spoiler_json: str | None
    changed_files: list[str]


def safe_seed_name(seed: str) -> str:
    text = unicodedata.normalize('NFKD', seed)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r'[^A-Za-z0-9_-]', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')[:40].strip('-')
    if not text:
        raise ValueError('The seed has no characters that are valid in a folder name.')
    return text


def _random_seed() -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(10))


def generate(nup_path: str, out_dir: str, settings: Settings,
             overwrite: bool = False) -> GenerateResult:
    if not settings.seed:
        settings = dataclasses.replace(settings, seed=_random_seed())
    try:
        name = safe_seed_name(settings.seed)
    except ValueError as e:
        raise GenerationError(str(e)) from e
    mod_dir = Path(out_dir) / f'Rando_{name}'
    tmp_dir = mod_dir.with_name(mod_dir.name + '.tmp')
    if mod_dir.exists() and not overwrite:
        raise GenerationError(f'The folder "{mod_dir}" already exists.', exists=True,
                              mod_dir=str(mod_dir))

    txt_path = json_path = None
    try:
        try:
            with NupArchive(nup_path) as nup:
                if nup.title_id != TITLE_ID:
                    raise GenerationError(
                        f'This file is not Ocarina of Time ({TITLE_ID:016X}).')
                if nup.update_version != SUPPORTED_UPDATE_VERSION:
                    raise GenerationError(
                        f'Unsupported game version: {nup.update_version}')
                game = GameData(nup)
                chests = game.chests()
                loc_map = locations.load_map()
                world_settings = dict(load_vanilla_settings())
                world_settings['tokensanity'] = settings.tokensanity
                skulltulas, gs_map, gs_forbidden = (), None, frozenset()
                if settings.tokensanity != 'off':
                    skulltulas = game.skulltulas()
                    gs_map = locations.load_gs_map()
                    gs_forbidden = _gs_forbidden(game, chests, loc_map)
                placement = place(chests, loc_map, World(world_settings), settings,
                                  skulltulas, gs_map, gs_forbidden)
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)
                tmp_dir.mkdir(parents=True)
                extras = sizes = None
                not_skipped = None
                rstb_report: list[str] = []
                if settings.skip_cutscenes:
                    try:
                        extras, report, sizes = files_with_fallback(game, 1)
                        not_skipped = _not_skipped(report)
                    except (ValueError, BfevflError, TimelineError) as e:
                        raise GenerationError(
                            f'Could not prepare the cutscenes: {e}') from e
                try:
                    changed = patch.write_mod(game, placement, tmp_dir, loc_map, extras,
                                              extra_sizes=sizes, report=rstb_report)
                except ValueError as e:
                    raise GenerationError(
                        f'Could not prepare the item wrappers: {e}') from e
                if not_skipped is not None:
                    # Grown flows with no RSTB entry (their size could not be updated).
                    not_skipped += rstb_report
                if settings.spoiler:
                    data = spoiler.build(settings, placement, chests, loc_map,
                                         SUPPORTED_DISPLAY_VERSION, skulltulas, gs_map, not_skipped)
                    # '\n' line endings everywhere, so the spoiler log is the same
                    # whether it is generated on Windows or in the browser.
                    (tmp_dir / 'spoiler.txt').write_text(spoiler.to_text(data),
                                                         encoding='utf-8', newline='\n')
                    (tmp_dir / 'spoiler.json').write_text(
                        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True),
                        encoding='utf-8', newline='\n')
                    txt_path = str(mod_dir / 'spoiler.txt')
                    json_path = str(mod_dir / 'spoiler.json')
        except (NupError, FillError) as e:
            raise GenerationError(str(e)) from e
        if not changed and not settings.spoiler:
            # Vanilla mode without a spoiler log: nothing to write.
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return GenerateResult(settings.seed, None, None, None, [])
        _swap_in(tmp_dir, mod_dir)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return GenerateResult(settings.seed, str(mod_dir), txt_path, json_path, changed)


_APPLIED = ('applied ', 'unchanged ', 'full skip built in ', 'full skip only ')


def _not_skipped(report: list[str]) -> list[str]:
    """The report lines that tell what the full skip did not do (fallbacks, untrimmed
    files, failed movies); the successful steps and the timing are left out."""
    return [line for line in report
            if not line.startswith(_APPLIED)
            and not (line.startswith('movie ') and ' not dropped from ' not in line)]


def _gs_forbidden(game, chests, loc_map) -> frozenset[str]:
    """Contents of eligible chests that no Skulltula can drop: no floating
    wrapper can be built for them and the game has no world actor for them."""
    original = {c.hash: c.drop for c in chests}
    rows = wrappers.pouch_rows(game)
    contents = {original[h] for h in _eligible(chests, loc_map, original)}
    wrappable = wrappers.wrap_sources(game, contents)
    return frozenset(c for c in sorted(contents)
                     if c not in wrappable and wrappers.vanilla_drop(c, rows) is None)


def _swap_in(tmp_dir: Path, mod_dir: Path) -> None:
    """tmp -> mod_dir without losing the previous mod if something fails."""
    old = mod_dir.with_name(mod_dir.name + '.old')
    backed_up = False
    if mod_dir.exists():
        if old.exists():
            shutil.rmtree(old)
        mod_dir.rename(old)
        backed_up = True
    try:
        tmp_dir.rename(mod_dir)
    except BaseException:
        if backed_up:
            old.rename(mod_dir)
        raise
    if backed_up:
        shutil.rmtree(old, ignore_errors=True)
