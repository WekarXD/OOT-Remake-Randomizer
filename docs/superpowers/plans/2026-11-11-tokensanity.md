# Tokensanity: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Opción Tokensanity (`off` / `dungeons` / `overworld` / `all`). Las Skulltulas doradas elegidas pasan a ser sitios del reparto, y sus fichas entran en el montón de objetos.

**Architecture:**
- `fill.place` sigue devolviendo `Hash -> contenido`, ahora también para los Hash de Skulltulas.
- `patch.write_mod` traduce el contenido de una Skulltula a un actor que se pueda soltar. Ese actor es o bien un `Obj_*` existente, o bien un envoltorio `Obj_Rando_<contenido>`, una copia de `Obj_Token_Gold` que genera el módulo nuevo `wrappers.py`.
- `wrappers.py` añade las filas RSDB y las entradas RSTB de los envoltorios.
- Las Skulltulas se asocian a ubicaciones de OoTR con `randomizer/data/gs_map.json`.

**Tech Stack:** Python 3 (biblioteca estándar), `unittest`, formatos propios en `randomizer/formats/`.

**Spec:** `docs/superpowers/specs/2026-11-10-tokensanity-design.md`. La fase 1 está superada (`docs/test-batch-15.md`). Este plan cubre las fases 2 y 3.

## Global Constraints

- Nunca se escribe en el `.nup` ni se hacen commits con archivos del juego. Los tests que leen el juego usan `OOT_NUP` y llevan `@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')`. Para pruebas puntuales: `OOT_NUP="C:\Users\wekar\Documents\Github\Randomizer OOT Remake\The Legend of Zelda Ocarina of Time [0400486024DEC000][v131072].nup"` (solo lectura).
- Los tests se ejecutan con `python -m unittest` desde la raíz del repositorio.
- Los commits no llevan líneas de atribución.
- Con `tokensanity='off'`, el mod generado y el spoiler son idénticos byte a byte a los de antes de este plan, y no se escribe ningún archivo `RSDB/`.
- Valores de la opción, exactamente: `TOKENSANITY = ('off', 'dungeons', 'overworld', 'all')`. Por defecto `'off'`.
- Ficha del remake: `TOKEN = 'Obj_Token_Gold'`. En la lógica de OoTR es `'Gold Skulltula Token'`.
- Prefijo de los envoltorios: `'Obj_Rando_'`, seguido del contenido tal cual (por ejemplo `Obj_Rando_Item_Hookshot`).
- La Bolsa de bombas (`Item_BombBag_Small`) sigue fija. No se toca, porque ya no es elegible.
- Los objetos clave no van a las zonas de `NO_KEY_TARGET_ZONES`, tampoco en sus Skulltulas.
- Textos de la interfaz y del spoiler en español.

## Review Focus

1. **Hash duplicado en dos Banc** (14 Skulltulas de niño/adulto o "Alternative"): `write_mod` tiene que cambiar todas sus copias, y el reparto tiene que contarlas una sola vez. Test en la tarea 5.
2. **Contenido de cofre que no se puede soltar** (lo que `wrappers.can_wrap` rechaza): nunca acaba en una Skulltula. Si eso deja menos contenidos válidos que Skulltulas, el error se da claro y en español. Test en la tarea 4.
3. **Skulltula sin `Dynamic`** (ninguna lo trae puesto): `write_mod` crea el dict y la clave. Test en la tarea 5.
4. **Mismo contenido en varias Skulltulas** (por ejemplo `TBox_Rupee_Red` en 10): se genera un solo envoltorio o actor, sin filas RSDB duplicadas. Test en la tarea 2.
5. **La misma semilla con `tokensanity` distinto** da repartos distintos. Con `off` da exactamente el reparto de antes, porque la clave del RNG no cambia. Test en la tarea 4.

---

### Task 1: Escritor SARC y alta en RSTB

**Files:**
- Modify: `randomizer/formats/sarc.py` (añadir `write`)
- Modify: `randomizer/formats/rstb.py` (añadir `Rstb.add`)
- Test: `tests/test_formats.py`

**Interfaces:**
- Produces: `sarc.write(files: dict[str, bytes], align: int = 8, data_align: int = 0x20) -> bytes`
- Produces: `Rstb.add(path: str, size: int) -> None`. Inserta `[crc32(path), size]` en `_crcs` manteniendo el orden por crc. Lanza `ValueError` si el crc ya existe.

El algoritmo de `write` está probado en el spike `sarcw.py` (scratchpad de la sesión). Si no se puede leer, este es el formato:
- cabecera `SARC` de 0x14 bytes, LE, BOM `0xFEFF`, versión `0x0100`;
- `SFAT` con hash multiplicador `0x65`;
- nodos ordenados por `h = (h*0x65 + c) & 0xFFFFFFFF` sobre los bytes del nombre;
- atributo `0x01000000 | (offset_del_nombre // 4)`;
- `SFNT` con nombres terminados en `\0` y rellenos a 4;
- inicio de datos alineado a `data_align`, y cada archivo alineado a `align`.

- [ ] **Step 1: tests que fallan**

```python
def test_sarc_write_roundtrip_synthetic(self):
    files = {'b/x.bin': b'\x01' * 5, 'a.txt': b'hola', 'c': b''}
    self.assertEqual(sarc.read(sarc.write(files)), files)

def test_sarc_write_node_order(self):
    raw = sarc.write({'zz': b'1', 'a': b'2'})
    # leer los dos hashes de SFAT (offset 0x14 + 0xC, 16 bytes por nodo) y comprobar que van en orden ascendente

def test_rstb_add_sorted_and_duplicate(self):
    r = Rstb((1, 160), [[10, 1], [0xFFFFFFF0, 3]], [])
    r.add('x', 7)
    crcs = [c for c, _ in r._crcs]
    self.assertEqual(crcs, sorted(crcs)); self.assertEqual(r.get('x'), 7)
    with self.assertRaises(ValueError): r.add('x', 8)

@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')
def test_sarc_write_byte_exact_real_packs(self):
    for name in ('Obj_Bottle_Letter', 'Item_Hookshot', 'Obj_Heart_Piece'):
        p = f'Pack/Actor/{name}.pack.zs'
        raw = codec.decompress(p, nup.read(p))
        self.assertEqual(sarc.write(sarc.read(raw)), raw)
```

- [ ] **Step 2:** `python -m unittest tests.test_formats -v`. Fallan con `AttributeError` (`write` / `add`).
- [ ] **Step 3:** implementar `sarc.write` y `Rstb.add`.
- [ ] **Step 4:** `python -m unittest tests.test_formats -v`. PASS, y con `OOT_NUP` definido también el test byte a byte.
- [ ] **Step 5:** commit `feat: SARC writer and RSTB add`.

### Task 2: Envoltorios (`randomizer/wrappers.py`)

**Files:**
- Create: `randomizer/wrappers.py`
- Test: `tests/test_wrappers.py`

**Interfaces:**
- Consumes: `sarc.read`, `sarc.write`, `Rstb.add`, `Rstb.get`, `Rstb.set`, `byml.load` y `byml.dump`, y `GameData` (`.nup`, `.codec`).
- Produces:
  - `WRAPPER_PREFIX = 'Obj_Rando_'`
  - `RSDB_TABLES = ('ActorInfo', 'GameActorInfo', 'PouchActorInfo')`, con ruta `f'RSDB/{t}.Product.111.rstbl.byml.zs'`
  - `pouch_rows(game: GameData) -> frozenset[str]`: los `__RowId` de `PouchActorInfo`.
  - `drop_actor(content: str, rows: frozenset[str]) -> str`. Aplica la primera regla que encaje:
    1. `content` empieza por `Obj_` y está en `rows`: devuelve `content`.
    2. Empieza por `TBox_` o `Tbox_`, y `'Obj_' + resto` está en `rows`: devuelve `'Obj_' + resto`.
    3. En cualquier otro caso: devuelve `WRAPPER_PREFIX + content`.
  - `can_wrap(game: GameData, content: str) -> bool`: True si existe `Pack/Actor/{content}.pack.zs`, si su ActorParam (`Actor/{content}.engine__actor__ActorParam.bgyml`) tiene las cinco refs `ActorNameRef`, `ModelInfoRef`, `AnimationRef`, `PouchContentRef` y `GameParameterTableRef`, y si `content` está en `PouchActorInfo` y en `ActorInfo`.
  - `build_wrapper_files(game: GameData, contents: Iterable[str], rstb: Rstb) -> dict[str, bytes]`. Hace lo siguiente:
    - Para cada contenido distinto que necesite envoltorio (según la regla 3 de `drop_actor`), genera `Pack/Actor/Obj_Rando_<c>.pack.zs` comprimido.
    - Genera las tres tablas RSDB, comprimidas y con sus filas nuevas.
    - Modifica `rstb` en el sitio: `add` para cada pack y `set` para cada tabla.
    - Devuelve `{}` si no hace falta ningún envoltorio.
    - Si algún contenido no pasa `can_wrap`, lanza `ValueError` con su nombre.

La receta es la del spec §3, tal cual. El spike de referencia es `lote15.py` (`clone` con `autoget=True` y sin injertos). Puntos concretos:
- **Contenido del pack.** Base: el pack de `Obj_Token_Gold` sin su ActorParam. Se sustituyen las cinco refs por las del contenido. Se añaden los archivos del pack del contenido que falten, salvo los de `Actor/`.
- **`PouchContentParam`.** Copia del del contenido con `DefaultAutoGet: True`, guardada en `Component/PouchContentParam/Obj_Rando_<c>.game__component__PouchContentParam.bgyml`.
- **ActorParam.** El nuevo es `Actor/Obj_Rando_<c>.engine__actor__ActorParam.bgyml`, con la misma versión BYML que el de la ficha.
- **Formato del pack.** `sarc.write(files, 8, 0x20)`. RSTB del pack: `len(raw) + 0x1000`.
- **`ActorInfo`.** Copia de la fila `Obj_Token_Gold` con estos cambios:
  - `__RowId` nuevo;
  - `ActorName = fila_contenido.get('ActorName', content)`;
  - las claves `FmdbName`, `ModelProjectName`, `AnimationResources`, `ModelAabbMax` y `ModelAabbMin`, copiadas del contenido si las tiene;
  - `InstanceHeapSize` y `PreActorRenderInfoHeapSize` = `max(token, contenido) + 0x10000`.
- **`GameActorInfo`.** Copia de la fila de la ficha, más `ModelVariationAnims` del contenido si lo tiene.
- **`PouchActorInfo`.** Copia de la fila del contenido con el `__RowId` nuevo.
- **Orden de las tablas.** Ordenadas por `__RowId`, con orden de cadena de Python.
- **RSTB de cada tabla.** `len(nuevo) + (rstb_original - len(original)) + 0x1000`.

- [ ] **Step 1: tests que fallan.** Los que no necesitan el juego:

```python
def test_drop_actor_rules(self):
    rows = frozenset({'Obj_Rupee_Red', 'Obj_Token_Gold', 'Obj_MagicJar_Large', 'Obj_Heart_Piece'})
    self.assertEqual(drop_actor('Obj_Token_Gold', rows), 'Obj_Token_Gold')
    self.assertEqual(drop_actor('TBox_Rupee_Red', rows), 'Obj_Rupee_Red')
    self.assertEqual(drop_actor('Tbox_MagicJar_Large', rows), 'Obj_MagicJar_Large')
    self.assertEqual(drop_actor('TBox_DekuNutBundle', rows), 'Obj_Rando_TBox_DekuNutBundle')
    self.assertEqual(drop_actor('Item_Hookshot', rows), 'Obj_Rando_Item_Hookshot')
```

Con `OOT_NUP` (clase `skipUnless`):
- `test_build_wrapper_boomerang`: `build_wrapper_files(game, ['Item_Boomerang', 'Item_Boomerang', 'TBox_Rupee_Red'], rstb)` devuelve exactamente un pack, `Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs`, más las tres tablas RSDB. Dentro del pack:
  - el ActorParam tiene `ActorNameRef == '?ActorSystem/ActorName/Item_Boomerang.engine__actor__ActorName.bgyml'`;
  - el `PouchContentParam` referenciado tiene `DefaultAutoGet is True`.

  En las tablas:
  - `ActorInfo` tiene una fila `Obj_Rando_Item_Boomerang` con `ActorName == 'Item_Boomerang'`;
  - `PouchActorInfo` tiene la fila con `AssignableItem == 'Boomerang'`;
  - las tres tablas siguen ordenadas.

  En el RSTB: `rstb.get('Pack/Actor/Obj_Rando_Item_Boomerang.pack') == len(pack_sin_comprimir) + 0x1000`.
- `test_build_wrapper_none_needed`: `build_wrapper_files(game, ['TBox_Rupee_Red', 'Obj_Token_Gold'], rstb) == {}` y el `rstb` no cambia (`rstb.dump()` igual que antes).
- `test_build_wrapper_deterministic`: dos llamadas con la misma entrada dan bytes iguales.
- `test_can_wrap`: `can_wrap(game, 'Item_Hookshot')` es True; `can_wrap(game, 'Item_NoExiste')` es False.
- `test_can_wrap_chest_contents`: para cada contenido distinto de `tests/fixtures/chests.json` que no empiece por un prefijo de `DUNGEON_ITEM_PREFIXES` y que `drop_actor` mande a envoltorio, `can_wrap` devuelve un bool sin excepción. La lista de los que dan False va al informe de la tarea; la tarea 6 la usa como `gs_forbidden`.

- [ ] **Step 2:** `python -m unittest tests.test_wrappers -v`. Falla porque el módulo no existe.
- [ ] **Step 3:** implementar `randomizer/wrappers.py`.
- [ ] **Step 4:** `python -m unittest tests.test_wrappers -v`. PASS (con `OOT_NUP`).
- [ ] **Step 5:** commit `feat: Skulltula drop wrappers (token clones + RSDB rows)`.

### Task 3: Las 100 Skulltulas: inventario y asociación con OoTR

**Files:**
- Modify: `randomizer/game.py` (añadir `SkulltulaActor`, `GameData.skulltulas()`, `load_skulltulas_fixture`, `skulltulas_to_json`)
- Create: `tools/dump_skulltulas_fixture.py` (como `tools/dump_chests_fixture.py`)
- Create: `tests/fixtures/skulltulas.json`, generado con la herramienta. Contiene solo Hash, Banc, claves de `Dynamic` y posición, ningún binario del juego.
- Create: `tools/draft_gs_map.py`
- Create: `randomizer/data/gs_map.json`
- Modify: `randomizer/locations.py` (añadir `GsEntry`, `GS_MAP_PATH`, `load_gs_map()`)
- Test: `tests/test_game.py`, `tests/test_gs_map.py`

**Interfaces:**
- Produces: `SkulltulaActor(banc: str, hash: int, flags: tuple[str, ...], pos: tuple[float, float, float])`, frozen dataclass. `flags` son las claves de `Dynamic` cuyo valor es verdadero, ordenadas.
- Produces: `GameData.skulltulas() -> list[SkulltulaActor]`. Incluye todas las colocaciones de `Enemy_Skulltula_Gold` (114), ordenadas por `(banc, hash)`.
- Produces: `GsEntry(hash: int, location: str, dungeon: bool, status: str, note: str)`. `status` vale `'confirmed'` o `'guessed'`.
- Produces: `load_gs_map(path=GS_MAP_PATH) -> dict[int, GsEntry]`. El JSON tiene la forma `{"<hash>": {"location": ..., "dungeon": bool, "status": ..., "note": ...}}`.

Qué hace la asociación:
- **Primero, por zona.** Las zonas son el segundo segmento de la ruta del Banc. El número de Skulltulas por zona cuadra con OoTR. El Banc `HyruleField` contiene también las de "LH" (Lago Hylia) y "LLR" (Rancho Lon Lon). Las OoTR son las 100 ubicaciones con `vanilla_item == 'Gold Skulltula Token'` que existen en `World` (sin MQ). Su región y su regla, en `randomizer/logic/ootr/World/*.json`, dan la edad y si es de noche (`at_night`), de tierra blanda (bean) o de gruta.
- **Dentro de cada zona,** se distinguen por:
  - `Enemy_Skulltula_Gold_Nocturnal` y `Enemy_Skulltula_Gold_IsMagicBeanSoil`;
  - el Banc de niño o de adulto (o los dos);
  - `DefaultDungeonRoomIndex` en mazmorras;
  - la posición respecto a los cofres de la misma zona ya asociados en `location_map.json`.
- **Si una zona tiene Skulltulas con los mismos requisitos en la lógica,** intercambiarlas no cambia nada de la lógica. Esas se pueden marcar `confirmed` con la nota "requisitos idénticos". Las demás dudosas van como `guessed`.
- **`dungeon` es True** si la zona es una de las 10 mazmorras: Árbol Deku, Dodongo, Jabu-Jabu, Bosque, Fuego, Agua, Sombras, Espíritu, Pozo y Caverna de Hielo.

- [ ] **Step 1: tests que fallan**

```python
# tests/test_game.py
def test_skulltulas_fixture(self):
    s = load_skulltulas_fixture(FIX)
    self.assertEqual(len(s), 114); self.assertEqual(len({x.hash for x in s}), 100)

# tests/test_gs_map.py
def test_gs_map_complete(self):
    m = load_gs_map()
    fixture_hashes = {x.hash for x in load_skulltulas_fixture(FIX)}
    self.assertEqual(set(m), fixture_hashes)
    w = World(load_vanilla_settings())
    names = {loc for _, loc, _ in w._all_locations}
    gs = {n for n, v in w.locations.items() if v['vanilla_item'] == 'Gold Skulltula Token' and n in names}
    self.assertEqual({e.location for e in m.values()}, gs)          # 100 distintas, biyección
    self.assertEqual(sum(e.dungeon for e in m.values()), 44)
    self.assertTrue(all(e.status in ('confirmed', 'guessed') for e in m.values()))
```

- [ ] **Step 2:** `python -m unittest tests.test_game tests.test_gs_map -v`. Falla.
- [ ] **Step 3:** implementar `SkulltulaActor` y `GameData.skulltulas`, más la herramienta de fixture (generar `tests/fixtures/skulltulas.json` con `OOT_NUP`).
- [ ] **Step 4:** escribir `tools/draft_gs_map.py`, generar `gs_map.json` y repasar a mano zona por zona. Cada nota dice el criterio, como en `location_map.json`.
- [ ] **Step 5:** `python -m unittest tests.test_game tests.test_gs_map -v`. PASS.
- [ ] **Step 6:** commit `feat: Gold Skulltula inventory and OoTR map`. El informe de la tarea lista las Skulltulas `guessed` agrupadas por zona.

### Task 4: Reparto con sitios Skulltula

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `SkulltulaActor`, `GsEntry` y `load_gs_map` (tarea 3).
- Produces:
  - `TOKENSANITY = ('off', 'dungeons', 'overworld', 'all')`, `TOKEN = 'Obj_Token_Gold'`, `OOTR_TOKEN = 'Gold Skulltula Token'`.
  - `Settings.tokensanity: str = 'off'`, como campo nuevo al final.
  - `place(chests, loc_map, world, settings, skulltulas: list[SkulltulaActor] = (), gs_map: dict[int, GsEntry] | None = None, gs_forbidden: frozenset[str] = frozenset()) -> dict[int, str]`. El dict contiene todos los Hash de cofres, como hoy, más los Hash de las Skulltulas que entran, con su contenido del remake (`'Obj_Token_Gold'`, `'TBox_Rupee_Red'`, `'Item_Hookshot'`…). Las Skulltulas que no entran no aparecen.
  - `gs_sites(skulltulas, gs_map, mode: str) -> list[int]`. Devuelve los Hash que entran según el modo:
    - `dungeons`: los que tienen `dungeon` en True;
    - `overworld`: los que lo tienen en False;
    - `all`: todos los asociados;
    - `off`: ninguno.

    Sin duplicados y ordenados.

Cambios en el algoritmo:
- **Clave del RNG.** `_settings_key` solo incluye `tokensanity` si es distinto de `'off'`, para que con `off` todo quede igual.
- **Modo inválido.** Si `settings.tokensanity` no está en `TOKENSANITY`, se lanza `FillError`.
- **Sitios elegibles.** Los de las Skulltulas que entran son elegibles, y su contenido original es `TOKEN`. El mapa interno `Hash -> ubicación OoTR` une `loc_map` (cofres) y `gs_map`. `base` pone `FILLER` en esas ubicaciones, igual que con los cofres.
- **Fichas en `fixed`.** `_fixed` pone `OOTR_TOKEN` en la ubicación de cualquier sitio con `TOKEN`, además de los objetos clave. Así `can_beat` cuenta las fichas.
- **Zonas prohibidas.** `no_key` incluye también las Skulltulas cuya zona de Banc esté en `NO_KEY_TARGET_ZONES`.
- **Reparto del resto.** El contenido que no es clave se baraja como hoy, pero:
  - los sitios Skulltula libres se llenan primero con los primeros contenidos barajados que no estén en `gs_forbidden`;
  - lo que queda, incluidos los contenidos prohibidos, va a los cofres libres en el orden barajado;
  - si no hay bastantes contenidos permitidos para todas las Skulltulas libres, se lanza `FillError('No hay suficientes objetos que se puedan soltar en las Skulltulas')`.
- **Bolsa de bombas.** No cambia (sigue fuera de lo elegible).
- **World.** Se construye fuera; `generate` le pasa `tokensanity` (tarea 6). El fill no lo modifica.

- [ ] **Step 1: tests que fallan.** Usan `tests/fixtures/skulltulas.json` y `load_gs_map()`; en el código, `P(seed, mode, forbidden=frozenset())` abrevia `place(chests, loc_map, world, Settings(seed=seed, tokensanity=mode), skulltulas, gs_map, forbidden)`.

```python
def test_tokensanity_off_identical(self):
    self.assertEqual(self._place(seed='ABC'), P('ABC', 'off'))

def test_tokensanity_all_places_gs(self):
    r = P('T', 'all'); gs = gs_sites(skulltulas, gs_map, 'all')
    self.assertEqual(len(gs), 100); self.assertTrue(set(gs) <= set(r))
    self.assertEqual(sum(1 for v in r.values() if v == TOKEN), 100)       # se conservan las 100
    self.assertTrue(any(r[h] != TOKEN for h in gs))                       # algo se ha movido
    self.assertTrue(any(v == TOKEN for h, v in r.items() if h not in gs))  # fichas en cofres

def test_tokensanity_modes_counts(self):
    self.assertEqual(len(gs_sites(skulltulas, gs_map, 'dungeons')), 44)
    self.assertEqual(len(gs_sites(skulltulas, gs_map, 'overworld')), 56)
    self.assertEqual(gs_sites(skulltulas, gs_map, 'off'), [])

def test_tokensanity_seed_differs_by_mode(self):
    self.assertNotEqual(P('S', 'all'), P('S', 'dungeons'))

def test_tokensanity_forbidden_never_on_gs(self):
    forbidden = frozenset({'Item_ScrubBusinessSeed', 'TBox_DekuNutBundle'})
    r = P('F', 'all', forbidden)
    for h in gs_sites(skulltulas, gs_map, 'all'):
        self.assertNotIn(r[h], forbidden)

def test_tokensanity_no_key_in_forbidden_zones(self):
    # para semillas 'Z0'..'Z4' con 'all': ninguna Skulltula cuya zona de Banc esté en NO_KEY_TARGET_ZONES contiene un KEY_ITEMS

def test_tokensanity_completable(self):
    # para semillas 'C0'..'C4' con 'all': world.can_beat(fixed) es True, con fixed = vanilla_fixed() + KEY_ITEMS en sus ubicaciones
    # + 'Gold Skulltula Token' donde hay TOKEN + 'Rupees (5)' en el resto de sitios elegibles

def test_tokensanity_invalid_mode(self):
    with self.assertRaises(FillError): P('x', 'mucho')
```

- [ ] **Step 2:** `python -m unittest tests.test_fill -v`. Los nuevos fallan.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** `python -m unittest tests.test_fill -v`. Todo PASS, y los tests antiguos sin cambios.
- [ ] **Step 5:** commit `feat: tokensanity fill (Skulltula sites, tokens in pool)`.

### Task 5: Escritura del mod con Skulltulas y envoltorios

**Files:**
- Modify: `randomizer/patch.py`
- Test: `tests/test_generate.py`, que usa `OOT_NUP`

**Interfaces:**
- Consumes: `GameData.skulltulas()` (tarea 3), y `wrappers.drop_actor`, `wrappers.pouch_rows` y `wrappers.build_wrapper_files` (tarea 2).
- Produces: `write_mod(game, placement, mod_root, loc_map, extra_files=None)`. La firma no cambia. Lo nuevo es que los Hash de `placement` que son de Skulltulas también se aplican:
  - en **todas** las copias de ese Hash en todos los Banc, `Dynamic` (se crea si falta) recibe `Drop__DropActor = drop_actor(contenido, pouch_rows(game))`;
  - si algún contenido necesita envoltorio, se añaden los archivos de `build_wrapper_files` con el mismo objeto `rstb` antes de escribirlo.

  Si `placement` no tiene ningún Hash de Skulltula, el comportamiento es exactamente el de hoy.

- [ ] **Step 1: tests que fallan.** Usan `OOT_NUP`. El placement se arma a mano, sin `generate`.
  - `test_write_mod_skulltula_drops`: placement de cofres sin cambios más tres Skulltulas:
    - una Skulltula duplicada, de las 14 en dos Banc, con `'Item_Boomerang'`;
    - una con `'TBox_Rupee_Red'`;
    - una con `'Obj_Token_Gold'`.

    Comprobaciones:
    - los dos Banc de la duplicada tienen `Drop__DropActor == 'Obj_Rando_Item_Boomerang'`;
    - la segunda tiene `'Obj_Rupee_Red'` y la tercera `'Obj_Token_Gold'`;
    - existe `romfs/Pack/Actor/Obj_Rando_Item_Boomerang.pack.zs` y existen las tres tablas RSDB;
    - el RSTB escrito tiene la entrada del pack.
  - `test_write_mod_no_skulltulas_no_rsdb`: con el placement de hoy no se escribe nada bajo `romfs/RSDB/`.
- [ ] **Step 2:** `python -m unittest tests.test_generate -v`. Falla.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** `python -m unittest tests.test_generate -v`. PASS. El test byte a byte que ya existe sigue pasando.
- [ ] **Step 5:** commit `feat: write Skulltula drops and wrappers`.

### Task 6: Generación y spoiler

**Files:**
- Modify: `randomizer/generate.py`
- Modify: `randomizer/spoiler.py`
- Test: `tests/test_generate.py`; tests de spoiler junto a los que ya hay.

**Interfaces:**
- Consumes: `place` con sus parámetros nuevos (tarea 4), `load_gs_map` (tarea 3) y `wrappers.can_wrap` (tarea 2).
- Produces: `spoiler.build(settings, placement, chests, loc_map, game_version, skulltulas=(), gs_map=None) -> dict`. Añade:
  - `settings.tokensanity`;
  - la sección `skulltulas`: lista de `{'hash', 'zone', 'location', 'placed', 'label'}` ordenada por `location`, solo con las Skulltulas que entran.
- `to_text` añade:
  - la línea de ajustes `  Fichas de Skulltula (Tokensanity): <etiqueta>`, con las etiquetas `{'off': 'Desactivado', 'dungeons': 'Solo mazmorras', 'overworld': 'Solo mundo exterior', 'all': 'Todas'}`;
  - una sección `Skulltulas` con una línea por sitio, `  <location> (<zone>): <etiqueta del contenido>`. Las fichas se llaman "Ficha de Skulltula dorada".

  Con `off` no aparece la sección, y `to_text` y `build` dan lo mismo que hoy, es decir, sin claves nuevas. Así se cumple la regla de que con `off` todo sea byte a byte igual.

En `generate`:
- **World.** `World(settings_dict)` lleva `tokensanity` igual a `settings.tokensanity`.
- **Skulltulas y bloqueos.** Si es distinto de `'off'`:
  - `skulltulas = game.skulltulas()`;
  - `gs_map = locations.load_gs_map()`;
  - `gs_forbidden` es el conjunto de contenidos de los cofres elegibles que necesitan envoltorio (regla 3 de `drop_actor`) y no pasan `can_wrap`.
- **Errores.** Un `ValueError` de los envoltorios se convierte en `GenerationError`.

- [ ] **Step 1: tests que fallan** (con `OOT_NUP`):
  - `test_generate_tokensanity_all`: `generate(NUP, out, Settings(seed='gs', tokensanity='all'))`. Comprobaciones:
    - el spoiler JSON tiene 100 entradas en `skulltulas`;
    - todo `Obj_Rando_*` que aparezca en un Banc tiene su pack en `romfs/Pack/Actor/`;
    - la misma semilla da bytes idénticos dos veces.
  - `test_generate_tokensanity_off_unchanged`: `Settings(seed='x')` y `Settings(seed='x', tokensanity='off')` dan el mismo spoiler y los mismos archivos.
  - Test sin juego: `spoiler.to_text` con un dict de ejemplo con `tokensanity='dungeons'` contiene "Solo mazmorras" y la sección "Skulltulas".
- [ ] **Step 2:** ejecutar. Fallan.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** `python -m unittest` completo. PASS.
- [ ] **Step 5:** commit `feat: tokensanity in generate and spoiler`.

### Task 7: Opción en la página

**Files:**
- Modify: `randomizer/web/static/index.html`, `randomizer/web/static/app.js`, `randomizer/web/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `TOKENSANITY` y `Settings.tokensanity` (tarea 4).
- Produces:
  - **Formulario.** El cuerpo de `/api/generate` acepta `tokensanity`, que es opcional (por defecto `'off'`).
  - **Validación.** Un valor que no esté en `TOKENSANITY` da el error `'Valor de Tokensanity no válido.'`.
  - **Configuración.** Se guarda en `last_settings.tokensanity`.

Página:
- Un `<fieldset>` con `<legend>Shuffle</legend>` después de "Excluir objetos". Si la fase B de los regalos ya lo creó, se reutiliza.
- Dentro va `<label for="tokensanity">Fichas de Skulltula (Tokensanity)</label>` y un `<select id="tokensanity">` con cuatro opciones, en este orden: `off` "Desactivado", `dungeons` "Solo mazmorras", `overworld` "Solo mundo exterior" y `all` "Todas".
- Debajo, una pista `<p class="hint">`: "Las Skulltulas doradas elegidas pueden soltar cualquier objeto, y sus fichas se reparten por cofres y otras Skulltulas."
- `app.js` envía el valor y lo restaura desde `last_settings`.

- [ ] **Step 1: tests que fallan.** En `tests/test_server.py`, siguiendo el patrón de `skip_cutscenes`:
  - un valor inválido devuelve el error;
  - un valor válido llega a `Settings` (con `generate` simulado como en los tests de ahora) y se guarda en la configuración;
  - si no se envía, vale `'off'`.
- [ ] **Step 2:** ejecutar. Fallan.
- [ ] **Step 3:** implementar.
- [ ] **Step 4:** `python -m unittest tests.test_server -v`. PASS. Comprobación a mano: `python -m randomizer --no-browser`, abrir `http://127.0.0.1:8765` en el navegador integrado y comprobar que el selector aparece y se recuerda tras generar. Mirarlo también a 375 px de ancho.
- [ ] **Step 5:** commit `feat: Tokensanity option in the web UI`.

### Task 8: Lotes de prueba en el juego

**Files:**
- Create: `tools/make_gs_check.py`, `docs/test-batch-16.md`, `docs/test-batch-17.md`
- Modify: `randomizer/data/gs_map.json`, según lo que diga el lote 16.

Esta tarea la hace el controlador con el usuario. **Se para y espera su informe del juego.**

1. **Lote 16: comprobar las Skulltulas `guessed`.** `tools/make_gs_check.py` genera `test-mod/0400486024DEC000/TestGS` con:
   - cada Skulltula `guessed` soltando una rupia de color distinto dentro de su zona (verde, azul, roja, morada y dorada, en el orden de la ubicación OoTR);
   - la Skulltula de tierra blanda del Bosque Kokiri soltando un envoltorio (pendiente del lote 15).

   La guía `docs/test-batch-16.md` tiene una tabla por zona: "Skulltula de <sitio OoTR en español> → color esperado". El usuario apunta lo que no coincide.
2. **Corregir.** Se corrige `gs_map.json`, se pasan a `confirmed` las comprobadas, se pasan los tests y se hace commit `fix: gs_map from batch 16`.
3. **Lote 17: semilla de prueba.** Se genera `TestTokens1` con `Settings(seed='TestTokens1', tokensanity='all')` en `test-mod/0400486024DEC000/`. La guía `docs/test-batch-17.md` la saca del spoiler: qué hay en las Skulltulas del Árbol Deku, del Bosque Kokiri y de Kakariko, más dos cofres con ficha. El usuario lo juega en parte y se apuntan los resultados.
