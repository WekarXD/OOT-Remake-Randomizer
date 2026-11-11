import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from randomizer import config
from randomizer.generate import GenerateResult, GenerationError
from randomizer.web.server import make_server


class ServerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.cfg = self.tmp / 'config.json'
        self.server = make_server(0, self.cfg)
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'
        t = threading.Thread(target=self.server.serve_forever, daemon=True)
        t.start()
        self.addCleanup(t.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def req(self, path, body=None, raw=None, headers=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        r = urllib.request.Request(self.base + path, data=data)
        if data is not None:
            r.add_header('Content-Type', 'application/json')
        for k, v in (headers or {}).items():
            r.add_header(k, v)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def jreq(self, path, body=None):
        status, headers, data = self.req(path, body)
        return status, json.loads(data)

    def gen_body(self, **kw):
        b = {'nup_path': 'a.nup', 'out_dir': str(self.tmp / 'out'), 'seed': 's',
             'key_items_mode': 'any_chest', 'excluded_items': [], 'spoiler': True,
             'overwrite': False}
        b.update(kw)
        return b

    def test_validate_bad_path(self):
        status, d = self.jreq('/api/validate', {'nup_path': str(self.tmp / 'nope.nup')})
        self.assertFalse(d['ok'])
        self.assertTrue(d['error'].startswith('El archivo no existe'))

    def test_generate_exists_flag(self):
        with mock.patch('randomizer.web.server.generate',
                        side_effect=GenerationError('x', exists=True, mod_dir='o/Rando_s')):
            status, d = self.jreq('/api/generate', self.gen_body())
        self.assertFalse(d['ok'])
        self.assertTrue(d['exists'])
        self.assertEqual(d['mod_dir'], 'o/Rando_s')

    def test_generate_ok_saves_config(self):
        res = GenerateResult('s', 'mod', 'mod/spoiler.txt', None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res) as g:
            status, d = self.jreq('/api/generate', self.gen_body(seed='  s  '))
        self.assertTrue(d['ok'])
        self.assertEqual(d['spoiler_txt'], 'mod/spoiler.txt')
        self.assertEqual(g.call_args.args[2].seed, 's')
        saved = json.loads(self.cfg.read_text(encoding='utf-8'))
        self.assertEqual(saved['nup_path'], 'a.nup')
        self.assertEqual(saved['out_dir'], str(self.tmp / 'out'))

    def test_generate_whitespace_seed_is_empty(self):
        res = GenerateResult('r', 'mod', None, None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res) as g:
            self.jreq('/api/generate', self.gen_body(seed='   '))
        self.assertEqual(g.call_args.args[2].seed, '')

    def test_generate_validates_input(self):
        with mock.patch('randomizer.web.server.generate') as g:
            s1, d1 = self.jreq('/api/generate', self.gen_body(key_items_mode='raro'))
            s2, d2 = self.jreq('/api/generate', self.gen_body(excluded_items=['Item_Nope']))
        self.assertEqual((s1, s2), (400, 400))
        self.assertFalse(d1['ok'])
        self.assertFalse(d2['ok'])
        g.assert_not_called()

    def test_generate_rejects_non_excludable(self):
        with mock.patch('randomizer.web.server.generate') as g:
            status, d = self.jreq('/api/generate',
                                  self.gen_body(excluded_items=['Item_Longshot']))
        self.assertEqual(status, 400)
        self.assertEqual(d['error'], 'No se puede excluir Gancho largo: la lógica necesita '
                         'moverlo para que la partida sea completable.')
        g.assert_not_called()

    def test_generate_drops_non_movable_from_excluded(self):
        res = GenerateResult('s', 'mod', None, None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res) as g:
            self.jreq('/api/generate', self.gen_body(
                excluded_items=['Item_Hookshot', 'Item_Range_Bow']))
        self.assertEqual(g.call_args.args[2].excluded_items, frozenset({'Item_Range_Bow'}))

    def test_generate_spoiler_must_be_bool(self):
        with mock.patch('randomizer.web.server.generate') as g:
            for bad in ('no', 0, None):
                status, d = self.jreq('/api/generate', self.gen_body(spoiler=bad))
                self.assertEqual(status, 400, bad)
        g.assert_not_called()

    def test_skip_cutscenes_strict_bool(self):
        with mock.patch('randomizer.web.server.generate') as g:
            for bad in ('si', 1, None):
                status, d = self.jreq('/api/generate', self.gen_body(skip_cutscenes=bad))
                self.assertEqual(status, 400, bad)
                self.assertEqual(d['error'], 'skip_cutscenes debe ser true o false')
        g.assert_not_called()

    def test_tokensanity_invalid(self):
        with mock.patch('randomizer.web.server.generate') as g:
            for bad in ('todo', 1, None, ['all']):
                status, d = self.jreq('/api/generate', self.gen_body(tokensanity=bad))
                self.assertEqual(status, 400, bad)
                self.assertEqual(d['error'], 'Valor de Tokensanity no válido.')
        g.assert_not_called()

    def test_tokensanity_valid_reaches_settings_and_config(self):
        res = GenerateResult('s', 'mod', None, None, [])
        for value in ('off', 'dungeons', 'overworld', 'all'):
            with self.subTest(value=value):
                with mock.patch('randomizer.web.server.generate', return_value=res) as g:
                    status, d = self.jreq('/api/generate', self.gen_body(tokensanity=value))
                self.assertTrue(d['ok'])
                self.assertEqual(g.call_args.args[2].tokensanity, value)
                saved = json.loads(self.cfg.read_text(encoding='utf-8'))
                self.assertEqual(saved['last_settings']['tokensanity'], value)

    def test_tokensanity_defaults_to_off(self):
        res = GenerateResult('s', 'mod', None, None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res) as g:
            self.jreq('/api/generate', self.gen_body())
        self.assertEqual(g.call_args.args[2].tokensanity, 'off')
        saved = json.loads(self.cfg.read_text(encoding='utf-8'))
        self.assertEqual(saved['last_settings']['tokensanity'], 'off')

    def test_last_settings_without_skip(self):
        config.save(self.cfg, {'last_settings': {'seed': 'a'}})
        status, d = self.jreq('/api/config')
        self.assertEqual(status, 200)
        self.assertNotIn('skip_cutscenes', d['last_settings'])

    def test_generate_null_mod_dir(self):
        res = GenerateResult('s', None, None, None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res):
            status, d = self.jreq('/api/generate', self.gen_body())
        self.assertTrue(d['ok'])
        self.assertIsNone(d['mod_dir'])

    def test_generate_concurrent_409(self):
        started, release = threading.Event(), threading.Event()

        def slow(*a, **k):
            started.set()
            release.wait(10)
            return GenerateResult('s', 'mod', None, None, [])

        results = []
        with mock.patch('randomizer.web.server.generate', side_effect=slow):
            t = threading.Thread(
                target=lambda: results.append(self.jreq('/api/generate', self.gen_body())))
            t.start()
            self.assertTrue(started.wait(10))
            status, d = self.jreq('/api/generate', self.gen_body())
            release.set()
            t.join(10)
        self.assertEqual(status, 409)
        self.assertEqual(d, {'ok': False, 'error': 'Ya hay una generación en curso.'})
        self.assertTrue(results[0][1]['ok'])
        # El cerrojo se libera.
        res = GenerateResult('s', 'mod', None, None, [])
        with mock.patch('randomizer.web.server.generate', return_value=res):
            self.assertTrue(self.jreq('/api/generate', self.gen_body())[1]['ok'])

    def test_unhandled_exception_500(self):
        with mock.patch('randomizer.web.server.generate', side_effect=RuntimeError('boom')):
            status, d = self.jreq('/api/generate', self.gen_body())
        self.assertEqual(status, 500)
        self.assertEqual(d['error'], 'Error interno: RuntimeError')

    def test_body_too_large(self):
        status, _, _ = self.req('/api/validate', raw=b'x' * (1024 * 1024 + 1))
        self.assertEqual(status, 413)

    def test_spoiler_path_traversal(self):
        status, _, _ = self.req('/api/spoiler?path=C:/Windows/win.ini')
        self.assertEqual(status, 403)

    def test_spoiler_inside_out_dir(self):
        out = self.tmp / 'out'
        (out / 'Rando_x').mkdir(parents=True)
        f = out / 'Rando_x' / 'spoiler.txt'
        f.write_text('hola ñ', encoding='utf-8')
        other = out / 'Rando_x' / 'otro.txt'
        other.write_text('no', encoding='utf-8')
        config.save(self.cfg, {'out_dir': str(out)})
        status, headers, data = self.req('/api/spoiler?path=' + urllib.request.quote(str(f)))
        self.assertEqual(status, 200)
        self.assertEqual(data.decode('utf-8'), 'hola ñ')
        self.assertIn('text/plain; charset=utf-8', headers['Content-Type'])
        status, _, _ = self.req('/api/spoiler?path=' + urllib.request.quote(str(other)))
        self.assertEqual(status, 403)

    def test_items_labels(self):
        status, items = self.jreq('/api/items')
        self.assertEqual(len(items), 15)
        self.assertTrue(all(i['label'] for i in items))
        excludable = {i['actor'] for i in items if i['excludable']}
        self.assertFalse(excludable & {'Item_Longshot', 'Item_Gauntlet_Gold'})
        self.assertTrue(all(not i['excludable'] for i in items if not i['movable']))
        self.assertEqual(len(excludable), 15 - 7 - 2)
        movable = {i['actor'] for i in items if not i['movable']}
        self.assertEqual(movable, {'Item_HeavyBoot', 'Item_Gauntlet_Silver',
                                   'Item_Shield_Mirror', 'Item_HoverBoot', 'Item_BombBag_Small',
                                   'Item_Hookshot', 'Item_Boomerang'})

    def test_config_roundtrip_and_corrupt(self):
        self.assertEqual(self.jreq('/api/config')[1], {})
        self.cfg.write_text('{no json', encoding='utf-8')
        self.assertEqual(config.load(self.cfg), {})
        config.save(self.cfg, {'nup_path': 'x'})
        self.assertEqual(self.jreq('/api/config')[1], {'nup_path': 'x'})

    def test_static_only_serves_static_dir(self):
        self.assertEqual(self.req('/static/../server.py')[0], 404)
        self.assertEqual(self.req('/static/nope.css')[0], 404)

    def raw_http(self, method, path, headers, body=b''):
        import http.client
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1])
        c.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for k, v in headers.items():
            c.putheader(k, v)
        c.endheaders(body)
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data

    def test_bad_host_rejected(self):
        st, _ = self.raw_http('GET', '/api/config', {'Host': 'evil.com'})
        self.assertEqual(st, 403)
        port = self.server.server_address[1]
        st, _ = self.raw_http('GET', '/api/config', {'Host': f'localhost:{port}'})
        self.assertEqual(st, 200)

    def test_post_requires_json_content_type(self):
        st, _, _ = self.req('/api/validate', raw=b'{}',
                            headers={'Content-Type': 'text/plain'})
        self.assertEqual(st, 415)

    def test_post_bad_origin_rejected(self):
        st, _, _ = self.req('/api/validate', {'nup_path': 'x'},
                            headers={'Origin': 'http://evil.com'})
        self.assertEqual(st, 403)
        st, _, _ = self.req('/api/validate', {'nup_path': 'x'}, headers={'Origin': self.base})
        self.assertEqual(st, 200)

    def test_negative_content_length(self):
        port = self.server.server_address[1]
        st, _ = self.raw_http('POST', '/api/validate', {
            'Host': f'127.0.0.1:{port}', 'Content-Type': 'application/json',
            'Content-Length': '-5'})
        self.assertEqual(st, 400)

    def test_validate_nul_path(self):
        st, d = self.jreq('/api/validate', {'nup_path': 'C:\\a\x00b'})
        self.assertEqual(st, 200)
        self.assertFalse(d['ok'])
        self.assertTrue(d['error'].startswith('El archivo no existe'))

    def test_validate_non_nup_file(self):
        f = self.tmp / 'x.nup'
        f.write_bytes(b'not a nup' * 20)
        st, d = self.jreq('/api/validate', {'nup_path': str(f)})
        self.assertFalse(d['ok'])
        self.assertTrue(d['error'])

    def test_validate_reports_display_version(self):
        from randomizer.nup import SUPPORTED_UPDATE_VERSION, TITLE_ID
        f = self.tmp / 'g.nup'
        f.write_bytes(b'x')
        fake = mock.MagicMock(title_id=TITLE_ID, update_version=SUPPORTED_UPDATE_VERSION)
        with mock.patch('randomizer.web.server.NupArchive', return_value=fake):
            st, d = self.jreq('/api/validate', {'nup_path': str(f)})
        self.assertEqual(d, {'ok': True, 'version': '1.1.1'})

    def test_static_encoded_traversal(self):
        st, _, _ = self.req('/static/%2e%2e/server.py')
        self.assertIn(st, (403, 404))

    def test_index_served(self):
        status, headers, data = self.req('/')
        self.assertEqual(status, 200)
        html = data.decode('utf-8')
        for tab in ('General', 'Objetos', 'Lógica', 'Spoiler'):
            self.assertIn(tab, html)


if __name__ == '__main__':
    unittest.main()
