import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import build_site  # noqa: E402


class BuildSiteTest(unittest.TestCase):
    def test_build(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'site'
            zip_path = build_site.build(out)
            for name in ('index.html', 'app.js', 'worker.js', 'style.css', '.nojekyll'):
                self.assertTrue((out / name).is_file(), name)
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                zf.extractall(Path(d) / 'pkg')
            for needed in ('randomizer/browser.py', 'randomizer/data/location_map.json',
                           'randomizer/data/gs_map.json', 'randomizer/logic/ootr/locations.json',
                           'randomizer/logic/vanilla_settings.json'):
                self.assertIn(needed, names)
            self.assertFalse([n for n in names if '__pycache__' in n or n.endswith('.pyc')])
            self.assertTrue(all(n.startswith('randomizer/') for n in names))
            # The unpacked package works on its own, as it does in Pyodide.
            code = ('import sys; sys.path.insert(0, sys.argv[1]); '
                    'from randomizer.browser import call; print(call("items"))')
            r = subprocess.run([sys.executable, '-I', '-c', code, str(Path(d) / 'pkg')],
                               capture_output=True, text=True, check=True, cwd=d)
            self.assertIn('Kokiri Sword', [row['label'] for row in json.loads(r.stdout)])

    def test_worker_pins_pyodide_version(self):
        worker = (ROOT / 'site' / 'worker.js').read_text(encoding='utf-8')
        self.assertEqual(worker.count('pyodide/v314.0.7/full/'), 2)


if __name__ == '__main__':
    unittest.main()
