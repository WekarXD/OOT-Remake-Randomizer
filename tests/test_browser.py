import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from randomizer import browser
from randomizer.generate import generate
from randomizer.fill import Settings
from randomizer.nup import SUPPORTED_UPDATE_VERSION, TITLE_ID

NUP_PATH = os.environ.get('OOT_NUP')


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        s = browser.parse_settings({'seed': '  abc '})
        self.assertEqual(s, Settings(seed='abc'))

    def test_full(self):
        s = browser.parse_settings({'seed': 'x', 'key_items_mode': 'vanilla',
                                    'spoiler': False, 'skip_cutscenes': True,
                                    'tokensanity': 'all', 'excluded_items': ['Item_Hammer']})
        self.assertEqual(s, Settings(seed='x', key_items_mode='vanilla', spoiler=False,
                                     skip_cutscenes=True, tokensanity='all',
                                     excluded_items=frozenset({'Item_Hammer'})))

    def test_invalid(self):
        for bad in ({'key_items_mode': 'nope'}, {'tokensanity': 'some'},
                    {'tokensanity': 1}, {'spoiler': 'yes'}, {'skip_cutscenes': 1},
                    {'excluded_items': 'Item_Hammer'}, {'excluded_items': ['Nope']},
                    {'seed': 5}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                browser.parse_settings(bad)
        with self.assertRaises(ValueError):
            browser.parse_settings([])

    def test_non_excludable_rejected(self):
        from randomizer.items import NON_EXCLUDABLE
        item = sorted(NON_EXCLUDABLE)[0]
        with self.assertRaisesRegex(ValueError, 'Cannot exclude'):
            browser.parse_settings({'excluded_items': [item]})

    def test_non_movable_dropped_from_excluded(self):
        fixed = [a for a, ok in browser.movable_flags().items() if not ok]
        self.assertTrue(fixed)
        s = browser.parse_settings({'excluded_items': fixed[:1]})
        self.assertEqual(s.excluded_items, frozenset())

    def test_items_list(self):
        rows = browser.items()
        labels = {r['actor']: r['label'] for r in rows}
        self.assertEqual(labels['Item_Sword_Kokiri'], 'Kokiri Sword')
        self.assertTrue(all(set(r) == {'actor', 'label', 'movable', 'excludable'} for r in rows))

    def test_call_dispatch(self):
        self.assertEqual(json.loads(browser.call('items')), browser.items())
        self.assertFalse(json.loads(browser.call('nope'))['ok'])
        r = json.loads(browser.call('generate_zip', json.dumps(['x.nup', {'tokensanity': 'bad'}])))
        self.assertEqual(r, {'ok': False, 'error': 'Invalid Tokensanity value.'})


class CheckNupTest(unittest.TestCase):
    def test_not_a_nup(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'x.nup'
            f.write_bytes(b'not a nup' * 20)
            r = browser.check_nup(str(f))
        self.assertFalse(r['ok'])
        self.assertTrue(r['error'])

    def test_missing_file(self):
        r = browser.check_nup('/does/not/exist.nup')
        self.assertFalse(r['ok'])

    def test_version_checks(self):
        cases = [(TITLE_ID, SUPPORTED_UPDATE_VERSION, {'ok': True, 'version': '1.1.1'}),
                 (1, SUPPORTED_UPDATE_VERSION, 'not Zelda'),
                 (TITLE_ID, None, 'no update'),
                 (TITLE_ID, 5, 'update 5')]
        for tid, ver, expected in cases:
            fake = mock.MagicMock(title_id=tid, update_version=ver)
            with self.subTest(tid=tid, ver=ver), \
                    mock.patch('randomizer.browser.NupArchive', return_value=fake):
                r = browser.check_nup('g.nup')
                if isinstance(expected, dict):
                    self.assertEqual(r, expected)
                else:
                    self.assertFalse(r['ok'])
                    self.assertIn(expected, r['error'])
                fake.close.assert_called_once()


@unittest.skipUnless(NUP_PATH, 'OOT_NUP not set')
class GenerateZipTest(unittest.TestCase):
    def test_zip_matches_folder_generation(self):
        with tempfile.TemporaryDirectory() as out, tempfile.TemporaryDirectory() as ref:
            r = browser.generate_zip(NUP_PATH, {'seed': 'ZipCheck', 'tokensanity': 'all'}, out)
            self.assertTrue(r['ok'], r)
            self.assertEqual(r['zip_name'], 'Rando_ZipCheck.zip')
            self.assertEqual(os.listdir(out), ['Rando_ZipCheck.zip'])
            res = generate(NUP_PATH, ref, Settings(seed='ZipCheck', tokensanity='all'))
            mod = Path(res.mod_dir)
            expected = {f.relative_to(ref).as_posix(): f.read_bytes()
                        for f in mod.rglob('*') if f.is_file()}
            with zipfile.ZipFile(r['zip_path']) as zf:
                got = {n: zf.read(n) for n in zf.namelist()}
            self.assertEqual(got, expected)
            self.assertIn('Rando_ZipCheck/spoiler.txt', got)
            self.assertTrue(all(n.startswith('Rando_ZipCheck/') for n in got))
            self.assertEqual(r['changed_files'], len(res.changed_files))

    def test_vanilla_without_spoiler_is_an_error(self):
        with tempfile.TemporaryDirectory() as out:
            r = browser.generate_zip(NUP_PATH, {'seed': 'v', 'key_items_mode': 'vanilla',
                                                'spoiler': False}, out)
            self.assertFalse(r['ok'])
            self.assertEqual(os.listdir(out), [])

    def test_bad_settings_do_not_touch_disk(self):
        with tempfile.TemporaryDirectory() as out:
            r = browser.generate_zip(NUP_PATH, {'key_items_mode': 'x'}, out)
            self.assertEqual(r, {'ok': False, 'error': 'Invalid key item mode.'})
            self.assertEqual(os.listdir(out), [])
