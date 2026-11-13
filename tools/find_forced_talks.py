"""Finds forced conversations (the "Skip cutscenes" option, extension 1).

Usage: python -I tools/find_forced_talks.py <nup> [--age child|adult] [--zones Z1,Z2,...]

Only reads the .nup. Prints, per zone, the candidate (flow, entry) pairs,
how they are triggered, and which actions the phase 1 trim would remove if
the entry were listed alone in `story_flows`. The curated list lives in
`tools/build_cutscene_list.py` (FORCED_TALKS); this tool does not write it.

How an event is triggered (investigated on 2026-11-09):
- Each named event is a row of `RSDB/EventSetting.Product.*.rstbl`:
  `__RowId` -> `FlowchartFileName` + `EntryPointName` + a component list
  (`EventSettingComponentList`) that says how it starts:
  `NPCTalkNoPause`/`NPCTalk` = the player presses A in front of an NPC; `NPCNear` =
  bubble on approach (does not stop the player); `FlowchartEvent` and variants =
  event launched by another actor; `NaviHintEvent` = Navi hint.
- The actors of the bancs (`Banc/<Zone>/*.bcett.byml.zs`) name rows in
  their `Dynamic` parameters. The parameter says who launches it:
  - FORCED: `RequestEventName` of `EventRequestActor` /
    `EventProxyRequestActor` (zone trigger: fires on stepping into an area or
    when a condition is met), `PlayerDiscoveredEventName` (a guard sees you),
    `JumpSlushTutorialEventName` (tutorial on hitting the rock).
  - VOLUNTARY: `TalkEventName` (talking), `CheckEventName*` (opening a
    door), `EventNameFromInstanceParam` (reading a sign), `DamageEventName`
    (hitting the NPC), `GetEventName` (chest).
  - ZONE ENTRANCE: `InitEventName`/`FirstEventName`/`NextEventName`/
    `AddEventName` (`Dm_*`/`Goto_*` flows, already treated as story).
- NPCs that block the way: their flow uses the blocking AI (`EventNpcBlocker*`)
  and the engine launches their chat entry when the player bumps into them
  (Mido before having the sword and shield). The entries of the `Npc_*` flows
  of the zones' actors whose graph uses those actions are searched for.
- Rows launched by the game's code (with no reference in the bancs), e.g.
  `NaviLockOnHint`/`NaviLockOnHintObject` -> `NaviHint:Hint_00`. They are listed in
  ENGINE_ROWS so they are reviewed all the same.
- An entry that is also used voluntarily (another non-forced row
  points to it) is marked SHARED and must not be listed.
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer.cutscenes import (FLOW_DIR, FLOW_EXT, active_actions,  # noqa: E402
                                  load_policy, reachable, trim_flow)
from randomizer.formats import byml  # noqa: E402
from randomizer.formats.bfevfl import ACTION, SUBFLOW, EventFlow  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.nup import NupArchive, NupError  # noqa: E402

CHILD_ZONES = ('KokiriForest', 'InsideTheDekuTree', 'HyruleField', 'Market',
               'HyruleCastle', 'KakarikoVillage')
# Adult rollout (full-skip spec §6 step 3): the zones Link visits as an adult, without
# Ganon's Castle (step 4) and the boss rooms (DreamWorld: boss scenes are kept). Lake Hylia
# and Lon Lon Ranch are part of HyruleField. Bancs with no age in their name (temples)
# count for both ages.
ADULT_ZONES = ('KokiriForest', 'LostWood', 'SacredForestMeadow', 'ForestTemple',
               'HyruleField', 'Market', 'KakarikoVillage', 'Graveyard', 'ShadowTemple',
               'BottomOfTheWell', 'DeathMountainTrail', 'DeathMountainCrater', 'GoronCity',
               'FireTemple', 'ZoraRiver', 'ZoraDomain', 'ZoraFountain', 'IceCavern',
               'WaterTemple', 'GerudoValley', 'GerudoFortress',
               'GerudoTrainingGround', 'HountedWasteland', 'DesertColossus', 'SpiritTemple',
               'SageRoom', 'HyruleCastle')
OTHER_AGE = {'child': '_Adult', 'adult': '_Child'}  # banc name mark of the other age
RSDB = 'RSDB/EventSetting.Product.111.rstbl.byml.zs'
FORCED_PARAMS = {'RequestEventName', 'PlayerDiscoveredEventName',
                 'JumpSlushTutorialEventName'}
VOLUNTARY_PARAMS = {'TalkEventName', 'CheckEventName', 'CheckEventNameIndoor',
                    'EventNameFromInstanceParam', 'DamageEventName', 'GetEventName'}
ENGINE_ROWS = {'NaviLockOnHint': 'KokiriForest', 'NaviLockOnHintObject': 'KokiriForest'}
VOLUNTARY_COMPONENTS = ('NPCTalk', 'NPCGatherTalk', 'NPCChaseTalk', 'NaviHint',
                        'EnemyScrubBusinessTalk', 'MiniGame')


def _base(path: str | None) -> str:
    return (path or '').rsplit('/', 1)[-1].split('.', 1)[0]


def load_rows(game) -> dict[str, dict]:
    _ver, rows = byml.load(game.codec.decompress(RSDB, game.nup.read(RSDB)))
    return {r['__RowId']: r for r in rows}


def _strings(obj, key=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, str(k))
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v, key)
    elif isinstance(obj, str):
        yield key, obj


def banc_triggers(game, rows, zones, age='child'):
    """(zone, actor, parameter, row) of the zones' bancs of that age (and ageless ones)."""
    out = []
    for path in game.nup.list('Banc/'):
        parts = path.split('/')
        if (len(parts) != 3 or parts[1] not in zones or OTHER_AGE[age] in parts[2]
                or not path.endswith('.bcett.byml.zs')):
            continue
        _ver, root = game.load_banc(path)
        for a in (root.get('Actors') if isinstance(root, dict) else None) or []:
            if not isinstance(a, dict):
                continue
            for key, val in _strings(a.get('Dynamic') or {}):
                if val in rows:
                    out.append((parts[1], str(a.get('Gyaml')), key, val))
    return out


def zone_npcs(game, zones, age='child'):
    """Zone -> `Npc_*` actor names of that age (or ageless) from its bancs of that age."""
    out = defaultdict(set)
    for path in game.nup.list('Banc/'):
        parts = path.split('/')
        if (len(parts) != 3 or parts[1] not in zones or OTHER_AGE[age] in parts[2]
                or not path.endswith('.bcett.byml.zs')):
            continue
        _ver, root = game.load_banc(path)
        for a in (root.get('Actors') if isinstance(root, dict) else None) or []:
            g = str(a.get('Gyaml', '')) if isinstance(a, dict) else ''
            if g.startswith('Npc_') and not g.endswith(OTHER_AGE[age]):
                out[parts[1]].add(g)
    return out


def classify(param: str) -> str:
    if param in FORCED_PARAMS:
        return 'forced'
    if param in VOLUNTARY_PARAMS:
        return 'voluntary'
    if param in ('InitEventName', 'FirstEventName', 'NextEventName', 'AddEventName'):
        return 'entrance'
    return 'other'


class Flows:
    def __init__(self, game):
        self.game = game
        self.cache = {}

    def raw(self, name):
        if name not in self.cache:
            path = FLOW_DIR + name + FLOW_EXT
            try:
                data = self.game.nup.read(path)
            except NupError:
                self.cache[name] = None
            else:
                self.cache[name] = self.game.codec.decompress(path, data)
        return self.cache[name]


def subflow_calls(raw: bytes, name: str, entry: str) -> list[str]:
    """Subflows ('flow:entry') called by the entry (without following them).

    Their dialogues are only trimmed if that entry is also listed.
    """
    fl = EventFlow(raw)
    events_p = fl._u64(fl._u64(fl._u64(0x28)) + 0x30)  # event table
    out = set()
    for i in reachable(fl.events, fl.entry_points[entry]):
        if fl.events[i].kind == SUBFLOW:
            e = events_p + 0x30 * i
            out.add(f'{fl._str(fl._u64(e + 0x18)) or name}:{fl._str(fl._u64(e + 0x20))}')
    return sorted(out)


def trim_effect(raw: bytes, entry: str, pairs) -> Counter:
    """Actions that disappear from the entry when it is listed alone."""
    new = trim_flow(raw, [entry], pairs)
    if new is None:
        return Counter()
    fo, fn = EventFlow(raw), EventFlow(new)
    before = reachable(fo.events, fo.entry_points[entry])
    after = reachable(fn.events, fn.entry_points[entry])
    return Counter(f'{fo.events[i].actor}.{fo.events[i].action}'
                   for i in before - after if fo.events[i].kind == ACTION)


def find(game, zones=CHILD_ZONES, age='child'):
    rows = load_rows(game)
    policy = load_policy()
    pairs = active_actions(policy)
    flows = Flows(game)
    by_target = defaultdict(set)  # (flow, entry) -> rows
    for rid, r in rows.items():
        if r.get('FlowchartFileName'):
            by_target[(_base(r['FlowchartFileName']), r.get('EntryPointName'))].add(rid)

    cands = {}  # (flow, entry) -> {zones, triggers}

    def add(flow, entry, zone, how):
        c = cands.setdefault((flow, entry), {'zones': set(), 'how': set()})
        c['zones'].add(zone)
        c['how'].add(how)

    forced_rows = set()
    for zone, actor, param, rid in banc_triggers(game, rows, zones, age):
        if classify(param) != 'forced':
            continue
        r = rows[rid]
        forced_rows.add(rid)
        comp = _base(r.get('EventSettingComponentList'))
        add(_base(r.get('FlowchartFileName')), r.get('EntryPointName'), zone,
            f'{actor}.{param}={rid} [{comp}]')
    for rid, zone in ENGINE_ROWS.items():
        if rid in rows and zone in zones:
            r = rows[rid]
            forced_rows.add(rid)
            add(_base(r.get('FlowchartFileName')), r.get('EntryPointName'), zone,
                f'engine={rid} [{_base(r.get("EventSettingComponentList"))}]')
    for zone, npcs in zone_npcs(game, zones, age).items():
        for npc in sorted(npcs):
            raw = flows.raw(npc)
            if raw is None:
                continue
            fl = EventFlow(raw)
            for entry, start in fl.entry_points.items():
                acts = {fl.events[i].action for i in reachable(fl.events, start)
                        if fl.events[i].kind == ACTION}
                if any(a and 'NpcBlocker' in a for a in acts):
                    add(npc, entry, zone, 'blocker AI (EventNpcBlocker*)')

    report = []
    for (flow, entry), c in sorted(cands.items(), key=lambda kv: (sorted(kv[1]['zones']), kv[0])):
        spec = policy['story_flows'].get(flow)
        raw = flows.raw(flow) if entry else None
        if spec == '*':
            status = 'ALREADY*'
        elif isinstance(spec, list) and entry in spec:
            status = 'LISTED'
        elif raw is None or entry not in EventFlow(raw).entry_points:
            status = 'NOFLOW'
        else:
            others = []
            for rid in by_target.get((flow, entry), ()):
                comp = _base(rows[rid].get('EventSettingComponentList'))
                if rid not in forced_rows and comp.startswith(VOLUNTARY_COMPONENTS):
                    others.append(rid)
            status = 'SHARED:' + ','.join(sorted(others)) if others else 'CANDIDATE'
        effect = (trim_effect(raw, entry, pairs) if status in ('CANDIDATE', 'LISTED')
                  else Counter())
        calls = subflow_calls(raw, flow, entry) if status != 'NOFLOW' and raw else []
        report.append({'flow': flow, 'entry': entry, 'zones': sorted(c['zones']),
                       'how': sorted(c['how']), 'status': status,
                       'removed': dict(sorted(effect.items())), 'calls': calls})
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('nup')
    ap.add_argument('--age', choices=sorted(OTHER_AGE), default='child')
    ap.add_argument('--zones', default=None, help='default: the zones of that age')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    default = CHILD_ZONES if args.age == 'child' else ADULT_ZONES
    zones = tuple(z for z in args.zones.split(',') if z) if args.zones else default
    with NupArchive(args.nup) as nup:
        report = find(GameData(nup), zones, args.age)
    if args.json:
        print(json.dumps(report, indent=1, ensure_ascii=False))
        return 0
    for r in report:
        talks = sum(n for k, n in r['removed'].items() if k.endswith('.EventTalk'))
        print(f"{'/'.join(r['zones'])}  {r['flow']}:{r['entry']}  {r['status']}  "
              f"talks-={talks}")
        for h in r['how']:
            print(f'    via {h}')
        if r['removed']:
            print('    removes: ' + ', '.join(f'{k} x{n}' for k, n in r['removed'].items()))
        if r['calls']:
            print('    calls: ' + ', '.join(r['calls']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
