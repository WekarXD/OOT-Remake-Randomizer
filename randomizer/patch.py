"""Escritura del mod: reescribe los mapas Banc con los cofres cambiados."""
from pathlib import Path

from . import locations
from .formats import byml
from .formats.rstb import Rstb, banc_rstb_size
from .game import GameData

RSTB_PATH = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs'


def _write(mod_root: Path, rel: str, data: bytes) -> None:
    p = Path(mod_root) / 'romfs' / Path(*rel.split('/'))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def write_mod(game: GameData, placement: dict[int, str], mod_root: Path) -> list[str]:
    chests = game.chests()
    original = {c.hash: c.drop for c in chests}
    changed = {h for h, d in placement.items() if original.get(h) != d}
    loc_map = locations.load_map()
    # Sitios cambiados que pierden su GetEventName (evento que solo entrega
    # el objeto original). Nunca se toca el evento de otros cofres.
    strip = {h for h in changed if h in loc_map and loc_map[h].strip_event}
    bancs = sorted({c.banc for c in chests if c.hash in changed})
    if not bancs:
        return []

    rs_raw = game.codec.decompress(RSTB_PATH, game.nup.read(RSTB_PATH))
    rstb = Rstb.load(rs_raw)
    written = []
    for path in bancs:
        ver, root = game.load_banc(path)
        for a in root['Actors']:
            if not isinstance(a, dict):
                continue
            h = a.get('Hash')
            dyn = a.get('Dynamic')
            if h in changed and isinstance(dyn, dict) and 'Drop__DropActor' in dyn:
                dyn['Drop__DropActor'] = placement[h]
                if h in strip:
                    dyn.pop('GetEventName', None)
        raw = byml.dump(root, ver)
        _write(mod_root, path, game.codec.compress(path, raw))
        rstb.set(path[:-3], banc_rstb_size(len(raw)))
        written.append(path)
    _write(mod_root, RSTB_PATH, game.codec.compress(RSTB_PATH, rstb.dump()))
    written.append(RSTB_PATH)
    return sorted(written)
