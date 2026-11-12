"""Generates randomizer/data/full_skip.json (the full cutscene skip, childhood = phase 1).

Usage: python -I tools/build_full_skip_list.py <nup> [--dry-run]

Only reads the .nup. Targets (all phase 1):
- `flows`: every `Dm_*` event flow whose bytes mention `_Child`/`_child` and not
  `_Adult`/`_adult` (entry `EntryPoint0`); the entries `cutscenes.json` lists for the
  childhood story flows (CUTSCENE_FLOWS); the childhood entries of `DoorOfTime`; the
  hand-kept CHILD_EXTRA scenes (neither or both ages); the NPC gifts and songs of
  GIFT_TALKS; minus KEEP_TALKS and REVIEWED_OUT; minus entries whose rewrite keeps
  nothing (they would start at 0xFFFF) and entries whose rewrite, applied as the builder
  does, would change what a KEEP_TALKS entry reaches (`keep_talks_guard`).
- `timelines`: timeline-only `Dm_*` files with the same age rule and CHILD_EXTRA, except
  `_Effect`/`_Env` (shortened with their parent) and the movies.
- `movies`: MOVIES plus every `Dm_MelodyGet_Sun_*` in `Event/Movie/`, each with the flows
  that start it (`EventTransition` to its name).

`choices` and `reviewed_forks` are hand-edited in the JSON; regenerating keeps them.
Prints a review table: per target its method, the `effects_only` result, the entries
of its flow called from other files and its fork dependencies; the neither/both scenes
of the childhood zones with the CHILD_EXTRA decision; the kept effects of GIFT_TALKS.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer.cutscenes import FLOW_DIR, FLOW_EXT, load_policy  # noqa: E402
from randomizer.flow_callers import entry_callers  # noqa: E402
from randomizer.formats.bfevfl import ACTION, SUBFLOW, SUBFLOW_SWITCH, SWITCH, EventFlow  # noqa: E402
from randomizer.formats.zs import ZsCodec  # noqa: E402
from randomizer.full_skip import (TARGETS_PATH, new_end_cases, protected_entries,  # noqa: E402
                                  skip_flow)
from randomizer.movie_skip import TRANSITION  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402
from randomizer.skipflow import SkipTable, effects_only, fork_dependencies, reachable  # noqa: E402
from tools.build_cutscene_list import KEEP_TALKS  # noqa: E402

PHASE = 1
# System flows, credits and title: not story scenes (as in build_cutscene_list).
EXCLUDED_PREFIXES = ('Dm_SY_', 'Dm_StaffCredit_', 'Dm_Title_')
SUBTIMELINE_SUFFIXES = ('_Effect', '_Env')
# Childhood story flows whose cutscenes.json entries are targeted.
CUTSCENE_FLOWS = (
    'OpeningEvent', 'Meet_DekuTree', 'Get_StoneOfForest', 'Goto_HyruleCastle',
    'Get_StoneOfFire', 'Get_StoneOfWater', 'SubEvent_GetEponaSong',
    'HyruleCastle_FoundBySecurity', 'MelodyGet_Sun_SubEvent', 'Npc_Hylia_Zelda_Child',
    'Npc_Kokiri_007_Child', 'Npc_Kokiri_010_Child', 'Npc_Kokiri_011_Child',
    'Npc_Kokiri_Mido_Child', 'Npc_Hylia_052_Child', 'Npc_Hylia_ImperialSoldier_001_Child')
DOOR_OF_TIME_CHILD = (
    'Step01_Npc_Hylia_Impa_Child_Talk', 'Dm_MelodyGet_Zelda_After_Npc_Hylia_Impa_Child_Talk',
    'DoorOfTime_GetOcarinaOfTime', 'DoorOfTime_GetOcarinaOfTime_AreaOut',
    'Dm_MelodyGet_Time_After')
MOVIES = ('Dm_Kokiri_0000', 'Dm_Kokiri_0095', 'Dm_HrlCastle_0045')
MOVIE_PATTERN = 'Dm_MelodyGet_Sun_'
# Zones (second part of the name) of the childhood, as in the spec's rollout §6.
CHILD_ZONES = frozenset({
    'Kokiri', 'Deku', 'HrlField', 'HrlCastle', 'Market', 'LonLon', 'Kakariko',
    'DeathMtTrail', 'DeathMtCrater', 'Goron', 'DodongoCave', 'Zora', 'ZoraRiver',
    'ZoraFountain', 'InsideJabu', 'MelodyGet'})

# Dm_* scenes of the childhood zones that mention neither age or both (review 2026-11-12,
# from the table this tool prints; who starts each scene decides its age). When unsure:
# left out (a scene that still plays is better than a wrong skip). Reasons in
# NOT_CHILD_EXTRA and the task 7 report.
CHILD_EXTRA: dict[str, str] = {
    'Dm_DeathMtTrail_0027': 'leaving Dodongo\'s Cavern (Get_StoneOfFire_Complete)',
    'Dm_DodongoCave_0000': 'entering Dodongo\'s Cavern (location name)',
    'Dm_DodongoCave_0020': 'Dodongo skull eyes lit (Get_StoneOfFire_EmitLight)',
    'Dm_DodongoCave_0030': 'escaping Dodongo\'s Cavern after the boss (Get_StoneOfFire_EscapeDungeon)',
    'Dm_HrlCastle_0000': 'first arrival at the castle with Kaepora and Talon\'s wagon (childhood only)',
    'Dm_HrlField_0000': 'first step into Hyrule Field (Goto_HyruleCastle_Kaepora_00)',
    'Dm_HrlField_0010': 'Kaepora in Hyrule Field (Goto_HyruleCastle_Kaepora_00)',
    'Dm_Kakariko_0000': 'arrival at Kakariko (location name)',
    'Dm_Kakariko_0010': 'the guard opens the Death Mountain gate after Zelda\'s Letter',
    'Dm_Kakariko_0060': 'the guard closes the gate (SubEvent_MaskSalesman, childhood)',
    'Dm_MelodyGet_Epona': 'Epona\'s Song from Malon (child song)',
    'Dm_MelodyGet_Sun': 'Royal Family Tomb wall, Sun\'s Song (child song)',
    'Dm_MelodyGet_Sun_03': 'Sun\'s Song granted (GetPouchContent) after the tomb wall',
    'Dm_FairyFountain_Din': 'Great Fairy gives Din\'s Fire (childhood spell)',
    'Dm_FairyFountain_Frore': 'Great Fairy gives Farore\'s Wind (childhood spell)',
    'Dm_HrlField_0030': 'Kaepora Gaebora (the owl only meets child Link)',
    'Dm_HrlField_0040': 'Kaepora Gaebora (the owl only meets child Link)',
    'Dm_HrlField_0050': 'Kaepora Gaebora with the scarecrows (the owl only meets child Link)',
    'Dm_LostWood_0010': 'Kaepora Gaebora in the Lost Woods (the owl only meets child Link)',
    'Dm_Zora_0000': 'arrival at Zora\'s Domain (location name)',
}
# Reviewed and left out, with the reason (printed in the table).
NOT_CHILD_EXTRA: dict[str, str] = {
    'Dm_DeathMtCrater_0000': 'no EntryPoint0; crater entrance reached at both ages',
    'Dm_DeathMtTrail_0000': 'arrival at Death Mountain Trail; age switch inside (both ages)',
    'Dm_DeathMtTrail_0005': 'no flow starts it; nature unknown (falling rocks?)',
    'Dm_Goron_0045': 'Goron City spinning pot prize (minigame)',
    'Dm_ZoraFountain_0000': ('arrival at Zora\'s Fountain: the rewrite serialised its fork so '
                             'Link walked on a black screen (childhood test, 2026-11-12)'),
    'Dm_Kakariko_0040': 'flashback timeline with Sheik (KakarikoVillage_FlashbackScenes, adult)',
    'Dm_Kokiri_0162': 'after the Forest Temple (ForestTemple_SageOfForest_..., adult)',
    'Dm_Zora_0020': 'diving minigame (MiniGame_Diving)',
}

# NPC gifts and songs in conversations the player starts (spec §4.3): flow -> entries.
# Some are already targets through cutscenes.json; listing them here documents the gift.
GIFT_TALKS: dict[str, list[str]] = {
    # Malon gives the Weird Egg (SUB Dm_SY_GetInEvent ActorName Item_WeirdEgg).
    'Goto_HyruleCastle': ['Goto_HyruleCastle_AfterMalonAppear'],
    # Epona's Song: starts Dm_MelodyGet_Epona.
    'SubEvent_GetEponaSong': ['GetEponaSong_MelodyGet_Epona'],
    # Saria's Song in the Sacred Forest Meadow: starts Dm_MelodyGet_Saria.
    'SacredForestMeadow': ['SacredForestMeadow_Field_MelodyGet_Saria'],
    # The Sun's Song: reading the Royal Family Tomb wall starts Dm_MelodyGet_Sun(_03).
    'GimmickFlow_RoyalFamilyTomb': ['CheckStone_To_MelodyGet_Sun'],
    # Zelda's Lullaby after the letter: Impa starts Dm_MelodyGet_Zelda.
    'DoorOfTime': ['Step01_Npc_Hylia_Impa_Child_Talk'],
}

# Forced conversations outside cutscenes.json that the childhood test still showed
# (2026-11-12): the owl stopping Link, the targeting and Deku Shield tutorials.
# Which tutorial entries start by themselves is a guess from their names; the next
# test confirms it.
FORCED_TALKS_EXTRA: dict[str, list[str]] = {
    'Npc_Kaepora_LakeHylia': ['Talk', 'Near'],
    'Npc_Kaepora_DeathMountainTrail': ['Near'],
    'Npc_Kokiri_006_Child': ['ActionTutorial_1st_Talk', 'AttentionMove_LectureTalk_IsFirst'],
    'Npc_Kokiri_010_Child': ['DekuShield_TutorialTalk'],
}

# Boss scenes are kept (user decision, 2026-11-12: boss intros and defeats play).
BOSS_ENTRIES = frozenset({
    ('Get_StoneOfForest', 'Boss_Appear'), ('Get_StoneOfForest', 'BossAppearSkipFunc'),
    ('Get_StoneOfForest', 'Boss_Win'), ('Get_StoneOfForest', 'Boss_Win_DreamWorld'),
    ('Get_StoneOfForest', 'InitDefeatBoss'),
    ('Get_StoneOfFire', 'Get_StoneOfFire_AppearBoss'),
    ('Get_StoneOfFire', 'Get_StoneOfFire_DefeatBoss'),
    ('Get_StoneOfWater', 'StoneOfWater_BossAppear'),
    ('Get_StoneOfWater', 'StoneOfWater_DestroyBoss'),
})
BOSS_TIMELINE_MARKS = ('_BossIn', '_BossOut')

# Entries left out of phase 1 by name (review of 2026-11-12), unless listed in GIFT_TALKS or FORCED_TALKS_ALLOW:
# (reason, test on (flow, entry)). Checked after KEEP_TALKS.
ADULT_BOSSES = ('Ganon', 'Ganondorf', 'KotakeKoume', 'Morpha', 'Nabooru', 'Phantom',
                'Twinrova', 'Valvagia')
CHATTER = re.compile(r'(^|_)(Talk|Near)$|^IrregularTalk$|^Talk_Nearby_')
EXCLUDED_ENTRIES = (
    ('adult boss intro skip (Get_StoneOfForest "*" lists every boss)',
     lambda f, e: e.startswith('BossAppearSkip_') and e[len('BossAppearSkip_'):] in ADULT_BOSSES),
    ('boss intro or defeat (kept by the user)',
     lambda f, e: (f, e) in BOSS_ENTRIES or e.startswith('BossAppearSkip')),
    ('developer test entry (Test_*)', lambda f, e: e.startswith('Test_')),
    ('player-started chatter (Talk / Near, *_Talk / *_Near, IrregularTalk, Talk_Nearby_*)',
     lambda f, e: not f.startswith('Dm_') and CHATTER.search(e) is not None),
)

# Forced or story conversations the user asked to skip (2026-11-09 review and the task 7
# brief), exempt from the chatter rule of EXCLUDED_ENTRIES.
FORCED_TALKS_ALLOW = frozenset({
    ('Npc_Kokiri_Mido_Child', 'Talk'),         # Mido blocks the way
    ('Npc_Kokiri_007_Child', 'Talk'),          # a Kokiri blocks the exit
    ('DoorOfTime', 'Dm_MelodyGet_Zelda_After_Npc_Hylia_Impa_Child_Talk'),  # brief's list
    ('Get_StoneOfWater', 'Step10_Npc_Zora_Ruto_Child_001_Talk'),
})

# Targets removed after reviewing their kept effects: (flow, entry) -> reason.
REVIEWED_OUT: dict[tuple[str, str], str] = {}


def age(data: bytes) -> str:
    child = re.search(rb'_[Cc]hild', data) is not None
    adult = re.search(rb'_[Aa]dult', data) is not None
    return {(True, False): 'child', (False, True): 'adult', (True, True): 'both'}.get(
        (child, adult), 'none')


def is_timeline(data: bytes) -> bool:
    """A BFEVFL with no flowchart (only a timeline)."""
    return data[0x20:0x22] == b'\0\0'


def zone(name: str) -> str:
    return name.split('_')[1] if name.count('_') >= 1 else ''


def load_all(nup):
    codec = ZsCodec.from_archive(nup)
    raw = {}
    for p in nup.list(FLOW_DIR):
        if p.endswith(FLOW_EXT):
            raw[p[len(FLOW_DIR):-len(FLOW_EXT)]] = codec.decompress(p, nup.read(p))
    movies = sorted(p.split('/')[-1][:-len('.webm')] for p in nup.list('Event/Movie/'))
    return raw, movies


def transition_callers(flows, names) -> dict[str, list[str]]:
    out = {n: set() for n in names}
    for fname, flow in flows.items():
        for i, ev in enumerate(flow.events):
            if ev.kind == ACTION and ev.action == TRANSITION:
                target = flow.action_params(i).get('EventName')
                if target in out:
                    out[target].add(fname)
    return {n: sorted(v) for n, v in out.items()}


def kept_effects(flow, rw) -> list[str]:
    out = []
    for i in rw.kept:
        ev = flow.events[rw.copies.get(i, i)]
        if ev.kind == ACTION:
            params = flow.action_params(ev.index)
            key = {k: v for k, v in params.items()
                   if k in ('GameDataName', 'Actor', 'ActorName', 'EventName', 'Num', 'Value',
                            'ChallengeName', 'StepName')}
            out.append(f'{i}:{ev.actor}.{ev.action} {key}' if key else f'{i}:{ev.actor}.{ev.action}')
        elif ev.kind in (SUBFLOW, SUBFLOW_SWITCH):
            out.append(f'{i}:SUB {ev.sub_flow}:{ev.sub_entry}')
        elif ev.kind == SWITCH:
            out.append(f'{i}:?{ev.actor}.{ev.query}')
        else:
            out.append(f'{i}:kind{ev.kind}')
    return out


def keep_talks_guard(raw, flows, targets, callers, table, movies, choices, forks
                     ) -> list[tuple[str, str, str]]:
    """Leaves out (in place) every target whose rewrite, as the builder applies it, changes
    what a KEEP_TALKS entry reaches: a target that calls such an entry as a same-file
    subflow inlines it and relinks its events, which `check_rewrite` (rule 4) allows for
    inlined entries. Returns (flow, entry, KEEP_TALKS entry) for each one left out."""
    out = []
    for name in sorted(set(targets) & set(KEEP_TALKS)):
        keep = [e for e in KEEP_TALKS[name] if e in flows[name].entry_points]
        while True:
            called = {m for m, c in movies.items() if name in c}
            _, steps, _ = skip_flow(raw[name], name, targets[name], called, table, callers,
                                    choices.get(name, {}), forks.get(name, frozenset()))
            bad = None
            for step in steps:
                a, b = EventFlow(step.before), EventFlow(step.after)
                changed = [k for k in keep
                           if reachable(a.events, a.entry_points, [a.entry_points[k]])
                           != reachable(b.events, b.entry_points, [b.entry_points[k]])]
                if changed:
                    bad = (step.entry, changed[0])
                    break
            if bad is None:
                break
            targets[name].discard(bad[0])
            out.append((name, *bad))
    for name in [n for n, es in targets.items() if not es]:
        del targets[name]
    return out


def build(nup, old: dict | None = None):
    """(targets, timelines, movies, summary); `old` is the current JSON (its hand-edited
    choices and reviewed_forks are used for the review)."""
    old = old or {}
    choices = {n: {int(k): v for k, v in r.get('choices', {}).items()}
               for n, r in old.get('flows', {}).items()}
    forks = {n: frozenset(v) for n, v in old.get('reviewed_forks', {}).items()}
    raw, movie_files = load_all(nup)
    flows = {n: EventFlow(d) for n, d in raw.items()}
    callers = entry_callers(flows)
    policy = load_policy()['story_flows']
    table = SkipTable.load()

    targets: dict[str, set[str]] = {}
    sources: dict[tuple[str, str], str] = {}

    def add(name, entry, source):
        if name not in flows or entry not in flows[name].entry_points:
            raise ValueError(f'{source}: {name}/{entry} does not exist')
        targets.setdefault(name, set()).add(entry)
        sources.setdefault((name, entry), source)

    timelines: set[str] = set()
    movies = sorted(set(MOVIES) | {m for m in movie_files if m.startswith(MOVIE_PATTERN)})
    review_rows = []  # neither/both scenes of the childhood zones
    for name in sorted(raw):
        if not name.startswith('Dm_') or name.startswith(EXCLUDED_PREFIXES):
            continue
        data = raw[name]
        tl = is_timeline(data)
        if tl and (name.endswith(SUBTIMELINE_SUFFIXES) or name in movie_files
                   or any(m in name for m in BOSS_TIMELINE_MARKS)):
            continue
        a = age(data)
        if a in ('none', 'both'):
            if zone(name) in CHILD_ZONES or name in CHILD_EXTRA:
                review_rows.append((name, 'timeline' if tl else 'flow', a))
            if name not in CHILD_EXTRA:
                continue
        elif a != 'child':
            continue
        if tl:
            timelines.add(name)
        elif 'EntryPoint0' in flows[name].entry_points:
            add(name, 'EntryPoint0', 'age' if a == 'child' else 'CHILD_EXTRA')
        else:
            print(f'NOTE {name}: no EntryPoint0, not targeted')
    for name in CUTSCENE_FLOWS:
        spec = policy[name]
        for e in (sorted(flows[name].entry_points) if spec == '*' else spec):
            add(name, e, 'cutscenes.json')
    for e in DOOR_OF_TIME_CHILD:
        add('DoorOfTime', e, 'DoorOfTime')
    for name, entries in GIFT_TALKS.items():
        for e in entries:
            add(name, e, 'GIFT_TALKS')
    for name, entries in FORCED_TALKS_EXTRA.items():
        for e in entries:
            add(name, e, 'FORCED_TALKS_EXTRA')
    for name, entries in KEEP_TALKS.items():
        for e in entries:
            targets.get(name, set()).discard(e)
    for (name, e) in REVIEWED_OUT:
        targets.get(name, set()).discard(e)
    gifts = ({(n, e) for n, es in GIFT_TALKS.items() for e in es} | FORCED_TALKS_ALLOW
             | {(n, e) for n, es in FORCED_TALKS_EXTRA.items() for e in es})
    print('== Entries left out by name ==')
    for reason, test in EXCLUDED_ENTRIES:
        out = sorted((n, e) for n, es in targets.items() for e in es
                     if (n, e) not in gifts and test(n, e))
        print(f'{reason}: {len(out)}')
        for n, e in out:
            print(f'    {n}/{e}')
            targets[n].discard(e)
    targets = {n: es for n, es in targets.items() if es}
    missing = set(CHILD_EXTRA) - {n for n, _, _ in review_rows}
    if missing:
        raise ValueError(f'CHILD_EXTRA: not neither/both Dm_ scenes: {sorted(missing)}')

    mcallers = transition_callers(flows, movies)
    movie_targets = {m: c for m, c in mcallers.items() if c}

    # --- review table
    results = {}
    empty = []
    print('\n== Targets (method flow) ==')
    print('flow/entry | source | result | kept | external | fork deps')
    for name in sorted(targets):
        flow = flows[name]
        for e in sorted(targets[name]):
            ext = protected_entries(callers, name, flow, targets[name], e)
            rw = effects_only(flow, e, table, choices.get(name, {}),
                              forks.get(name, frozenset()), ext)
            deps = fork_dependencies(flow, e)
            res = 'ok' if rw.error is None else f'{rw.error}: {rw.detail[:70]}'
            if rw.error is None and new_end_cases(flow, rw):
                res = f'new END case: {new_end_cases(flow, rw)}'
            if rw.error is None and not rw.kept:
                res = 'EMPTY (left out)'
                empty.append((name, e))
            results[(name, e)] = res.split(':')[0]
            print(f'{name}/{e} | {sources[(name, e)]} | {res} | {len(rw.kept)} | '
                  f'{sorted(ext)[:4]}{"..." if len(ext) > 4 else ""} | {deps[:3]}')
    # An entry that keeps nothing would start at 0xFFFF; the old trimming never makes one
    # and it is untested in game, so it is left out (its file keeps its other targets).
    for name, e in empty:
        targets[name].discard(e)
    targets = {n: es for n, es in targets.items() if es}
    guarded = keep_talks_guard(raw, flows, targets, callers, table, movie_targets, choices,
                               forks)
    for name, e, keep in guarded:
        print(f'KEEP_TALKS guard: {name}/{e} left out (its rewrite changes {keep})')
    print('\n== Timelines (method shorten) ==')
    for name in sorted(timelines):
        print(f'{name} | {age(raw[name])}')
    print('\n== Movies (method drop transition) ==')
    for m in movies:
        print(f'{m} | callers {mcallers[m] or "NONE (not targeted)"}')
    print('\n== Neither/both Dm_ scenes of the childhood zones ==')
    tcallers = transition_callers(flows, [n for n, _, _ in review_rows])
    for name, kind, a in review_rows:
        mark = 'IN ' if name in CHILD_EXTRA else 'out'
        why = CHILD_EXTRA.get(name) or NOT_CHILD_EXTRA.get(name, '(not reviewed)')
        print(f'{mark} {name} | {kind} | {a} | started by {tcallers[name]} | {why}')
    print('\n== GIFT_TALKS kept effects ==')
    for name, entries in GIFT_TALKS.items():
        flow = flows[name]
        for e in entries:
            rw = effects_only(flow, e, table, choices.get(name, {}),
                              forks.get(name, frozenset()),
                              protected_entries(callers, name, flow, targets.get(name, ()), e))
            print(f'{name}/{e}: {rw.error or "ok"} {rw.detail}')
            for line in kept_effects(flow, rw):
                print('    ' + line)
    n_entries = sum(len(v) for v in targets.values())
    # Counts of what is left (each entry alone on the original file; the builder applies
    # them in sequence, so its counts differ).
    stats = Counter(results[(n, e)] for n, es in targets.items() for e in es)
    summary = (f'{len(targets)} flows / {n_entries} entries ({stats["ok"]} rewrite cleanly; '
               + ', '.join(f'{k} {v}' for k, v in sorted(stats.items()) if k != 'ok')
               + f'; {len(empty)} empty and {len(guarded)} by the KEEP_TALKS guard left out'
               + f'), {len(timelines)} timelines, {len(movie_targets)} movies')
    return targets, sorted(timelines), movie_targets, summary


def merge(old: dict, targets, timelines, movies) -> dict:
    """The new JSON, keeping hand-edited `choices` and `reviewed_forks` (and the phase of
    targets that already had one)."""
    old_flows = old.get('flows', {})
    flows = {}
    for name in sorted(targets):
        prev = old_flows.get(name, {})
        rec = {'phase': prev.get('phase', PHASE), 'entries': sorted(targets[name])}
        if prev.get('choices'):
            rec['choices'] = prev['choices']
        flows[name] = rec
    old_tl, old_mv = old.get('timelines', {}), old.get('movies', {})
    return {
        'flows': flows,
        'timelines': {n: old_tl.get(n, PHASE) for n in timelines},
        'movies': {m: {'phase': old_mv.get(m, {}).get('phase', PHASE), 'callers': c}
                   for m, c in sorted(movies.items())},
        'reviewed_forks': old.get('reviewed_forks', {}),
    }


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    with NupArchive(argv[1]) as nup:
        old = {}
        if TARGETS_PATH.exists():
            with open(TARGETS_PATH, encoding='utf-8') as f:
                old = json.load(f)
        targets, timelines, movies, summary = build(nup, old)
    data = merge(old, targets, timelines, movies)
    print('\n' + summary)
    if '--dry-run' in argv:
        return 0
    with open(TARGETS_PATH, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write('\n')
    print(f'{TARGETS_PATH} written')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
