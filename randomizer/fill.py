"""Deterministic fill of key items among chests (assumed fill).

`place` returns, for each chest Hash, the `Drop__DropActor` it will have.
Only eligible sites are touched (a chest mapped to an OoTR location, with no
event patch, outside the shop and not holding a dungeon item). The key items
of those sites are placed with *assumed fill*: when placing each one, all
those still to be placed are assumed owned and a site is chosen at random
among the reachable free sites. The rest of the contents of the eligible
sites is shuffled among the sites left free. The result is validated with
`World.can_beat`; if it fails, it is retried with another RNG.

With `tokensanity` other than `'off'`, the Gold Skulltulas that qualify under
the mode (`gs_sites`) are additional eligible sites, whose original content
is the token (`TOKEN`). Tokens enter the fill like the rest of the content.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from dataclasses import dataclass

from randomizer import RANDO_VERSION
from randomizer.game import ChestActor, SkulltulaActor
from randomizer.items import (DUNGEON_ITEM_PREFIXES, ITEM_LEVEL, KEY_ITEMS, LABELS,
                              NON_EXCLUDABLE)
from randomizer.locations import GsEntry, LocationEntry
from randomizer.logic.world import World

MODES = ('vanilla', 'any_chest')
TOKENSANITY = ('off', 'dungeons', 'overworld', 'all')
TOKEN = 'Obj_Token_Gold'
OOTR_TOKEN = 'Gold Skulltula Token'
MAX_ATTEMPTS = 100
FILLER = 'Rupees (5)'
# Zones (path segment of the Banc after 'Banc/') where no key items are
# placed. Their chests are still sources of items and destinations for filler,
# but in the remake the number of small keys and doors in these dungeons
# differs from the N64 (Water Temple has 4 keys instead of 6, Gerudo Training
# Ground, Well) and the free key in the Fire Temple is an OoTR assumption;
# the logic is not reliable there.
NO_KEY_TARGET_ZONES = frozenset({'WaterTemple', 'GerudoTrainingGround',
                                 'BottomOfTheWell', 'FireTemple'})


@dataclass(frozen=True)
class Settings:
    seed: str
    key_items_mode: str = 'any_chest'  # 'vanilla' | 'any_chest'
    excluded_items: frozenset[str] = frozenset()
    spoiler: bool = True
    skip_cutscenes: bool = False
    tokensanity: str = 'off'  # see TOKENSANITY


class FillError(Exception):
    pass


def _settings_key(settings: Settings) -> str:
    data = dataclasses.asdict(settings)
    del data['seed']
    del data['spoiler']  # only affects the output files, not the placement
    del data['skip_cutscenes']  # same: does not change the placement
    data['excluded_items'] = sorted(settings.excluded_items)
    if settings.tokensanity == 'off':
        del data['tokensanity']  # the key stays as it was before the option existed
    return json.dumps(data, sort_keys=True)


def _rng(settings: Settings, attempt: int) -> random.Random:
    text = f'{RANDO_VERSION}|{settings.seed}|{_settings_key(settings)}|{attempt}'
    digest = hashlib.sha256(text.encode()).digest()
    return random.Random(int.from_bytes(digest[:8], 'big'))


def _original_drops(chests: list[ChestActor]) -> dict[int, str]:
    out: dict[int, str] = {}
    for c in chests:
        prev = out.setdefault(c.hash, c.drop)
        if prev != c.drop:
            raise FillError(f'Chest {c.hash} has different contents in its copies')
    return out


def _eligible(chests: list[ChestActor], loc_map: dict[int, LocationEntry],
              original: dict[int, str]) -> list[int]:
    shop = {c.hash for c in chests if 'HrlCity_Shop' in c.gyaml}
    out = []
    for h in sorted(original):
        entry = loc_map.get(h)
        if entry is None or entry.status == 'unmapped' or entry.needs_event_patch:
            continue
        if h in shop or original[h].startswith(DUNGEON_ITEM_PREFIXES):
            continue
        out.append(h)
    return out


def gs_sites(skulltulas: list[SkulltulaActor], gs_map: dict[int, GsEntry] | None,
             mode: str) -> list[int]:
    """Hashes of the Skulltulas that are sites under this tokensanity mode,
    without duplicates and sorted. Those not in `gs_map` are left out."""
    if mode not in TOKENSANITY:
        raise FillError(f'Unknown tokensanity mode: {mode!r}')
    if mode == 'off' or not gs_map:
        return []
    out = set()
    for s in skulltulas:
        entry = gs_map.get(s.hash)
        if entry is not None and (mode == 'all' or entry.dungeon == (mode == 'dungeons')):
            out.add(s.hash)
    return sorted(out)


def _fixed(world_base: dict[str, str], site_loc: dict[int, str],
           placed: dict[int, str]) -> dict[str, str]:
    """The logic's `fixed`: vanilla base with the eligible sites set to filler
    (`world_base`) and the key items and tokens already placed on top."""
    fixed = dict(world_base)
    for h in sorted(placed):
        drop = placed[h]
        if drop in KEY_ITEMS:
            fixed[site_loc[h]] = drop
        elif drop == TOKEN:
            fixed[site_loc[h]] = OOTR_TOKEN
    return fixed


def _attempt(rng: random.Random, original: dict[int, str], eligible: list[int],
             moving: list[int], site_loc: dict[int, str], world: World,
             base: dict[str, str], no_key: frozenset[int] = frozenset(),
             gs: frozenset[int] = frozenset(),
             gs_forbidden: frozenset[str] = frozenset()) -> dict[int, str] | None:
    # Eligible sites that stay fixed: those of excluded key items.
    pinned = {h: original[h] for h in eligible
              if original[h] in KEY_ITEMS and h not in moving}
    free = [h for h in eligible if h not in pinned]

    to_place = [original[h] for h in moving]
    rng.shuffle(to_place)
    # Stable: higher-level progressives first, the rest in shuffled order.
    to_place.sort(key=lambda a: -ITEM_LEVEL[a][1] if a in ITEM_LEVEL else 0)

    placed: dict[int, str] = dict(pinned)
    for i, item in enumerate(to_place):
        reach = world.reachable_locations(_fixed(base, site_loc, placed),
                                          owned=to_place[i + 1:])
        candidates = [h for h in free if h not in placed and h not in no_key
                      and site_loc[h] in reach
                      and not (h in gs and item in gs_forbidden)]
        if not candidates:
            return None
        placed[rng.choice(candidates)] = item

    rest = [original[h] for h in free if h not in moving]
    rng.shuffle(rest)
    open_sites = [h for h in free if h not in placed]
    # Free Skulltulas are filled first, with the first shuffled contents that
    # can be dropped; what is left goes to the free chests.
    open_gs = [h for h in open_sites if h in gs]
    allowed = [i for i, drop in enumerate(rest) if drop not in gs_forbidden][:len(open_gs)]
    if len(allowed) < len(open_gs):
        raise FillError('Not enough items that can be dropped by the Skulltulas')
    for h, i in zip(open_gs, allowed, strict=True):
        placed[h] = rest[i]
    taken = set(allowed)
    rest = [drop for i, drop in enumerate(rest) if i not in taken]
    open_chests = [h for h in open_sites if h not in gs]
    for h, drop in zip(open_chests, rest, strict=True):
        placed[h] = drop

    if not world.can_beat(_fixed(base, site_loc, placed)):
        return None
    result = dict(original)
    result.update(placed)
    return result


def place(chests: list[ChestActor], loc_map: dict[int, LocationEntry],
          world: World, settings: Settings,
          skulltulas: list[SkulltulaActor] = (),
          gs_map: dict[int, GsEntry] | None = None,
          gs_forbidden: frozenset[str] = frozenset()) -> dict[int, str]:
    """Hash -> Drop__DropActor map for all chests in `chests` and the
    Skulltulas that qualify under `settings.tokensanity` (see `gs_sites`).
    `gs_forbidden`: contents that cannot go to a Skulltula."""
    if settings.key_items_mode not in MODES:
        raise FillError(f'Unknown key item mode: {settings.key_items_mode!r}')
    bad = settings.excluded_items & NON_EXCLUDABLE
    if bad:
        label = ', '.join(LABELS.get(a, a) for a in sorted(bad))
        raise FillError(f'Cannot exclude {label}: the logic needs to move it '
                        'for the game to be beatable.')
    gs = gs_sites(skulltulas, gs_map, settings.tokensanity)
    original = _original_drops(chests)
    for h in gs:
        if h in original:
            raise FillError(f'Hash {h} is both a chest and a Skulltula')
        original[h] = TOKEN
    if settings.key_items_mode == 'vanilla':
        return dict(original)

    chest_sites = _eligible(chests, loc_map, original)
    eligible = sorted(chest_sites + gs)
    site_loc = {h: loc_map[h].location for h in chest_sites}
    site_loc.update((h, gs_map[h].location) for h in gs)
    moving = [h for h in eligible if original[h] in KEY_ITEMS
              and original[h] not in settings.excluded_items]
    bancs = [(c.hash, c.banc) for c in chests] + [(s.hash, s.banc) for s in skulltulas]
    no_key = frozenset(h for h, banc in bancs
                       if banc.split('/')[1:2] and banc.split('/')[1] in NO_KEY_TARGET_ZONES)
    no_key |= frozenset(h for h in gs
                        if gs_map[h].no_key or gs_map[h].status == 'guessed')
    base = world.vanilla_fixed()
    for h in eligible:
        base[site_loc[h]] = FILLER

    for attempt in range(MAX_ATTEMPTS + 1):
        result = _attempt(_rng(settings, attempt), original, eligible, moving,
                          site_loc, world, base, no_key, frozenset(gs), gs_forbidden)
        if result is not None:
            return result
    raise FillError('Could not generate a beatable seed with these settings')
