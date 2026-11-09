"""Genera randomizer/data/cutscenes.json (opción "Saltar cinemáticas").

Uso: python tools/build_cutscene_list.py <nup>

Solo lee el .nup. Escribe:
- `intro_component_lists`: introducciones cuyo salto se desbloquea;
- `story_flows`: flujos de historia ("*") por prefijo y, para los flujos de
  PNJ de historia, la lista de entradas candidatas (las que no son charla
  `Talk`/`Near`) menos las descartadas en la revisión manual (REVIEWED_OUT),
  más las conversaciones forzadas curadas (FORCED_TALKS);
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
        'GoToDekuTree', 'GoToMido', 'Talk'],
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
    'Npc_Hylia_Zelda_Child': ['Zelda_CanbeStopped_Impa_01', 'Zelda_CanbeStopped_Impa_02'],
    # Kakariko: avisos de Navi sobre las Skulltulas doradas
    'GatheringTokenGold': ['NaviGuide_GatheringTokenGold', 'NaviGuide_TokenGold_Over10'],
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


def build(nup) -> dict:
    game = GameData(nup)
    names = [p[len(FLOW_DIR):-len(FLOW_EXT)] for p in nup.list(FLOW_DIR)
             if p.endswith(FLOW_EXT)]
    story: dict = {}
    for name in names:
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
