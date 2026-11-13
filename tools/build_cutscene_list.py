"""Generates randomizer/data/cutscenes.json (the "Skip cutscenes" option).

Usage: python tools/build_cutscene_list.py <nup>

Only reads the .nup. Writes:
- `intro_component_lists`: intros whose skipping is unlocked;
- `story_flows`: story flows ("*") by prefix and, for the story NPC
  flows, the list of candidate entries (those that are not chatter
  `Talk`/`Near`) minus those discarded in the manual review (REVIEWED_OUT),
  plus the curated forced conversations (FORCED_TALKS); finally, the
  conversations that are never trimmed (KEEP_TALKS: gameplay hints) are
  removed from the list and a "*" flow with any of them becomes the list of its
  other entries;
- `actions`: allowlist of actions per phase.

Prints the candidate NPC entries with their actions for review.
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
# DmF_: cucco/fall/game over. Credits and title: out of scope.
# Dm_SY_: system flows (receiving items, chests, bottles, ocarina,
# zone changes), not story scenes.
EXCLUDED_PREFIXES = ('DmF_', 'Dm_StaffCredit_', 'Dm_Title_', 'Dm_SY_')
NPC_RE = re.compile(r'Npc_(Hylia_Zelda_|Hylia_Impa_|Kokiri_Saria_|Goron_Darunia_|'
                    r'Zora_Ruto_|Gerudo_Nabooru_|Hylia_Rauru|Hylia_Sheik_)')
CHATTER_RE = re.compile(r'(^|_)(Talk|Near)\d*$')

# Round 2b (2026-11-09): frozen-Link: join waits on animations. Scenes whose
# join waits on animations that are not removed (phase 2): if trimmed, Link
# stands still until they finish. They are not trimmed. Dm_HrlCastle_0020.110 is the
# variant of Dm_HrlCastle_0020.
FROZEN_LINK = frozenset({
    'Dm_Kokiri_0060', 'Dm_Kokiri_0130', 'Dm_Kokiri_0145', 'Dm_Kokiri_0155',
    'Dm_Deku_0003', 'Dm_HrlField_0020', 'Dm_HrlCastle_0000', 'Dm_HrlCastle_0020',
    'Dm_HrlCastle_0020.110', 'Dm_HrlCastle_0035', 'Dm_HrlCastle_0050',
    'Dm_LonLon_0020', 'Dm_Kakariko_0010'})

# Manual review (2026-11-09): candidate entries that are normal or
# repeatable chatter (random topics, choices, masks, auxiliary cameras,
# Impa notices). When in doubt they are left out: better to see a scene than to get stuck.
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

# Extension 1 (2026-11-09): forced childhood conversations, reviewed
# by hand from tools/find_forced_talks.py (see its docstring for the
# criterion). They are added to `story_flows` even if the entry is in REVIEWED_OUT.
# Left out (and why) in the task 6 report: Navi (Hint_00 shared with
# the voluntary hint and without dialogue in the flow), bubbles on approach,
# shops, minigames and the actions tutorial of Npc_Kokiri_006 (optional).
FORCED_TALKS = {
    # Kokiri Forest
    'Npc_Kokiri_Mido_Child': [            # blocks the way (blocking AI)
        'KokiriForest_Get_StoneOfForest_Completed_Event',  # zone trigger
        'Talk'],
    'Npc_Kokiri_007_Child': [             # blocks the exit (blocking AI)
        'GoToDekuTree', 'GoToMido', 'Talk',
        # Round 2: reaction on approaching the exit (bubble). It is launched by a
        # zone trigger (EventRequestActor.RequestEventName in
        # KokiriForest_Child_Static, SubEvent row). It is a single bubble that
        # ends in "end", so the end-pointer rule keeps it.
        'Near_FirstReaction',
        # Round 4: after the Deku Tree it stops Link, talks and steps aside
        # (InitTalk_Blocker + EventNpcBlockerEndBlockerAI).
        'Get_StoneOfForest_IsCompleted_Exp_Talk'],
    'Npc_Kokiri_010_Child': [             # target-locking tutorial
        'FocusOnAttentionRock_ShieldDeku', 'FocusOnAttentionRock_ShieldDeku_Short'],
    'Npc_Kokiri_011_Child': [             # stops you in front of the shop
        'KokiriForest_Kokiri_011_StopInFrontOfShop_00'],
    # Kokiri Forest and Hyrule Field: Navi's notice about soft soil
    'Field_PlantMagicBean': ['CheckSoil', 'CheckSoil_01', 'CheckSoil_ZoraRiver'],
    # Market, Castle and Kakariko: guards who stop you (CanbeStopped)
    'NpcCommon': ['Sub_CanbeStopped_Npc_01', 'Sub_CanbeStopped_Npc_02'],
    # Market: the house owner on entering
    'Npc_Hylia_052_Child': ['isPlayerInHouse'],
    # Castle: the guards catch you; the guard who shoots; Impa stops you
    'HyruleCastle_FoundBySecurity': [
        'FoundBySecurity', 'FoundBySecurity_Common', 'FoundBySecurity_Common_Courtyard',
        'FoundBySecurity_Common_IsFirst', 'FoundBySecurity_Courtyard',
        'Soldier_RandomTalk', 'Soldier_RandomTalk_IsAfterSecond'],
    'Npc_Hylia_ImperialSoldier_001_Child': ['Retaliation'],
    # Extension 1b (requested by the user): the chat with Zelda in the garden.
    # It is not forced: the player presses A (row Npc_Hylia_Zelda_Child_DC1C2_TTT,
    # NPCTalkNoPause -> Talk), but the user wants it out because it is
    # story. The forced garden scene (Goto_HyruleCastle_MeetZelda ->
    # Dm_HrlCastle_0035/_0050) is already "*". Talk and the entries it
    # calls are listed; the mask ones (Mask_*) stay. Questions with
    # choices and topic-menu loops are kept by the rules.
    'Npc_Hylia_Zelda_Child': [
        'Zelda_CanbeStopped_Impa_01', 'Zelda_CanbeStopped_Impa_02',
        'Talk', 'Intro', 'aboutGeneral', 'ThatsAll', 'AboutFireStone',
        'AboutWaterStone', 'InterestTalk_Zelda_Child',
        'InterestTalk_Zelda_Child_ChangeTheTopic'],
    # Kakariko: Navi's notices about the Gold Skulltulas
    'GatheringTokenGold': ['NaviGuide_GatheringTokenGold', 'NaviGuide_TokenGold_Over10'],
    # Adult (2026-11-13, find_forced_talks.py --age adult): adult Mido blocks the
    # Sacred Forest Meadow; the carpenter before Gerudo Fortress; the Gerudo before the
    # Haunted Wasteland (Navi after the Water Temple level change is in SageOfWater, "*").
    'Npc_Kokiri_Mido_Adult': [
        'SageOfForest_Blocker_Talk', 'SageOfForest_Blocker_Talk_Common',
        'SageOfForest_Blocker_Talk_OcarinaPlaying'],
    'Npc_Hylia_012_Adult': ['GerudoValley_StopInFrontOfGerudoFortress'],
    'Npc_Gerudo_006': ['GerudoFortress_StopInFrontOfHountedWasteland'],
}

# Round 2 (2026-11-09): conversations that are never trimmed even if they are in
# a "*" flow. Mostly gameplay hints (user request: the Deku Scrub in the
# Deku Tree who gives the order clue lost the chat). When in doubt they are
# kept. The "*" flow becomes the list of all its entries minus these
# and minus the entries of story flows that they call as a subflow
# (chained); `removable_events` already protects everything reached from an
# unlisted entry. Reasons in the round 2 report.
KEEP_TALKS = {
    # Deku Scrubs in the Deku Tree (order clue 2-3-1) and their versions when
    # hit (TalkEventName / DamageEventName of Enemy_Scrub_Deku*).
    'Get_StoneOfForest': [
        'Talk_Deku_01', 'Talk_Deku_02', 'Talk_Deku_03',
        'Talk_Deku_01_Attacked', 'Talk_Deku_02_Attacked', 'Talk_Deku_03_Attacked'],
    # Navi at Darunia's door (hint: play music); the player
    # shows masks to Darunia (voluntary, like Zelda's Mask_*).
    'Get_StoneOfFire': ['Check_DaruniaDoor', 'Mask_Darunia_Message'],
    # Reading the stones altar (EventNameFromInstanceParam).
    'DoorOfTime': ['Check_SpiritStoneBase'],
    # Navi hints in dungeons and areas (puzzles, heat).
    'Get_StoneOfWater': ['StoneOfWater_ElevatedFloor_NaviTalk'],
    'SageOfFire': ['SageOfFire_NaviScorching', 'SageOfFire_NaviCraterTalk'],
    'SageOfWater': ['WaterTemple_WaterLevelChange_Navi'],
    'SageOfSpirit_RescueCarpenter': ['Windowhint_1', 'Windowhint_4'],
    # Deku Scrub target minigame (Lost Woods): minigames are kept.
    'Dm_LostWood_0040': ['C01', 'Dm_LostWood_0040_SecondTure',
                         'Dm_LostWood_0040_SecondFalse', 'HitTargetOfDekuScrub_WalletFull'],
    # Showing masks (voluntary).
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
    """Removes from `story` the KEEP_TALKS entries and their story subflows."""
    keep: dict[str, set] = {}
    todo = []
    for name, entries in KEEP_TALKS.items():
        if name not in story:
            raise ValueError(f'{name}: not a story flow')
        _raw, flow = _flow(game, nup, name)
        missing = set(entries) - set(flow.entry_points)
        if missing:
            raise ValueError(f'{name}: nonexistent entries {sorted(missing)}')
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
            raise ValueError(f'{name}: nonexistent entries {sorted(missing)}')
        if story.get(name) == '*':
            raise ValueError(f'{name}: already a complete story flow')
        story[name] = sorted(set(story.get(name, [])) | set(entries))
    missing = FROZEN_LINK - set(names)
    if missing:
        raise ValueError(f'FROZEN_LINK: nonexistent flows {sorted(missing)}')
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
    print(f'{POLICY_PATH}: {len(policy["story_flows"])} flows ({n_star} complete)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
