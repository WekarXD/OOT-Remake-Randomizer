"""Item wrappers for the Gold Skulltulas.

A wrapper is a clone of Obj_Token_Gold that carries the identity of other
content: a new actor pack plus a row in three RSDB tables and in the RSTB.
"""
import copy
from collections.abc import Iterable

from .formats import byml, sarc
from .formats.rstb import Rstb

WRAPPER_PREFIX = 'Obj_Rando_'
TOKEN = 'Obj_Token_Gold'
RSDB_TABLES = ('ActorInfo', 'GameActorInfo', 'PouchActorInfo')
ITEM_REFS = ('ActorNameRef', 'ModelInfoRef', 'AnimationRef', 'PouchContentRef',
             'GameParameterTableRef')
ACTOR_INFO_COPY = ('FmdbName', 'ModelProjectName', 'AnimationResources',
                   'ModelAabbMax', 'ModelAabbMin')
HEAP_KEYS = ('InstanceHeapSize', 'PreActorRenderInfoHeapSize')


def _table_path(t: str) -> str:
    return f'RSDB/{t}.Product.111.rstbl.byml.zs'


def _pack_path(name: str) -> str:
    return f'Pack/Actor/{name}.pack.zs'


def _ap_path(name: str) -> str:
    return f'Actor/{name}.engine__actor__ActorParam.bgyml'


def _load_table(game, t: str):
    p = _table_path(t)
    raw = game.codec.decompress(p, game.nup.read(p))
    ver, rows = byml.load(raw)
    return len(raw), ver, rows


def _load_pack(game, name: str) -> dict:
    p = _pack_path(name)
    return sarc.read(game.codec.decompress(p, game.nup.read(p)))


def pouch_rows(game) -> frozenset:
    return frozenset(r['__RowId'] for r in _load_table(game, 'PouchActorInfo')[2])


def drop_actor(content: str, rows: frozenset) -> str:
    """Actor dropped in the world for a chest content."""
    if content.startswith('Obj_') and content in rows:
        return content
    for prefix in ('TBox_', 'Tbox_'):
        if content.startswith(prefix) and 'Obj_' + content[len(prefix):] in rows:
            return 'Obj_' + content[len(prefix):]
    return WRAPPER_PREFIX + content


def can_wrap(game, content: str) -> bool:
    if not game.nup.has(_pack_path(content)):
        return False
    try:
        pack = _load_pack(game, content)
        _v, ap = byml.load(pack[_ap_path(content)])
        comp = ap['Components']
        if not all(k in comp for k in ITEM_REFS):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    if content not in pouch_rows(game):
        return False
    if not any(r['__RowId'] == content for r in _load_table(game, 'GameActorInfo')[2]):
        return False
    return any(r['__RowId'] == content for r in _load_table(game, 'ActorInfo')[2])


def _clone_pack(game, token_pack: dict, content: str) -> bytes:
    new = WRAPPER_PREFIX + content
    files = dict(token_pack)
    tver, tap = byml.load(files.pop(_ap_path(TOKEN)))
    cpack = _load_pack(game, content)
    _cver, cap = byml.load(cpack[_ap_path(content)])
    comp = tap['Components']
    for k in ITEM_REFS:
        comp[k] = cap['Components'][k]
    for k, v in cpack.items():
        if not k.startswith('Actor/') and k not in files:
            files[k] = v
    pver, pc = byml.load(cpack[comp['PouchContentRef'].lstrip('?')])
    pc['DefaultAutoGet'] = True
    ppath = f'Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml'
    files[ppath] = byml.dump(pc, pver)
    comp['PouchContentRef'] = '?' + ppath
    files[_ap_path(new)] = byml.dump(tap, tver)
    return sarc.write(files, 8, 0x20)


def build_wrapper_files(game, contents: Iterable[str], rstb: Rstb) -> dict:
    """Generate the wrapper packs and RSDB tables; modifies `rstb`."""
    rows = pouch_rows(game)
    needed = sorted({c for c in contents
                     if drop_actor(c, rows).startswith(WRAPPER_PREFIX)})
    if not needed:
        return {}
    for c in needed:
        if not can_wrap(game, c):
            raise ValueError(f'Cannot create a wrapper for {c}')
    out = {}
    token_pack = _load_pack(game, TOKEN)
    for c in needed:
        raw = _clone_pack(game, token_pack, c)
        p = _pack_path(WRAPPER_PREFIX + c)
        out[p] = game.codec.compress(p, raw)
        rstb.add(p[:-3], len(raw) + 0x1000)
    for t in RSDB_TABLES:
        orig_len, ver, table = _load_table(game, t)
        by = {r['__RowId']: r for r in table}
        for c in needed:
            new = WRAPPER_PREFIX + c
            crow = by[c]
            if t == 'PouchActorInfo':
                row = copy.deepcopy(crow)
            else:
                row = copy.deepcopy(by[TOKEN])
                if t == 'ActorInfo':
                    row['ActorName'] = crow.get('ActorName', c)
                    for k in ACTOR_INFO_COPY:
                        if k in crow:
                            row[k] = copy.deepcopy(crow[k])
                    for k in HEAP_KEYS:
                        row[k] = max(by[TOKEN].get(k, 0), crow.get(k, 0)) + 0x10000
                elif 'ModelVariationAnims' in crow:
                    row['ModelVariationAnims'] = copy.deepcopy(crow['ModelVariationAnims'])
            row['__RowId'] = new
            table.append(row)
        table.sort(key=lambda r: r['__RowId'])
        raw = byml.dump(table, ver)
        p = _table_path(t)
        rstb.set(p[:-3], len(raw) + (rstb.get(p[:-3]) - orig_len) + 0x1000)
        out[p] = game.codec.compress(p, raw)
    return dict(sorted(out.items()))
