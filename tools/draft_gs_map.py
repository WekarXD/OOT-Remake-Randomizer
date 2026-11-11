"""Generates the draft of randomizer/data/gs_map.json (Gold Skulltulas).

Usage: python tools/draft_gs_map.py <nup>
       python tools/draft_gs_map.py --fixture tests/fixtures/skulltulas.json

Groups the Skulltulas (Hash) by zone (second segment of the Banc path)
and matches them with the 100 'Gold Skulltula Token' locations of OoTR (no MQ)
by name prefix. A zone with a single Skulltula and a single
candidate is mapped automatically ('confirmed'). The rest is left with location null,
status 'guessed' and a note with the data and the candidates, to be reviewed
by hand zone by zone.

Never overwrites an entry that already has a location: those are the reviewed ones.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer.game import load_skulltulas_fixture  # noqa: E402
from randomizer.locations import GS_MAP_PATH  # noqa: E402

TOKEN = 'Gold Skulltula Token'

# Remake zone -> prefixes of the OoTR names ('<prefix> GS ...').
ZONE_PREFIXES: dict[str, tuple[str, ...]] = {
    'KokiriForest': ('KF',),
    'LostWood': ('LW',),
    'SacredForestMeadow': ('SFM',),
    'HyruleField': ('HF', 'LLR', 'LH'),
    'Market': ('Market',),
    'HyruleCastle': ('HC',),
    'GanonCastle': ('OGC',),
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
    'DesertColossus': ('Colossus',),
    'InsideTheDekuTree': ('Deku Tree',),
    'DodongoCavern': ('Dodongos Cavern',),
    'InsideJabuJabuBelly': ('Jabu Jabus Belly',),
    'ForestTemple': ('Forest Temple',),
    'FireTemple': ('Fire Temple',),
    'WaterTemple': ('Water Temple',),
    'ShadowTemple': ('Shadow Temple',),
    'SpiritTemple': ('Spirit Temple',),
    'BottomOfTheWell': ('Bottom of the Well',),
    'IceCavern': ('Ice Cavern',),
}

DUNGEON_ZONES = frozenset({
    'InsideTheDekuTree', 'DodongoCavern', 'InsideJabuJabuBelly', 'ForestTemple',
    'FireTemple', 'WaterTemple', 'ShadowTemple', 'SpiritTemple',
    'BottomOfTheWell', 'IceCavern',
})


def zone_of(banc: str) -> str:
    return banc.split('/')[1]


def gs_locations() -> list[str]:
    """The 100 OoTR Skulltula locations that exist in the vanilla world."""
    from randomizer.logic.world import World, load_vanilla_settings
    w = World(load_vanilla_settings())
    names = {loc for _, loc, _ in w._all_locations}
    return sorted(n for n, v in w.locations.items()
                  if v['vanilla_item'] == TOKEN and n in names)


def fmt_pos(pos) -> str:
    return '(' + ', '.join(f'{x:.1f}' for x in pos) + ')'


def describe(placements) -> str:
    """Bancs, flags and position of all the placements of a Hash."""
    bancs = sorted(p.banc.rsplit('/', 1)[1].split('.')[0] for p in placements)
    flags = sorted({f.removeprefix('Enemy_Skulltula_Gold_')
                    for p in placements for f in p.flags})
    return f'{"+".join(bancs)} [{",".join(flags)}] {fmt_pos(placements[0].pos)}'


def draft(skulltulas, locations: list[str], existing: dict) -> dict:
    by_hash = defaultdict(list)
    for s in skulltulas:
        by_hash[s.hash].append(s)
    zones = defaultdict(list)
    for h, ps in by_hash.items():
        zones[zone_of(ps[0].banc)].append(h)

    out = {}
    for zone, hashes in sorted(zones.items()):
        prefixes = ZONE_PREFIXES[zone]
        cands = [n for n in locations if n.split(' GS')[0] in prefixes]
        if len(cands) != len(hashes):
            raise ValueError(f'{zone}: {len(hashes)} Skulltulas, {len(cands)} in OoTR')
        dungeon = zone in DUNGEON_ZONES
        for h in sorted(hashes):
            old = existing.get(str(h))
            if old and old.get('location'):
                out[str(h)] = dict(old, dungeon=dungeon)
                continue
            where = f'{zone} {describe(by_hash[h])}'
            if len(cands) == 1:
                entry = {'location': cands[0], 'status': 'confirmed',
                         'note': f'auto: the only one in the area; {where}'}
            else:
                entry = {'location': None, 'status': 'guessed',
                         'note': f'pending; {where}; candidates: {"; ".join(cands)}'}
            out[str(h)] = dict(entry, dungeon=dungeon)
    return out


def write_map(data: dict, path=GS_MAP_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write('\n')


def main(argv):
    if len(argv) == 2 and argv[0] == '--fixture':
        skulltulas = load_skulltulas_fixture(argv[1])
    elif len(argv) == 1:
        from randomizer.game import GameData
        from randomizer.nup import NupArchive
        with NupArchive(argv[0]) as nup:
            skulltulas = GameData(nup).skulltulas()
    else:
        sys.exit(__doc__)
    existing = {}
    if GS_MAP_PATH.exists():
        existing = json.loads(GS_MAP_PATH.read_text(encoding='utf-8'))
    data = draft(skulltulas, gs_locations(), existing)
    write_map(data)
    counts = defaultdict(int)
    for e in data.values():
        counts['pending' if e['location'] is None else e['status']] += 1
    print(f'{len(data)} Skulltulas -> {GS_MAP_PATH}: {dict(sorted(counts.items()))}')


if __name__ == '__main__':
    main(sys.argv[1:])
