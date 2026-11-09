"""Orquestador: .nup + ajustes -> mod con spoiler."""
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
from .cutscenes import build_cutscene_files
from .formats.bfevfl import BfevflError
from .fill import FillError, Settings, place
from .game import GameData
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
        raise ValueError('La semilla no contiene caracteres válidos para un nombre de carpeta.')
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
        raise GenerationError(f'Ya existe la carpeta "{mod_dir}".', exists=True,
                              mod_dir=str(mod_dir))

    txt_path = json_path = None
    try:
        try:
            with NupArchive(nup_path) as nup:
                if nup.title_id != TITLE_ID:
                    raise GenerationError(
                        f'Este archivo no es Ocarina of Time ({TITLE_ID:016X}).')
                if nup.update_version != SUPPORTED_UPDATE_VERSION:
                    raise GenerationError(
                        f'Versión del juego no soportada: {nup.update_version}')
                game = GameData(nup)
                chests = game.chests()
                loc_map = locations.load_map()
                placement = place(chests, loc_map,
                                  World(load_vanilla_settings()), settings)
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)
                tmp_dir.mkdir(parents=True)
                extras = None
                if settings.skip_cutscenes:
                    try:
                        extras = build_cutscene_files(game)
                    except (ValueError, BfevflError) as e:
                        raise GenerationError(
                            f'No se pudieron preparar las cinemáticas: {e}') from e
                changed = patch.write_mod(game, placement, tmp_dir, loc_map, extras)
                if settings.spoiler:
                    data = spoiler.build(settings, placement, chests, loc_map,
                                         SUPPORTED_DISPLAY_VERSION)
                    (tmp_dir / 'spoiler.txt').write_text(spoiler.to_text(data),
                                                         encoding='utf-8')
                    (tmp_dir / 'spoiler.json').write_text(
                        json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True),
                        encoding='utf-8')
                    txt_path = str(mod_dir / 'spoiler.txt')
                    json_path = str(mod_dir / 'spoiler.json')
        except (NupError, FillError) as e:
            raise GenerationError(str(e)) from e
        if not changed and not settings.spoiler:
            # Modo Vanilla sin spoiler: no hay nada que escribir.
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return GenerateResult(settings.seed, None, None, None, [])
        _swap_in(tmp_dir, mod_dir)
    except BaseException:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
    return GenerateResult(settings.seed, str(mod_dir), txt_path, json_path, changed)


def _swap_in(tmp_dir: Path, mod_dir: Path) -> None:
    """tmp -> mod_dir sin perder el mod anterior si algo falla."""
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
