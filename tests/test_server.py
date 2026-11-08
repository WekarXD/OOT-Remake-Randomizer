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
                        side_effect=GenerationError('x', exists=True)):
            status, d = self.jreq('/api/generate', self.gen_body())
        self.assertFalse(d['ok'])
        self.assertTrue(d['exists'])

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
        movable = {i['actor'] for i in items if not i['movable']}
        self.assertEqual(movable, {'Item_HeavyBoot', 'Item_Gauntlet_Silver',
                                   'Item_Shield_Mirror', 'Item_HoverBoot',
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
