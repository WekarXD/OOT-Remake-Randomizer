import os
import unittest

from randomizer.formats.bfevfl import SUBFLOW, EventFlow
from randomizer.formats.zs import ZsCodec
from randomizer.logic import ootr_data
from randomizer.nup import NupArchive
from randomizer.songs import (CRATER_FLOW, SHUFFLE_SONGS, SONG_BY_ACTOR, SONG_BY_LOCATION,
                              SONGS, WINDMILL_FLOW, song_flow_patches)

NUP_PATH = os.environ.get('OOT_NUP')
VANILLA = {s.location: s.actor for s in SONGS}
STORM_FLAG = 'IsGet.Item_Melody_StormSong'
WINDMILL_FLAG = 'HavePlayedEvent.Dm_MelodyGet_Storm'


def _swap(a: str, b: str) -> dict[str, str]:
    out = dict(VANILLA)
    out[a], out[b] = VANILLA[b], VANILLA[a]
    return out


def _lessons(flow):
    """`Dm_SY_Ocarina:LearningOcarina*` calls that name a melody (PlayAuto has none)."""
    return [i for i, ev in enumerate(flow.events)
            if ev.kind == SUBFLOW and ev.sub_flow == 'Dm_SY_Ocarina'
            and (ev.sub_entry or '').startswith('LearningOcarina')
            and 'MelodyType' in flow.action_params(i)]


def _params(flow):
    return [flow.action_params(i) for i in range(len(flow.events))]


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class SongPatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flows = {}
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            names = {f for s in SONGS for f in s.flows} | {WINDMILL_FLOW, CRATER_FLOW}
            for name in names:
                p = f'Event/EventFlow/{name}.bfevfl.zs'
                cls.flows[name] = codec.decompress(p, nup.read(p))

    def _patch(self, placement):
        return song_flow_patches(self.flows.__getitem__, placement)

    def test_identity_placement_changes_nothing(self):
        self.assertEqual(self._patch(VANILLA), {})

    def test_swap_impa_saria(self):
        out = self._patch(_swap('Song from Impa', 'Song from Saria'))
        self.assertEqual(set(out), {'Dm_MelodyGet_Zelda', 'Dm_MelodyGet_Saria'})
        old, new = EventFlow(self.flows['Dm_MelodyGet_Zelda']), EventFlow(out['Dm_MelodyGet_Zelda'])
        changed = {}
        for i, (a, b) in enumerate(zip(_params(old), _params(new), strict=True)):
            if a != b:
                changed[i] = {k: v for k, v in b.items() if a.get(k) != v}
        lessons = {i: {'MelodyType': 2} for i in _lessons(new)}
        self.assertEqual(len(lessons), 2)  # PlayExample and FollowExample
        grants = {i: {'ActorName': 'Item_Melody_SariaSong'} for i, p in enumerate(_params(old))
                  if p.get('ActorName') == 'Item_Melody_ZeldaLullaby'}
        self.assertEqual(changed, {**lessons, **grants})

    def test_crater_flag_follows_song(self):
        out = self._patch(_swap('Sheik in Crater', 'Song from Windmill'))
        names = [p.get('GameDataName') for p in _params(EventFlow(out[CRATER_FLOW]))]
        self.assertIn('IsGet.Item_Melody_StormSong', names)
        self.assertNotIn('IsGet.Item_Melody_FireBolero', names)

    def test_windmill_queries(self):
        out = self._patch(_swap('Sheik in Crater', 'Song from Windmill'))
        names = [p.get('GameDataName') for p in _params(EventFlow(out[WINDMILL_FLOW]))]
        self.assertNotIn(STORM_FLAG, names)
        self.assertEqual(names.count(WINDMILL_FLAG), 4)

    def test_windmill_untouched_when_storm_stays(self):
        self.assertNotIn(WINDMILL_FLOW, self._patch(_swap('Song from Impa', 'Song from Saria')))

    def test_sun_split(self):
        out = self._patch(_swap('Song from Royal Familys Tomb', 'Song from Saria'))
        self.assertTrue({'Dm_MelodyGet_Sun', 'Dm_MelodyGet_Sun_03', 'Dm_MelodyGet_Saria'}
                        <= set(out))
        sun = EventFlow(out['Dm_MelodyGet_Sun'])
        self.assertEqual([sun.action_params(i)['MelodyType'] for i in _lessons(sun)], [2] * 4)
        grant = [p['ActorName'] for p in _params(EventFlow(out['Dm_MelodyGet_Sun_03']))
                 if 'ActorName' in p and p['ActorName'].startswith('Item_Melody_')]
        self.assertEqual(grant, ['Item_Melody_SariaSong'])

    def test_full_rotation(self):
        actors = [s.actor for s in SONGS]
        rotated = {s.location: actors[(k + 1) % 12] for k, s in enumerate(SONGS)}
        out = self._patch(rotated)
        for s in SONGS:
            granted = {p.get('ActorName') for f in s.flows
                       for p in _params(EventFlow(out[f]))}
            self.assertIn(rotated[s.location], granted, s.location)
            self.assertNotIn(s.actor, granted, s.location)

    def _autos(self, data):
        flow = EventFlow(data)
        return [ev.sub_entry for ev in flow.events if ev.kind == SUBFLOW
                and ev.sub_flow == 'Dm_SY_Ocarina' and 'PlayAuto' in (ev.sub_entry or '')]

    def test_lesson_end_follows_song_group(self):
        # PlayAuto only handles melodies 0-5 (and 12), PlayAutoForSeek only the warp
        # songs 6-11: teaching a song of the other group hung the game (batch 22).
        out = self._patch(_swap('Sheik in Crater', 'Song from Windmill'))
        self.assertEqual(self._autos(out['Dm_MelodyGet_Storm']),
                         ['LearningOcarinaPlayAutoForSeek'])
        self.assertEqual(self._autos(out[CRATER_FLOW]), ['LearningOcarinaPlayAuto'])

    def test_lesson_end_kept_within_group(self):
        out = self._patch(_swap('Song from Impa', 'Song from Saria'))
        self.assertEqual(self._autos(out['Dm_MelodyGet_Zelda']), ['LearningOcarinaPlayAuto'])

    def _reached(self, data, name):
        """Events reached from every entry, following same-file subflow calls."""
        flow = EventFlow(data)
        seen, stack = set(), list(flow.entry_points.values())
        while stack:
            i = stack.pop()
            if i in seen or i == 0xFFFF:
                continue
            seen.add(i)
            ev = flow.events[i]
            stack += [n for n in (ev.next, ev.join) if isinstance(n, int)]
            stack += list(ev.cases or []) + list(ev.forks or [])
            if ev.kind == SUBFLOW and ev.sub_flow in ('', name) and ev.sub_entry in flow.entry_points:
                stack.append(flow.entry_points[ev.sub_entry])
        return flow, seen

    def test_impa_gives_shield(self):
        placement = dict(VANILLA, **{'Song from Impa': 'TBox_Shield_Deku'})
        out = self._patch(placement)
        self.assertEqual(set(out), {'Dm_MelodyGet_Zelda'})
        flow, seen = self._reached(out['Dm_MelodyGet_Zelda'], 'Dm_MelodyGet_Zelda')
        self.assertEqual([i for i in seen if 'LearningOcarina' in (flow.events[i].sub_entry or '')],
                         [])
        grants = {flow.action_params(i).get('ActorName') for i in seen}
        self.assertIn('TBox_Shield_Deku', grants)
        self.assertNotIn('Item_Melody_ZeldaLullaby', grants)

    def test_crater_gives_hookshot(self):
        out = self._patch(dict(VANILLA, **{'Sheik in Crater': 'Item_Hookshot'}))
        self.assertNotIn(WINDMILL_FLOW, out)
        flow, seen = self._reached(out[CRATER_FLOW], CRATER_FLOW)
        names = [flow.action_params(i).get('GameDataName') for i in seen]
        self.assertNotIn('IsGet.Item_Melody_FireBolero', names)
        self.assertIn('Item_Hookshot', {flow.action_params(i).get('ActorName') for i in seen})
        self.assertEqual([i for i in seen if 'LearningOcarina' in (flow.events[i].sub_entry or '')],
                         [])

    def test_storm_elsewhere_patches_windmill(self):
        out = self._patch(dict(VANILLA, **{'Sheik in Crater': 'Item_Melody_StormSong',
                                           'Song from Windmill': 'Obj_Rupee_Red'}))
        names = [p.get('GameDataName') for p in _params(EventFlow(out[WINDMILL_FLOW]))]
        self.assertEqual(names.count(WINDMILL_FLAG), 4)
        grants = {p.get('ActorName') for p in _params(EventFlow(out['Dm_MelodyGet_Storm']))}
        self.assertIn('Obj_Rupee_Red', grants)
        # The crater gives a song: its flag follows the song, as in Song Locations.
        crater = [p.get('GameDataName') for p in _params(EventFlow(out[CRATER_FLOW]))]
        self.assertIn('IsGet.Item_Melody_StormSong', crater)

    def test_emptied_fork_branch_goes_to_join(self):
        # A lesson is often the whole of a fork branch; an empty branch points at its
        # fork's join, as the game's own empty branches do (Dm_MelodyGet_Storm fork 39).
        old = EventFlow(self.flows['Dm_MelodyGet_Epona'])
        lessons = {i for i, ev in enumerate(old.events) if ev.kind == SUBFLOW
                   and (ev.sub_entry or '').startswith('LearningOcarina')}
        emptied = [(f, k) for f, ev in enumerate(old.events) if ev.forks
                   for k, b in enumerate(ev.forks) if b in lessons]
        self.assertTrue(emptied)
        out = self._patch(dict(VANILLA, **{'Song from Malon': 'Obj_Rupee_Red'}))
        new = EventFlow(out['Dm_MelodyGet_Epona'])
        for f, k in emptied:
            self.assertNotIn(new.events[f].forks[k], lessons | {0xFFFF}, (f, k))
        self.assertTrue(any(new.events[f].forks[k] == new.events[f].join for f, k in emptied))

    def test_song_twice_raises(self):
        with self.assertRaises(ValueError):
            self._patch(dict(VANILLA, **{'Song from Impa': 'Item_Melody_SariaSong'}))

    def test_missing_location_raises(self):
        placement = dict(VANILLA)
        del placement['Song from Impa']
        with self.assertRaises(ValueError):
            self._patch(placement)

    def test_bad_placement_raises(self):
        bad = dict(VANILLA)
        bad['Song from Impa'] = 'Item_Melody_SariaSong'
        with self.assertRaises(ValueError):
            self._patch(bad)


class SongTableTest(unittest.TestCase):
    def test_table_matches_ootr(self):
        locations = ootr_data.load_locations()
        for row in SONGS:
            self.assertEqual(locations[row.location]['vanilla_item'], row.song, row.location)

    def test_table_is_a_permutation(self):
        self.assertEqual(len(SONGS), 12)
        self.assertEqual(len({r.location for r in SONGS}), 12)
        self.assertEqual(len({r.actor for r in SONGS}), 12)
        self.assertEqual(sorted(r.melody for r in SONGS), list(range(12)))
        self.assertEqual(set(SONG_BY_LOCATION), {r.location for r in SONGS})
        self.assertEqual(set(SONG_BY_ACTOR), {r.actor for r in SONGS})
        self.assertTrue(all(r.actor.startswith('Item_Melody_') and r.flows for r in SONGS))

    def test_shuffle_values(self):
        self.assertEqual(SHUFFLE_SONGS, ('off', 'song_locations'))
