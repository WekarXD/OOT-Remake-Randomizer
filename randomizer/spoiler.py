"""Spoiler log: JSON and text."""
from . import RANDO_VERSION
from .fill import TOKEN, filler_sites
from .items import DUNGEON_ITEM_PREFIXES, KEY_ITEMS, LABELS

TOKEN_LABEL = 'Gold Skulltula Token'


def _label(drop: str) -> str:
    if drop == TOKEN:
        return TOKEN_LABEL
    return LABELS.get(drop, drop)


MODE_LABELS = {'any_chest': 'Any chest', 'vanilla': 'Vanilla'}
TOKENSANITY_LABELS = {'off': 'Off', 'dungeons': 'Dungeons Only',
                      'overworld': 'Overworld Only', 'all': 'All Tokens'}


def _zone(banc: str) -> str:
    parts = banc.split('/')
    return parts[1] if len(parts) > 2 else banc


def build(settings, placement, chests, loc_map, game_version,
          skulltulas=(), gs_map=None) -> dict:
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
        if placed in KEY_ITEMS and e is not None and not e.needs_event_patch:
            key_items.append({'item': placed, 'label': _label(placed),
                              'location': e.location, 'zone': _zone(c.banc),
                              'hash': str(h)})
        if row['changed'] and e is not None and e.strip_event:
            stripped.append(str(h))
    seen_gs = set()
    for s in skulltulas:
        e = (gs_map or {}).get(s.hash)
        if s.hash in seen_gs or e is None or placement.get(s.hash) not in KEY_ITEMS:
            continue
        seen_gs.add(s.hash)
        key_items.append({'item': placement[s.hash], 'label': _label(placement[s.hash]),
                          'location': e.location, 'zone': _zone(s.banc),
                          'hash': str(s.hash)})
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
    if 'skulltulas' in d:
        lines += ['', 'Skulltulas']
        for r in d['skulltulas']:
            lines.append(f'  {r["location"]} ({r["zone"]}): {r["label"]}')
    return '\n'.join(lines) + '\n'
