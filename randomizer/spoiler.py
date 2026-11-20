"""Spoiler log: JSON and text."""
from . import RANDO_VERSION
from .fill import TOKEN, filler_sites
from .items import DUNGEON_ITEM_PREFIXES, KEY_ITEMS, LABELS
from .songs import SONG_BY_ACTOR

TOKEN_LABEL = 'Gold Skulltula Token'


def _label(drop: str) -> str:
    if drop == TOKEN:
        return TOKEN_LABEL
    if drop in SONG_BY_ACTOR:
        return SONG_BY_ACTOR[drop].song
    return LABELS.get(drop, drop)


MODE_LABELS = {'any_chest': 'Any chest', 'vanilla': 'Vanilla'}
TOKENSANITY_LABELS = {'off': 'Off', 'dungeons': 'Dungeons Only',
                      'overworld': 'Overworld Only', 'all': 'All Tokens'}
SHUFFLE_SONGS_LABELS = {'off': 'Off', 'song_locations': 'Song Locations', 'anywhere': 'Anywhere',
                        'dungeon_rewards': 'Dungeon Rewards'}


def _zone(banc: str) -> str:
    parts = banc.split('/')
    return parts[1] if len(parts) > 2 else banc


def build(settings, placement, chests, loc_map, game_version,
          skulltulas=(), gs_map=None, cutscenes_not_skipped=None, songs=None,
          hearts=None, fairies=None, gifts=None) -> dict:
    original: dict[int, str] = {}
    site: dict[int, object] = {}
    for c in chests:
        original.setdefault(c.hash, c.drop)
        site.setdefault(c.hash, c)
    shop = {c.hash for c in chests if 'HrlCity_Shop' in c.gyaml}
    # Unmapped chests that take part in the fill with minor items.
    filler = set(filler_sites(chests, loc_map)) if settings.key_items_mode != 'vanilla' else set()

    all_chests, key_items, excluded, stripped = [], [], [], []
    for h in sorted(site):
        c = site[h]
        e = loc_map.get(h)
        if e is not None and e.status == 'unmapped':
            e = None
        placed = placement.get(h, original[h])
        row = {'hash': str(h), 'zone': _zone(c.banc),
               'location': e.location if e else None,
               'original': original[h], 'placed': placed,
               'changed': placed != original[h]}
        all_chests.append(row)
        reason = None
        if h in shop:
            reason = 'shop'
        elif original[h].startswith(DUNGEON_ITEM_PREFIXES):
            reason = 'dungeon item'
        elif e is None and h not in filler:
            reason = 'unmapped'
        elif e is not None and e.needs_event_patch:
            reason = 'story event'
        if reason:
            excluded.append({**row, 'reason': reason})
        is_key = placed in KEY_ITEMS or placed in SONG_BY_ACTOR
        if is_key and e is not None and not e.needs_event_patch:
            key_items.append({'item': placed, 'label': _label(placed),
                              'location': e.location, 'zone': _zone(c.banc),
                              'hash': str(h)})
        if row['changed'] and e is not None and e.strip_event:
            stripped.append(str(h))
    seen_gs = set()
    for s in skulltulas:
        e = (gs_map or {}).get(s.hash)
        if s.hash in seen_gs or e is None or (placement.get(s.hash) not in KEY_ITEMS
                                              and placement.get(s.hash) not in SONG_BY_ACTOR):
            continue
        seen_gs.add(s.hash)
        key_items.append({'item': placement[s.hash], 'label': _label(placement[s.hash]),
                          'location': e.location, 'zone': _zone(s.banc),
                          'hash': str(s.hash)})
    if settings.shuffle_songs in ('anywhere', 'dungeon_rewards'):
        # Song scenes (and boss hearts) are item locations too: list the key items and
        # songs they give.
        sites = [(loc, a, 'Song scene') for loc, a in sorted((songs or {}).items())]
        sites += [(loc, a, 'Boss heart') for loc, a in sorted((hearts or {}).items())]
        for loc, actor, zone in sites:
            if actor in KEY_ITEMS or actor in SONG_BY_ACTOR:
                key_items.append({'item': actor, 'label': _label(actor), 'location': loc,
                                  'zone': zone, 'hash': ''})
    # Great Fairy fountains (key items shuffled) are item locations too.
    for loc, actor in sorted((fairies or {}).items()):
        if actor in KEY_ITEMS or actor in SONG_BY_ACTOR:
            key_items.append({'item': actor, 'label': _label(actor), 'location': loc,
                              'zone': 'Great Fairy', 'hash': ''})
    # NPC gifts (key items shuffled) too.
    for loc, actor in sorted((gifts or {}).items()):
        if actor in KEY_ITEMS or actor in SONG_BY_ACTOR:
            key_items.append({'item': actor, 'label': _label(actor), 'location': loc,
                              'zone': 'NPC gift', 'hash': ''})
    key_items.sort(key=lambda r: (r['label'], r['location'], r['hash']))
    result = {
        'seed': settings.seed,
        'settings': {'key_items_mode': settings.key_items_mode,
                     'excluded_items': sorted(settings.excluded_items),
                     'spoiler': settings.spoiler,
                     'skip_cutscenes': settings.skip_cutscenes},
        'randomizer_version': RANDO_VERSION,
        'game_version': game_version,
        'key_items': key_items,
        'chests': all_chests,
        'excluded': excluded,
        'stripped_event_sites': stripped,
    }
    if settings.tokensanity != 'off':
        result['settings']['tokensanity'] = settings.tokensanity
        result['skulltulas'] = _skulltula_rows(placement, skulltulas, gs_map or {})
    if settings.shuffle_songs != 'off':
        result['settings']['shuffle_songs'] = settings.shuffle_songs
        result['songs'] = [{'location': loc, 'song': actor,
                            'label': _label(actor)}
                           for loc, actor in sorted((songs or {}).items())]
    if hearts:
        result['boss_hearts'] = [{'location': loc, 'item': a, 'label': _label(a)}
                                 for loc, a in sorted(hearts.items())]
    if fairies:
        result['great_fairies'] = [{'location': loc, 'item': a, 'label': _label(a)}
                                   for loc, a in sorted(fairies.items())]
    if gifts:
        result['npc_gifts'] = [{'location': loc, 'item': a, 'label': _label(a)}
                               for loc, a in sorted(gifts.items())]
    if cutscenes_not_skipped is not None and settings.skip_cutscenes:
        result['cutscenes_not_skipped'] = list(cutscenes_not_skipped)
    return result


def _skulltula_rows(placement, skulltulas, gs_map) -> list[dict]:
    rows, seen = [], set()
    for s in skulltulas:
        if s.hash in seen or s.hash not in placement or s.hash not in gs_map:
            continue
        seen.add(s.hash)
        placed = placement[s.hash]
        label = _label(placed)
        rows.append({'hash': str(s.hash), 'zone': _zone(s.banc),
                     'location': gs_map[s.hash].location, 'placed': placed,
                     'label': label})
    rows.sort(key=lambda r: (r['location'], r['hash']))
    return rows


def to_text(d: dict) -> str:
    s = d['settings']
    excl = ', '.join(_label(i) for i in s['excluded_items']) or 'none'
    lines = ['Seed', f'  {d["seed"]}', '', 'Settings',
             f'  Key item mode: {MODE_LABELS.get(s["key_items_mode"], s["key_items_mode"])}',
             f'  Excluded items: {excl}',
             f'  Skip cutscenes: {"Yes" if s.get("skip_cutscenes") else "No"}']
    if 'tokensanity' in s:
        lines.append('  Gold Skulltula Tokens (Tokensanity): '
                     f'{TOKENSANITY_LABELS.get(s["tokensanity"], s["tokensanity"])}')
    if 'shuffle_songs' in s:
        lines.append('  Shuffle Songs: '
                     f'{SHUFFLE_SONGS_LABELS.get(s["shuffle_songs"], s["shuffle_songs"])}')
    lines += ['', 'Randomizer version', f'  {d["randomizer_version"]}', '',
             'Game version', f'  {d["game_version"]}', '', 'Key items']
    for k in d['key_items']:
        lines.append(f'  {k["label"]}: {k["location"]} ({k["zone"]})')
    lines += ['', 'All chests']
    for r in d['chests']:
        mark = '*' if r['changed'] else ' '
        loc = r['location'] or 'unmapped'
        lines.append(f' {mark} {r["zone"]} {r["hash"]} [{loc}]: '
                     f'{_label(r["original"])} -> {_label(r["placed"])}')
    lines += ['', 'Excluded / unmapped']
    for r in d['excluded']:
        loc = r['location'] or 'unmapped'
        lines.append(f'  {r["zone"]} {r["hash"]} [{loc}]: {_label(r["original"])}'
                     f' ({r["reason"]})')
    if 'songs' in d:
        lines += ['', 'Songs']
        lines += [f'  {r["location"]}: {r["label"]}' for r in d['songs']]
    if 'boss_hearts' in d:
        lines += ['', 'Boss hearts']
        lines += [f'  {r["location"]}: {r["label"]}' for r in d['boss_hearts']]
    if 'great_fairies' in d:
        lines += ['', 'Great Fairies']
        lines += [f'  {r["location"]}: {r["label"]}' for r in d['great_fairies']]
    if 'npc_gifts' in d:
        lines += ['', 'NPC Gifts']
        lines += [f'  {r["location"]}: {r["label"]}' for r in d['npc_gifts']]
    if 'skulltulas' in d:
        lines += ['', 'Skulltulas']
        for r in d['skulltulas']:
            lines.append(f'  {r["location"]} ({r["zone"]}): {r["label"]}')
    if 'cutscenes_not_skipped' in d:
        lines += ['', 'Cutscenes not skipped']
        lines += [f'  {line}' for line in d['cutscenes_not_skipped']] or ['  none']
    return '\n'.join(lines) + '\n'
