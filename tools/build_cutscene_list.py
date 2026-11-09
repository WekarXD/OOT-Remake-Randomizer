"""Genera randomizer/data/cutscenes.json (opción "Saltar cinemáticas").

Uso: python tools/build_cutscene_list.py <nup>

Solo lee el .nup. Escribe:
- `intro_component_lists`: introducciones cuyo salto se desbloquea;
- `story_flows`: flujos de historia ("*") por prefijo y, para los flujos de
  PNJ de historia, la lista de entradas candidatas (las que no son charla
  `Talk`/`Near`) menos las descartadas en la revisión manual (REVIEWED_OUT),
  más las conversaciones forzadas curadas (FORCED_TALKS); al final, las
  conversaciones que nunca se recortan (KEEP_TALKS: pistas de juego) salen
  de la lista y un flujo "*" con alguna de ellas pasa a ser la lista de sus
  demás entradas;
- `actions`: lista blanca de acciones por fase.

Imprime las entradas candidatas de los PNJ con sus acciones para revisarlas.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer.cutscenes import FLOW_DIR, FLOW_EXT, POLICY_PATH, reachable  # noqa: E402
from randomizer.formats.bfevfl import ACTION, SWITCH, EventFlow  # noqa: E402
from randomizer.game import GameData  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from tools.find_forced_talks import subflow_calls  # noqa: E402

STORY_PREFIXES = ('Dm_', 'Get_Stone', 'SageOf', 'AllSage', 'Meet_', 'Goto_',
                  'MelodyGet_', 'SubEvent_Get', 'Get_Epona', 'DoorOfTime',
                  'OpeningEvent', 'Defeat_Ganon', 'EscapeFromCrumblingGanonCastle')
# DmF_: cucco/caída/game over. Créditos y título: fuera de alcance.
# Dm_SY_: flujos del sistema (recibir objeto, cofres, botellas, ocarina,
# cambios de zona), no escenas de historia.
EXCLUDED_PREFIXES = ('DmF_', 'Dm_StaffCredit_', 'Dm_Title_', 'Dm_SY_')
NPC_RE = re.compile(r'Npc_(Hylia_Zelda_|Hylia_Impa_|Kokiri_Saria_|Goron_Darunia_|'
                    r'Zora_Ruto_|Gerudo_Nabooru_|Hylia_Rauru|Hylia_Sheik_)')
CHATTER_RE = re.compile(r'(^|_)(Talk|Near)\d*$')

# Ronda 2b (2026-11-09): frozen-Link: join waits on animations. Escenas cuyo
# join espera a animaciones que no se quitan (fase 2): recortadas, Link se
# queda quieto hasta que acaban. No se recortan. Dm_HrlCastle_0020.110 es la
# variante de Dm_HrlCastle_0020.
FROZEN_LINK = frozenset({
    'Dm_Kokiri_0060', 'Dm_Kokiri_0130', 'Dm_Kokiri_0145', 'Dm_Kokiri_0155',
    'Dm_Deku_0003', 'Dm_HrlField_0020', 'Dm_HrlCastle_0000', 'Dm_HrlCastle_0020',
    'Dm_HrlCastle_0020.110', 'Dm_HrlCastle_0035', 'Dm_HrlCastle_0050',
    'Dm_LonLon_0020', 'Dm_Kakariko_0010'})

# Revisión manual (2026-11-09): entradas candidatas que son charla normal o
# repetible (temas al azar, elecciones, máscaras, cámaras auxiliares, avisos
# de Impa). Ante la duda se dejan fuera: mejor ver una escena que bloquearse.
REVIEWED_OUT = {
    'Npc_Hylia_Zelda_Child': {
        'AboutFireStone', 'AboutWaterStone', 'InterestTalk_Zelda_Child',
        'InterestTalk_Zelda_Child_ChangeTheTopic', 'Intro', 'Mask_All',
        'Sub_CanbeStopped_Impa_Camera', 'ThatsAll', 'aboutGeneral'},
    'Npc_Hylia_Zelda_Adult': {'Mask_All'},
    'Npc_Goron_Darunia_Child': {'Mask_All'},
    'Npc_Hylia_Sheik_Adult': {'Mask_Talk_NoTopic', 'Talk_AfterKakariko'},
    'Npc_Kokiri_Saria_Child': {
        'CameraPan', 'Camera_for_Shop', 'CommonFlowOfSwordAndShield',
        'GuideToDekuTree', 'GuideToDekuTree_BeforeTalkMido',
        'InitTalk_Saria_OcarinaPlaying', 'KokiriForest_StopInFrontOfLinkHouse',
        'Mask_All', 'Pardon'},
    'Npc_Kokiri_Saria_Child_SacredForestMeadow': {
        'InitTalk_Saria_OcarinaPlaying_SacredForestMeadow', 'Mask_All',
        'PlayOcarina_InBack', 'PlayOcarina_InFront',
        'StartTalking_DuringPlayerTurn_ForSaria'},
}

# Ampliación 1 (2026-11-09): conversaciones forzadas de la infancia, revisadas
# a mano a partir de tools/find_forced_talks.py (ver su docstring para el
# criterio). Se suman a `story_flows` aunque la entrada esté en REVIEWED_OUT.
# Fuera (y por qué) en el informe de la tarea 6: Navi (Hint_00 compartida con
# la pista voluntaria y sin diálogo en el flujo), burbujas al acercarse,
# tiendas, minijuegos y el tutorial de acciones de Npc_Kokiri_006 (opcional).
FORCED_TALKS = {
    # Bosque Kokiri
    'Npc_Kokiri_Mido_Child': [            # corta el paso (IA de bloqueo)
        'KokiriForest_Get_StoneOfForest_Completed_Event',  # activador de zona
        'Talk'],
    'Npc_Kokiri_007_Child': [             # corta la salida (IA de bloqueo)
        'GoToDekuTree', 'GoToMido', 'Talk',
        # Ronda 2: reacción al acercarse a la salida (globo). La lanza un
        # activador de zona (EventRequestActor.RequestEventName en
        # KokiriForest_Child_Static, fila SubEvent). Es un solo globo que
        # acaba en "fin", así que la regla de punteros a fin lo conserva.
        'Near_FirstReaction'],
    'Npc_Kokiri_010_Child': [             # tutorial de fijar el blanco
        'FocusOnAttentionRock_ShieldDeku', 'FocusOnAttentionRock_ShieldDeku_Short'],
    'Npc_Kokiri_011_Child': [             # te para delante de la tienda
        'KokiriForest_Kokiri_011_StopInFrontOfShop_00'],
    # Bosque Kokiri y Campo de Hyrule: aviso de Navi sobre la tierra blanda
    'Field_PlantMagicBean': ['CheckSoil', 'CheckSoil_01'],
    # Mercado, Castillo y Kakariko: guardias que te paran (CanbeStopped)
    'NpcCommon': ['Sub_CanbeStopped_Npc_01', 'Sub_CanbeStopped_Npc_02'],
    # Mercado: la dueña de la casa al entrar
    'Npc_Hylia_052_Child': ['isPlayerInHouse'],
    # Castillo: te pillan los guardias; el guardia que dispara; Impa te para
    'HyruleCastle_FoundBySecurity': [
        'FoundBySecurity', 'FoundBySecurity_Common', 'FoundBySecurity_Common_Courtyard',
        'FoundBySecurity_Common_IsFirst', 'FoundBySecurity_Courtyard',
        'Soldier_RandomTalk', 'Soldier_RandomTalk_IsAfterSecond'],
    'Npc_Hylia_ImperialSoldier_001_Child': ['Retaliation'],
    # Ampliación 1b (pedida por el usuario): la charla con Zelda en el jardín.
    # No es forzada: el jugador pulsa A (fila Npc_Hylia_Zelda_Child_DC1C2_TTT,
    # NPCTalkNoPause -> Talk), pero el usuario la quiere fuera por ser
    # historia. La escena forzada del jardín (Goto_HyruleCastle_MeetZelda ->
    # Dm_HrlCastle_0035/_0050) ya es "*". Se listan Talk y las entradas a las
    # que llama; las de máscaras (Mask_*) se quedan. Las preguntas con
    # elección y los bucles del menú de temas se conservan por las reglas.
    'Npc_Hylia_Zelda_Child': [
        'Zelda_CanbeStopped_Impa_01', 'Zelda_CanbeStopped_Impa_02',
        'Talk', 'Intro', 'aboutGeneral', 'ThatsAll', 'AboutFireStone',
        'AboutWaterStone', 'InterestTalk_Zelda_Child',
        'InterestTalk_Zelda_Child_ChangeTheTopic'],
    # Kakariko: avisos de Navi sobre las Skulltulas doradas
    'GatheringTokenGold': ['NaviGuide_GatheringTokenGold', 'NaviGuide_TokenGold_Over10'],
}

# Ronda 2 (2026-11-09): conversaciones que nunca se recortan aunque estén en
# un flujo "*". Sobre todo pistas de juego (pedido del usuario: el Deku del
# Árbol Deku que da la clave del orden perdía la charla). Ante la duda se
# dejan. El flujo "*" pasa a ser la lista de todas sus entradas menos estas
# y menos las entradas de flujos de historia a las que llaman como subflujo
# (en cadena); `removable_events` ya protege todo lo que se alcanza desde una
# entrada no listada. Motivos en el informe de la ronda 2.
KEEP_TALKS = {
    # Dekus del Árbol Deku (clave del orden 2-3-1) y sus versiones al
    # golpearlos (TalkEventName / DamageEventName de Enemy_Scrub_Deku*).
    'Get_StoneOfForest': [
        'Talk_Deku_01', 'Talk_Deku_02', 'Talk_Deku_03',
        'Talk_Deku_01_Attacked', 'Talk_Deku_02_Attacked', 'Talk_Deku_03_Attacked'],
    # Navi ante la puerta de Darunia (pista: tocar música); el jugador
    # enseña máscaras a Darunia (voluntario, como Mask_* de Zelda).
    'Get_StoneOfFire': ['Check_DaruniaDoor', 'Mask_Darunia_Message'],
    # Leer el altar de las piedras (EventNameFromInstanceParam).
    'DoorOfTime': ['Check_SpiritStoneBase'],
    # Pistas de Navi en mazmorras y zonas (puzles, calor).
    'Get_StoneOfWater': ['StoneOfWater_ElevatedFloor_NaviTalk'],
    'SageOfFire': ['SageOfFire_NaviScorching', 'SageOfFire_NaviCraterTalk'],
    'SageOfWater': ['WaterTemple_WaterLevelChange_Navi'],
    'SageOfSpirit_RescueCarpenter': ['Windowhint_1', 'Windowhint_4'],
    # Minijuego del Deku de las dianas (Bosque Perdido): los minijuegos se quedan.
    'Dm_LostWood_0040': ['C01', 'Dm_LostWood_0040_SecondTure',
                         'Dm_LostWood_0040_SecondFalse', 'HitTargetOfDekuScrub_WalletFull'],
    # Enseñar máscaras (voluntario).
    'Get_Epona': ['Mask_All'],
    'SubEvent_GetEponaSong': ['Mask_All'],
}

ACTIONS = {
    '1': [
        ['*', 'EventTalk'],
        ['*', 'EventTriggerBalloonMessage'],
        ['Npc_Navi', 'EventNaviRequestBallonMessage'],
        ['EventSystemActor', 'EventWait'],
        ['EventCamera', 'EventMoveToTargetPosCamera'],
        ['EventCamera', 'EventMoveCameraAnimationInstructionsForFlowchart'],
        ['EventCamera', 'EventBasedOnLookAtCamera'],
        ['EventCamera', 'EventTriggerRequestCameraShake'],
        ['EventCamera', 'EventSendEventTalkMessageToPlayerCamera'],
        ['Player_Event', 'EventPlayerTurnAndLook'],
        ['Player_Event', 'EventTriggerPlayerLookAtObject'],
        ['*', 'EventNPCTurnToTarget'],
        ['*', 'EventTriggerLookAtObject'],
        ['Npc_Navi', 'EventNaviLookAtObject'],
        ['PostProcessingActor', 'EventSetAdvancedDoFForFlowchart'],
        ['PostProcessingActor', 'EventSetDoFForFlowchart'],
        ['PostProcessingActor', 'EventNorifyCutChangeForGraphics'],
        ['PostProcessingActor', 'EventEditLocationalLight'],
        ['GameSystemActor', 'EventTriggerControllerRumble'],
        ['DevelopEventSystemActor', 'EventDemoProductSupportComment'],
        ['*', 'EventTriggerChangeEmotion'],
        ['GameSystemActor', 'EventWaitTalkCameraInterpolationEnd'],
    ],
    '2': [
        ['*', 'EventPlayAS'],
        ['Player_Event', 'EventPlayerPlayASForFlowchart'],
        ['Player_Event', 'EventPlayerMove'],
        ['Player_Event', 'EventPlayerMoveToAnchor'],
        ['SoundSystemActor', 'EventSoundStartSound'],
        ['SoundSystemActor', 'EventTriggerSoundReadRiddle'],
        ['Npc_Navi', 'EventNaviMoveAroundToPlayer'],
        ['Npc_Navi', 'EventNaviMoveAtPos'],
    ],
}


def _describe(flow, start):
    out = []
    for i in sorted(reachable(flow.events, start)):
        ev = flow.events[i]
        if ev.kind == ACTION:
            out.append(f'{ev.actor}.{ev.action}')
        elif ev.kind == SWITCH:
            out.append(f'?{ev.actor}.{ev.query}')
    return ' | '.join(out)


def _flow(game, nup, name):
    path = FLOW_DIR + name + FLOW_EXT
    raw = game.codec.decompress(path, nup.read(path))
    return raw, EventFlow(raw)


def _apply_keep_talks(game, nup, story):
    """Quita de `story` las entradas de KEEP_TALKS y sus subflujos de historia."""
    keep: dict[str, set] = {}
    todo = []
    for name, entries in KEEP_TALKS.items():
        if name not in story:
            raise ValueError(f'{name}: no es un flujo de historia')
        _raw, flow = _flow(game, nup, name)
        missing = set(entries) - set(flow.entry_points)
        if missing:
            raise ValueError(f'{name}: entradas inexistentes {sorted(missing)}')
        todo += [(name, e) for e in entries]
    while todo:
        name, entry = todo.pop()
        if entry in keep.get(name, ()):
            continue
        keep.setdefault(name, set()).add(entry)
        raw, _flow_ = _flow(game, nup, name)
        for call in subflow_calls(raw, name, entry):
            sub, sub_entry = call.split(':', 1)
            if sub in story and sub_entry in _flow(game, nup, sub)[1].entry_points:
                todo.append((sub, sub_entry))
    for name, entries in sorted(keep.items()):
        spec = story[name]
        allowed = _flow(game, nup, name)[1].entry_points if spec == '*' else spec
        rest = sorted(e for e in allowed if e not in entries)
        print(f'KEEP {name}: {", ".join(sorted(entries))}')
        if rest:
            story[name] = rest
        else:
            del story[name]


def build(nup) -> dict:
    game = GameData(nup)
    names = [p[len(FLOW_DIR):-len(FLOW_EXT)] for p in nup.list(FLOW_DIR)
             if p.endswith(FLOW_EXT)]
    story: dict = {}
    for name in names:
        if name in FROZEN_LINK:
            continue
        if name.startswith(STORY_PREFIXES) and not name.startswith(EXCLUDED_PREFIXES):
            story[name] = '*'
        elif NPC_RE.match(name):
            path = FLOW_DIR + name + FLOW_EXT
            flow = EventFlow(game.codec.decompress(path, nup.read(path)))
            cands = sorted(e for e in flow.entry_points if not CHATTER_RE.search(e))
            out = REVIEWED_OUT.get(name, set())
            for e in cands:
                mark = 'OUT ' if e in out else 'KEEP'
                print(f'{mark} {name}:{e}: {_describe(flow, flow.entry_points[e])[:300]}')
            keep = [e for e in cands if e not in out]
            if keep:
                story[name] = keep
    for name, entries in FORCED_TALKS.items():
        path = FLOW_DIR + name + FLOW_EXT
        flow = EventFlow(game.codec.decompress(path, nup.read(path)))
        missing = set(entries) - set(flow.entry_points)
        if missing:
            raise ValueError(f'{name}: entradas inexistentes {sorted(missing)}')
        if story.get(name) == '*':
            raise ValueError(f'{name}: ya es un flujo de historia completo')
        story[name] = sorted(set(story.get(name, [])) | set(entries))
    missing = FROZEN_LINK - set(names)
    if missing:
        raise ValueError(f'FROZEN_LINK: flujos inexistentes {sorted(missing)}')
    _apply_keep_talks(game, nup, story)
    return {
        'intro_component_lists': ['Dm_Kokiri_0000'],
        'story_flows': dict(sorted(story.items())),
        'actions': ACTIONS,
    }


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with NupArchive(argv[1]) as nup:
        policy = build(nup)
    with open(POLICY_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(policy, f, indent=1, ensure_ascii=False)
        f.write('\n')
    n_star = sum(1 for v in policy['story_flows'].values() if v == '*')
    print(f'{POLICY_PATH}: {len(policy["story_flows"])} flujos ({n_star} completos)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
