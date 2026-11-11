import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from randomizer import locations
from randomizer.fill import Settings
from randomizer.formats import byml
from randomizer.formats.rstb import Rstb, banc_rstb_size
from randomizer.game import GameData
from randomizer.generate import GenerationError, generate, safe_seed_name
from randomizer.nup import NupArchive
from randomizer.patch import RSTB_PATH, write_mod

NUP_PATH = os.environ.get('OOT_NUP')


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


class SeedNameTest(unittest.TestCase):
    def test_safe_seed_name(self):
        self.assertEqual(safe_seed_name('Mi semilla ñ/1'), 'Mi-semilla-n-1')
        with self.assertRaises(ValueError):
            safe_seed_name('///')
        self.assertEqual(len(safe_seed_name('a' * 60)), 40)


@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')
class RealTests(unittest.TestCase):
    def test_failed_generation_leaves_nothing(self):
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.fill.World.can_beat', return_value=False):
                with self.assertRaises(GenerationError):
                    generate(NUP_PATH, out, Settings(seed='fallo'))
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
            s = Settings(seed='atomico')
            r = generate(NUP_PATH, out, s)
            before = _hashes(Path(r.mod_dir))
            with mock.patch.object(Path, 'rename', flaky):
                with self.assertRaises(OSError):
                    generate(NUP_PATH, out, s, overwrite=True)
            self.assertEqual(_hashes(Path(r.mod_dir)), before)
            self.assertEqual(sorted(os.listdir(out)), ['Rando_atomico'])
            # Y un overwrite normal funciona y no deja .old.
            generate(NUP_PATH, out, s, overwrite=True)
            self.assertEqual(_hashes(Path(r.mod_dir)), before)
            self.assertEqual(sorted(os.listdir(out)), ['Rando_atomico'])

    def test_wrong_title_id(self):
        with tempfile.TemporaryDirectory() as out:
            with mock.patch('randomizer.generate.TITLE_ID', 1):
                with self.assertRaises(GenerationError) as cm:
                    generate(NUP_PATH, out, Settings(seed='t'))
            self.assertIn('no es Ocarina of Time', str(cm.exception))
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
            r = generate(NUP_PATH, out, Settings(seed='cine', skip_cutscenes=True))
            self.assertIn('Event/EventSetting/EventSettingComponentList/'
                          'Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml',
                          r.changed_files)
            self.assertTrue(any(f.startswith('Event/EventFlow/') and f.endswith('.bfevfl.zs')
                                for f in r.changed_files))
            text = Path(r.spoiler_txt).read_text(encoding='utf-8')
            self.assertIn('Saltar cinemáticas: Sí', text)

    def test_cutscene_errors_wrapped(self):
        from randomizer.formats.bfevfl import BfevflError
        for exc in (ValueError('crece'), BfevflError('roto')):
            with tempfile.TemporaryDirectory() as out:
                with mock.patch('randomizer.generate.build_cutscene_files',
                                side_effect=exc):
                    with self.assertRaises(GenerationError) as cm:
                        generate(NUP_PATH, out, Settings(seed='cine', skip_cutscenes=True))
                self.assertIn('No se pudieron preparar las cinemáticas', str(cm.exception))
                self.assertEqual(os.listdir(out), [])

    def test_vanilla_with_skip_cutscenes(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='v', key_items_mode='vanilla',
                                                 spoiler=False, skip_cutscenes=True))
            self.assertIsNotNone(r.mod_dir)
            self.assertTrue(r.changed_files)
            self.assertFalse(any('Banc' in f for f in r.changed_files))
            self.assertNotIn(RSTB_PATH, r.changed_files)

    def test_spoiler_excluded_reasons(self):
        with tempfile.TemporaryDirectory() as out:
            r = generate(NUP_PATH, out, Settings(seed='razon'))
            data = json.loads(Path(r.spoiler_json).read_text(encoding='utf-8'))
            reasons = {x['reason'] for x in data['excluded']}
            self.assertTrue({'tienda', 'objeto de mazmorra'} <= reasons)

    def test_generate_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            s = Settings(seed='igual')
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
            # Todas las copias de cada cofre cambiado están en un mapa escrito.
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
            self.assertEqual(set(drops(b)), {'Obj_Rupee_Red'})
            self.assertEqual(set(drops(c)), {None})
            pack = 'Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs'
            self.assertTrue((root / pack).exists())
            self.assertIn(pack, written)
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

    def test_spoiler_sections(self):
        with tempfile.TemporaryDirectory() as out:
            res = generate(NUP_PATH, out, Settings(seed='texto'))
            text = Path(res.spoiler_txt).read_text(encoding='utf-8')
            for sec in ('Semilla', 'Ajustes', 'Versión del randomizer',
                        'Versión del juego', 'Objetos clave', 'Todos los cofres',
                        'Excluidos / sin asociar'):
                self.assertIn(sec, text)
            self.assertFalse((Path(res.mod_dir) / 'romfs' / 'spoiler.txt').exists())


if __name__ == '__main__':
    unittest.main()
