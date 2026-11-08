"""Compilador de reglas de OoTR (cadenas de los World/*.json) a funciones Python.

Reproduce la semántica de `RuleParser.py` de OoTR (solo como referencia; no se
importa ni ejecuta código de OoTR): la regla se parsea con
`ast.parse(text, mode='eval')`, se expanden los alias de `LogicHelpers.json`
(con sustitución textual de parámetros, como OoTR), los ajustes se pliegan
como constantes en tiempo de compilación y el resultado es
`fn(state, age) -> bool`, con `age` en ('child', 'adult').

Diferencias con OoTR (todas en dirección conservadora o indiferentes en vanilla):

- Todo identificador desconocido lanza `RuleError` al compilar. OoTR trata
  cualquier nombre en mayúscula desconocido como un evento; aquí un evento
  solo es válido si lo define algún `"events"` de los World/*.json (o es un
  subevento de `here()`/`at()`).
- `at_day`, `at_night`, `at_dampe_time`: verdaderos para una edad si esa edad
  ha alcanzado alguna región con `"time_passes": true` (`state.tod`). OoTR sin
  barajado de entradas los trata como `True` constante, así que esto es más
  estricto. `provides_time` (salas de jefes, tumba de Dampé) se ignora.
- `has_all_notes_for_song(song)`: no tenemos las notas de las canciones; exige
  los cinco botones de ocarina (más estricto). Con
  `shuffle_individual_ocarina_notes = false` la llamada se pliega y no aparece.
- `has_soul(x)` es siempre verdadero (igual que OoTR).
- `region_has_shortcuts(r)` se resuelve al compilar con `dungeon_shortcuts`.
- Objetos progresivos con nivel en `items.ITEM_LEVEL` (gancho y fuerza),
  modelo "directo" del remake: `items[nombre]` guarda el nivel máximo. El
  objeto OoTR genérico (`'Progressive Hookshot'`, `'Progressive Strength
  Upgrade'`, p. ej. el brazalete Goron vanilla) cuenta como nivel 1 y nunca
  sube de nivel a lo ya conseguido (OoTR sumaría; esto nunca da más).
"""
from __future__ import annotations

import ast
import json
import operator
import re
from collections import Counter
from collections.abc import Callable
from functools import lru_cache
from typing import Any

from randomizer import items as remake_items
from randomizer.logic import ootr_data


class RuleError(Exception):
    """Regla de OoTR que no se puede compilar."""


AGES = ('child', 'adult')

_ESCAPE = re.compile(r"['()\[\]-]")


def escape_name(name: str) -> str:
    """Igual que `RulesCommon.escape_name` de OoTR."""
    return _ESCAPE.sub('', name.replace(' ', '_'))


def _load_item_table() -> dict[str, dict]:
    path = ootr_data.DATA_DIR / 'items.json'
    return json.loads(path.read_text(encoding='utf-8'))


ITEM_TABLE: dict[str, dict] = _load_item_table()
ESCAPED_ITEMS: dict[str, str] = {escape_name(n): n for n in ITEM_TABLE}
BOTTLES = tuple(sorted(n for n, e in ITEM_TABLE.items() if e.get('bottle')))
MEDALLIONS = tuple(sorted(n for n, e in ITEM_TABLE.items() if e.get('medallion')))
STONES = tuple(sorted(n for n, e in ITEM_TABLE.items() if e.get('stone')))
OCARINA_BUTTONS = tuple(sorted(n for n, e in ITEM_TABLE.items() if e.get('ocarina_button')))
ALIASES: dict[str, tuple[str, int]] = {
    n: (e['alias'][0], e['alias'][1]) for n, e in ITEM_TABLE.items() if 'alias' in e}
# Objetos progresivos con nivel en el remake (modelo directo).
LEVELED: frozenset[str] = frozenset(name for name, _ in remake_items.ITEM_LEVEL.values())


@lru_cache(maxsize=1)
def world_event_names() -> frozenset[str]:
    names = set()
    for regions in ootr_data.load_world_files().values():
        for region in regions:
            names.update((region.get('events') or {}).keys())
    return frozenset(names)


@lru_cache(maxsize=1)
def region_dungeons() -> dict[str, str | None]:
    return {r['region_name']: r.get('dungeon')
            for regions in ootr_data.load_world_files().values() for r in regions}


class State:
    """Objetos y eventos conseguidos (compartidos por niño y adulto)."""

    __slots__ = ('items', 'events', 'tod')

    def __init__(self) -> None:
        self.items: Counter[str] = Counter()
        self.events: set[str] = set()
        # Edades que han alcanzado una región donde pasa el tiempo.
        self.tod: set[str] = set()

    def has(self, item: str, n: int = 1) -> bool:
        return self.items[item] >= n or (n <= 1 and item in self.events)

    def collect(self, item: str) -> None:
        """Recoge un objeto OoTR o un actor del remake de `items.KEY_ITEMS`."""
        if item in remake_items.ITEM_LEVEL:
            name, level = remake_items.ITEM_LEVEL[item]
            if self.items[name] < level:
                self.items[name] = level
            return
        if item in remake_items.KEY_ITEMS:
            item = remake_items.KEY_ITEMS[item]
        elif item not in ITEM_TABLE:
            raise KeyError(f'unknown item {item!r}')
        if item in LEVELED:
            if self.items[item] < 1:
                self.items[item] = 1
            return
        alias = ALIASES.get(item)
        if alias:
            self.items[alias[0]] += alias[1]
        self.items[item] += 1

    # Funciones de estado usadas por las reglas (equivalentes a State.py).
    def has_bottle(self) -> bool:
        return any(self.has(b) for b in BOTTLES) or self.items['Rutos Letter'] >= 2

    def heart_count(self) -> int:
        return self.items['Piece of Heart'] // 4 + 3

    def count_distinct(self, names: tuple[str, ...]) -> int:
        return sum(1 for n in names if self.has(n))


def _true(state: State, age: str) -> bool:
    return True


def _false(state: State, age: str) -> bool:
    return False


_CMP_OPS = {
    ast.Eq: ('==', operator.eq), ast.NotEq: ('!=', operator.ne),
    ast.Lt: ('<', operator.lt), ast.LtE: ('<=', operator.le),
    ast.Gt: ('>', operator.gt), ast.GtE: ('>=', operator.ge),
    ast.In: ('in', lambda a, b: a in b), ast.NotIn: ('not in', lambda a, b: a not in b),
}

_DAMAGE_THRESHOLD = {'ohko': 0, 'quadruple': 0.75, 'double': 1.5, 'normal': 3, 'half': 6}
_NIGHT_STARTS = ('sunset', 'evening', 'midnight', 'witching-hour')
_TOD_NAMES = ('at_day', 'at_night', 'at_dampe_time')
_MAX_DEPTH = 64


class _Const:
    __slots__ = ('value',)

    def __init__(self, value: Any) -> None:
        self.value = value


class Compiler:
    """Compila reglas compartiendo caché, alias y subeventos de here()/at()."""

    def __init__(self, helpers: dict[str, str], settings: dict,
                 events: frozenset[str] | set[str] | None = None) -> None:
        self.settings = settings
        self.aliases: dict[str, tuple[list[re.Pattern[str]], str]] = {}
        for key, repl in helpers.items():
            if '(' in key:
                name, args = key[:-1].split('(', 1)
                params = [re.compile(rf'\b{a.strip()}\b') for a in args.split(',')]
            else:
                name, params = key, []
            self.aliases[name] = (params, repl)
        known = world_event_names() if events is None else events
        self.escaped_events: dict[str, str] = {escape_name(e): e for e in known}
        self.event_names: frozenset[str] = frozenset(known)
        self.cache: dict[str, Callable[[State, str], bool]] = {}
        # Nombres de objeto OoTR que alguna regla consulta.
        self.referenced: set[str] = set()
        self._subrule_keys: dict[tuple[str, str], str] = {}
        self._subrule_count: Counter[str] = Counter()
        self._pending: list[tuple[str, ast.expr, str]] = []
        # (región, evento, regla) de los subeventos ya compilados.
        self.subrules: list[tuple[str, str, Callable[[State, str], bool]]] = []
        self._region: str | None = None
        self._depth = 0

    # ---- API -------------------------------------------------------------
    def compile(self, text: str, region: str | None = None) -> Callable[[State, str], bool]:
        text = text.split('#', 1)[0].strip()
        try:
            tree = ast.parse(text, mode='eval')
        except SyntaxError as e:
            raise RuleError(f'syntax error in rule {text!r}: {e}') from e
        return self._compile_node(tree.body, region, text)

    def compile_pending_subrules(self) -> None:
        while self._pending:
            region, node, name = self._pending.pop(0)
            fn = self._compile_node(node, region, ast.unparse(node))
            self.subrules.append((region, name, fn))

    # ---- internals -------------------------------------------------------
    def _compile_node(self, node: ast.expr, region: str | None, text: str):
        self._region = region
        self._depth = 0
        try:
            out = self._bool(self.visit(node))
        except RuleError as e:
            raise RuleError(f'{e} (rule: {text!r}, region: {region!r})') from None
        if isinstance(out, _Const):
            return _true if out.value else _false
        fn = self.cache.get(out)
        if fn is None:
            fn = eval(compile(f'lambda state, age: {out}', '<rule>', 'eval'),
                      {'__builtins__': {}})
            self.cache[out] = fn
        return fn

    @staticmethod
    def _bool(expr):
        if isinstance(expr, _Const):
            return _Const(bool(expr.value))
        return expr

    def visit(self, node: ast.AST):
        self._depth += 1
        if self._depth > _MAX_DEPTH * 8:
            raise RuleError('rule expansion too deep (recursive alias?)')
        method = getattr(self, 'visit_' + type(node).__name__, None)
        if method is None:
            raise RuleError(f'unsupported syntax {type(node).__name__}')
        try:
            return method(node)
        finally:
            self._depth -= 1

    def _has_code(self, name: str, count: int = 1):
        """Código que comprueba un objeto o evento por su nombre OoTR."""
        if count <= 0:
            return _Const(True)
        parts = []
        if name in ITEM_TABLE:
            self.referenced.add(name)
            parts.append(f'state.items[{name!r}] >= {count}')
        if name in self.event_names and count <= 1:
            parts.append(f'{name!r} in state.events')
        if not parts:
            raise RuleError(f'unknown item or event {name!r}')
        return parts[0] if len(parts) == 1 else '(' + ' or '.join(parts) + ')'

    def _lookup_item_or_event(self, ident: str) -> str | None:
        if ident in ESCAPED_ITEMS:
            return ESCAPED_ITEMS[ident]
        if ident in self.escaped_events:
            return self.escaped_events[ident]
        return None

    def _expand_alias(self, name: str, args: list[ast.expr]):
        params, repl = self.aliases[name]
        if len(params) != len(args):
            raise RuleError(f'expected {len(params)} args for {name}, not {len(args)}')
        for pattern, arg in zip(params, args):
            if isinstance(arg, ast.Name):
                val = arg.id
            elif isinstance(arg, ast.Constant):
                val = repr(arg.value)
            else:
                raise RuleError(f'invalid argument {ast.dump(arg)} for {name}')
            repl = pattern.sub(val, repl)
        try:
            body = ast.parse(repl.strip(), mode='eval').body
        except SyntaxError as e:
            raise RuleError(f'syntax error in helper {name}: {e}') from e
        return self.visit(body)

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, str):
            name = self._lookup_item_or_event(escape_name(node.value))
            if name is None:
                raise RuleError(f'unknown item or event {node.value!r}')
            return self._has_code(name)
        return _Const(node.value)

    def visit_Name(self, node: ast.Name):
        ident = node.id
        if ident in _TOD_NAMES:
            return '(age in state.tod)'
        if ident in self.aliases:
            return self._expand_alias(ident, [])
        if ident in ESCAPED_ITEMS:
            return self._has_code(ESCAPED_ITEMS[ident])
        if ident in self.settings:
            return _Const(self.settings[ident])
        if ident == 'has_bottle':
            self.referenced.update(BOTTLES)
            self.referenced.add('Rutos Letter')
            return 'state.has_bottle()'
        if ident == 'had_night_start':
            return _Const(self.settings.get('starting_tod') in _NIGHT_STARTS)
        if ident == 'age':
            return 'age'
        if ident in self.escaped_events:
            return self._has_code(self.escaped_events[ident])
        raise RuleError(f'unknown identifier {ident!r}')

    def visit_Tuple(self, node: ast.Tuple):
        if len(node.elts) != 2:
            raise RuleError('tuple must have 2 values')
        return self._count_check(*node.elts)

    def _count_check(self, item: ast.expr, count: ast.expr):
        if isinstance(item, ast.Name):
            name = self._lookup_item_or_event(item.id)
        elif isinstance(item, ast.Constant) and isinstance(item.value, str):
            name = self._lookup_item_or_event(escape_name(item.value))
        else:
            raise RuleError('first tuple value must be an item')
        if name is None:
            raise RuleError(f'unknown item or event in count check: {ast.unparse(item)}')
        if isinstance(count, ast.Constant) and isinstance(count.value, int):
            n = count.value
        elif isinstance(count, ast.Name) and count.id in self.settings:
            n = self.settings[count.id]
        else:
            raise RuleError(f'second tuple value must be a number: {ast.unparse(count)}')
        if not isinstance(n, int) or isinstance(n, bool):
            raise RuleError(f'count must be an int, got {n!r}')
        return self._has_code(name, n)

    def visit_Subscript(self, node: ast.Subscript):
        if not isinstance(node.value, ast.Name) or node.value.id not in self.settings:
            raise RuleError(f'unknown subscript {ast.unparse(node)}')
        key = node.slice
        if isinstance(key, ast.Name):
            key = key.id.replace('_', ' ')
        elif isinstance(key, ast.Constant):
            key = key.value
        else:
            raise RuleError(f'unsupported subscript {ast.unparse(node)}')
        try:
            return _Const(self.settings[node.value.id][key])
        except (KeyError, TypeError) as e:
            raise RuleError(f'bad subscript {ast.unparse(node)}') from e

    def visit_BoolOp(self, node: ast.BoolOp):
        is_or = isinstance(node.op, ast.Or)
        parts = []
        for value in node.values:
            out = self._bool(self.visit(value))
            if isinstance(out, _Const):
                if out.value == is_or:
                    return _Const(is_or)
                continue
            parts.append(out)
        if not parts:
            return _Const(not is_or)
        if len(parts) == 1:
            return parts[0]
        return '(' + (' or ' if is_or else ' and ').join(parts) + ')'

    def visit_UnaryOp(self, node: ast.UnaryOp):
        if not isinstance(node.op, ast.Not):
            if isinstance(node.operand, ast.Constant):
                return _Const(ast.literal_eval(node))
            raise RuleError(f'unsupported unary op {ast.unparse(node)}')
        out = self._bool(self.visit(node.operand))
        if isinstance(out, _Const):
            return _Const(not out.value)
        return f'(not {out})'

    def _cmp_operand(self, node: ast.expr):
        if isinstance(node, ast.Name) and node.id in ESCAPED_ITEMS:
            return _Const(ESCAPED_ITEMS[node.id])
        if isinstance(node, ast.Constant):
            return _Const(node.value)
        return self.visit(node)

    def visit_Compare(self, node: ast.Compare):
        if len(node.ops) != 1:
            raise RuleError(f'chained comparison not supported: {ast.unparse(node)}')
        op_type = type(node.ops[0])
        if op_type not in _CMP_OPS:
            raise RuleError(f'unsupported comparison {ast.unparse(node)}')
        left, right = node.left, node.comparators[0]
        # Atajo de OoTR para can_use(): `item == Bow` con dos nombres que no
        # son ajustes se decide comparando los identificadores.
        if (op_type in (ast.Eq, ast.NotEq) and isinstance(left, ast.Name)
                and isinstance(right, ast.Name) and left.id not in self.settings
                and right.id not in self.settings):
            same = left.id == right.id
            return _Const(same if op_type is ast.Eq else not same)
        lhs, rhs = self._cmp_operand(left), self._cmp_operand(right)
        symbol, func = _CMP_OPS[op_type]
        if isinstance(lhs, _Const) and isinstance(rhs, _Const):
            try:
                return _Const(func(lhs.value, rhs.value))
            except TypeError as e:
                raise RuleError(f'bad comparison {ast.unparse(node)}: {e}') from e
        lcode = repr(lhs.value) if isinstance(lhs, _Const) else lhs
        rcode = repr(rhs.value) if isinstance(rhs, _Const) else rhs
        return f'({lcode} {symbol} {rcode})'

    def visit_BinOp(self, node: ast.BinOp):
        try:
            return _Const(ast.literal_eval(node))
        except ValueError:
            raise RuleError(f'unsupported expression {ast.unparse(node)}') from None

    # ---- llamadas --------------------------------------------------------
    def _call_args(self, node: ast.Call) -> list:
        """Argumentos de una función de estado, resueltos como OoTR."""
        out = []
        for arg in node.args:
            if isinstance(arg, ast.Name):
                if arg.id in self.settings:
                    out.append(self.settings[arg.id])
                elif arg.id in self.aliases:
                    raise RuleError(f'alias {arg.id} used as a function argument')
                elif arg.id in ESCAPED_ITEMS:
                    out.append(ESCAPED_ITEMS[arg.id])
                else:
                    out.append(arg.id.replace('_', ' '))
            elif isinstance(arg, ast.Constant):
                out.append(arg.value)
            else:
                raise RuleError(f'unsupported argument {ast.unparse(arg)}')
        return out

    def visit_Call(self, node: ast.Call):
        if not isinstance(node.func, ast.Name) or node.keywords:
            raise RuleError(f'unsupported call {ast.unparse(node)}')
        fname = node.func.id
        if fname == 'here':
            if len(node.args) != 1 or self._region is None:
                raise RuleError('here() needs one argument and a region')
            return self._subrule(self._region, node.args[0])
        if fname == 'at':
            if (len(node.args) != 2 or not isinstance(node.args[0], ast.Constant)
                    or not isinstance(node.args[0].value, str)):
                raise RuleError('invalid at() arguments')
            return self._subrule(node.args[0].value, node.args[1])
        if fname == 'has':
            if len(node.args) == 1:
                return self._count_check(node.args[0], ast.Constant(1))
            if len(node.args) == 2:
                return self._count_check(*node.args)
            raise RuleError('has() takes 1 or 2 arguments')
        if fname in self.aliases:
            return self._expand_alias(fname, node.args)
        if fname in _TOD_NAMES:
            return '(age in state.tod)'
        args = self._call_args(node)
        handler = getattr(self, '_fn_' + fname, None)
        if handler is None:
            raise RuleError(f'unknown function {fname!r}')
        try:
            return handler(*args)
        except TypeError as e:
            raise RuleError(f'bad arguments for {fname}: {e}') from None

    def _subrule(self, region: str, node: ast.expr):
        key = (region, ast.dump(node))
        name = self._subrule_keys.get(key)
        if name is None:
            self._subrule_count[region] += 1
            name = f'{region} Subrule {self._subrule_count[region]}'
            self._subrule_keys[key] = name
            self._pending.append((region, node, name))
        return f'({name!r} in state.events)'

    @staticmethod
    def _int_arg(n) -> int:
        if not isinstance(n, int) or isinstance(n, bool):
            raise RuleError(f'expected an int, got {n!r}')
        return n

    def _fn_has_bottle(self):
        return self.visit_Name(ast.Name('has_bottle'))

    def _fn_had_night_start(self):
        return self.visit_Name(ast.Name('had_night_start'))

    def _fn_has_hearts(self, n):
        self.referenced.add('Piece of Heart')
        return f'(state.heart_count() >= {self._int_arg(n)})'

    def _distinct(self, names: tuple[str, ...], n):
        self.referenced.update(names)
        return f'(state.count_distinct({names!r}) >= {self._int_arg(n)})'

    def _fn_has_medallions(self, n):
        return self._distinct(MEDALLIONS, n)

    def _fn_has_stones(self, n):
        return self._distinct(STONES, n)

    def _fn_has_dungeon_rewards(self, n):
        return self._distinct(MEDALLIONS + STONES, n)

    def _fn_has_ocarina_buttons(self, n):
        return self._distinct(OCARINA_BUTTONS, n)

    def _fn_has_all_notes_for_song(self, song):
        # Sin tabla de notas: exige todos los botones (conservador).
        if song == 'Scarecrow Song' and self.settings.get('scarecrow_behavior') == 'free':
            return _Const(True)
        need = 2 if song == 'Scarecrow Song' else len(OCARINA_BUTTONS)
        return self._distinct(OCARINA_BUTTONS, need)

    def _fn_has_soul(self, enemy):
        return _Const(True)

    def _fn_region_has_shortcuts(self, region):
        dungeon = region_dungeons().get(region)
        return _Const(dungeon is not None and dungeon in self.settings.get('dungeon_shortcuts', ()))

    def _fn_can_live_dmg(self, hearts, allow_revive=True, allow_nayrus=True):
        mult = self.settings.get('damage_multiplier')
        if mult not in _DAMAGE_THRESHOLD:
            raise RuleError(f'unknown damage_multiplier {mult!r}')
        if hearts < _DAMAGE_THRESHOLD[mult]:
            return _Const(True)
        alts = []
        if allow_revive:
            alts.append('Fairy')
        if allow_nayrus:
            alts.append('(Nayrus_Love and Magic_Meter)')
        if not alts:
            return _Const(False)
        return self.visit(ast.parse(' or '.join(alts), mode='eval').body)


def compile_rule(text: str, helpers: dict[str, str], settings: dict,
                 region: str | None = None) -> Callable[[State, str], bool]:
    """Compila una regla suelta. Los subeventos de here()/at() quedan sin
    evaluar (siempre falsos fuera de un World): usar `World` para eso."""
    return Compiler(helpers, settings).compile(text, region)
