import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

from randomizer import locations, spoiler
from randomizer.fill import Settings
from randomizer.formats import byml
from randomizer.formats.bfevfl import SUBFLOW, EventFlow
from randomizer.formats.rstb import Rstb, banc_rstb_size
from randomizer.formats.zs import ZsCodec
from randomizer.songs import SONGS
from randomizer.items import KEY_ITEMS
from randomizer.game import GameData, load_chests_fixture, load_skulltulas_fixture
from randomizer.generate import GenerationError, generate, safe_seed_name
from randomizer.nup import NupArchive
from randomizer.patch import RSTB_PATH, write_mod

NUP_PATH = os.environ.get('OOT_NUP')
CHESTS_FIXTURE = Path(__file__).parent / 'fixtures' / 'chests.json'
SK_FIXTURE = Path(__file__).parent / 'fixtures' / 'skulltulas.json'


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


class SeedNameTest(unittest.TestCase):
    def test_safe_seed_name(self):
        self.assertEqual(safe_seed_name('My seed é/1'), 'My-seed-e-1')
        with self.assertRaises(ValueError):
            safe_seed_name('///')
        self.assertEqual(len(safe_seed_name('a' * 60)), 40)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class RealTests(unittest.TestCase):
    def test_failed_generation_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.fill.World.can_beat', return_value=False):
                with self.assertRaises(GenerationError):
                    generate(NUP_PATH, out, Settings(seed='fail'))
            self.assertEqual(os.listdir(out), [])

    def test_existing_dir_not_overwritten(self):
        with tempfile.TemporaryDirectory() as out:
            s = Settings(seed='dup')
            r = generate(NUP_PATH, out, s)
            before = _hashes(Path(r.mod_dir))
            with self.assertRaises(GenerationError) as cm:
                generate(NUP_PATH, out, s)
            self.assertIs(cm.exception.exists, True)
            self.assertEqual(_hashes(Path(r.mod_dir)), before)

    def test_overwrite_failure_keeps_old_mod(self):
        real_rename = Path.rename

        def flaky(self, target):
            if self.name.endswith('.tmp'):
                raise OSError('boom')
            return real_rename(self, target)

        with tempfile.TemporaryDirectory() as out:
            s = Settings(seed='atomic')
            r = generate(NUP_PATH, out, s)
            before = _hashes(Path(r.mod_dir))
            with mock.patch.object(Path, 'rename', flaky):
                with self.assertRaises(OSError):
                    generate(NUP_PATH, out, s, overwrite=True)
            self.assertEqual(_hashes(Path(r.mod_dir)), before)
            self.assertEqual(sorted(os.listdir(out)), ['Rando_atomic'])
            # And a normal overwrite works and leaves no .old.
            generate(NUP_PATH, out, s, overwrite=True)
            self.assertEqual(_hashes(Path(r.mod_dir)), before)
            self.assertEqual(sorted(os.listdir(out)), ['Rando_atomic'])

    def test_wrong_title_id(self):
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.generate.TITLE_ID', 1):
                with self.assertRaises(GenerationError) as cm:
                    generate(NUP_PATH, out, Settings(seed='t'))
            self.assertIn('is not Ocarina of Time', str(cm.exception))
            self.assertEqual(os.listdir(out), [])

    def test_vanilla_mode_no_changes(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla',
                                                 spoiler=False))
            self.assertIsNone(r.mod_dir)
            self.assertEqual(r.changed_files, [])
            self.assertEqual(os.listdir(out), [])
            r = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla'))
            self.assertEqual(r.changed_files, [])
            self.assertEqual(sorted(os.listdir(r.mod_dir)), ['spoiler.json', 'spoiler.txt'])

    def test_generate_skip_cutscenes(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='cutscene', skip_cutscenes=True))
            self.assertIn('Event/EventSetting/EventSettingComponentList/'
                          'Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml',
                          r.changed_files)
            self.assertTrue(any(f.startswith('Event/EventFlow/') and f.endswith('.bfevfl.zs')
                                for f in r.changed_files))
            text = Path(r.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Skip cutscenes: Yes', text)

    def test_cutscene_errors_wrapped(self):
        from randomizer.formats.bfevfl import BfevflError
        from randomizer.formats.timeline import TimelineError
        for exc in (ValueError('grows'), BfevflError('broken'), TimelineError('bad')):
            with tempfile.TemporaryDirectory() as out:
                with mock.patch('randomizer.generate.files_with_fallback',
                                side_effect=exc):
                    with self.assertRaises(GenerationError) as cm:
                        generate(NUP_PATH, out, Settings(seed='cutscene', skip_cutscenes=True))
                self.assertIn('Could not prepare the cutscenes', str(cm.exception))
                self.assertEqual(os.listdir(out), [])

    def test_option_off_never_touches_cutscene_code(self):
        from randomizer import patch
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.generate.files_with_fallback') as fwf, \
                    mock.patch('randomizer.full_skip.build_cutscene_files') as old, \
                    mock.patch('randomizer.generate.patch.write_mod',
                               wraps=patch.write_mod) as wm:
                r = generate(NUP_PATH, out, Settings(seed='off'))
            fwf.assert_not_called()
            old.assert_not_called()
            # The only extra files are the Great Fairy flows, the flows of the NPC gifts
            # whose item changed and the analysed-event table (key items shuffled).
            from randomizer.analyzed_info import ANALYZED_INFO
            from randomizer.fairies import FOUNTAINS, TRIFORCE_FLOW
            from randomizer.gifts import GIFT_BY_LOCATION, Gift
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            gift_flows = {f'Event/EventFlow/{GIFT_BY_LOCATION[g["location"]].flow}.bfevfl.zs'
                          for g in data['npc_gifts']
                          if isinstance(GIFT_BY_LOCATION[g['location']], Gift)
                          and g['item'] != GIFT_BY_LOCATION[g['location']].content}
            fairy_flows = {f'Event/EventFlow/{n}.bfevfl.zs'
                           for n in [f.flow for f in FOUNTAINS] + [TRIFORCE_FLOW]} | gift_flows
            self.assertEqual(set(wm.call_args.args[4]) - {ANALYZED_INFO}, fairy_flows)
            text = Path(r.spoiler_txt).read_text(encoding='utf-8')
            self.assertNotIn('Cutscenes not skipped', text)
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('cutscenes_not_skipped', data)
            self.assertEqual({f for f in r.changed_files if f.startswith('Event/')}, fairy_flows)

    def test_full_skip_option_on(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            on = generate(NUP_PATH, a, Settings(seed='fs', skip_cutscenes=True))
            off = generate(NUP_PATH, b, Settings(seed='fs'))
            self.assertIn('Event/EventFlow/OpeningEvent.bfevfl.zs', on.changed_files)
            text = Path(on.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('\nCutscenes not skipped\n', text)
            self.assertNotIn('\r', text)
            d_on = json.loads(Path(on.spoiler_json).read_text(encoding='utf-8'))
            d_off = json.loads(Path(off.spoiler_json).read_text(encoding='utf-8'))
            # Same seed: same placement whether or not cutscenes are skipped.
            self.assertEqual(d_on['chests'], d_off['chests'])
            self.assertEqual(d_on['key_items'], d_off['key_items'])
            # Only the actual not-skipped findings are listed, not the applied steps.
            self.assertFalse([l for l in d_on['cutscenes_not_skipped']
                              if l.startswith(('applied ', 'unchanged ', 'full skip built'))])
            # The exit Kokiri's conversation (shared events, grown file) is skipped.
            self.assertFalse([l for l in d_on['cutscenes_not_skipped']
                              if 'Npc_Kokiri_007_Child/Talk' in l])

    def test_full_skip_no_spoiler(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='fs2', skip_cutscenes=True,
                                                 spoiler=False))
            self.assertIn('Event/EventFlow/OpeningEvent.bfevfl.zs', r.changed_files)
            self.assertIsNone(r.spoiler_txt)
            self.assertFalse((Path(r.mod_dir) / 'spoiler.txt').exists())

    def test_vanilla_with_skip_cutscenes(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla',
                                                 spoiler=False, skip_cutscenes=True))
            self.assertIsNotNone(r.mod_dir)
            self.assertTrue(r.changed_files)
            self.assertFalse(any(f.startswith('Banc/') for f in r.changed_files))
            # No banc changed, but grown flows update the RSTB: original + size change.
            self.assertIn(RSTB_PATH, r.changed_files)
            root = Path(r.mod_dir) / 'romfs'
            flow = 'Event/EventFlow/Npc_Kokiri_007_Child.bfevfl.zs'
            self.assertIn(flow, r.changed_files)
            with NupArchive(NUP_PATH) as nup:
                game = GameData(nup)
                orig_rstb = Rstb.load(game.codec.decompress(RSTB_PATH, nup.read(RSTB_PATH)))
                new_rstb = Rstb.load(game.codec.decompress(
                    RSTB_PATH, (root / RSTB_PATH).read_bytes()))
                old_len = len(game.codec.decompress(flow, nup.read(flow)))
                new_len = len(game.codec.decompress(flow, (root / flow).read_bytes()))
            self.assertGreater(new_len, old_len)
            self.assertEqual(new_rstb.get(flow[:-3]), orig_rstb.get(flow[:-3]) + new_len - old_len)

    def test_missing_rstb_entry_is_reported_in_the_spoiler(self):
        path = 'Event/EventFlow/NoSuchFlow.bfevfl.zs'
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.generate.files_with_fallback',
                            return_value=({}, ['applied X/Y'], {path: 16})):
                r = generate(NUP_PATH, out, Settings(seed='nostb', skip_cutscenes=True))
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            self.assertEqual([l for l in data['cutscenes_not_skipped'] if 'RSTB' in l],
                             [f'no RSTB entry for {path} (its size was not updated)'])

    def test_missing_rstb_entry_is_printed_without_a_spoiler(self):
        path = 'Event/EventFlow/NoSuchFlow.bfevfl.zs'
        err = io.StringIO()
        with tempfile.TemporaryDirectory() as out, contextlib.redirect_stderr(err):
            with mock.patch('randomizer.generate.files_with_fallback',
                            return_value=({}, ['applied X/Y'], {path: 16})):
                r = generate(NUP_PATH, out, Settings(seed='nostb2', skip_cutscenes=True,
                                                     spoiler=False))
            self.assertIsNone(r.spoiler_txt)
        self.assertIn(f'no RSTB entry for {path} (its size was not updated)', err.getvalue())

    def test_spoiler_excluded_reasons(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='reason'))
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            reasons = {x['reason'] for x in data['excluded']}
            self.assertTrue({'shop', 'dungeon item'} <= reasons)

    def test_generate_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            s = Settings(seed='same')
            ra = generate(NUP_PATH, a, s)
            rb = generate(NUP_PATH, b, s)
            ha, hb = _hashes(Path(ra.mod_dir)), _hashes(Path(rb.mod_dir))
            self.assertTrue(ha)
            self.assertEqual(ha, hb)

    def test_generated_files_reread_and_events(self):
        loc_map = locations.load_map()
        with tempfile.TemporaryDirectory() as out, NupArchive(NUP_PATH) as nup:
            res = generate(NUP_PATH, out, Settings(seed='reread'))
            game = GameData(nup)
            chests = game.chests()
            original = {c.hash: c.drop for c in chests}
            orig_event = {c.hash: c.event for c in chests}
            spoil = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            placement = {int(r['hash']): r['placed'] for r in spoil['chests']}
            stripped = {int(h) for h in spoil['stripped_event_sites']}
            changed = {h for h, d in placement.items() if original[h] != d}
            self.assertTrue(stripped)
            self.assertTrue(stripped <= changed)
            self.assertTrue(all(loc_map[h].strip_event for h in stripped))

            rstb = Rstb.load(game.codec.decompress(
                RSTB_PATH, (Path(res.mod_dir) / 'romfs' / RSTB_PATH).read_bytes()))
            files = [f for f in res.changed_files if f.startswith('Banc/')]
            self.assertTrue(files)
            kept_event = 0
            for f in files:
                comp = (Path(res.mod_dir) / 'romfs' / f).read_bytes()
                raw = game.codec.decompress(f, comp)
                self.assertEqual(rstb.get(f[:-3]), banc_rstb_size(len(raw)), f)
                _ver, root = byml.load(raw)
                for a in root['Actors']:
                    dyn = a.get('Dynamic') if isinstance(a, dict) else None
                    h = a.get('Hash') if isinstance(a, dict) else None
                    if not isinstance(dyn, dict) or h not in original \
                            or 'Drop__DropActor' not in dyn:
                        continue
                    self.assertEqual(dyn['Drop__DropActor'], placement[h])
                    if h in stripped:
                        self.assertNotIn('GetEventName', dyn)
                    elif h in changed and orig_event[h] is not None:
                        self.assertEqual(dyn.get('GetEventName'), orig_event[h])
                        kept_event += 1
            self.assertGreater(kept_event, 0)
            # All copies of each changed chest are in a written map.
            written = set(files)
            for c in chests:
                if c.hash in changed:
                    self.assertIn(c.banc, written)

    def test_write_mod_skulltula_drops(self):
        with tempfile.TemporaryDirectory() as out, NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            sk = game.skulltulas()
            count = {}
            for s in sk:
                count[s.hash] = count.get(s.hash, 0) + 1
            dup = next(h for h, n in count.items() if n > 1)
            others = [h for h in dict.fromkeys(s.hash for s in sk) if h != dup]
            a, b, c = dup, others[0], others[1]
            placement = {x.hash: x.drop for x in game.chests()}
            placement.update({a: 'Item_Boomerang', b: 'TBox_Rupee_Red',
                              c: 'Obj_Token_Gold'})
            written = write_mod(game, placement, Path(out), locations.load_map())
            root = Path(out) / 'romfs'

            def drops(h):
                res = []
                for banc in sorted({s.banc for s in sk if s.hash == h}):
                    raw = game.codec.decompress(
                        banc, (root / banc).read_bytes())
                    _v, r = byml.load(raw)
                    for act in r['Actors']:
                        if isinstance(act, dict) and act.get('Hash') == h:
                            res.append((act.get('Dynamic') or {}).get('Drop__DropActor'))
                return res
            self.assertEqual(len(drops(a)), 2)
            self.assertEqual(set(drops(a)), {'Obj_Rando_Item_Boomerang'})
            # Minor items float too: the red rupee gets a wrapper.
            self.assertEqual(set(drops(b)), {'Obj_Rando_TBox_Rupee_Red'})
            self.assertEqual(set(drops(c)), {None})
            pack = 'Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs'
            for p in (pack, 'Pack/Actor/Obj_Rando_TBox_Rupee_Red.pack.zs'):
                self.assertTrue((root / p).exists())
                self.assertIn(p, written)
            for t in ('ActorInfo', 'GameActorInfo', 'PouchActorInfo'):
                self.assertTrue((root / 'RSDB' / f'{t}.Product.111.rstbl.byml.zs').exists())
            rstb = Rstb.load(game.codec.decompress(
                RSTB_PATH, (root / RSTB_PATH).read_bytes()))
            self.assertGreater(rstb.get(pack[:-3]), 0)

    def test_write_mod_no_skulltulas_no_rsdb(self):
        with tempfile.TemporaryDirectory() as out, NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            placement = {x.hash: x.drop for x in game.chests()}
            first = game.chests()[0]
            placement[first.hash] = 'Item_Boomerang'
            write_mod(game, placement, Path(out), locations.load_map())
            self.assertFalse((Path(out) / 'romfs' / 'RSDB').exists())

    def test_write_mod_chests_only_does_not_scan_skulltulas(self):
        with tempfile.TemporaryDirectory() as out, NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            placement = {x.hash: x.drop for x in game.chests()}
            placement[game.chests()[0].hash] = 'Item_Boomerang'
            with mock.patch.object(GameData, 'skulltulas',
                                   side_effect=AssertionError('escaneo')):
                write_mod(game, placement, Path(out), locations.load_map())

    def test_spoiler_sections(self):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='text'))
            text = Path(res.spoiler_txt).read_text(encoding='utf-8')
            for sec in ('Seed', 'Settings', 'Randomizer version',
                        'Game version', 'Key items', 'All chests',
                        'Excluded / unmapped'):
                self.assertIn(sec, text)
            self.assertFalse((Path(res.mod_dir) / 'romfs' / 'spoiler.txt').exists())
            # Same bytes on every platform (the web page writes '\n').
            for name in ('spoiler.txt', 'spoiler.json'):
                self.assertNotIn(b'\r\n', (Path(res.mod_dir) / name).read_bytes())

    def test_generate_tokensanity_all(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            s = Settings(seed='gs', tokensanity='all')
            ra = generate(NUP_PATH, a, s)
            data = json.loads(Path(ra.spoiler_json).read_text(encoding='utf-8'))
            self.assertEqual(data['settings']['tokensanity'], 'all')
            self.assertEqual(len(data['skulltulas']), 100)
            self.assertEqual([r['location'] for r in data['skulltulas']],
                             sorted(r['location'] for r in data['skulltulas']))
            text = Path(ra.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Skulltulas', text)
            self.assertIn('Gold Skulltula Tokens (Tokensanity): All Tokens', text)
            root = Path(ra.mod_dir) / 'romfs'
            used = set()
            with NupArchive(NUP_PATH) as nup:
                game = GameData(nup)
                for banc in {x.banc for x in game.skulltulas()} |                         {x.banc for x in game.chests()}:
                    f = root / banc
                    if not f.exists():
                        continue
                    _v, r = byml.load(game.codec.decompress(banc, f.read_bytes()))
                    for act in r['Actors']:
                        dyn = act.get('Dynamic') if isinstance(act, dict) else None
                        d = dyn.get('Drop__DropActor') if isinstance(dyn, dict) else None
                        if isinstance(d, str) and d.startswith('Obj_Rando_'):
                            used.add(d)
            self.assertTrue(used)
            for d in used:
                self.assertTrue((root / 'Pack' / 'Actor' / f'{d}.pack.zs').exists(), d)
            rb = generate(NUP_PATH, b, s)
            self.assertEqual(_hashes(Path(ra.mod_dir)), _hashes(Path(rb.mod_dir)))

    def test_generate_tokensanity_off_unchanged(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra = generate(NUP_PATH, a, Settings(seed='x'))
            rb = generate(NUP_PATH, b, Settings(seed='x', tokensanity='off'))
            self.assertEqual(_hashes(Path(ra.mod_dir)), _hashes(Path(rb.mod_dir)))
            data = json.loads(Path(ra.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('skulltulas', data)
            self.assertNotIn('tokensanity', data['settings'])
            self.assertNotIn('Skulltula', Path(ra.spoiler_txt).read_text(encoding='utf-8'))

    def test_generate_songs_off_unchanged(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra = generate(NUP_PATH, a, Settings(seed='x'))
            rb = generate(NUP_PATH, b, Settings(seed='x', shuffle_songs='off'))
            self.assertEqual(_hashes(Path(ra.mod_dir)), _hashes(Path(rb.mod_dir)))
            data = json.loads(Path(ra.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('songs', data)
            self.assertNotIn('shuffle_songs', data['settings'])
            self.assertNotIn('Songs', Path(ra.spoiler_txt).read_text(encoding='utf-8'))

    def _granted(self, root: Path, nup, codec) -> dict[str, str]:
        """OoTR song location -> the song its scene grants in the mod (or the game)."""
        out = {}
        for row in SONGS:
            granted = set()
            for flow in row.flows:
                rel = f'Event/EventFlow/{flow}.bfevfl.zs'
                p = root / Path(*rel.split('/'))
                raw = p.read_bytes() if p.exists() else nup.read(rel)
                f = EventFlow(codec.decompress(rel, raw))
                granted |= {f.action_params(i).get('ActorName') for i in range(len(f.events))}
            melodies = {g for g in granted if isinstance(g, str) and g.startswith('Item_Melody_')}
            self.assertEqual(len(melodies), 1, (row.location, melodies))
            out[row.location] = melodies.pop()
        return out

    def _check_songs(self, settings):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, settings)
            data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            self.assertEqual(data['settings']['shuffle_songs'], 'song_locations')
            songs = {r['location']: r['song'] for r in data['songs']}
            self.assertEqual(len(songs), 12)
            self.assertNotEqual(songs, {s.location: s.actor for s in SONGS})
            with NupArchive(NUP_PATH) as nup:
                codec = ZsCodec.from_archive(nup)
                self.assertEqual(self._granted(Path(res.mod_dir) / 'romfs', nup, codec), songs)
            text = Path(res.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Shuffle Songs: Song Locations', text)
            section = text.split('\nSongs\n', 1)[1].split('\n\n', 1)[0]
            self.assertEqual(len(section.splitlines()), 12)
            return self._calls(Path(res.mod_dir) / 'romfs')

    @staticmethod
    def _calls(root: Path) -> dict[str, list]:
        """Song flow -> its subflow calls other than the lesson end, for the flows the
        mod writes."""
        out = {}
        with NupArchive(NUP_PATH) as nup:
            codec = ZsCodec.from_archive(nup)
            for row in SONGS:
                for flow in row.flows:
                    rel = f'Event/EventFlow/{flow}.bfevfl.zs'
                    p = root / Path(*rel.split('/'))
                    if p.exists():
                        f = EventFlow(codec.decompress(rel, p.read_bytes()))
                        out[flow] = sorted((e.sub_flow or '', e.sub_entry or '')
                                           for e in f.events if e.kind == SUBFLOW
                                           and 'PlayAuto' not in (e.sub_entry or ''))
        return out

    def test_generate_song_locations(self):
        self._check_songs(Settings(seed='songs', shuffle_songs='song_locations'))

    def test_generate_song_locations_with_skip(self):
        # The song patch is built on the skip's flows: a song flow the skip rewrote
        # keeps the skip's calls (only the lesson end may be retargeted).
        with_songs = self._check_songs(Settings(seed='songs', shuffle_songs='song_locations',
                                                skip_cutscenes=True))
        with tempfile.TemporaryDirectory() as out:
            plain = generate(NUP_PATH, out, Settings(seed='songs', skip_cutscenes=True))
            skip_only = self._calls(Path(plain.mod_dir) / 'romfs')
        self.assertTrue(skip_only)
        for flow, calls in skip_only.items():
            self.assertEqual(with_songs[flow], calls, flow)

    def test_generate_songs_anywhere(self):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='anywhere', shuffle_songs='anywhere',
                                                   skip_cutscenes=True, tokensanity='all'))
            data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            self.assertEqual(data['settings']['shuffle_songs'], 'anywhere')
            scenes = {r['location']: r['song'] for r in data['songs']}
            root = Path(res.mod_dir) / 'romfs'
            with NupArchive(NUP_PATH) as nup:
                codec = ZsCodec.from_archive(nup)
                for row in SONGS:
                    granted = set()
                    for flow in row.flows:
                        rel = f'Event/EventFlow/{flow}.bfevfl.zs'
                        p = root / Path(*rel.split('/'))
                        f = EventFlow(codec.decompress(rel, p.read_bytes() if p.exists()
                                                       else nup.read(rel)))
                        granted |= {f.action_params(i).get('ActorName')
                                    for i in range(len(f.events))}
                    self.assertIn(scenes[row.location], granted, row.location)
                # Every song and key item is in "Key items", song scenes included (review).
                songs = [k['item'] for k in data['key_items'] if k['item'].startswith('Item_Melody_')]
                self.assertEqual(len(songs), 12)
                self.assertEqual(len(set(songs)), 12)
                listed = {k['location'] for k in data['key_items']}
                for loc, actor in scenes.items():
                    if actor.startswith('Item_Melody_') or actor in KEY_ITEMS:
                        self.assertIn(loc, listed, loc)
                in_chests = {r['placed'] for r in data['chests'] if r['changed']}
                self.assertTrue(any(a.startswith('Item_Melody_') for a in in_chests))
                sk = {r['placed'] for r in data.get('skulltulas', [])}
                self.assertFalse(any(a.startswith('Item_Melody_') for a in sk))
            text = Path(res.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Shuffle Songs: Anywhere', text)

    def test_generate_songs_dungeon_rewards(self):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='rewards', shuffle_songs='dungeon_rewards',
                                                   skip_cutscenes=True))
            data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            self.assertEqual(data['settings']['shuffle_songs'], 'dungeon_rewards')
            hearts = {r['location']: r['item'] for r in data['boss_hearts']}
            self.assertEqual(len(hearts), 8)
            root = Path(res.mod_dir) / 'romfs'
            with NupArchive(NUP_PATH) as nup:
                game = GameData(nup)
                for heart in game.boss_hearts():
                    song = hearts[heart.location]
                    self.assertTrue(song.startswith('Item_Melody_'), heart.location)
                    _v, banc = byml.load(game.codec.decompress(
                        heart.banc, (root / Path(*heart.banc.split('/'))).read_bytes()))
                    actor = next(x for x in banc['Actors'] if x.get('Hash') == heart.hash)
                    self.assertEqual(actor['Gyaml'], f'Obj_Rando_{song}', heart.location)
                    self.assertTrue((root / 'Pack' / 'Actor' / f'Obj_Rando_{song}.pack.zs').exists())
            text = Path(res.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Shuffle Songs: Dungeon Rewards', text)
            self.assertIn('Boss hearts', text)

    def test_great_fairies_in_mod(self):
        # Design 2026-11-15-great-fairies: with key items shuffled each fountain gives
        # what the spoiler says, with and without the full skip.
        from randomizer.fairies import FOUNTAIN_BY_LOCATION, TRIFORCE_FLOW
        for skip in (False, True):
            with self.subTest(skip=skip), tempfile.TemporaryDirectory() as out:
                res = generate(NUP_PATH, out, Settings(seed='hadas', skip_cutscenes=skip))
                data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
                fairies = {r['location']: r['item'] for r in data['great_fairies']}
                self.assertEqual(set(fairies), set(FOUNTAIN_BY_LOCATION))
                self.assertIn('\nGreat Fairies\n', Path(res.spoiler_txt).read_text(encoding='utf-8'))
                self.assertFalse([l for l in data.get('cutscenes_not_skipped', [])
                                  if 'FairyFountain' in l or 'TriForcePoint' in l])
                root = Path(res.mod_dir) / 'romfs'
                with NupArchive(NUP_PATH) as nup:
                    codec = ZsCodec.from_archive(nup)
                    rel = f'Event/EventFlow/{TRIFORCE_FLOW}.bfevfl.zs'
                    self.assertTrue((root / rel).exists())
                    for loc, f in FOUNTAIN_BY_LOCATION.items():
                        rel = f'Event/EventFlow/{f.flow}.bfevfl.zs'
                        self.assertIn(rel, res.changed_files)
                        flow = EventFlow(codec.decompress(rel, (root / rel).read_bytes()))
                        given = {flow.action_params(i)['ActorName']
                                 for i, ev in enumerate(flow.events)
                                 if ev.kind == SUBFLOW and ev.sub_flow == 'Dm_SY_GetInEvent'
                                 and 'ActorName' in flow.action_params(i)}
                        self.assertIn(fairies[loc], given, loc)
                    rstb = Rstb.load(codec.decompress(RSTB_PATH, (root / RSTB_PATH).read_bytes()))
                    for f in FOUNTAIN_BY_LOCATION.values():
                        rel = f'Event/EventFlow/{f.flow}.bfevfl'
                        size = len(codec.decompress(rel + '.zs', (root / (rel + '.zs')).read_bytes()))
                        self.assertGreaterEqual(rstb.get(rel), size, rel)

    def test_npc_gifts_in_mod(self):
        # Design 2026-11-20-npc-gifts-batch-1: with key items shuffled each NPC gift gives
        # what the spoiler says, with and without the full skip.
        from randomizer.formats import byml
        from randomizer.gifts import GIFT_BY_LOCATION, Gift
        from randomizer.test_start import ANALYZED_INFO
        for skip in (False, True):
            with self.subTest(skip=skip), tempfile.TemporaryDirectory() as out:
                res = generate(NUP_PATH, out, Settings(seed='regalos', skip_cutscenes=skip))
                data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
                gifts = {r['location']: r['item'] for r in data['npc_gifts']}
                self.assertEqual(set(gifts), set(GIFT_BY_LOCATION))
                self.assertIn('\nNPC Gifts\n', Path(res.spoiler_txt).read_text(encoding='utf-8'))
                root = Path(res.mod_dir) / 'romfs'
                changed = {loc: g for loc, g in GIFT_BY_LOCATION.items() if gifts[loc] != g.content}
                self.assertTrue(changed)
                with NupArchive(NUP_PATH) as nup:
                    codec = ZsCodec.from_archive(nup)
                    for loc, g in changed.items():
                        if isinstance(g, Gift):
                            rel = f'Event/EventFlow/{g.flow}.bfevfl.zs'
                            flow = EventFlow(codec.decompress(rel, (root / rel).read_bytes()))
                            given = {flow.action_params(i).get(g.key)
                                     for i, ev in enumerate(flow.events) if ev.kind == SUBFLOW}
                            self.assertIn(gifts[loc], given, loc)
                            self.assertFalse(set(g.vanilla) & given, loc)
                        else:
                            banc = byml.load(codec.decompress(g.banc, (root / g.banc).read_bytes()))[1]
                            actor = next(x for x in banc['Actors'] if x.get('Hash') == g.hash)
                            self.assertEqual(actor['Gyaml'], f'Obj_Rando_{gifts[loc]}', loc)
                            self.assertTrue((root / 'Pack' / 'Actor'
                                             / f'Obj_Rando_{gifts[loc]}.pack.zs').exists())
                    entry_changed = [g for g in changed.values()
                                     if isinstance(g, Gift) and g.entry and g.flow.startswith('Dm_')]
                    if entry_changed:
                        info = byml.load(codec.decompress(
                            ANALYZED_INFO, (root / ANALYZED_INFO).read_bytes()))[1]
                        rows = {r['__RowId']: r.get('SubFlowList', []) for r in info}
                        for g in entry_changed:
                            self.assertIn('ActionGuide', rows[g.flow], g.location)

    def test_npc_gifts_not_with_vanilla_keys(self):
        from randomizer.gifts import GIFTS, Gift
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla'))
            data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('npc_gifts', data)
            for g in GIFTS:
                if isinstance(g, Gift):
                    self.assertNotIn(f'Event/EventFlow/{g.flow}.bfevfl.zs', res.changed_files)

    def test_great_fairies_not_with_vanilla_keys(self):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla'))
            data = json.loads(Path(res.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('great_fairies', data)

    def test_world_gift_sites_hold_proven_wrappers_only(self):
        # Final review: minor-item wrappers (rupees, arrow bundles...) are untested in game
        # (batch 18 open), so a world NPC gift only holds key items, songs and hearts.
        from randomizer.generate import _world_forbidden
        with NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            out = _world_forbidden(game, game.chests())
        for c in ('TBox_Rupee_Red', 'TBox_ArrowBundle_Medium', 'Item_ScrubBusinessSeed'):
            self.assertIn(c, out)
        for c in ('Item_Hookshot', 'Item_Melody_StormSong', 'Obj_Heart_Piece', 'Item_DinFire'):
            self.assertNotIn(c, out)

    def test_gs_forbidden_extra(self):
        from randomizer.generate import _gs_forbidden
        with NupArchive(NUP_PATH) as nup:
            game = GameData(nup)
            out = _gs_forbidden(game, game.chests(), locations.load_map(),
                                extra={'Item_NoSuchActor_Rando'})
        self.assertIn('Item_NoSuchActor_Rando', out)

    def test_wrapper_error_becomes_generation_error(self):
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.patch.build_wrapper_files',
                            side_effect=ValueError('roto')):
                with self.assertRaises(GenerationError):
                    generate(NUP_PATH, out, Settings(seed='gs', tokensanity='all'))
            self.assertEqual(os.listdir(out), [])


class SpoilerGsKeyItemsTest(unittest.TestCase):
    def _build(self, mode):
        chests = load_chests_fixture(CHESTS_FIXTURE)
        sk = load_skulltulas_fixture(SK_FIXTURE)
        gs_map = locations.load_gs_map()
        loc_map = locations.load_map()
        placement = {c.hash: c.drop for c in chests}
        s = next(s for s in sk if s.hash in gs_map)
        placement[s.hash] = 'Item_Hookshot' if mode != 'off' else 'Obj_Token_Gold'
        settings = Settings(seed='x', tokensanity=mode)
        return s, gs_map, spoiler.build(settings, placement, chests, loc_map, '1.3.1',
                                        sk, gs_map)

    def test_gs_key_item_listed(self):
        s, gs_map, d = self._build('all')
        rows = [r for r in d['key_items'] if r['hash'] == str(s.hash)]
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), {'item', 'label', 'location', 'zone', 'hash'})
        self.assertEqual(rows[0]['item'], 'Item_Hookshot')
        self.assertEqual(rows[0]['location'], gs_map[s.hash].location)

    def test_token_label_everywhere(self):
        self.assertEqual(spoiler._label('Obj_Token_Gold'), 'Gold Skulltula Token')

    def test_off_has_no_gs_key_items(self):
        s, _m, d = self._build('off')
        self.assertFalse([r for r in d['key_items'] if r['hash'] == str(s.hash)])


class FakeCodec:
    def decompress(self, path, data):
        return data

    def compress(self, path, data):
        return data


class FakeGame:
    """No chests; the RSTB holds `sizes` (romfs path without .zs -> size)."""
    def __init__(self, sizes):
        self.codec = FakeCodec()
        rows = sorted([zlib.crc32(p.encode()), n] for p, n in sizes.items())
        self.nup = mock.Mock()
        self.nup.read.return_value = Rstb((1, 160), rows, []).dump()

    def chests(self):
        return []


class WriteModSizesTest(unittest.TestCase):
    FLOW = 'Event/EventFlow/A.bfevfl.zs'
    GONE = 'Event/EventFlow/B.bfevfl.zs'

    def test_grown_flow_updates_its_rstb_entry(self):
        with tempfile.TemporaryDirectory() as out:
            report = []
            written = write_mod(FakeGame({self.FLOW[:-3]: 1000}), {}, Path(out), {},
                                {self.FLOW: b'x'}, {self.FLOW: 48}, report)
            self.assertEqual(written, [self.FLOW, RSTB_PATH])
            rstb = Rstb.load((Path(out) / 'romfs' / RSTB_PATH).read_bytes())
            self.assertEqual(rstb.get(self.FLOW[:-3]), 1048)
            self.assertEqual(report, [])

    def test_missing_entry_is_skipped_and_reported(self):
        with tempfile.TemporaryDirectory() as out:
            report = []
            write_mod(FakeGame({self.FLOW[:-3]: 1000}), {}, Path(out), {},
                      {self.FLOW: b'x', self.GONE: b'y'}, {self.FLOW: 8, self.GONE: 16}, report)
            rstb = Rstb.load((Path(out) / 'romfs' / RSTB_PATH).read_bytes())
            self.assertEqual(rstb.get(self.FLOW[:-3]), 1008)
            self.assertIsNone(rstb.get(self.GONE[:-3]))
            self.assertEqual(report, [f'no RSTB entry for {self.GONE} (its size was not updated)'])

    def test_no_sizes_no_rstb(self):
        for sizes in (None, {}):
            with tempfile.TemporaryDirectory() as out:
                written = write_mod(FakeGame({self.FLOW[:-3]: 1000}), {}, Path(out), {},
                                    {self.FLOW: b'x'}, sizes)
                self.assertEqual(written, [self.FLOW])
                self.assertFalse((Path(out) / 'romfs' / RSTB_PATH).exists())


class NotSkippedFilterTest(unittest.TestCase):
    def test_rstb_lines_are_kept(self):
        from randomizer.generate import _not_skipped
        line = 'no RSTB entry for Event/EventFlow/X.bfevfl.zs (its size was not updated)'
        self.assertEqual(_not_skipped(['applied F/E', line]), [line])

    def test_filter(self):
        from randomizer.generate import _not_skipped
        report = ['movie A dropped from B', 'movie A not dropped from B: err',
                  'applied F/E', 'unchanged F/E: already effects-only',
                  'full skip only F: the old trimming is not applied on top',
                  'full skip built in 1.00 s', 'fallback to trimming F/E: x',
                  'not written F: no targeted entry changed it (the old trimming applies)']
        self.assertEqual(_not_skipped(report),
                         ['movie A not dropped from B: err', 'fallback to trimming F/E: x',
                          'not written F: no targeted entry changed it (the old trimming applies)'])


class SpoilerTextTest(unittest.TestCase):
    def _data(self, mode):
        d = {'seed': 's', 'settings': {'key_items_mode': 'any_chest', 'excluded_items': [],
                                       'spoiler': True, 'skip_cutscenes': False},
             'randomizer_version': '1', 'game_version': '1.3.1', 'key_items': [],
             'chests': [], 'excluded': [], 'stripped_event_sites': []}
        if mode != 'off':
            d['settings']['tokensanity'] = mode
            d['skulltulas'] = [{'hash': '5', 'zone': 'Kokiri', 'location': 'GS House',
                                'placed': 'Obj_Token_Gold',
                                'label': 'Gold Skulltula Token'}]
        return d

    def test_to_text_tokensanity(self):
        text = spoiler.to_text(self._data('dungeons'))
        self.assertIn('Gold Skulltula Tokens (Tokensanity): Dungeons Only', text)
        self.assertIn('\nSkulltulas\n  GS House (Kokiri): Gold Skulltula Token', text)

    def test_to_text_cutscenes_not_skipped(self):
        d = self._data('off')
        d['cutscenes_not_skipped'] = ['FALLBACK Foo/Bar: reason']
        text = spoiler.to_text(d)
        self.assertIn('\nCutscenes not skipped\n  FALLBACK Foo/Bar: reason\n', text)
        d['cutscenes_not_skipped'] = []
        self.assertIn('\nCutscenes not skipped\n  none\n', spoiler.to_text(d))
        self.assertNotIn('Cutscenes not skipped', spoiler.to_text(self._data('off')))

    def test_great_fairies_section(self):
        chests = load_chests_fixture(CHESTS_FIXTURE)
        placement = {c.hash: c.drop for c in chests}
        fairies = {'HC Great Fairy Reward': 'Item_Hookshot',
                   'DMT Great Fairy Reward': 'TBox_Rupee_Red'}
        d = spoiler.build(Settings(seed='x'), placement, chests, locations.load_map(),
                          '1.3.1', fairies=fairies)
        self.assertEqual(d['great_fairies'],
                         [{'location': 'DMT Great Fairy Reward', 'item': 'TBox_Rupee_Red',
                           'label': spoiler._label('TBox_Rupee_Red')},
                          {'location': 'HC Great Fairy Reward', 'item': 'Item_Hookshot',
                           'label': 'Hookshot'}])
        rows = [r for r in d['key_items'] if r['location'] == 'HC Great Fairy Reward']
        self.assertEqual([(r['item'], r['zone']) for r in rows],
                         [('Item_Hookshot', 'Great Fairy')])
        text = spoiler.to_text(d)
        self.assertIn('\nGreat Fairies\n  DMT Great Fairy Reward: ', text)
        self.assertNotIn('Great Fairies', spoiler.to_text(self._data('off')))

    def test_npc_gifts_section(self):
        chests = load_chests_fixture(CHESTS_FIXTURE)
        placement = {c.hash: c.drop for c in chests}
        gifts = {'GC Darunias Joy': 'Item_Hookshot', 'Kak Man on Roof': 'TBox_Rupee_Red'}
        d = spoiler.build(Settings(seed='x'), placement, chests, locations.load_map(),
                          '1.3.1', gifts=gifts)
        self.assertEqual(d['npc_gifts'],
                         [{'location': 'GC Darunias Joy', 'item': 'Item_Hookshot',
                           'label': 'Hookshot'},
                          {'location': 'Kak Man on Roof', 'item': 'TBox_Rupee_Red',
                           'label': spoiler._label('TBox_Rupee_Red')}])
        rows = [r for r in d['key_items'] if r['location'] == 'GC Darunias Joy']
        self.assertEqual([(r['item'], r['zone']) for r in rows], [('Item_Hookshot', 'NPC gift')])
        text = spoiler.to_text(d)
        self.assertIn('\nNPC Gifts\n  GC Darunias Joy: Hookshot', text)
        self.assertNotIn('NPC Gifts', spoiler.to_text(self._data('off')))

    def test_to_text_off_has_no_section(self):
        text = spoiler.to_text(self._data('off'))
        self.assertNotIn('Skulltula', text)
        self.assertNotIn('Tokensanity', text)


if __name__ == '__main__':
    unittest.main()
