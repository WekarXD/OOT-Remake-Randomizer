"""Inventario de datos del juego: cofres y Skulltulas doradas de los mapas Banc."""
import json
from dataclasses import dataclass

from .formats import byml
from .formats.zs import ZsCodec


@dataclass(frozen=True)
class ChestActor:
    banc: str
    hash: int
    gyaml: str
    drop: str
    event: str | None
    pos: tuple[float, float, float]


@dataclass(frozen=True)
class SkulltulaActor:
    banc: str
    hash: int
    # Claves de Dynamic cuyo valor es verdadero, ordenadas.
    flags: tuple[str, ...]
    pos: tuple[float, float, float]


SKULLTULA_GYAML = 'Enemy_Skulltula_Gold'


def load_chests_fixture(path) -> list[ChestActor]:
    with open(path, encoding='utf-8') as f:
        rows = json.load(f)
    return [ChestActor(r['banc'], int(r['hash']), r['gyaml'], r['drop'],
                       r['event'], tuple(r['pos'])) for r in rows]


def chests_to_json(chests) -> list[dict]:
    return [{'banc': c.banc, 'hash': str(c.hash), 'gyaml': c.gyaml,
             'drop': c.drop, 'event': c.event, 'pos': list(c.pos)}
            for c in chests]


def load_skulltulas_fixture(path) -> list[SkulltulaActor]:
    with open(path, encoding='utf-8') as f:
        rows = json.load(f)
    return [SkulltulaActor(r['banc'], int(r['hash']), tuple(r['flags']),
                           tuple(r['pos'])) for r in rows]


def skulltulas_to_json(skulltulas) -> list[dict]:
    return [{'banc': s.banc, 'hash': str(s.hash), 'flags': list(s.flags),
             'pos': list(s.pos)} for s in skulltulas]


class GameData:
    def __init__(self, nup):
        self.nup = nup
        self.codec = ZsCodec.from_archive(nup)
        self._chests = None
        self._skulltulas = None

    def load_banc(self, path: str) -> tuple[int, dict]:
        raw = self.codec.decompress(path, self.nup.read(path))
        return byml.load(raw)

    def chests(self) -> list[ChestActor]:
        if self._chests is None:
            out = []
            for path, a in self._banc_actors():
                if 'TBox' not in str(a.get('Gyaml', '')):
                    continue
                dyn = a.get('Dynamic')
                if not isinstance(dyn, dict) or 'Drop__DropActor' not in dyn:
                    continue
                pos = a.get('Translate') or (0.0, 0.0, 0.0)
                out.append(ChestActor(
                    path, int(a['Hash']), a['Gyaml'], dyn['Drop__DropActor'],
                    dyn.get('GetEventName'), tuple(float(x) for x in pos)))
            out.sort(key=lambda c: (c.banc, c.hash))
            self._chests = out
        return list(self._chests)

    def _banc_actors(self):
        for path in self.nup.list('Banc/'):
            if not path.endswith('.bcett.byml.zs'):
                continue
            _ver, root = self.load_banc(path)
            actors = root.get('Actors') if isinstance(root, dict) else None
            for a in actors or []:
                if isinstance(a, dict):
                    yield path, a

    def skulltulas(self) -> list[SkulltulaActor]:
        if self._skulltulas is None:
            out = []
            for path, a in self._banc_actors():
                if a.get('Gyaml') != SKULLTULA_GYAML:
                    continue
                dyn = a.get('Dynamic')
                flags = tuple(sorted(k for k, v in dyn.items() if v))                     if isinstance(dyn, dict) else ()
                pos = a.get('Translate') or (0.0, 0.0, 0.0)
                out.append(SkulltulaActor(path, int(a['Hash']), flags,
                                          tuple(float(x) for x in pos)))
            out.sort(key=lambda s: (s.banc, s.hash))
            self._skulltulas = out
        return list(self._skulltulas)
