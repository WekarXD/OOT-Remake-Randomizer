"""Builds randomizer/data/skip_actions.json from the game's event flows.
Usage: python -I tools/build_skip_actions.py <nup>
Only reads the .nup. Prints the names classified 'review'.
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from randomizer.formats.bfevfl import BfevflError, EventFlow  # noqa: E402
from randomizer.formats.zs import ZsCodec  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'randomizer', 'data', 'skip_actions.json')
ACTION_DROP = ('PlayAS', 'XLink', 'Talk', 'Camera', 'Wait', 'LookAt', 'Turn', 'DoF', 'Light', 'Palette',
               'Rumble', 'Sound', 'Bgm', 'Voice', 'Shake', 'Emotion', 'Ducking', 'Comment', 'DoNothing',
               'Navi', 'Ballon', 'CloseMessageDialog', 'ShadingParams', 'Effect', 'NorifyCutChange',
               'PlayOcarina')
ACTION_STATE = ('GameData', 'EventBool', 'Pouch')
ACTION_KEEP = ('Transition', 'BancChange', 'Warp', 'AutoSave', 'Fade')
QUERY_COLLAPSE = ('TalkChoice', 'Select', 'Random', 'Anim', 'Camera')
QUERY_STATE = ('GameData', 'Pouch', 'Flag', 'Item', 'Count', 'Have', 'Is')
SUBFLOWS_DROP = ['GetPouchContent/DisplayGetByActorName', 'Dm_SY_Ocarina/LearningOcarina*', 'Common_Camera_*/*']
# Per-actor exceptions to the rules above ('actor.action' -> class).
# King Zora moves aside through an animation after reading Ruto's letter (Dm_Zora_0010);
# dropping it left him blocking the way until the area was reloaded (childhood test,
# 2026-11-12).
ACTOR_ACTIONS = {'Npc_Zora_KingZora_child.EventPlayAS': 'keep'}


def classify_action(name):
    if any(s in name for s in ACTION_STATE):
        return 'keep'
    if any(s in name for s in ACTION_DROP):
        return 'drop'
    if any(s in name for s in ACTION_KEEP):
        return 'keep'
    return 'review'


def classify_query(name):
    if any(s in name for s in QUERY_STATE):
        return 'state'
    if any(s in name for s in QUERY_COLLAPSE):
        return 'collapse'
    return 'review'


def scan(nup):
    codec = ZsCodec.from_archive(nup)
    actions, queries = Counter(), Counter()
    skipped = []
    for path in nup.list('Event/EventFlow/'):
        if not path.endswith('.bfevfl.zs'):
            continue
        try:
            flow = EventFlow(codec.decompress(path, nup.read(path)))
        except BfevflError:
            skipped.append(path)
            continue
        for ev in flow.events:
            if ev.kind == 0 and ev.action:
                actions[ev.action] += 1
            elif ev.kind == 1 and ev.query:
                queries[ev.query] += 1
    return actions, queries, skipped


def build(actions, queries):
    return {
        'actions': {n: classify_action(n) for n in sorted(actions)},
        'actor_actions': dict(sorted(ACTOR_ACTIONS.items())),
        'queries': {n: classify_query(n) for n in sorted(queries)},
        'subflows_drop': SUBFLOWS_DROP,
        'counts': {n: c for n, c in sorted({**actions, **queries}.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('nup')
    a = ap.parse_args()
    with NupArchive(a.nup) as nup:
        actions, queries, skipped = scan(nup)
    table = build(actions, queries)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(table, f, indent=1, sort_keys=True)
        f.write('\n')
    print(f'{len(actions)} actions, {len(queries)} queries, {len(skipped)} flows skipped')
    for kind, cls_map, cnt in (('action', table['actions'], actions), ('query', table['queries'], queries)):
        for n, c in cls_map.items():
            if c == 'review':
                print(f'review {kind}: {n} ({cnt[n]})')


if __name__ == '__main__':
    main()
