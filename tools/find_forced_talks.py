"""Busca conversaciones forzadas (opción "Saltar cinemáticas", ampliación 1).

Uso: python -I tools/find_forced_talks.py <nup> [--zones Z1,Z2,...]

Solo lee el .nup. Imprime, por zona, los pares (flujo, entrada) candidatos,
cómo se disparan y qué acciones quitaría el recorte de fase 1 si la entrada
se listara sola en `story_flows`. La lista curada vive en
`tools/build_cutscene_list.py` (FORCED_TALKS); esta herramienta no la escribe.

Cómo se dispara un evento (investigado el 2026-11-09):
- Cada evento con nombre es una fila de `RSDB/EventSetting.Product.*.rstbl`:
  `__RowId` -> `FlowchartFileName` + `EntryPointName` + una lista de
  componentes (`EventSettingComponentList`) que dice cómo arranca:
  `NPCTalkNoPause`/`NPCTalk` = el jugador pulsa A ante un PNJ; `NPCNear` =
  burbuja al acercarse (no para al jugador); `FlowchartEvent` y variantes =
  evento lanzado por otro actor; `NaviHintEvent` = pista de Navi.
- Los actores de los bancs (`Banc/<Zona>/*.bcett.byml.zs`) nombran filas en
  sus parámetros `Dynamic`. El parámetro dice quién lo lanza:
  - FORZADO: `RequestEventName` de `EventRequestActor` /
    `EventProxyRequestActor` (activador de zona: salta al pisar un área o al
    cumplirse una condición), `PlayerDiscoveredEventName` (un guardia te ve),
    `JumpSlushTutorialEventName` (tutorial al golpear la roca).
  - VOLUNTARIO: `TalkEventName` (hablar), `CheckEventName*` (abrir una
    puerta), `EventNameFromInstanceParam` (leer un cartel), `DamageEventName`
    (golpear al PNJ), `GetEventName` (cofre).
  - ENTRADA DE ZONA: `InitEventName`/`FirstEventName`/`NextEventName`/
    `AddEventName` (flujos `Dm_*`/`Goto_*`, ya tratados como historia).
- PNJ que cortan el paso: su flujo usa la IA de bloqueo (`EventNpcBlocker*`)
  y el motor lanza su entrada de charla cuando el jugador choca con ellos
  (Mido antes de tener espada y escudo). Se buscan las entradas de los flujos
  `Npc_*` de los actores de las zonas cuyo grafo usa esas acciones.
- Filas que lanza el código del juego (sin referencia en los bancs), p. ej.
  `NaviLockOnHint`/`NaviLockOnHintObject` -> `NaviHint:Hint_00`. Se listan en
  ENGINE_ROWS para revisarlas igual.
- Una entrada que también se usa de forma voluntaria (otra fila no forzada
  apunta a ella) se marca SHARED y no se debe listar.
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


def banc_triggers(game, rows, zones):
    """(zona, actor, parámetro, fila) de los bancs de infancia de las zonas."""
    out = []
    for path in game.nup.list('Banc/'):
        parts = path.split('/')
        if (len(parts) != 3 or parts[1] not in zones or '_Adult' in parts[2]
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


def zone_npcs(game, zones):
    """Zona -> nombres de actor `Npc_*` (sin adultos) de sus bancs."""
    out = defaultdict(set)
    for path in game.nup.list('Banc/'):
        parts = path.split('/')
        if (len(parts) != 3 or parts[1] not in zones or '_Adult' in parts[2]
                or not path.endswith('.bcett.byml.zs')):
            continue
        _ver, root = game.load_banc(path)
        for a in (root.get('Actors') if isinstance(root, dict) else None) or []:
            g = str(a.get('Gyaml', '')) if isinstance(a, dict) else ''
            if g.startswith('Npc_') and not g.endswith('_Adult'):
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
    """Subflujos ('flujo:entrada') que llama la entrada (sin seguirlos).

    Sus diálogos solo se recortan si esa entrada también se lista.
    """
    fl = EventFlow(raw)
    events_p = fl._u64(fl._u64(fl._u64(0x28)) + 0x30)  # tabla de eventos
    out = set()
    for i in reachable(fl.events, fl.entry_points[entry]):
        if fl.events[i].kind == SUBFLOW:
            e = events_p + 0x30 * i
            out.add(f'{fl._str(fl._u64(e + 0x18)) or name}:{fl._str(fl._u64(e + 0x20))}')
    return sorted(out)


def trim_effect(raw: bytes, entry: str, pairs) -> Counter:
    """Acciones que desaparecen de la entrada al listarla sola."""
    new = trim_flow(raw, [entry], pairs)
    if new is None:
        return Counter()
    fo, fn = EventFlow(raw), EventFlow(new)
    before = reachable(fo.events, fo.entry_points[entry])
    after = reachable(fn.events, fn.entry_points[entry])
    return Counter(f'{fo.events[i].actor}.{fo.events[i].action}'
                   for i in before - after if fo.events[i].kind == ACTION)


def find(game, zones=CHILD_ZONES):
    rows = load_rows(game)
    policy = load_policy()
    pairs = active_actions(policy)
    flows = Flows(game)
    by_target = defaultdict(set)  # (flujo, entrada) -> filas
    for rid, r in rows.items():
        if r.get('FlowchartFileName'):
            by_target[(_base(r['FlowchartFileName']), r.get('EntryPointName'))].add(rid)

    cands = {}  # (flujo, entrada) -> {zonas, disparos}

    def add(flow, entry, zone, how):
        c = cands.setdefault((flow, entry), {'zones': set(), 'how': set()})
        c['zones'].add(zone)
        c['how'].add(how)

    forced_rows = set()
    for zone, actor, param, rid in banc_triggers(game, rows, zones):
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
    for zone, npcs in zone_npcs(game, zones).items():
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
    ap.add_argument('--zones', default=','.join(CHILD_ZONES))
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    zones = tuple(z for z in args.zones.split(',') if z)
    with NupArchive(args.nup) as nup:
        report = find(GameData(nup), zones)
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
            print('    quita: ' + ', '.join(f'{k} x{n}' for k, n in r['removed'].items()))
        if r['calls']:
            print('    llama: ' + ', '.join(r['calls']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
