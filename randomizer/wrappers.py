"""Item wrappers for the Gold Skulltulas.

A wrapper is a clone of Obj_Token_Gold that carries the identity of other
content: a new actor pack plus a row in three RSDB tables and in the RSTB.
It floats where the Skulltula died and is picked up by walking over it, like
the token itself.

The identity comes from a *source* actor: the content itself when it is a
complete actor (key items such as `Item_Hookshot`), or otherwise the game's
own world actor for that content (`TBox_Rupee_Purple` -> `Obj_Rupee_Purple`).
The source's components may be inherited through its `$parent` chain.
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


def vanilla_drop(content: str, rows: frozenset) -> str | None:
    """The game's own world actor for a chest content (it falls to the
    floor when dropped), or None if there is none."""
    if content.startswith('Obj_') and content in rows:
        return content
    for prefix in ('TBox_', 'Tbox_'):
        if content.startswith(prefix) and 'Obj_' + content[len(prefix):] in rows:
            return 'Obj_' + content[len(prefix):]
    return None


def drop_actor(content: str, wrappable: frozenset, rows: frozenset) -> str:
    """Actor a Skulltula drops for `content`: its floating wrapper when one
    can be built (`wrappable`), otherwise the game's own world actor."""
    if content in wrappable:
        return WRAPPER_PREFIX + content
    actor = vanilla_drop(content, rows)
    if actor is None:
        raise ValueError(f'No actor can drop {content}')
    return actor


def _resolved_refs(pack: dict, name: str) -> dict[str, str]:
    """The ITEM_REFS of actor `name`, following its `$parent` chain inside
    its own pack. Empty or missing references are left out."""
    refs: dict[str, str] = {}
    current, seen = name, set()
    while current not in seen and _ap_path(current) in pack:
        seen.add(current)
        _v, ap = byml.load(pack[_ap_path(current)])
        comp = ap.get('Components') or {}
        for k in ITEM_REFS:
            if k not in refs and comp.get(k):
                refs[k] = comp[k]
        parent = ap.get('$parent') or ''
        current = parent.rsplit('/', 1)[-1].split('.', 1)[0]
    return refs


class _Tables:
    """RSDB row ids, loaded once per batch of checks."""

    def __init__(self, game):
        self.ids = {t: frozenset(r['__RowId'] for r in _load_table(game, t)[2])
                    for t in RSDB_TABLES}


def _wrappable(game, actor: str, tables: _Tables) -> bool:
    if not all(actor in tables.ids[t] for t in RSDB_TABLES):
        return False
    if not game.nup.has(_pack_path(actor)):
        return False
    try:
        pack = _load_pack(game, actor)
        refs = _resolved_refs(pack, actor)
    except (KeyError, TypeError, ValueError):
        return False
    return (all(k in refs for k in ITEM_REFS)
            and refs['PouchContentRef'].lstrip('?') in pack)


def wrap_source(game, content: str, tables: _Tables | None = None) -> str | None:
    """The actor whose identity a wrapper for `content` carries, or None
    if no wrapper can be built."""
    tables = tables or _Tables(game)
    candidates = [content]
    vanilla = vanilla_drop(content, tables.ids['PouchActorInfo'])
    if vanilla and vanilla != content:
        candidates.append(vanilla)
    for actor in candidates:
        if _wrappable(game, actor, tables):
            return actor
    return None


def wrap_sources(game, contents: Iterable[str]) -> dict[str, str]:
    """Content -> source actor, for the contents that can be wrapped."""
    tables = _Tables(game)
    out = {}
    for c in sorted(set(contents)):
        if c == TOKEN:
            continue
        source = wrap_source(game, c, tables)
        if source is not None:
            out[c] = source
    return out


def can_wrap(game, content: str) -> bool:
    return wrap_source(game, content) is not None


def _clone_pack(game, token_pack: dict, content: str, source: str) -> bytes:
    new = WRAPPER_PREFIX + content
    files = dict(token_pack)
    tver, tap = byml.load(files.pop(_ap_path(TOKEN)))
    spack = _load_pack(game, source)
    refs = _resolved_refs(spack, source)
    comp = tap['Components']
    for k in ITEM_REFS:
        comp[k] = refs[k]
    for k, v in spack.items():
        if not k.startswith('Actor/') and k not in files:
            files[k] = v
    pver, pc = byml.load(spack[comp['PouchContentRef'].lstrip('?')])
    pc['DefaultAutoGet'] = True
    ppath = f'Component/PouchContentParam/{new}.game__component__PouchContentParam.bgyml'
    files[ppath] = byml.dump(pc, pver)
    comp['PouchContentRef'] = '?' + ppath
    files[_ap_path(new)] = byml.dump(tap, tver)
    return sarc.write(files, 8, 0x20)


def build_wrapper_files(game, sources: dict[str, str], rstb: Rstb) -> dict:
    """Generate the wrapper packs and RSDB tables for `sources` (content ->
    source actor, see `wrap_sources`); modifies `rstb`."""
    needed = sorted(sources)
    if not needed:
        return {}
    out = {}
    token_pack = _load_pack(game, TOKEN)
    for c in needed:
        raw = _clone_pack(game, token_pack, c, sources[c])
        p = _pack_path(WRAPPER_PREFIX + c)
        out[p] = game.codec.compress(p, raw)
        rstb.add(p[:-3], len(raw) + 0x1000)
    for t in RSDB_TABLES:
        orig_len, ver, table = _load_table(game, t)
        by = {r['__RowId']: r for r in table}
        for c in needed:
            new = WRAPPER_PREFIX + c
            source = sources[c]
            crow = by[source]
            if t == 'PouchActorInfo':
                row = copy.deepcopy(crow)
            else:
                row = copy.deepcopy(by[TOKEN])
                if t == 'ActorInfo':
                    row['ActorName'] = crow.get('ActorName', source)
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
