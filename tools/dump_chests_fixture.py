"""Genera tests/fixtures/chests.json desde el .nup real (OOT_NUP)."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from randomizer.game import GameData, chests_to_json  # noqa: E402
from randomizer.nup import NupArchive  # noqa: E402


def main():
    nup_path = os.environ.get('OOT_NUP')
    if not nup_path:
        sys.exit('Defina la variable de entorno OOT_NUP.')
    out = ROOT / 'tests' / 'fixtures' / 'chests.json'
    with NupArchive(nup_path) as nup:
        rows = chests_to_json(GameData(nup).chests())
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'{len(rows)} cofres -> {out}')


if __name__ == '__main__':
    main()
