# Regalos — Fase B: Plan de construcción

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a la página los interruptores de las ocarinas, la Tarjeta Gerudo, las recompensas de Skulltulas, las ranas y el pez Loach. Con un interruptor encendido, los regalos de esas escenas entran en el reparto.

**Architecture:**
- Un archivo de datos (`gift_map.json`) asocia cada regalo con su ubicación de OoTR, su flujo, los eventos y claves que hay que cambiar, y el objeto original.
- El reparto trata los regalos activos como sitios más. Un regalo solo recibe objetos `Item_*` del conjunto que se mueve, y todos los regalos activos reciben uno.
- Los originales menores de los regalos (`Obj_*`) pasan a los cofres.
- El mod reescribe los parámetros de texto con `set_string_param`, encima del recorte de "Saltar cinemáticas" si está activo. También actualiza la RSTB si el flujo crece.

**Tech Stack:** Python 3.14, solo stdlib.

**Spec:** `docs/superpowers/specs/2026-11-10-regalos-design.md` (§4.2, §4.3, §4.4 B y §7). La fase A está superada en el juego (`docs/test-batch-7.md`).

## Global Constraints

- Nunca se escribe en el `.nup` ni se hace commit de archivos del juego.
- Los tests que usan el juego llevan `@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')` y se ejecutan con `python -m unittest` (sin `-I`).
- Solo biblioteca estándar. Los textos de cara al usuario van en español y los commits no llevan líneas de atribución.
- Compatibilidad (spec §7): con todos los interruptores nuevos apagados, la clave del RNG, el reparto y el mod son idénticos a los de hoy. Los ajustes nuevos solo entran en la clave cuando están encendidos.
- Lo que puede ir en un regalo (spec §7): solo objetos `Item_*`, es decir, los objetos clave del reparto y los `Item_*` originales de los regalos activos.
- Escenas compartidas (spec §7): solo se cambia un parámetro que sea de ese sitio. Si `string_param_owners` muestra eventos ajenos, el sitio queda fuera.
- Si un sitio no se puede confirmar (no se sabe qué evento es, o el regalo se puede recibir más de una vez), queda fuera y se documenta. No bloquea a los demás (spec §6).
- La lógica de OoTR se carga con `vanilla_settings.json` sin cambios. Ninguno de estos ajustes aparece en las reglas vendidas (`grep` del 2026-11-10); solo cambian qué sitios entran en el reparto.

## Review Focus

1. **Ocarinas fuera de orden.** Si la Ocarina del Tiempo se consigue antes que la de las Hadas, la lógica cuenta nivel 2 y no la rebaja al recibir la otra. Además, en vanilla (sin interruptores) la Puerta del Tiempo sigue siendo alcanzable. Test en la tarea 2.
2. **Todos los regalos activos reciben un objeto.** Nunca queda un regalo vacío ni recibe un objeto `Obj_*` o `TBox_*`. Los cofres reciben exactamente los objetos que quedan. Test en la tarea 3.
3. **Regalo en un flujo que también recorta "Saltar cinemáticas".** El evento del regalo sigue siendo alcanzable tras el recorte, y los dos cambios llegan al mismo archivo. Test en la tarea 4.
4. **Un flujo que crece.** La RSTB del mod lleva la entrada de ese flujo, aunque no haya ningún Banc cambiado. Test en la tarea 4.
5. **Datos o petición inválidos.** Una ubicación o un ajuste que no existe en OoTR, o un interruptor que no es booleano en la petición, da un error claro y no genera nada. Tests en las tareas 1 y 5.

---

### Task 1: Datos de los regalos

**Files:**
- Create:
  - `randomizer/data/gift_map.json`
  - `randomizer/gifts.py`
  - `tests/test_gifts.py`

**Interfaces:**
- Consumes: `EventFlow`, `string_param_owners` (`randomizer/formats/bfevfl.py`) y `ootr_data.load_locations()`.
- Produces, en `randomizer/gifts.py`:
  - `GiftSite`, una dataclass congelada con estos campos:
    - `location: str` (ubicación de OoTR, que hace de id);
    - `option: str` (nombre del ajuste en `Settings`);
    - `flow: str` (ruta sin `.zs`, por ejemplo `'Event/EventFlow/Dm_Kokiri_0155.bfevfl'`);
    - `edits: tuple[tuple[int, str], ...]` (pares evento y clave);
    - `original: str` (actor original).
  - `GIFT_MAP_PATH` y `load_gift_map(path=GIFT_MAP_PATH) -> dict[str, GiftSite]` (por ubicación).
  - `OPTIONS: tuple[tuple[str, str], ...]`, con el ajuste y su etiqueta en español, en este orden:
    - `('shuffle_ocarinas', 'Ocarinas (Shuffle Ocarinas)')`
    - `('shuffle_gerudo_card', 'Tarjeta Gerudo (Shuffle Gerudo Card)')`
    - `('shuffle_skulltula_rewards', 'Recompensas de Skulltulas (Shuffle 100 Skulltula Reward y de 10 a 50)')`
    - `('shuffle_frogs', 'Piezas de corazón de las ranas')`
    - `('shuffle_loach_reward', 'Premio del pez Loach (Shuffle Hyrule Loach Reward)')`
  - `available_options() -> list[tuple[str, str]]`: las de `OPTIONS` con al menos un sitio en el mapa.
- Formato del JSON: `{"<ubicación OoTR>": {"option": ..., "flow": ..., "edits": [[evento, "clave"], ...], "original": ..., "note": ...}}`.

Sitios confirmados por la exploración del 2026-11-10 (`action_params` sobre el juego):

| Ubicación OoTR | option | flow (`Event/EventFlow/…bfevfl`) | edits | original |
|---|---|---|---|---|
| LW Gift from Saria | shuffle_ocarinas | Dm_Kokiri_0155 | (51,'Actor'), (52,'ActorName') | Item_Ocarina_Fairy |
| HF Ocarina of Time Item | shuffle_ocarinas | Dm_MelodyGet_Time | (106,'Actor'), (255,'ActorName') | Item_Ocarina_Time |
| Hideout Gerudo Membership Card | shuffle_gerudo_card | Dm_Gerudo_0025 | (120,'ActorName') | Item_Token_Gerudo |
| Kak 10 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (245,'TakenRewardActor') | Item_Wallet_Medium |
| Kak 20 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (246,'TakenRewardActor') | Item_AgonyStone |
| Kak 30 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (247,'TakenRewardActor') | Item_Wallet_Large |
| Kak 40 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (248,'TakenRewardActor') | Item_BombchuBundle_Large |
| Kak 50 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (249,'TakenRewardActor') | Obj_Heart_Piece |
| Kak 100 Gold Skulltula Reward | shuffle_skulltula_rewards | GatheringTokenGold | (250,'TakenRewardActor') | Obj_Rupee_Gold |

Sin confirmar; los decide el implementador:
- **Ranas.** `MiniGame_FrogTenors`: eventos 71 y 91 (`Obj_Heart_Piece`, con `IsRetry` false y true), 72 y 92 (`Obj_Rupee_Blue`) y 247 (`Obj_Heart_Piece`). Hay que averiguar cuál es "ZR Frogs in the Rain" y cuál "ZR Frogs Ocarina Game", y si la rama `IsRetry` puede volver a dar el premio.
- **Pez Loach.** `MiniGame_Fishing`, eventos 655 a 660 (rupias). Hay que averiguar si alguno es el premio del Loach ("LH Loach Fishing") y si se da una sola vez.
- **Regla para los dos casos.** Solo entra un sitio que tenga un evento claro y se reciba una vez. Si no, queda fuera y se explica en `docs/superpowers/specs/2026-11-10-regalos-design.md` §8 (sección nueva "Fase B: sitios descartados"). `available_options()` oculta entonces esa opción.

- [ ] **Step 1: Tests**
  - Tests sin juego:
    - `test_map_loads`: `load_gift_map()` devuelve `GiftSite` y cada `option` está en `dict(OPTIONS)`.
    - `test_locations_exist`: cada clave existe en `ootr_data.load_locations()`.
    - `test_bad_option_rejected`: un JSON temporal con `option` desconocida o una ubicación inexistente hace que `load_gift_map(path)` lance `ValueError`, con la ubicación en el mensaje.
    - `test_available_options`: solo salen opciones con sitios, en el orden de `OPTIONS`.
  - Test con `OOT_NUP`, `test_sites_match_game`:
    - para cada sitio y cada edit, `action_params(evento)[clave] == original`;
    - `set(string_param_owners(...))` está contenido en los eventos de ese sitio.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_gifts -v`. Se espera un FAIL.
- [ ] **Step 3:** Investigar las ranas y el Loach con el lector BFEVFL, siguiendo las ramas `switch`, las consultas de los eventos y los indicadores. Escribir el JSON y `gifts.py`, y documentar en el spec §8 lo que se descarte.
- [ ] **Step 4:** Ejecutar los tests y la suite completa. Se espera un PASS.
- [ ] **Step 5:** Commit con el mensaje `feat: gift site map`.

### Task 2: Objetos de los regalos en la lógica

**Files:**
- Modify:
  - `randomizer/items.py`
  - `randomizer/logic/rules.py` (`State.collect`)
  - `randomizer/logic/world.py` (`vanilla_fixed`, `_relevant`)
- Test: `tests/test_logic.py`

**Interfaces:**
- Produces, en `items.py`:
  - `GIFT_ITEMS: dict[str, str]`, de actor a objeto OoTR:
    - `Item_Ocarina_Fairy` → `'Ocarina'`
    - `Item_Ocarina_Time` → `'Ocarina'`
    - `Item_Token_Gerudo` → `'Gerudo Membership Card'`
    - `Item_Wallet_Medium` → `'Progressive Wallet'`
    - `Item_Wallet_Large` → `'Progressive Wallet'`
    - `Item_AgonyStone` → `'Stone of Agony'`
    - `Item_BombchuBundle_Large` → `'Bombchus (10)'`
  - En `ITEM_LEVEL`, añadir:
    - `Item_Ocarina_Fairy` → `('Ocarina', 1)` y `Item_Ocarina_Time` → `('Ocarina', 2)`;
    - `Item_Wallet_Medium` → `('Progressive Wallet', 1)` y `Item_Wallet_Large` → `('Progressive Wallet', 2)`.
  - `GIFT_ITEM_HOME: dict[str, str]`, de actor a ubicación vanilla, para los siete actores de `GIFT_ITEMS`:
    - `Item_Ocarina_Fairy` → 'LW Gift from Saria'
    - `Item_Ocarina_Time` → 'HF Ocarina of Time Item'
    - `Item_Token_Gerudo` → 'Hideout Gerudo Membership Card'
    - `Item_Wallet_Medium` → 'Kak 10 Gold Skulltula Reward'
    - `Item_AgonyStone` → 'Kak 20 Gold Skulltula Reward'
    - `Item_Wallet_Large` → 'Kak 30 Gold Skulltula Reward'
    - `Item_BombchuBundle_Large` → 'Kak 40 Gold Skulltula Reward'
  - `LABELS_ES` añade:
    - Ocarina de las Hadas
    - Ocarina del Tiempo
    - Tarjeta Gerudo
    - Bolsa de rupias grande
    - Bolsa de rupias gigante
    - Piedra de la Agonía
    - Bombchus (10)
  - `ALL_ITEMS = {**KEY_ITEMS, **GIFT_ITEMS}`.
- `rules.State.collect` y `World._relevant` aceptan cualquier actor de `ALL_ITEMS`.
- `World.vanilla_fixed` pone también los actores de `GIFT_ITEM_HOME`. Hace falta porque `'Ocarina'` y `'Progressive Wallet'` pasan a ser `LEVELED`, y dos `'Ocarina'` genéricas ya no suman nivel 2.
- `KEY_ITEMS`, `KEY_ITEM_HOME` y la lista de la página no cambian.

- [ ] **Step 1: Tests**
  - `test_vanilla_still_beatable`: `World(load_vanilla_settings()).can_beat(world.vanilla_fixed())` sigue siendo el mismo resultado que hoy.
  - `test_door_of_time_vanilla`: con `vanilla_fixed()` se alcanza 'Song from Ocarina of Time'. También se alcanza al menos una ubicación de 'Temple of Time' que pide `(Ocarina, 2)`, porque `stones_oot_sot` exige la Ocarina del Tiempo.
  - `test_ocarina_out_of_order`: `State()` que recoge `Item_Ocarina_Time` y después `Item_Ocarina_Fairy` tiene `items['Ocarina'] == 2`.
  - `test_wallet_out_of_order`: lo mismo con las carteras.
  - `test_no_other_leveled_vanilla`: ninguna ubicación de `locations.json` con `vanilla_item` en `{'Ocarina', 'Progressive Wallet'}` queda fuera de `GIFT_ITEM_HOME.values()`.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_logic -v`. Se espera un FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Ejecutar la suite completa. Se espera un PASS, y `test_fill` y `test_generate` sin cambios.
- [ ] **Step 5:** Commit con el mensaje `feat: gift items in logic`.

### Task 3: Reparto con regalos

**Files:**
- Modify: `randomizer/fill.py`
- Test: `tests/test_fill.py`

**Interfaces:**
- Consumes: `GiftSite` y `load_gift_map` (tarea 1), y `GIFT_ITEMS` y `ALL_ITEMS` (tarea 2).
- Produces:
  - `Settings` añade los campos `shuffle_ocarinas`, `shuffle_gerudo_card`, `shuffle_skulltula_rewards`, `shuffle_frogs` y `shuffle_loach_reward`, todos `bool = False`.
  - `_settings_key` quita cada uno de esos campos cuando vale `False`. Así la clave con todo apagado es idéntica a la de hoy.
  - `place_full(chests, loc_map, world, settings, gift_map: dict[str, GiftSite]) -> tuple[dict[int, str], dict[str, str]]`: el reparto de cofres (como hoy) y el de regalos (ubicación → actor), solo para los regalos activos.
  - `place(...)` se queda con la misma firma y el mismo resultado: llama a `place_full` con `{}` y devuelve el primer elemento.
- Reglas del reparto:
  - **Regalos activos:** los de `gift_map` cuyo ajuste está encendido en `settings`. En modo `vanilla` no hay ninguno.
  - **Objetos que se mueven:** los objetos clave de los cofres, como hoy, más los originales de los regalos activos que estén en `GIFT_ITEMS`.
  - **Originales menores:** son los que no están en `GIFT_ITEMS`, como `Obj_Heart_Piece` y `Obj_Rupee_Gold`. Van al montón `rest`, que rellena cofres.
  - **Sitios libres:** los cofres libres de hoy más los regalos activos. Un regalo solo acepta objetos del conjunto que se mueve.
  - **Base de la lógica:** los regalos activos se ponen a `FILLER` en la base, igual que los cofres elegibles.
  - **Elección de sitio en cada paso del *assumed fill*.** `g` es el número de regalos vacíos y `r` el de objetos que quedan por colocar, incluido el actual:
    - si `g == r`, los candidatos son solo los regalos vacíos alcanzables;
    - si no, con probabilidad `g / r` (usando el RNG del intento) se elige entre los regalos vacíos alcanzables, y si no hay ninguno, entre los cofres;
    - en el otro caso se elige entre los cofres libres alcanzables, como hoy;
    - si un conjunto de candidatos queda vacío, el intento devuelve `None`.
  - **Cuentas:** cofres libres que quedan = `len(rest)`, sin `strict=False`. `_fixed` usa `ALL_ITEMS` en vez de `KEY_ITEMS`.

- [ ] **Step 1: Tests** (con el fixture de cofres que ya usa `test_fill` y los sitios de verdad de `load_gift_map()`)
  - `test_all_off_identical`: `place(...)` y `place_full(..., load_gift_map())[0]` con `Settings(seed='X')` son iguales. Además `_settings_key` es igual al de un `Settings` sin los campos nuevos, comparando el JSON contra una cadena fija generada hoy.
  - `test_gifts_filled_with_items`: con `shuffle_ocarinas` y `shuffle_skulltula_rewards` encendidos, cada regalo activo recibe un actor de `ALL_ITEMS`, ninguno `Obj_*` ni `TBox_*`, y `World.can_beat` es `True` con el resultado.
  - `test_minor_originals_go_to_chests`: `Obj_Heart_Piece` (50 Skulltulas) y `Obj_Rupee_Gold` (100) aparecen en algún cofre del reparto. El multiconjunto de contenidos de cofres y regalos es el de antes, con los regalos activos incluidos.
  - `test_deterministic`: misma semilla y mismos ajustes dan el mismo resultado. Encender `shuffle_ocarinas` cambia la clave.
  - `test_vanilla_mode_no_gifts`: con `key_items_mode='vanilla'`, el diccionario de regalos está vacío.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_fill -v`. Se espera un FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Ejecutar la suite completa. Se espera un PASS.
- [ ] **Step 5:** Commit con el mensaje `feat: place items in NPC gifts`.

### Task 4: Escribir los regalos en el mod y en el spoiler

**Files:**
- Modify:
  - `randomizer/gifts.py`
  - `randomizer/patch.py`
  - `randomizer/generate.py`
  - `randomizer/spoiler.py`
- Test: `tests/test_gifts.py`, `tests/test_generate.py`

**Interfaces:**
- Consumes:
  - `set_string_param`;
  - `build_cutscene_files(game) -> dict[str, bytes]` (rutas `.zs` y datos comprimidos);
  - `place_full` (tarea 3);
  - `Rstb`, `RSTB_PATH` y `GameData` (`game.codec`, `game.nup`).
- Produces:
  - `gifts.build_gift_files(game, gifts: dict[str, str], gift_map, base_files: dict[str, bytes]) -> tuple[dict[str, bytes], dict[str, int]]`. Devuelve los archivos (los de `base_files` más los flujos de regalos) y los valores RSTB de los flujos que crecen.
    - Para cada flujo se parte de `base_files[flow + '.zs']` descomprimido si existe. Si no, se parte del `.nup`.
    - Se aplican todas las ediciones de los regalos de ese flujo cuyo actor no sea el original.
    - Si el flujo crece, el valor RSTB es el original + (crecimiento redondeado hacia arriba a 0x100) + 0x1000, igual que `tools/make_gift_batch.py`.
  - `patch.write_mod(..., extra_files=None, extra_rstb: dict[str, int] | None = None)`. Aplica `extra_rstb` a la misma RSTB y la escribe también si no hay Bancs cambiados pero `extra_rstb` no está vacío.
  - `generate` llama a `place_full` y a `build_gift_files` (sobre `extras` si se saltan cinemáticas) y pasa `extra_rstb`. Los errores `BfevflError` se convierten en `GenerationError('No se pudieron preparar los regalos: …')`.
  - `spoiler.build(..., gifts: dict[str, str] | None = None)` añade la clave `'regalos'`: una lista ordenada de `{'ubicacion', 'objeto'}` con `LABELS_ES`. `to_text` añade la sección "Regalos" solo si hay alguno. "Shuffle" en los ajustes del spoiler lista los interruptores encendidos.

- [ ] **Step 1: Tests** (con OOT_NUP)
  - `test_build_gift_files_roundtrip`: Saria pasa a `Item_Gauntlet_Silver`, que es más largo y obliga a crecer. Al releer el flujo, los dos edits dan el actor nuevo y hay un valor RSTB para ese flujo.
  - `test_gift_over_trim`:
    - Con `base_files = build_cutscene_files(game)`, si `Dm_Kokiri_0155` u otro flujo de regalo está en `base_files`, el resultado contiene a la vez el recorte (los punteros de `base_files`) y el actor nuevo.
    - Cada evento de edición sigue siendo alcanzable desde algún punto de entrada. El test incluye un recorrido sencillo por `next`, `cases`, `forks` y `join`.
  - `test_write_mod_rstb_without_banc`: `write_mod` con colocación vanilla y `extra_rstb={'Event/EventFlow/X.bfevfl': 123}` escribe la RSTB, y al cargarla `get` da 123.
  - `test_generate_all_on`:
    - Una semilla con los cinco interruptores escribe los flujos de regalos.
    - El spoiler JSON tiene `'regalos'` con un elemento por regalo activo.
    - Con todo apagado, la lista de archivos escritos es idéntica a la de hoy.
- [ ] **Step 2:** Ejecutar los tests. Se espera un FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Ejecutar la suite completa. Se espera un PASS.
- [ ] **Step 5:** Commit con el mensaje `feat: write NPC gifts to the mod and spoiler`.

### Task 5: Sección "Shuffle" en la página

**Files:**
- Modify:
  - `randomizer/web/server.py`
  - `randomizer/web/static/index.html`
  - `randomizer/web/static/app.js`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `gifts.available_options()` y los campos nuevos de `Settings`.
- Produces:
  - El GET de configuración añade `'shuffle_options': [{'key', 'label'}]`, en el orden de `available_options()`.
  - El POST acepta cada clave como booleano estricto, igual que `skip_cutscenes`. Si no es booleano, devuelve un error 400 `'<clave> debe ser true o false'`. Una clave que no está en `available_options()` también da error 400.
  - La página tiene, en el panel Objetos, un `<fieldset>` con la leyenda "Shuffle". Lleva una casilla por opción, con id `shuffle-<clave>`, desmarcadas por defecto. Se guardan y se cargan como las demás opciones de la página.

- [ ] **Step 1: Tests**
  - `test_shuffle_options_listed`
  - `test_shuffle_strict_bool` (un `"yes"` da 400)
  - `test_unknown_shuffle_key_400`
  - `test_shuffle_passed_to_settings`: el `Settings` que llega a `generate` lleva `shuffle_ocarinas=True`.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_server -v`. Se espera un FAIL.
- [ ] **Step 3:** Implementar. Comprobar la página en el navegador del panel, con capturas de la sección.
- [ ] **Step 4:** Ejecutar la suite completa. Se espera un PASS.
- [ ] **Step 5:** Commit con el mensaje `feat: Shuffle section in the web UI`.

### Task 6: Lote de prueba 8 (semilla con todo encendido)

**Files:**
- Create: `docs/test-batch-8.md`

- [ ] **Step 1:** Generar `output/test/Rando_TestRegalos1` (ignorado por git) con estos ajustes:
  - semilla `TestRegalos1`;
  - `any_chest`;
  - todos los interruptores de Shuffle encendidos;
  - "Saltar cinemáticas" activado;
  - spoiler activado.

  Se genera con `python -m randomizer` o con la función `generate`, y se apunta qué recibió cada regalo.
- [ ] **Step 2:** Escribir `docs/test-batch-8.md` en español, con casillas:
  - partida nueva y solo este mod;
  - una tabla con lo que da cada regalo según el spoiler;
  - comprobar cada regalo alcanzable sin mucho esfuerzo: Saria, Ocarina del Tiempo, recompensa de 10 Skulltulas, ranas o Loach si entraron;
  - ¿llega el objeto nuevo y se puede usar a esa edad?;
  - si una ocarina sale antes que la otra, ¿se pueden tocar canciones?, ¿se rebaja alguna al recibir la segunda?;
  - si la Tarjeta Gerudo está fuera de la fortaleza: ¿se abre la puerta del Centro de Entrenamiento con la tarjeta conseguida en otro sitio? ¿Las guardias se vuelven amigas al rescatar a los carpinteros sin la tarjeta? Es el riesgo de §3.5;
  - cartera grande y gigante fuera de orden;
  - una sección de "Resultados" vacía.
- [ ] **Step 3:** Ejecutar la suite completa. Se espera un PASS.
- [ ] **Step 4:** Commit con el mensaje `test: gift test batch 8 (all Shuffle on)`.

### Puerta (después de la tarea 6)

El usuario prueba `Rando_TestRegalos1` en Lichii.
- **Si funciona:** se escribe el plan de la fase C (judías y mercaderes caros).
- **Si un tipo de regalo falla:** ese sitio se saca de `gift_map.json`, se documenta, y los demás siguen.
