"""Orchestrator: .nup + settings -> mod with spoiler log."""
import dataclasses
import json
import re
import secrets
import shutil
import string
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from . import locations, patch, spoiler
from .formats.bfevfl import BfevflError
from .formats.timeline import TimelineError
from .fill import VANILLA_SONGS, FillError, Settings, _eligible, place_all
from .full_skip import files_with_fallback

# Phases of full_skip.json the "Skip cutscenes" option builds (1 childhood, 2 adult).
# The adult phase is built and unit-tested but not yet tested in game: releases ship the
# childhood only (the site says the option is in development).
FULL_SKIP_PHASE = 1
from .game import GameData
from . import wrappers
from .songs import song_flow_patches
from .fairies import FAIRY_REWARDS, fairy_flow_patches
from .items import KEY_ITEMS
from .gifts import GIFTS, gift_actor_swaps, gift_flow_patches, gift_subflow_list
from .formats.bfevfl import EventFlow
from .analyzed_info import ANALYZED_INFO
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
                shuffled = settings.key_items_mode != 'vanilla'
                # The world NPC gifts become wrappers: never what cannot be wrapped.
                world_forbidden = _world_forbidden(game, chests) if shuffled else frozenset()
                if settings.tokensanity != 'off':
                    skulltulas = game.skulltulas()
                    gs_map = locations.load_gs_map()
                    # The Great Fairy rewards and NPC gift items are in no chest: check them too.
                    gs_forbidden = _gs_forbidden(
                        game, chests, loc_map, _moving_extras() if shuffled else ())
                    if settings.shuffle_songs == 'anywhere':
                        # No Skulltula can drop a song (no wrapper or world actor).
                        gs_forbidden |= frozenset(VANILLA_SONGS.values())
                placed = place_all(chests, loc_map, World(world_settings), settings,
                                   skulltulas, gs_map, gs_forbidden,
                                   world_forbidden=world_forbidden)
                placement = placed.chests
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir)
                tmp_dir.mkdir(parents=True)
                extras = sizes = None
                not_skipped = None
                rstb_report: list[str] = []
                if settings.skip_cutscenes:
                    try:
                        extras, report, sizes = files_with_fallback(game, FULL_SKIP_PHASE)
                        not_skipped = _not_skipped(report)
                    except (ValueError, BfevflError, TimelineError) as e:
                        raise GenerationError(
                            f'Could not prepare the cutscenes: {e}') from e
                if placed.songs != VANILLA_SONGS:
                    try:
                        extras, sizes = _with_flow_patches(
                            game, lambda read: song_flow_patches(read, placed.songs),
                            extras, sizes)
                    except (ValueError, BfevflError) as e:
                        raise GenerationError(f'Could not prepare the songs: {e}') from e
                if placed.fairies:
                    try:
                        extras, sizes = _with_flow_patches(
                            game, lambda read: fairy_flow_patches(read, placed.fairies),
                            extras, sizes)
                    except (ValueError, BfevflError) as e:
                        raise GenerationError(
                            f'Could not prepare the Great Fairies: {e}') from e
                if placed.gifts:
                    try:
                        extras, sizes = _with_flow_patches(
                            game, lambda read: gift_flow_patches(read, placed.gifts),
                            extras, sizes)
                        extras, sizes = _with_file_patch(
                            game, ANALYZED_INFO,
                            lambda info, load: gift_subflow_list(info, load, placed.gifts),
                            extras, sizes)
                    except (ValueError, BfevflError) as e:
                        raise GenerationError(f'Could not prepare the NPC gifts: {e}') from e
                try:
                    swaps = ({h.hash: (h.banc, placed.hearts[h.location])
                              for h in game.boss_hearts()} if placed.hearts else {})
                    swaps.update(gift_actor_swaps(placed.gifts))
                    swaps = swaps or None
                    changed = patch.write_mod(game, placement, tmp_dir, loc_map, extras,
                                              extra_sizes=sizes, report=rstb_report,
                                              actor_swaps=swaps)
                except ValueError as e:
                    raise GenerationError(
                        f'Could not prepare the item wrappers: {e}') from e
                if not_skipped is not None:
                    # Grown flows with no RSTB entry (their size could not be updated).
                    not_skipped += rstb_report
                if rstb_report and not settings.spoiler:
                    # No spoiler log to hold them: tell the user anyway.
                    print('\n'.join(rstb_report), file=sys.stderr)
                if settings.spoiler:
                    data = spoiler.build(settings, placement, chests, loc_map,
                                         SUPPORTED_DISPLAY_VERSION, skulltulas, gs_map, not_skipped,
                                         placed.songs, placed.hearts, placed.fairies,
                                         placed.gifts)
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


FLOW_DIR, FLOW_EXT = 'Event/EventFlow/', '.bfevfl.zs'


def _with_flow_patches(game: GameData, patches,
                       extras: dict[str, bytes] | None,
                       sizes: dict[str, int] | None) -> tuple[dict[str, bytes], dict[str, int]]:
    """`extras` (romfs path -> compressed bytes) and `sizes` (romfs path -> size change
    against the game's file) with the flows `patches(read)` returns ({flow: bytes}; the
    song scenes, the Great Fairy fountains). A flow the full skip already rewrote is
    patched on top of the skip's version, which it replaces."""
    files, deltas = dict(extras or {}), dict(sizes or {})

    def path(name: str) -> str:
        return FLOW_DIR + name + FLOW_EXT

    def read(name: str) -> bytes:
        p = path(name)
        raw = files[p] if p in files else game.nup.read(p)
        return game.codec.decompress(p, raw)

    for name, data in patches(read).items():
        p = path(name)
        files[p] = game.codec.compress(p, data)
        grow = len(data) - len(game.codec.decompress(p, game.nup.read(p)))
        deltas.pop(p, None)
        if grow:
            deltas[p] = grow
    return files, deltas


def _with_file_patch(game: GameData, path: str, patch_fn,
                     extras: dict[str, bytes] | None,
                     sizes: dict[str, int] | None) -> tuple[dict[str, bytes], dict[str, int]]:
    """`extras` and `sizes` with `path` (a romfs path ending in .zs) replaced by
    `patch_fn(data, load)`: `data` is its decompressed current version (from `extras` if a
    patch wrote it, else the game's) and `load(flow)` gives a flow's current EventFlow (or
    None). An unchanged result is left out."""
    files, deltas = dict(extras or {}), dict(sizes or {})

    def current(p: str) -> bytes:
        return game.codec.decompress(p, files[p] if p in files else game.nup.read(p))

    def load(name: str) -> EventFlow | None:
        p = FLOW_DIR + name + FLOW_EXT
        return EventFlow(current(p)) if p in files or game.nup.has(p) else None

    before = current(path)
    data = patch_fn(before, load)
    if data == before:
        return files, deltas
    files[path] = game.codec.compress(path, data)
    grow = len(data) - len(game.codec.decompress(path, game.nup.read(path)))
    deltas.pop(path, None)
    if grow:
        deltas[path] = grow
    return files, deltas


# What a world NPC gift's wrapper is proven to hand over in game: key items (27f, 28a),
# songs (Dungeon Rewards boss hearts) and Pieces of Heart / Heart Containers (the
# token-clone recipe, batch 14). Minor-item wrappers (rupees, ammo...) are still untested.
def _moving_extras() -> frozenset[str]:
    """What moves with key items shuffled but is in no chest: the Great Fairy rewards and
    every NPC gift content (key items, Pieces of Heart, upgrades, bombchus)."""
    return frozenset(FAIRY_REWARDS) | {g.content for g in GIFTS}


_WORLD_PROVEN = frozenset(KEY_ITEMS) | frozenset(VANILLA_SONGS.values()) | {
    'Obj_Heart_Piece', 'Obj_Heart_Container'}


def _world_forbidden(game, chests) -> frozenset[str]:
    """What a world NPC gift (an actor swapped for a wrapper) can never hold: the
    contents of the pool (chests, fountain rewards, NPC gift items, songs) that are not
    proven wrapper contents (`_WORLD_PROVEN`) or that no wrapper can be built for."""
    contents = ({c.drop for c in chests} | set(FAIRY_REWARDS) | {g.content for g in GIFTS}
                | set(VANILLA_SONGS.values()))
    wrappable = wrappers.wrap_sources(game, contents)
    return frozenset(c for c in sorted(contents)
                     if c not in wrappable or c not in _WORLD_PROVEN)


def _gs_forbidden(game, chests, loc_map, extra=()) -> frozenset[str]:
    """Contents of eligible chests, plus `extra` (moving items that are in no chest,
    such as the Great Fairy rewards), that no Skulltula can drop: no floating wrapper
    can be built for them and the game has no world actor for them."""
    original = {c.hash: c.drop for c in chests}
    rows = wrappers.pouch_rows(game)
    contents = {original[h] for h in _eligible(chests, loc_map, original)} | set(extra)
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
