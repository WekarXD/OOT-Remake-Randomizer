import json
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


if __name__ == '__main__':
    unittest.main()
