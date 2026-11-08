# OoT Remake Randomizer v1 — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicación local con interfaz web que genera una carpeta de mod para Lichii en la que los 15 objetos clave de cofres del remake de OoT (Switch 2) se reparten entre cualquier cofre permitido. Una lógica derivada de OoTR garantiza que la partida se puede completar sin glitches.

**Architecture:** Paquete Python `randomizer/` en capas: (1) acceso al juego, que lee el `.nup` por offset, descomprime zstd con diccionarios y lee/escribe BYML, SARC y RESTBL; (2) datos, con la tabla `Hash del remake → ubicación OoTR` y la tabla de objetos; (3) lógica, que evalúa las regiones y reglas de OoTR copiadas de una versión fija; (4) reparto determinista por semilla; (5) parcheo, que escribe `Rando_<semilla>/romfs/...`; (6) servidor web con librería estándar y una página HTML/JS estática con pestañas.

**Tech Stack:** Python 3.14 (stdlib: `compression.zstd`, `http.server`, `ast`, `unittest`, `random`, `hashlib`, `zlib`, `json`, `secrets`), HTML/CSS/JS sin frameworks. Sin dependencias de terceros.

**Spec:** `docs/superpowers/specs/2026-11-08-oot-remake-randomizer-design.md`

## Global Constraints

- Python **3.14+** y solo librería estándar. No hay pip en el flujo normal; los tests corren con `python -m unittest`.
- **Nunca se escribe en el `.nup`**: se abre en modo `'rb'`, siempre.
- Los archivos del juego se leen del paquete de actualización v131072 (versión 1.1.1); el ID del juego es `0400486024DEC000`. Si es otra versión, se muestra un error claro.
- Mapas: `romfs/Banc/<Zona>/*.bcett.byml.zs`, comprimidos con zstd y el diccionario `bcett.byml.zsdic` de `romfs/Pack/ZsDic.pack.zs`. El contenido de un cofre es `Actors[i].Dynamic.Drop__DropActor`.
- RSTB: `romfs/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs`. Para mapas, el valor es `((n + 31) & ~31) + 264`.
- Un sitio lógico es un `Hash`. Todas las copias de un `Hash` (en mapas de niño o adulto) reciben el mismo objeto.
- Salida: `<carpeta_salida>/Rando_<semilla>/romfs/<ruta romfs>`. Solo contiene los mapas modificados y la RSTB.
- La misma semilla, con los mismos ajustes y la misma versión del randomizer, debe producir archivos **idénticos byte a byte**.
- El repo no puede contener archivos del juego. `.gitignore` excluye `*.nup`, `test-mod/`, `output/`, `.superpowers/` y `user_config.json`.
- La lógica de OoTR se copia del commit `526b4c8d81b7c4023ef4573ffbaf39344e270d5b` de `OoTRandomizer/OoT-Randomizer`. El proyecto se licencia GPL-3.0, con atribución.
- Los textos de la interfaz están en español.
- Los tests que necesitan el juego leen la ruta de la variable de entorno `OOT_NUP`. Si no está definida, se marcan como `skip` con `unittest.skipUnless`.

## Review Focus

1. **Ruta del `.nup` con espacios y corchetes** (`...[0400486024DEC000][v131072].nup`): la ruta del usuario es así, así que debe funcionar. El test va en la Task 2 (`test_minimal_synthetic_nup`).
2. **Pulsar Generar dos veces con la misma semilla:** no se sobrescribe sin confirmación. Los tests van en la Task 9 (`test_existing_dir_not_overwritten`) y la Task 10 (`test_generate_exists_flag`).
3. **Archivo que no es un `.nup`, o ruta inexistente:** se devuelve un mensaje en español, no un traceback. Los tests van en la Task 2 (`test_rejects_non_nup`) y la Task 10 (`test_validate_bad_path`).
4. **Ajustes con los que no se puede generar una semilla:** se muestra un error claro y no queda una carpeta de mod a medias. El test va en la Task 9 (`test_failed_generation_leaves_nothing`).
5. **Semilla vacía o con caracteres raros** (espacios, tildes, `/`): se normaliza a un nombre de carpeta seguro y siempre da el mismo resultado. El test va en la Task 9 (`test_safe_seed_name`).

---

## Fase 0 — Lote de pruebas en el juego (puerta del usuario)

### Task 1: Repo y lote de mods de prueba R1–R3

**Files:**
- Create: `.gitignore`, `LICENSE` (texto GPL-3.0), `README.md` (cómo ejecutar, con atribución a OoTR)
- Create: `tools/make_test_batch.py`
- Create: `docs/test-batch-1.md` (lista de comprobación para el usuario)
- Uses: `spikes/peek.py`, `spikes/byml.py`, `spikes/hookshot_test.py` (solo se leen; no se modifican)

**Interfaces:**
- Produces: `python -I tools/make_test_batch.py <nup> <files.tsv> <out_dir>`, que crea `<out_dir>/0400486024DEC000/TestLote1/` y `<out_dir>/0400486024DEC000/TestLote2/`. Para obtener `files.tsv`, primero se ejecuta `spikes/nuplist.py`.

- [ ] **Step 1:** `git init`, crear `.gitignore` con las entradas de Global Constraints, `LICENSE` y un `README.md` mínimo. Commit `chore: init repo`.
- [ ] **Step 2:** Escribir `tools/make_test_batch.py`. Debe reutilizar las funciones de `spikes/` (con `sys.path`) para aplicar varios cambios `Hash → Drop__DropActor` en varios mapas y actualizar todas las entradas RSTB afectadas en una sola RSTB por mod. Los cambios son:

  **TestLote1** (Bosque Kokiri de niño, al principio del juego), en `Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs`:
  | Hash | Original | Nuevo | Comprueba |
  |---|---|---|---|
  | 16757992849254467386 | Item_Sword_Kokiri | TBox_Rupee_Green | R1: ¿el evento `Get_StoneOfForest_GetSword` da la espada igualmente? |
  | 10831981390482426294 | TBox_Rupee_Green | Item_Longshot | R2: Gancho largo sin Gancho |
  | 4555665598794293658 | TBox_Rupee_Blue | Item_Gauntlet_Gold | R2: Guanteletes de oro sin brazalete ni plata |
  | 9725242744547055868 | TBox_Rupee_Blue | Item_Shield_Mirror | R3: objeto de adulto de niño |
  | 12786193094758345086 | TBox_Rupee_Blue | Item_Arrow_Ice | R2/R3: flechas sin arco |

  El mismo Hash del cofre de la espada también existe en `KokiriForest_Adult_Dynamic.bcett.byml.zs`, así que se aplica el mismo cambio allí.

  **TestLote2** (eventos de historia; hace falta una partida guardada de adulto), en `Banc/IceCavern/IceCavern_Static.bcett.byml.zs`: Hash 6859289214373847284, de `Item_HeavyBoot` a `TBox_Rupee_Blue`. Comprueba R1: ¿se aprende igualmente la Serenata del Agua?
- [ ] **Step 3:** Ejecutarlo contra el juego real. El script vuelve a leer cada mapa y confirma cada cambio, igual que `hookshot_test.py`. Salida esperada: una línea `OK <hash> <nuevo>` por cambio y `RSTB <ruta> <old> -> <new>` por mapa.
- [ ] **Step 4:** Escribir `docs/test-batch-1.md` en español. Para cada fila: dónde ir, qué hacer, qué anotar (el objeto recibido, el texto o la escena mostrada, si aparece en el inventario o el menú y si se puede usar) y casillas OK/FALLO. Debe recordar que hay que desactivar otros mods.
- [ ] **Step 5:** Commit `test: add in-game test batch 1`.
- [ ] **Step 6 (PUERTA):** Dar los mods y la lista al usuario y **esperar sus resultados**. Anotarlos en `docs/test-batch-1.md` y decidir:
  - R1: si algún evento da el objeto original, esos Hash se marcan como `needs_event_patch: true` en la Task 6. Quedan fuera del reparto hasta que exista un plan aparte para editar BFEVFL, que es otro subsistema y otro plan. El resto del plan sigue igual.
  - R2: se elige el modelo de objetos progresivos de la Task 7. **Directo**: cada actor da su nivel aunque no tengas el anterior. **Secuencial**: el juego exige el nivel previo y la lógica lo impone.
  - R3: si un objeto de adulto conseguido de niño se pierde, se apunta en `docs/test-batch-1.md` y la Task 8 añade la regla "ese objeto solo se coloca en ubicaciones a las que llega el adulto".

## Fase 1 — Acceso al juego

### Task 2: `NupArchive` (lectura del `.nup`)

**Files:**
- Create: `randomizer/__init__.py` (con `RANDO_VERSION = '0.1.0'`), `randomizer/nup.py`
- Test: `tests/__init__.py`, `tests/test_nup.py`

**Interfaces:**
- Produces:
  - `class NupError(Exception)`, con un mensaje en español.
  - `class NupArchive`: `__init__(self, path: str | os.PathLike)`, que valida el superbloque y el SHA-256 de la TOC (lanza `NupError`); `.title_id: int` (base); `.update_version: int | None` (versión del paquete kind=1); `.has(romfs_path: str) -> bool`; `.read(romfs_path: str) -> bytes` (contenido sin compresión NUP, rutas relativas a `romfs/` con `/`, por ejemplo `'Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs'`; del paquete de actualización); `.list(prefix: str) -> list[str]`; `close()` y context manager.
  - `SUPPORTED_UPDATE_VERSION = 131072`, `TITLE_ID = 0x0400486024DEC000`.

- [ ] **Step 1: Tests**
  - `test_rejects_non_nup`: un archivo temporal con `b'hello'` → `NupError`, y el mensaje contiene `"no es un archivo .nup"`.
  - `test_minimal_synthetic_nup`: construir en el test un NUP mínimo según SPEC §7 (1 paquete con kind=1 y flag standalone, `romfs/hello.bin` con `b'hola'` sin comprimir, en un directorio temporal llamado `juego [x] y espacios`) → `NupArchive(p).read('hello.bin') == b'hola'` y `has('nope') is False`.
  - `test_real_game` (skipUnless `OOT_NUP`): `title_id == 0x0400486024DEC000`, `update_version == 131072`, `len([p for p in list('Banc/') if p.endswith('.bcett.byml.zs')]) == 160`, y `read('Pack/ZsDic.pack.zs')[:4] == b'\x28\xb5\x2f\xfd'`.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_nup -v`. Se espera que falle porque el módulo no existe.
- [ ] **Step 3:** Implementar a partir de `spikes/nuplist.py`, construyendo al abrir un índice `dict[ruta_romfs, (offset, extent_size, codec)]` solo para el paquete de actualización (o el base si no hay actualización). `codec==1` → `zstd.decompress`; cualquier otro codec distinto de 0 → `NupError`.
- [ ] **Step 4:** Volver a ejecutar los tests. Se espera PASS (y `test_real_game` en estado skip si no hay `OOT_NUP`).
- [ ] **Step 5:** Commit `feat: NupArchive reader`.

### Task 3: Formatos — zstd con diccionarios, SARC, BYML y RSTB

**Files:**
- Create: `randomizer/formats/__init__.py`, `randomizer/formats/sarc.py`, `randomizer/formats/byml.py` (pasar `spikes/byml.py`), `randomizer/formats/rstb.py`, `randomizer/formats/zs.py`
- Test: `tests/test_formats.py`

**Interfaces:**
- Consumes: `NupArchive.read`.
- Produces:
  - `sarc.read(data: bytes) -> dict[str, bytes]`
  - `byml.load(data: bytes) -> tuple[int, object]`, `byml.dump(root, ver: int = 7) -> bytes`, y las clases `U32, I64, U64, F64, F32, Bin` (igual que en el spike).
  - `class ZsCodec`: `@classmethod from_archive(nup: NupArchive) -> ZsCodec`; `decompress(romfs_path: str, data: bytes) -> bytes`; `compress(romfs_path: str, data: bytes) -> bytes`. Elige el diccionario por extensión: `.bcett.byml.zs` → `bcett.byml.zsdic`, `.pack.zs` → `pack.zsdic`, `.rsizetable.zs` → sin diccionario, y cualquier otro `.zs` → `zs.zsdic`. Comprime con `level=19`.
  - `class Rstb`: `@classmethod load(data: bytes) -> Rstb`; `get(path: str) -> int | None`; `set(path: str, size: int) -> None` (`KeyError` si no existe); `dump() -> bytes`. `path` es la ruta romfs **sin `.zs`**. Busca primero en la tabla de nombres y, si no está, por `zlib.crc32(path.encode())` en la tabla de crc ordenada.
  - `def banc_rstb_size(n: int) -> int` = `((n + 31) & ~31) + 264`.

- [ ] **Step 1: Tests**
  - `test_byml_roundtrip_synthetic`: el árbol `{'Actors': [{'Gyaml': 'Obj_TBox_A_01', 'Hash': U64(2**63+5), 'Dynamic': {'Drop__DropActor': 'TBox_Rupee_Blue'}}, {'f': F32(1.5), 'i': -3, 'b': True, 'u': U32(7)}]}` hace `load(dump(x))[1] == x`, y además `type(r['Actors'][0]['Hash']) is U64`.
  - `test_byml_shared_nodes_not_aliased`: dos actores con `Dynamic` idéntico se deduplican al hacer `dump`; tras `load`, cambiar uno no cambia el otro.
  - `test_rstb_roundtrip_synthetic`: una RESTBL creada en el test con 3 entradas crc y 1 de nombre: `set` → `dump` → `load` → `get` devuelve el valor nuevo en ambos tipos.
  - `test_banc_rstb_size`: `banc_rstb_size(510884) == 511176`.
  - `test_real_all_banc_roundtrip` (skipUnless `OOT_NUP`): los 160 mapas se descomprimen, pasan `load→dump→load` y son iguales con sus tipos. `Rstb.get(ruta_sin_zs) == banc_rstb_size(len(raw))` en los 160.
- [ ] **Step 2:** Ejecutar y comprobar que falla.
- [ ] **Step 3:** Implementar. Formato RESTBL: magic `b'RESTBL'`, `u32 version`, `u32 name_block_size`, `u32 crc_count`, `u32 name_count`, después `crc_count × (u32 crc, u32 size)` ordenados por crc y `name_count × (name[name_block_size] terminado en NUL, u32 size)`.
- [ ] **Step 4:** Ejecutar y comprobar que pasa.
- [ ] **Step 5:** Commit `feat: zstd/sarc/byml/rstb formats`.

### Task 4: `GameData` — inventario de cofres

**Files:**
- Create: `randomizer/game.py`
- Create: `tools/dump_chests_fixture.py` → `tests/fixtures/chests.json`
- Test: `tests/test_game.py`

**Interfaces:**
- Consumes: `NupArchive`, `ZsCodec`, `byml`.
- Produces:
  - `@dataclass(frozen=True) class ChestActor: banc: str; hash: int; gyaml: str; drop: str; event: str | None; pos: tuple[float, float, float]`
  - `class GameData`: `__init__(self, nup: NupArchive)`; `.codec: ZsCodec`; `chests() -> list[ChestActor]`, que devuelve los actores cuyo `Gyaml` contiene `'TBox'` y tienen `Dynamic.Drop__DropActor`, ordenados por `(banc, hash)` (se cachea); `load_banc(path: str) -> tuple[int, dict]`.
  - `tests/fixtures/chests.json`: una lista de `ChestActor` serializados (solo identificadores, nombres de actor y posiciones), para que los tests de la Task 8 corran sin el juego.

- [ ] **Step 1: Tests** (skipUnless `OOT_NUP`): `test_chest_counts`: `len(chests()) == 238` y `len({c.hash for c in chests()}) == 203`. `test_kokiri_sword_chest`: el Hash 16757992849254467386 aparece dos veces (bancs `KokiriForest_Child_Dynamic` y `KokiriForest_Adult_Dynamic`), con `drop == 'Item_Sword_Kokiri'` y `event == 'Get_StoneOfForest_GetSword'`. `test_fixture_matches`: el contenido de `tests/fixtures/chests.json` es igual a `chests()`.
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar y generar el fixture. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: chest inventory`.

## Fase 2 — Datos y lógica

### Task 5: Importar los datos de lógica de OoTR

**Files:**
- Create: `tools/import_ootr.py`
- Create (generado y versionado): `randomizer/logic/ootr/World/*.json`, `randomizer/logic/ootr/LogicHelpers.json`, `randomizer/logic/ootr/locations.json`, `randomizer/logic/ootr/SOURCE.md` (repo, commit y licencia)
- Test: `tests/test_ootr_data.py`

**Interfaces:**
- Produces: `python -I tools/import_ootr.py <ruta_a_clon_de_OoTR>`. El usuario clona `https://github.com/OoTRandomizer/OoT-Randomizer` y hace checkout de `526b4c8d81b7c4023ef4573ffbaf39344e270d5b`; el script se niega si `git -C <clon> rev-parse HEAD` no coincide.
  - Copia `data/World/*.json` (solo los de lógica glitchless; se excluyen los `*MQ*.json` y la carpeta `Glitched World`) y `data/LogicHelpers.json`. Si las rutas no existen en ese commit, para con un error que dice cuál falta.
  - `locations.json` = `{nombre: {"type": str, "scene": int|null, "vanilla_item": str|null, "categories": [str]}}`, extraído de `LocationList.py` con `ast` (se busca la asignación `location_table` y se evalúan sus tuplas con `ast.literal_eval` elemento a elemento, **sin importar ni ejecutar código de OoTR**).

- [ ] **Step 1: Tests**
  - `test_key_item_locations_exist`: en `locations.json` existen con `type == 'Chest'` estas 15 ubicaciones: `KF Kokiri Sword Chest`, `Deku Tree Slingshot Chest`, `Dodongos Cavern Bomb Bag Chest`, `Jabu Jabus Belly Boomerang Chest`, `Forest Temple Bow Chest`, `Fire Temple Megaton Hammer Chest`, `Water Temple Longshot Chest`, `Shadow Temple Hover Boots Chest`, `Ice Cavern Iron Boots Chest`, `Bottom of the Well Lens of Truth Chest`, `Spirit Temple Silver Gauntlets Chest`, `Spirit Temple Mirror Shield Chest`, `Graveyard Dampe Race Hookshot Chest`, `Gerudo Training Ground Maze Path Final Chest` y `Ganons Castle Shadow Trial Golden Gauntlets Chest`. Si algún nombre difiere en ese commit, se corrige **la lista del test, aquí y en la Task 6,** con el nombre real y se anota en `SOURCE.md`.
  - `test_world_files_parse`: todos los JSON cargan. OoTR usa JSON con comentarios `#`; se quitan las líneas cuyo primer carácter no blanco es `#` antes de `json.loads`.
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar e importar. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: vendor OoTR logic data @526b4c8` (incluye `SOURCE.md`).

### Task 6: Tabla de objetos y asociación de cofres

**Files:**
- Create: `randomizer/items.py`, `randomizer/locations.py`, `randomizer/data/location_map.json`, `tools/draft_location_map.py`
- Test: `tests/test_location_map.py`

**Interfaces:**
- Consumes: `GameData.chests()` (o el fixture), `locations.json`.
- Produces:
  - `items.KEY_ITEMS: dict[str, str]` (actor del remake → objeto de OoTR): `Item_Sword_Kokiri→'Kokiri Sword'`, `Item_Range_SlingShot→'Slingshot'`, `Item_Boomerang→'Boomerang'`, `Item_Range_Bow→'Bow'`, `Item_Hookshot→'Progressive Hookshot'`, `Item_Longshot→'Progressive Hookshot'`, `Item_Hammer→'Megaton Hammer'`, `Item_HeavyBoot→'Iron Boots'`, `Item_HoverBoot→'Hover Boots'`, `Item_Gauntlet_Silver→'Progressive Strength Upgrade'`, `Item_Gauntlet_Gold→'Progressive Strength Upgrade'`, `Item_GlassTruth→'Lens of Truth'`, `Item_Shield_Mirror→'Mirror Shield'`, `Item_Arrow_Ice→'Ice Arrows'`, `Item_BombBag_Small→'Bomb Bag'`.
  - `items.ITEM_LEVEL: dict[str, tuple[str, int]]` = `{'Item_Hookshot': ('Progressive Hookshot', 1), 'Item_Longshot': ('Progressive Hookshot', 2), 'Item_Gauntlet_Silver': ('Progressive Strength Upgrade', 2), 'Item_Gauntlet_Gold': ('Progressive Strength Upgrade', 3)}`. El nivel 1 de fuerza es el brazalete Goron, que es fijo, de evento.
  - `items.LABELS_ES: dict[str, str]`, el nombre en español de cada objeto de `KEY_ITEMS` (Espada Kokiri, Resortera, Bumerán, Arco, Gancho, Gancho largo, Martillo, Botas de hierro, Botas levitadoras, Guanteletes de plata, Guanteletes de oro, Lente de la Verdad, Escudo espejo, Flechas de hielo, Bolsa de bombas).
  - `items.DUNGEON_ITEM_PREFIXES = ('Item_Dungeon_', 'Obj_MiniGame_SmallKey', 'Obj_Dungeon_SmallKey_')`
  - `location_map.json`: `{"<hash>": {"location": "<nombre OoTR>"|null, "status": "auto"|"manual"|"unmapped", "needs_event_patch": bool, "note": str}}`, con las 203 claves.
  - `locations.load_map() -> dict[int, LocationEntry]`, con `@dataclass(frozen=True) LocationEntry(hash: int, location: str | None, status: str, needs_event_patch: bool)`.
  - `tools/draft_location_map.py <nup>`: genera un borrador asociando por (zona → prefijo OoTR, contenido original). Si hay un candidato único → `auto`. Si hay varios → `null` + `note` con los candidatos y las posiciones, para resolver a mano. Nunca sobrescribe entradas `manual`.
    - Tabla zona → prefijo, para completar con los nombres reales de `locations.json`: `KokiriForest→KF`, `LostWood→LW`, `SacredForestMeadow→SFM`, `HyruleField→HF`, `Market→Market`, `HyruleCastle→HC`, `KakarikoVillage→Kak`, `Graveyard→Graveyard`, `DeathMountainTrail→DMT`, `DeathMountainCrater→DMC`, `GoronCity→GC`, `ZoraRiver→ZR`, `ZoraDomain→ZD`, `ZoraFountain→ZF`, `GerudoValley→GV`, `GerudoFortress→GF`, `HountedWasteland→Wasteland`, `DesertColossus→Colossus` (aquí también `Spirit Temple`), `InsideTheDekuTree→Deku Tree`, `DodongoCavern→Dodongos Cavern`, `InsideJabuJabuBelly→Jabu Jabus Belly`, `ForestTemple→Forest Temple`, `FireTemple→Fire Temple`, `WaterTemple→Water Temple`, `ShadowTemple→Shadow Temple`, `SpiritTemple→Spirit Temple`, `IceCavern→Ice Cavern`, `BottomOfTheWell→Bottom of the Well`, `GerudoTrainingGround→Gerudo Training Ground`, `InsideGanonCastle→Ganons Castle`, `GanonCastle→Ganons Tower`.
    - Contenido del remake → objeto vanilla de OoTR para la comparación: `TBox_Rupee_Green/Obj_Rupee_Green→'Rupee (1)'`, `Blue→'Rupees (5)'`, `Red→'Rupees (20)'`, `Purple→'Rupees (50)'`, `Gold→'Rupees (200)'`, `Item_Dungeon_SmallKey→'Small Key (<mazmorra>)'`, `Item_Dungeon_Map→'Map (<mazmorra>)'`, `Item_Dungeon_Compass→'Compass (<mazmorra>)'`, `Item_Dungeon_BossKey→'Boss Key (<mazmorra>)'` y `KEY_ITEMS` para los objetos clave. Para el resto, el implementador busca su equivalente en `locations.json`.
- [ ] **Step 1: Tests**
  - `test_map_covers_all_hashes`: las claves de `location_map.json` son exactamente los 203 Hash del fixture de la Task 4.
  - `test_key_item_hashes_mapped`: estos Hash tienen `status != 'unmapped'` y estas ubicaciones: 16757992849254467386→`KF Kokiri Sword Chest`, 821372075822700622→`Deku Tree Slingshot Chest`, 12161709650443144121→`Dodongos Cavern Bomb Bag Chest`, 5527401621172639818→`Jabu Jabus Belly Boomerang Chest`, 11082303891540711688→`Forest Temple Bow Chest`, 12083259659219538030→`Fire Temple Megaton Hammer Chest`, 18059711820131847165→`Water Temple Longshot Chest`, 14535080241831873137→`Shadow Temple Hover Boots Chest`, 6859289214373847284→`Ice Cavern Iron Boots Chest`, 16654774376625985726→`Bottom of the Well Lens of Truth Chest`, 2490063409521505179→`Spirit Temple Silver Gauntlets Chest`, 10012167258643363548→`Spirit Temple Mirror Shield Chest`, 16041366920820397198→`Graveyard Dampe Race Hookshot Chest`, 1941083939696166170→`Gerudo Training Ground Maze Path Final Chest`, 17657623307936361670→`Ganons Castle Shadow Trial Golden Gauntlets Chest`.
  - `test_no_duplicate_locations`: dos Hash nunca apuntan a la misma ubicación de OoTR.
  - `test_mapped_locations_are_chests`: toda `location` no nula existe en `locations.json` con `type == 'Chest'`.
  - `test_needs_event_patch_from_batch`: el conjunto de Hash con `needs_event_patch == true` es igual al de la constante `EVENT_PATCH_HASHES` del test, que se rellena con el resultado de la PUERTA de la Task 1 (vacía si R1 salió bien).
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar `items.py` y `locations.py`, ejecutar el borrador y **resolver a mano** los casos ambiguos usando las posiciones y la zona. Los que no se puedan asegurar quedan `unmapped` con su motivo en `note`. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: chest→OoTR location map`.
- [ ] **Step 6:** Escribir `docs/test-batch-2.md`, con hasta 10 cofres `manual` elegidos entre los más dudosos para comprobarlos jugando. Es informativo y no bloquea.

### Task 7: Evaluador de reglas y búsqueda de alcanzabilidad

**Files:**
- Create: `randomizer/logic/__init__.py`, `randomizer/logic/rules.py`, `randomizer/logic/world.py`, `randomizer/logic/vanilla_settings.json`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: los datos de la Task 5 e `items.ITEM_LEVEL`.
- Produces:
  - `class RuleError(Exception)`.
  - `rules.compile_rule(text: str, helpers: dict[str, str], settings: dict) -> Callable[[State, str], bool]`. El segundo argumento es la edad, `'child'` o `'adult'`. Parsea con `ast.parse(text, mode='eval')`, igual que OoTR. Soporta: `and/or/not`, comparaciones con ajustes, `True/False`, nombres de objeto (`Kokiri_Sword` → `'Kokiri Sword'`, guiones bajos a espacios), `(Item, n)` y `has(Item, n)`, nombres de evento, funciones y macros de `LogicHelpers.json` (expandidas recursivamente con sustitución de parámetros), `is_adult`, `is_child`, `is_starting_age`, `at_day`, `at_night`, `at_dampe_time`, `here(rule)`, `at(region, rule)`, y los nombres de ajustes de `vanilla_settings.json`. **Cualquier identificador desconocido lanza `RuleError` al compilar**, nunca se trata como `False` en silencio.
  - `vanilla_settings.json` contiene los valores de OoTR que reproducen el juego original. Como mínimo: `open_forest: "closed"`, `open_door_of_time: false`, `zora_fountain: "closed"`, `gerudo_fortress: "normal"`, `bridge: "vanilla"`, `trials: 6`, `starting_age: "child"`, `shuffle_ganon_bosskey: "vanilla"`, todos los `shuffle_*` desactivados o vanilla, y todos los tricks `logic_*` a `false`. El implementador completa **todas** las claves que pidan las reglas copiadas, hasta que pase `test_all_rules_compile`.
  - `class State`: `items: Counter[str]`, `events: set[str]`. Método `has(item: str, n: int = 1) -> bool`. Los objetos progresivos se guardan en `items` como su nivel máximo conseguido, según `ITEM_LEVEL` (modelo "directo"). Si la PUERTA R2 dijo "secuencial", `World` solo suma un nivel cuando el anterior está presente.
  - `class World`: `__init__(self, settings: dict)`; `reachable_locations(fixed: dict[str, str]) -> set[str]`, una búsqueda de punto fijo sobre regiones, salidas, eventos y ubicaciones para niño y adulto, con un `State` compartido. Cada ubicación de `fixed` (ubicación OoTR → objeto OoTR, o el actor del remake si es un objeto clave con nivel) da su objeto al alcanzarse. `can_beat(fixed: dict[str, str]) -> bool` comprueba si se alcanza la ubicación de victoria de OoTR (la que da `'Triforce'`; se toma de `locations.json`).
  - `world.vanilla_fixed() -> dict[str, str]`: ubicación → `vanilla_item` de `locations.json`, sustituyendo el objeto de los 15 cofres clave por el actor del remake correspondiente (por ejemplo `'Water Temple Longshot Chest' → 'Item_Longshot'`), para que `ITEM_LEVEL` sea correcto.
  - La hora del día es una aproximación (decisión del plan): `at_day` y `at_night` son verdaderos para una edad si esa edad alcanza alguna región con `"time_passes": true`. `at_dampe_time` equivale a `at_night`.
- [ ] **Step 1: Tests**
  - `test_all_rules_compile`: todas las reglas de regiones, salidas, eventos y ubicaciones de todos los `World/*.json` compilan sin `RuleError`.
  - `test_unknown_identifier_raises`: `compile_rule('Foo_Bar_Baz', {}, {})` lanza `RuleError`.
  - `test_vanilla_is_beatable`: `World(vanilla).can_beat(world.vanilla_fixed())` es `True`.
  - `test_no_sword_not_beatable`: lo mismo con `'KF Kokiri Sword Chest' → 'Rupees (5)'` → `False`, porque el bosque cerrado exige la espada.
  - `test_slingshot_gates_deku`: con todo vanilla salvo `'Deku Tree Slingshot Chest' → 'Rupees (5)'`, la ubicación del corazón de Gohma (`Deku Tree Queen Gohma Heart`, nombre comprobado en `locations.json`) no está en `reachable_locations`.
  - `test_longshot_alone_counts_as_hookshot`: con modelo directo, un `State` que solo tiene `Item_Longshot` cumple `has('Progressive Hookshot', 1)` y `has('Progressive Hookshot', 2)`.
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: OoTR rule evaluator and reachability`.

## Fase 3 — Reparto, parcheo y spoiler

### Task 8: Reparto determinista

**Files:**
- Create: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `World`, `world.vanilla_fixed()`, `locations.load_map()`, `items`, `ChestActor` (del fixture `tests/fixtures/chests.json` en los tests).
- Produces:
  - `@dataclass(frozen=True) class Settings: seed: str; key_items_mode: str = 'any_chest'  # 'vanilla' | 'any_chest'; excluded_items: frozenset[str] = frozenset(); spoiler: bool = True`
  - `class FillError(Exception)`, con mensaje en español.
  - `def place(chests: list[ChestActor], loc_map: dict[int, LocationEntry], world: World, settings: Settings) -> dict[int, str]`, que devuelve un mapa `Hash → Drop__DropActor` para **todos** los Hash (el valor original si no cambia).
  - Sitios elegibles: `status != 'unmapped'`, `not needs_event_patch`, `'HrlCity_Shop' not in gyaml`, y contenido original sin prefijo de `DUNGEON_ITEM_PREFIXES`. Objetos que se mueven: los de `KEY_ITEMS` que no están en `excluded_items` y cuyo sitio original es elegible. El resto se queda en su sitio.
  - El `fixed` que se pasa a la lógica se construye así: se parte de `world.vanilla_fixed()` y, para cada sitio elegible, la ubicación OoTR recibe el actor colocado si es un objeto clave, o `'Rupees (5)'` como relleno neutro si no lo es.
  - Algoritmo: *assumed fill* sobre los objetos clave, en orden barajado, colocando primero los progresivos de nivel más alto. Después, el contenido no clave de los sitios elegibles se baraja entre los sitios elegibles que quedan libres. Al final, `world.can_beat(...)` sobre el resultado; si falla, hasta 100 reintentos derivando el RNG de `(seed, intento)`, y después `FillError('No se ha podido generar una semilla completable con estos ajustes')`.
  - RNG: `random.Random(int.from_bytes(hashlib.sha256(f'{RANDO_VERSION}|{seed}|{settings_key}|{attempt}'.encode()).digest()[:8], 'big'))`, donde `settings_key = json.dumps({...ajustes sin semilla, excluded_items ordenados...}, sort_keys=True)`. Los sitios se recorren siempre en orden por Hash; nunca se itera un `set` sin ordenar.
- [ ] **Step 1: Tests**
  - `test_deterministic`: `place(..., Settings(seed='ABC'))` dos veces da resultados iguales.
  - `test_different_seeds_differ`: las semillas `'A'` y `'B'` dan resultados distintos.
  - `test_multiset_preserved`: el multiconjunto de valores de `place` (un valor por Hash) es igual al original.
  - `test_beatable_many`: con 200 semillas `str(i)`, rehacer `fixed` en el test y comprobar que `world.can_beat` es `True` para cada una.
  - `test_excluded_stays`: con `excluded_items=frozenset({'Item_Hookshot'})`, el Hash 16041366920820397198 conserva `Item_Hookshot`.
  - `test_vanilla_mode_identity`: con `key_items_mode='vanilla'`, el resultado es igual al original.
  - `test_dungeon_item_chests_untouched`: todo Hash cuyo original empieza por un prefijo de `DUNGEON_ITEM_PREFIXES` conserva su valor.
  - `test_shop_chests_untouched`: todo Hash con `HrlCity_Shop` en `gyaml` conserva su valor.
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: deterministic fill`.

### Task 9: Parcheo, spoiler y orquestador `generate`

**Files:**
- Create: `randomizer/patch.py`, `randomizer/spoiler.py`, `randomizer/generate.py`
- Test: `tests/test_generate.py`

**Interfaces:**
- Consumes: `NupArchive`, `GameData`, `ZsCodec`, `Rstb`, `banc_rstb_size`, `place`, `Settings`, `FillError`, `items.LABELS_ES`.
- Produces:
  - `patch.write_mod(game: GameData, placement: dict[int, str], mod_root: Path) -> list[str]`: reescribe cada mapa que tenga al menos un cofre cambiado, aplicando el cambio a todas las copias de cada Hash, y actualiza la RSTB. Devuelve las rutas romfs escritas, ordenadas.
  - `spoiler.build(settings: Settings, placement: dict[int, str], chests: list[ChestActor], loc_map: dict[int, LocationEntry], game_version: str) -> dict` y `spoiler.to_text(d: dict) -> str`. El texto está en español y tiene las secciones `Semilla`, `Ajustes`, `Versión del randomizer`, `Versión del juego`, `Objetos clave` (nombre en español → ubicación OoTR y zona), `Todos los cofres` y `Excluidos / sin asociar`.
  - `def safe_seed_name(seed: str) -> str`: NFKD, quita las marcas diacríticas, cambia cada carácter fuera de `[A-Za-z0-9_-]` por `-`, junta los `-` repetidos, quita `-` al principio y al final, y limita a 40 caracteres. Si queda vacía, `ValueError`.
  - `class GenerationError(Exception)`, con `.exists: bool = False` y mensaje en español.
  - `def generate(nup_path: str, out_dir: str, settings: Settings, overwrite: bool = False) -> GenerateResult`, con `@dataclass GenerateResult: seed: str; mod_dir: str; spoiler_txt: str | None; spoiler_json: str | None; changed_files: list[str]`.
    - Si `settings.seed` está vacía, la sustituye por 10 caracteres alfanuméricos de `secrets` antes de todo.
    - Valida que `update_version == 131072`; si no, `GenerationError('Versión del juego no soportada: ...')`. Convierte `NupError` y `FillError` en `GenerationError`, con el mismo mensaje.
    - Si `mod_dir` (`<out_dir>/Rando_<safe_seed_name>`) existe y `overwrite` es falso → `GenerationError(exists=True)`.
    - Escribe todo en `<mod_dir>.tmp` y al final lo renombra a `mod_dir` (con `overwrite`, borra antes el antiguo). En cualquier excepción, borra `.tmp` y vuelve a lanzarla. Los spoilers van en `mod_dir/spoiler.txt` y `mod_dir/spoiler.json`, fuera de `romfs/`.
- [ ] **Step 1: Tests**
  - `test_safe_seed_name`: `'Mi semilla ñ/1'` → `'Mi-semilla-n-1'`, `'///'` → `ValueError`, y `'a'*60` → longitud 40.
  - `test_failed_generation_leaves_nothing` (skipUnless `OOT_NUP`): con `unittest.mock.patch('randomizer.fill.World.can_beat', return_value=False)`, `generate` lanza `GenerationError`, y ni `mod_dir` ni `mod_dir.tmp` existen después.
  - `test_existing_dir_not_overwritten` (skipUnless `OOT_NUP`): dos `generate` con la misma semilla; el segundo lanza `GenerationError` con `exists is True` y no cambia el sha256 de los archivos.
  - `test_generate_byte_identical` (skipUnless `OOT_NUP`): dos generaciones con la misma semilla en dos `out_dir` distintos producen los mismos archivos con el mismo sha256.
  - `test_generated_files_reread` (skipUnless `OOT_NUP`): cada mapa escrito se descomprime, se carga con `byml.load` y su `Drop__DropActor` coincide con `placement` para todas las copias de cada Hash. Cada entrada de la RSTB del mod de un mapa escrito es igual a `banc_rstb_size(len(raw))`.
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: patch writer, spoiler, generate`.

## Fase 4 — Interfaz web

### Task 10: Servidor local

**Files:**
- Create: `randomizer/web/__init__.py`, `randomizer/web/server.py`, `randomizer/__main__.py`, `randomizer/config.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `generate`, `GenerationError`, `NupArchive`, `NupError`, `Settings`, `items.KEY_ITEMS`, `items.LABELS_ES`.
- Produces:
  - `python -m randomizer [--port 8765] [--no-browser]`: arranca `ThreadingHTTPServer` solo en `127.0.0.1` y abre el navegador con `webbrowser.open`, salvo con `--no-browser`.
  - `def make_server(port: int, config_path: Path) -> ThreadingHTTPServer`, usada por los tests con `port=0`.
  - `config.load(path: Path) -> dict` / `config.save(path: Path, d: dict)`: `user_config.json` en la raíz del proyecto, con `{nup_path, out_dir, last_settings}`. Si el archivo no existe o está corrupto, devuelve `{}`.
  - `GET /` → `web/static/index.html`; `GET /static/<f>` sirve solo archivos de `web/static/`.
  - `GET /api/config` → la configuración.
  - `POST /api/validate {"nup_path"}` → `{"ok": true, "version": "1.1.1"}` o `{"ok": false, "error": "<es>"}`. Si la ruta no existe, el error es `"El archivo no existe: <ruta>"`. Si la versión no es la soportada, `ok: false` con el mensaje de versión.
  - `GET /api/items` → `[{"actor": "Item_Hookshot", "label": "Gancho"}, ...]`, los 15 objetos en el orden de `KEY_ITEMS`.
  - `POST /api/generate {"nup_path", "out_dir", "seed", "key_items_mode", "excluded_items": [], "spoiler": bool, "overwrite": bool}` → `{"ok": true, "seed", "mod_dir", "spoiler_txt"}`, `{"ok": false, "exists": true, "error"}` o `{"ok": false, "error"}`. Si va bien, guarda la configuración.
  - `GET /api/spoiler?path=<ruta>` → el texto del spoiler (`text/plain; charset=utf-8`) **solo si** la ruta resuelta está dentro del `out_dir` de la configuración y termina en `spoiler.txt`; en otro caso, 403.
  - Las excepciones no controladas devuelven HTTP 500 con `{"ok": false, "error": "Error interno: <tipo>"}` y la traza en la consola.
- [ ] **Step 1: Tests** (el servidor corre en un hilo con `make_server(0, tmp/config.json)`; `generate` se sustituye con `unittest.mock.patch('randomizer.web.server.generate')`)
  - `test_validate_bad_path`: `/api/validate` con una ruta inexistente → `ok: false` y un error que empieza por `"El archivo no existe"`.
  - `test_generate_exists_flag`: el `generate` simulado lanza `GenerationError('x', exists=True)` → la respuesta tiene `ok: false` y `exists: true`.
  - `test_generate_ok_saves_config`: el `generate` simulado devuelve un `GenerateResult` → `ok: true`, y `config.json` contiene `nup_path` y `out_dir`.
  - `test_spoiler_path_traversal`: `/api/spoiler?path=C:/Windows/win.ini` → 403.
  - `test_items_labels`: `/api/items` devuelve 15 elementos y todos los `label` son no vacíos.
  - `test_index_served`: `GET /` → 200, y el HTML contiene `General`, `Objetos`, `Lógica` y `Spoiler` (este test pasa después de la Task 11).
- [ ] **Step 2:** Ejecutar y comprobar que falla. **Step 3:** Implementar, con un `index.html` provisional que contenga los cuatro nombres de pestaña. **Step 4:** Ejecutar y comprobar que pasa. **Step 5:** Commit `feat: local web server`.

### Task 11: Página con pestañas (maqueta B)

**Files:**
- Modify: `randomizer/web/static/index.html`
- Create: `randomizer/web/static/app.js`, `randomizer/web/static/style.css`

**Interfaces:**
- Consumes: la API de la Task 10.
- Contenido:
  - **General**: campo "Ruta del juego (.nup)" que valida al perder el foco con `/api/validate` y muestra "✔ Versión 1.1.1 detectada" o el error; campo "Carpeta de salida (carpeta de mods de Lichii para este juego)"; campo "Semilla" con botón 🎲 que genera 10 caracteres alfanuméricos en el cliente; botón **Generar**.
  - **Objetos**: un desplegable "Objetos clave" con las opciones `Vanilla` y `Cualquier cofre` (por defecto), y casillas "Excluir objetos" con `/api/items`. En gris y desactivadas, con la etiqueta "(próximamente)": "Llaves pequeñas", "Mapas y brújulas", "Canciones", "Objetos de NPCs", "Rupias y consumibles". Nota: "Los cofres del minijuego de la Plaza del Mercado y los que tienen llaves, mapas o brújulas no reciben objetos clave en esta versión."
  - **Lógica**: "Sin glitches" marcado y desactivado; texto "Toda semilla generada se puede completar."
  - **Spoiler**: casilla "Generar registro de spoilers" (activada por defecto); después de generar, un enlace "Ver registro" que carga `/api/spoiler?path=...` en un `<pre>`.
  - Al generar: el botón se desactiva y muestra "Generando…". Si la respuesta trae `exists`, aparece `confirm('Ya existe Rando_<semilla>. ¿Sobrescribir?')` y se reintenta con `overwrite: true`. Si va bien: "✔ Mod Rando_<semilla> creado en <mod_dir>. Desactiva otros mods Rando_* de este juego en Lichii." Si falla: el mensaje de error en rojo.
  - Al cargar, los ajustes se rellenan con `/api/config`.
  - Colores definidos como variables CSS con tema oscuro (`prefers-color-scheme`). Funciona a 375 px de ancho: las pestañas hacen scroll horizontal y la página no.
- [ ] **Step 1:** Implementar los tres archivos.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_server -v`. Se espera PASS, incluido `test_index_served`.
- [ ] **Step 3:** Verificación manual: `python -m randomizer --no-browser`, abrir `http://127.0.0.1:8765` en el navegador interno, recorrer las 4 pestañas y comprobar el ancho de 375 px con `resize_window`. Con el `.nup` real: validar → generar con semilla `PRUEBA1` → aparece el mensaje de éxito y "Ver registro" muestra el spoiler. Generar otra vez → aparece la confirmación de sobrescritura.
- [ ] **Step 4:** Commit `feat: tabbed web UI`.

## Fase 5 — Cierre

### Task 12: Prueba de aceptación y documentación

**Files:**
- Modify: `README.md` (requisitos, `python -m randomizer`, cómo instalar el mod en Lichii, limitaciones de la v1, atribución y licencia de OoTR)
- Create: `docs/acceptance.md` (lista para el usuario)

- [ ] **Step 1:** `python -m unittest -v` en verde, con `OOT_NUP` definido. Sin ningún test fallido; los únicos `skip` permitidos son ninguno cuando `OOT_NUP` está definido.
- [ ] **Step 2:** Generar la semilla de aceptación desde la interfaz y dar al usuario `docs/acceptance.md`, que incluye: instalar el mod, empezar una partida nueva, comprobar 3 objetos clave según el spoiler y jugar hasta Ganon.
- [ ] **Step 3:** Commit `docs: README and acceptance checklist`.
- [ ] **Step 4 (PUERTA):** El usuario completa una semilla. Los fallos que aparezcan se apuntan como bugs, con su semilla y su spoiler.

## Fuera de este plan

- **Editar eventos (BFEVFL):** se hace en un plan aparte, solo si la PUERTA R1 marca Hash con `needs_event_patch`. Mientras tanto, esos cofres se quedan con su contenido original.
- Todo lo que el spec marca como no-objetivo de la v1.
