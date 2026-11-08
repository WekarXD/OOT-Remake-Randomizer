"""python -m randomizer [--port 8765] [--no-browser]"""
import argparse
import webbrowser

from . import config
from .web.server import make_server


def main():
    ap = argparse.ArgumentParser(prog='randomizer')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    args = ap.parse_args()
    server = make_server(args.port, config.DEFAULT_PATH)
    url = f'http://127.0.0.1:{server.server_address[1]}/'
    print(f'Servidor en {url} (Ctrl+C para salir)')
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
