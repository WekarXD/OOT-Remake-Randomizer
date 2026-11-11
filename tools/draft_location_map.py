"""Generates the draft of randomizer/data/location_map.json.

Usage: python tools/draft_location_map.py <nup>
       python tools/draft_location_map.py --fixture tests/fixtures/chests.json

Maps each chest (Hash) to an OoTR location by (zone -> OoTR prefix,
original content -> vanilla item). Single candidate -> 'auto'. Several or
none -> location null, status 'unmapped' and a note with the candidates and
the positions, to be resolved by hand.

Never overwrites hand-reviewed entries: status 'manual', or 'unmapped'
with a note that starts with 'manual:'. Always keeps needs_event_patch and
strip_event.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer import items  # noqa: E402
from randomizer.game import load_chests_fixture  # noqa: E402
from randomizer.locations import MAP_PATH  # noqa: E402
from randomizer.logic.ootr_data import load_locations  # noqa: E402

ZONE_PREFIXES: dict[str, tuple[str, ...]] = {
    'KokiriForest': ('KF',),
    'LostWood': ('LW',),
    'SacredForestMeadow': ('SFM',),
    'HyruleField': ('HF',),
    'Market': ('Market',),
    'HyruleCastle': ('HC',),
    'KakarikoVillage': ('Kak',),
    'Graveyard': ('Graveyard',),
    'DeathMountainTrail': ('DMT',),
    'DeathMountainCrater': ('DMC',),
    'GoronCity': ('GC',),
    'ZoraRiver': ('ZR',),
    'ZoraDomain': ('ZD',),
    'ZoraFountain': ('ZF',),
    'GerudoValley': ('GV',),
    'GerudoFortress': ('GF',),
    'HountedWasteland': ('Wasteland',),
    'DesertColossus': ('Colossus', 'Spirit Temple'),
    'InsideTheDekuTree': ('Deku Tree',),
    'DodongoCavern': ('Dodongos Cavern',),
    'InsideJabuJabuBelly': ('Jabu Jabus Belly',),
    'ForestTemple': ('Forest Temple',),
    'FireTemple': ('Fire Temple',),
    'WaterTemple': ('Water Temple',),
    'ShadowTemple': ('Shadow Temple',),
    'SpiritTemple': ('Spirit Temple',),
    'IceCavern': ('Ice Cavern',),
    'BottomOfTheWell': ('Bottom of the Well',),
    'GerudoTrainingGround': ('Gerudo Training Ground',),
    'InsideGanonCastle': ('Ganons Castle', 'Ganons Tower'),
    'GanonCastle': ('Ganons Tower',),
}


def zone_of(banc: str) -> str:
    return banc.split('/')[1]


def is_reviewed(e: dict) -> bool:
    return e['status'] == 'manual' or (
        e['status'] == 'unmapped' and e['note'].startswith('manual:'))


def chest_candidates(ootr: dict, prefixes) -> list[str]:
    out = []
    for name, loc in ootr.items():
        if loc['type'] != 'Chest' or ' MQ ' in name:
            continue
        if any(name.startswith(p + ' ') for p in prefixes):
            out.append(name)
    return sorted(out)


def fmt_pos(pos) -> str:
    return '(' + ', '.join(f'{x:.1f}' for x in pos) + ')'


def draft(chests, ootr: dict, existing: dict) -> dict:
    by_hash = {}
    for c in chests:
        by_hash.setdefault(c.hash, c)
    out = {}
    used = set()
    for h, c in by_hash.items():
        e = existing.get(str(h))
        if e and is_reviewed(e):
            out[str(h)] = dict(e)
            out[str(h)].setdefault('strip_event', False)
            if e['location']:
                used.add(e['location'])

    groups = defaultdict(list)
    for h, c in by_hash.items():
        if str(h) not in out:
            groups[(zone_of(c.banc), c.drop)].append(c)

    for (zone, drop), group in sorted(groups.items()):
        prefixes = ZONE_PREFIXES.get(zone)
        cands = [] if prefixes is None else [
            n for n in chest_candidates(ootr, prefixes)
            if n not in used and items.content_matches(drop, ootr[n]['vanilla_item'])]
        for c in sorted(group, key=lambda c: c.hash):
            key = str(c.hash)
            old = existing.get(key, {})
            entry = {'location': None, 'status': 'unmapped',
                     'needs_event_patch': bool(old.get('needs_event_patch', False)),
                     'strip_event': bool(old.get('strip_event', False)),
                     'note': ''}
            where = f'{c.gyaml} {drop} in {zone} {fmt_pos(c.pos)}'
            if prefixes is None:
                entry['note'] = f'area with no OoTR equivalent; {where}'
            elif len(group) == 1 and len(cands) == 1:
                note = f'auto: {where}'
                if old.get('status') == 'auto' and old.get('location') == cands[0]:
                    note = old['note']  # keep what was added by hand to the note
                entry.update(location=cands[0], status='auto', note=note)
                used.add(cands[0])
            elif not cands:
                entry['note'] = f'no candidate by content; {where}'
            else:
                others = ', '.join(f'{o.hash}{fmt_pos(o.pos)}' for o in group)
                entry['note'] = (f'ambiguous; {where}; candidates: {"; ".join(cands)}'
                                 f'; group chests: {others}')
            out[key] = entry
    return out


def write_map(data: dict, path=MAP_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write('\n')


def main(argv):
    if len(argv) == 2 and argv[0] == '--fixture':
        chests = load_chests_fixture(argv[1])
    elif len(argv) == 1:
        from randomizer.game import GameData
        from randomizer.nup import NupArchive
        with NupArchive(argv[0]) as nup:
            chests = GameData(nup).chests()
    else:
        sys.exit(__doc__)
    existing = {}
    if MAP_PATH.exists():
        existing = json.loads(MAP_PATH.read_text(encoding='utf-8'))
    data = draft(chests, load_locations(), existing)
    write_map(data)
    counts = defaultdict(int)
    for e in data.values():
        counts[e['status']] += 1
    print(f'{len(data)} chests -> {MAP_PATH}: {dict(sorted(counts.items()))}')


if __name__ == '__main__':
    main(sys.argv[1:])
