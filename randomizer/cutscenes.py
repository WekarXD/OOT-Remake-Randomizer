"""Opción "Saltar cinemáticas": política de escenas y archivos del mod.

- Desbloquea el salto de las introducciones listadas (quita `SkipSetting`
  de su EventSettingComponentList).
- Recorta de los flujos de historia las acciones que solo muestran (lista
  blanca de la fase activa) reescribiendo en su sitio los índices de evento;
  los archivos no cambian de tamaño.
"""
import json
from pathlib import Path

from .evtrim import compute_trim
from .formats import byml
from .formats.bfevfl import ACTION, END, FORK, SWITCH, EventFlow, patch_pointers

ACTIVE_PHASE = 1
# Carteles y textos del sistema: nunca se quitan (ver la especificación).
PROTECTED_ACTORS = frozenset({'SystemTextNPC', 'SignBoard_EventStarter'})
POLICY_PATH = Path(__file__).resolve().parent / 'data' / 'cutscenes.json'
FLOW_DIR = 'Event/EventFlow/'
FLOW_EXT = '.bfevfl.zs'
COMPONENT_DIR = 'Event/EventSetting/EventSettingComponentList/'
COMPONENT_EXT = '.engine__event__EventSettingComponentList.bgyml'


def load_policy() -> dict:
    with open(POLICY_PATH, encoding='utf-8') as f:
        return json.load(f)


def active_actions(policy: dict, phase: int = ACTIVE_PHASE) -> set[tuple[str, str]]:
    """Pares (actor|'*', acción) de las fases 1..phase."""
    return {tuple(p) for k, pairs in policy['actions'].items()
            if int(k) <= phase for p in pairs}


def _matches(ev, pairs) -> bool:
    return ev.kind == ACTION and ((ev.actor, ev.action) in pairs
                                  or ('*', ev.action) in pairs)


def _successors(events, i: int) -> list[int]:
    ev = events[i]
    out = [ev.next, *ev.cases, *ev.forks, ev.join]
    return [j for j in out if j is not None and j != END and 0 <= j < len(events)]


def on_cycle(events) -> set[int]:
    """Eventos que están en algún ciclo del grafo (Tarjan iterativo).

    Mismas aristas que `reachable`: next, casos, ramas y join.
    """
    index, low, onstack, stack, out = {}, {}, set(), [], set()
    counter = 0
    for root in range(len(events)):
        if root in index:
            continue
        work = [(root, iter(_successors(events, root)))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        onstack.add(root)
        while work:
            v, it = work[-1]
            w = next(it, None)
            if w is not None:
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    onstack.add(w)
                    work.append((w, iter(_successors(events, w))))
                elif w in onstack:
                    low[v] = min(low[v], index[w])
                continue
            work.pop()
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    onstack.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                if len(comp) > 1 or v in _successors(events, v):
                    out.update(comp)
    return out


def reachable(events, start: int) -> set[int]:
    """Eventos alcanzables desde `start` dentro del flujo.

    Sigue next, casos, ramas y join; no entra en las llamadas de subflujo.
    """
    seen, stack = set(), [start]
    while stack:
        i = stack.pop()
        if i is None or i == END or i in seen or not 0 <= i < len(events):
            continue
        seen.add(i)
        ev = events[i]
        stack.append(ev.next)
        stack.extend(ev.cases)
        stack.extend(ev.forks)
        stack.append(ev.join)
    return seen


def removable_events(flow: EventFlow, spec, pairs) -> set[int]:
    """Acciones que se pueden quitar del flujo según su lista de entradas."""
    events = flow.events
    story, other = set(), set()
    for name, start in flow.entry_points.items():
        target = story if spec == '*' or name in spec else other
        target |= reachable(events, start)
    # Nada que esté en un ciclo (p. ej. esperas de un bucle de sondeo
    # switch -> espera -> switch): quitarlo dejaría un bucle sin espera.
    cands = {i for i in story - other - on_cycle(events)
             if _matches(events[i], pairs) and events[i].actor not in PROTECTED_ACTORS}
    joins = _branch_joins(events)
    return {i for i in cands if not is_choice_talk(events, i, pairs, joins)}


def _branch_joins(events) -> dict[int, set[int]]:
    """Evento -> joins a los que sigue el flujo cuando su rama termina.

    Un evento de una rama de fork cuyo `next` (o un caso) es 0xFFFF continúa
    en el join del fork. Las ramas anidadas reciben también los joins de
    fuera (sobreaproximación: solo hace conservar más).
    """
    out: dict[int, set[int]] = {}
    for ev in events:
        if ev.kind != FORK or ev.join is None:
            continue
        seen, stack = set(), list(ev.forks)
        while stack:
            j = stack.pop()
            if j is None or j == END or j == ev.join or j in seen                     or not 0 <= j < len(events):
                continue
            seen.add(j)
            e = events[j]
            if e.next == END or END in e.cases:
                out.setdefault(j, set()).add(ev.join)
            stack.extend(_successors(events, j))
    return out


def _reaches_talk_choice(events, i: int, joins) -> bool:
    """Desde `i`, ¿se llega a un switch TalkChoice sin pasar por otro EventTalk?

    Sigue next, casos, ramas y join, y del final de una rama al join de su fork.
    """
    seen, stack = {i}, [*_successors(events, i), *joins.get(i, ())]
    while stack:
        j = stack.pop()
        if j in seen:
            continue
        seen.add(j)
        e = events[j]
        if e.kind == SWITCH and e.query and 'TalkChoice' in e.query:
            return True
        if e.kind == ACTION and e.action == 'EventTalk':
            continue
        stack.extend(_successors(events, j))
        stack.extend(joins.get(j, ()))
    return False


def is_choice_talk(events, i: int, pairs, joins=None) -> bool:
    """`EventTalk` cuyo resultado lee un switch posterior.

    Dos reglas (basta una):
    - Se sigue `next` saltando las acciones de la lista blanca que no son
      diálogos (p. ej. un cambio de emoción entre la pregunta y el switch),
      se quiten o no en este flujo; si lo primero que queda es un switch, el
      diálogo es una pregunta.
    - Se llega a un switch TalkChoice sin pasar por otro EventTalk, también a
      través de forks y joins (p. ej. pregunta -> fork -> join -> TalkChoice2).
    """
    if events[i].kind != ACTION or events[i].action != 'EventTalk':
        return False
    if joins is None:
        joins = _branch_joins(events)
    if _reaches_talk_choice(events, i, joins):
        return True
    seen = {i}
    j = events[i].next
    while (j is not None and j != END and 0 <= j < len(events) and j not in seen
           and _matches(events[j], pairs) and events[j].action != 'EventTalk'):
        seen.add(j)
        j = events[j].next
    return j is not None and 0 <= j < len(events) and events[j].kind == SWITCH


def trim_flow(data: bytes, spec, pairs) -> bytes | None:
    """Flujo recortado (misma longitud), o None si no cambia."""
    flow = EventFlow(data)
    if not flow.events:
        return None
    roots = {i for i in flow.entry_points.values() if i != END}
    removed, retarget = compute_trim(flow.events, removable_events(flow, spec, pairs),
                                     roots)
    if not removed:
        return None
    new_targets = {off: retarget[idx] for off, idx in flow.pointer_slots()
                   if idx in removed}
    out = patch_pointers(data, new_targets)
    return out if out != data else None


def unlock_skip(raw: bytes) -> bytes | None:
    """Lista de componentes sin `SkipSetting`, o None si no lo tiene."""
    ver, root = byml.load(raw)
    comps = root.get('Components') if isinstance(root, dict) else None
    if not isinstance(comps, dict) or 'SkipSetting' not in comps:
        return None
    del comps['SkipSetting']
    out = byml.dump(root, ver)
    if len(out) > len(raw):
        raise ValueError(f'La lista de componentes crece al quitar SkipSetting '
                         f'({len(raw)} -> {len(out)} bytes).')
    return out


def build_cutscene_files(game) -> dict[str, bytes]:
    """Ruta romfs -> bytes finales (los .zs comprimidos), en orden de ruta."""
    policy = load_policy()
    pairs = active_actions(policy)
    files: dict[str, bytes] = {}
    for name in policy['intro_component_lists']:
        path = COMPONENT_DIR + name + COMPONENT_EXT
        out = unlock_skip(game.nup.read(path))
        if out is not None:
            files[path] = out
    for name, spec in policy['story_flows'].items():
        path = FLOW_DIR + name + FLOW_EXT
        raw = game.codec.decompress(path, game.nup.read(path))
        out = trim_flow(raw, spec, pairs)
        if out is not None:
            files[path] = game.codec.compress(path, out)
    return {p: files[p] for p in sorted(files)}
