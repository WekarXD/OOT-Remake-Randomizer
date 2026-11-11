"""Escritura del mod: reescribe los mapas Banc con los cofres cambiados."""
from pathlib import Path

from .formats import byml
from .formats.rstb import Rstb, banc_rstb_size
from .game import GameData
from .locations import LocationEntry
from .wrappers import TOKEN, build_wrapper_files, drop_actor, pouch_rows

RSTB_PATH = 'System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs'


def _write(mod_root: Path, rel: str, data: bytes) -> None:
    p = Path(mod_root) / 'romfs' / Path(*rel.split('/'))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def write_mod(game: GameData, placement: dict[int, str], mod_root: Path,
              loc_map: dict[int, LocationEntry],
              extra_files: dict[str, bytes] | None = None) -> list[str]:
    chests = game.chests()
    original = {c.hash: c.drop for c in chests}
    changed = {h for h, d in placement.items() if original.get(h) != d}
    # Skulltulas cuyo contenido no es la ficha vanilla: reciben un drop.
    # Solo se escanean si el reparto trae algún Hash que no es de cofre.
    skulls = game.skulltulas() if any(h not in original for h in placement) else []
    sk_hashes = {s.hash for s in skulls}
    sk_changed = {h: c for h, c in placement.items()
                  if h in sk_hashes and c != TOKEN}
    changed -= sk_hashes
    # Sitios cambiados que pierden su GetEventName (evento que solo entrega
    # el objeto original). Nunca se toca el evento de otros cofres.
    strip = {h for h in changed if h in loc_map and loc_map[h].strip_event}
    bancs = sorted({c.banc for c in chests if c.hash in changed}
                   | {s.banc for s in skulls if s.hash in sk_changed})
    written = []
    for rel, data in (extra_files or {}).items():
        _write(mod_root, rel, data)
        written.append(rel)
    if not bancs:
        return sorted(written)

    rs_raw = game.codec.decompress(RSTB_PATH, game.nup.read(RSTB_PATH))
    rstb = Rstb.load(rs_raw)
    rows = pouch_rows(game) if sk_changed else None
    for path in bancs:
        ver, root = game.load_banc(path)
        for a in root['Actors']:
            if not isinstance(a, dict):
                continue
            h = a.get('Hash')
            dyn = a.get('Dynamic')
            if h in sk_changed:
                if not isinstance(dyn, dict):
                    dyn = a['Dynamic'] = {}
                dyn['Drop__DropActor'] = drop_actor(sk_changed[h], rows)
                continue
            if h in changed and isinstance(dyn, dict) and 'Drop__DropActor' in dyn:
                dyn['Drop__DropActor'] = placement[h]
                if h in strip:
                    dyn.pop('GetEventName', None)
        raw = byml.dump(root, ver)
        _write(mod_root, path, game.codec.compress(path, raw))
        rstb.set(path[:-3], banc_rstb_size(len(raw)))
        written.append(path)
    if sk_changed:
        wrappers = build_wrapper_files(game, sk_changed.values(), rstb)
        for rel, data in wrappers.items():
            _write(mod_root, rel, data)
            written.append(rel)
    _write(mod_root, RSTB_PATH, game.codec.compress(RSTB_PATH, rstb.dump()))
    written.append(RSTB_PATH)
    return sorted(written)
