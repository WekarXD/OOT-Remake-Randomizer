"""Spoiler: JSON y texto en español."""
from . import RANDO_VERSION
from .items import KEY_ITEMS, LABELS_ES


def _label(drop: str) -> str:
    return LABELS_ES.get(drop, drop)


MODE_LABELS = {'any_chest': 'Cualquier cofre', 'vanilla': 'Vanilla'}


def _zone(banc: str) -> str:
    parts = banc.split('/')
    return parts[1] if len(parts) > 2 else banc


def build(settings, placement, chests, loc_map, game_version) -> dict:
    original: dict[int, str] = {}
    site: dict[int, object] = {}
    for c in chests:
        original.setdefault(c.hash, c.drop)
        site.setdefault(c.hash, c)

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
        if e is None or e.needs_event_patch:
            excluded.append(row)
        if placed in KEY_ITEMS and e is not None and not e.needs_event_patch:
            key_items.append({'item': placed, 'label': _label(placed),
                              'location': e.location, 'zone': _zone(c.banc),
                              'hash': str(h)})
        if row['changed'] and e is not None and e.strip_event:
            stripped.append(str(h))
    key_items.sort(key=lambda r: (r['label'], r['location'], r['hash']))
    return {
        'seed': settings.seed,
        'settings': {'key_items_mode': settings.key_items_mode,
                     'excluded_items': sorted(settings.excluded_items),
                     'spoiler': settings.spoiler},
        'randomizer_version': RANDO_VERSION,
        'game_version': game_version,
        'key_items': key_items,
        'chests': all_chests,
        'excluded': excluded,
        'stripped_event_sites': stripped,
    }


def to_text(d: dict) -> str:
    s = d['settings']
    excl = ', '.join(_label(i) for i in s['excluded_items']) or 'ninguno'
    lines = ['Semilla', f'  {d["seed"]}', '', 'Ajustes',
             f'  Modo de objetos clave: {MODE_LABELS.get(s["key_items_mode"], s["key_items_mode"])}',
             f'  Objetos excluidos: {excl}',
             '', 'Versión del randomizer', f'  {d["randomizer_version"]}', '',
             'Versión del juego', f'  {d["game_version"]}', '', 'Objetos clave']
    for k in d['key_items']:
        lines.append(f'  {k["label"]}: {k["location"]} ({k["zone"]})')
    lines += ['', 'Todos los cofres']
    for r in d['chests']:
        mark = '*' if r['changed'] else ' '
        loc = r['location'] or 'sin asociar'
        lines.append(f' {mark} {r["zone"]} {r["hash"]} [{loc}]: '
                     f'{_label(r["original"])} -> {_label(r["placed"])}')
    lines += ['', 'Excluidos / sin asociar']
    for r in d['excluded']:
        loc = r['location'] or 'sin asociar'
        lines.append(f'  {r["zone"]} {r["hash"]} [{loc}]: {_label(r["original"])}')
    return '\n'.join(lines) + '\n'
