import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from randomizer import browser

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which('node')


@unittest.skipIf(NODE is None, 'node is not installed')
class PresetsTest(unittest.TestCase):
    def test_node_presets(self):
        r = subprocess.run([NODE, '--test', 'tests/js/*.test.cjs'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_presets_accepted_by_python(self):
        r = subprocess.run([NODE, '-e', 'console.log(JSON.stringify(require("./site/presets.js").LIST))'],
                           cwd=ROOT, capture_output=True, text=True, check=True)
        presets = json.loads(r.stdout)
        self.assertEqual(len(presets), 3)
        for p in presets:
            with self.subTest(preset=p['id']):
                s = browser.parse_settings({**p['settings'], 'seed': 'x'})
                for key, value in p['settings'].items():
                    self.assertEqual(getattr(s, key), value)


class MarkupTest(unittest.TestCase):
    def test_markup_has_every_id_app_uses(self):
        app = (ROOT / 'site' / 'app.js').read_text(encoding='utf-8')
        html = (ROOT / 'site' / 'index.html').read_text(encoding='utf-8')
        ids = set(re.findall(r"\$\('([\w-]+)'\)", app))
        ids |= {'panel-general', 'panel-items', 'panel-logic', 'panel-help', 'preset', 'preset-desc', 'theme'}
        missing = sorted(i for i in ids if f'id="{i}"' not in html)
        self.assertEqual(missing, [])

    def test_presets_script_loads_before_app(self):
        html = (ROOT / 'site' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('<script src="presets.js"></script>', html)
        self.assertLess(html.index('src="presets.js"'), html.index('src="app.js"'))


if __name__ == '__main__':
    unittest.main()
