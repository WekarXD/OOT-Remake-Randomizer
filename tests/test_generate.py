import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from randomizer import locations, spoiler
from randomizer.fill import Settings
from randomizer.formats import byml
from randomizer.formats.rstb import Rstb, banc_rstb_size
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
                    mock.patch('randomizer.cutscenes.build_cutscene_files') as old, \
                    mock.patch('randomizer.generate.patch.write_mod',
                               wraps=patch.write_mod) as wm:
                r = generate(NUP_PATH, out, Settings(seed='off'))
            fwf.assert_not_called()
            old.assert_not_called()
            self.assertIsNone(wm.call_args.args[4])  # no extra files: as before
            text = Path(r.spoiler_txt).read_text(encoding='utf-8')
            self.assertNotIn('Cutscenes not skipped', text)
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            self.assertNotIn('cutscenes_not_skipped', data)
            self.assertFalse(any(f.startswith('Event/') for f in r.changed_files))

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
            self.assertNotIn(RSTB_PATH, r.changed_files)

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

    def test_to_text_off_has_no_section(self):
        text = spoiler.to_text(self._data('off'))
        self.assertNotIn('Skulltula', text)
        self.assertNotIn('Tokensanity', text)


if __name__ == '__main__':
    unittest.main()
