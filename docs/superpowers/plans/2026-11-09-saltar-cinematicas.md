# Saltar cinemáticas — Plan de construcción

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir la opción "Saltar cinemáticas". Desbloquea el salto de la introducción y quita los pasos que solo muestran (fase 1) en las escenas de historia, conservando todo lo que cambia la partida.

**Architecture:**
- El lector BFEVFL convierte cada flujo en un grafo.
- Una función pura calcula qué eventos quitar y cómo redirigir cada índice.
- El reescritor parchea esos índices u16 en su sitio, sin cambiar el tamaño.
- Un módulo de política (lista de flujos y de acciones en `randomizer/data/cutscenes.json`) produce los archivos extra del mod.
- `write_mod` los escribe junto a los bancs.

**Tech Stack:** Python 3.14, solo stdlib (`compression.zstd`, `unittest`).

**Spec:** `docs/superpowers/specs/2026-11-09-saltar-cinematicas-design.md`

## Global Constraints

- Nunca se escribe en el `.nup` ni se hacen commits con archivos del juego. Los tests que leen el juego usan `OOT_NUP` y llevan `@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')`.
- Solo biblioteca estándar. El código de OoTR no se ejecuta.
- `skip_cutscenes` **no** entra en la clave de ajustes del RNG: la misma semilla da la misma colocación con la opción activada o no.
- Los flujos recortados tienen **exactamente el mismo tamaño** que el original y no se tocan sus entradas RSTB.
- La lista de componentes de la introducción reescrita debe ser de tamaño **≤ al original**. En ese caso se mantiene su valor RSTB, que es un límite superior de búfer. Si no lo es, la generación falla con error.
- Fase activa: **solo la fase 1** de acciones. La fase 2 queda en los datos pero no se aplica.
- Nunca se quitan forks, joins, switch ni subflujos. Tampoco se quita un `EventTalk` cuyo siguiente evento sea un switch (diálogo con elección).
- Los mensajes de cara al usuario van en español. Los commits no llevan líneas de atribución.

## Review Focus

1. **Evento compartido entre una entrada de historia y una que no lo es** (por ejemplo, un flujo de Zelda con charla normal). Se espera que no se recorte. Test en la tarea 3.
2. **Rama de fork que quedaría vacía.** Se espera que se conserve la primera acción de esa rama. Test en la tarea 2.
3. **Cadena de eventos quitados que acaba en "fin" (0xFFFF) o en un ciclo.** Se espera que se redirija a 0xFFFF sin bucle infinito. Test en la tarea 2.
4. **Modo Vanilla con la opción activada.** Se espera que el mod se genere solo con los archivos de escenas, sin el aviso de "sin cambios". Test en la tarea 4.
5. **Configuración guardada sin `skip_cutscenes`** (usuarios de antes). Se espera que la casilla salga desmarcada y que no haya error. Test en la tarea 4.

---

### Task 1: Lector y parcheador BFEVFL

**Files:**
- Create: `randomizer/formats/bfevfl.py`
- Test: `tests/test_bfevfl.py`

**Interfaces:**
- Produces:
  - `Event`: dataclass con `index: int`, `kind: int` (0 acción, 1 switch, 2 fork, 3 join, 4 subflujo), `actor: str|None`, `action: str|None`, `query: str|None`, `next: int|None`, `cases: list[int]`, `forks: list[int]`, `join: int|None`.
  - `EventFlow(data: bytes)` con:
    - `.events: list[Event]`;
    - `.entry_points: dict[str, int]` (nombre → evento principal);
    - `.pointer_slots() -> list[tuple[int, int]]`: (desplazamiento en el archivo, índice actual) de **todos** los u16 que referencian un evento. Incluye el siguiente de acciones, joins y subflujos, los casos de switch, las ramas y el join de forks, y el principal de los puntos de entrada.
  - `patch_pointers(data: bytes, new_targets: dict[int, int]) -> bytes`: reescribe cada slot (desplazamiento → nuevo índice). Mantiene la longitud.
- Layout (spec §3):
  - flowchart en `u64(u64(0x28))`;
  - contadores u16 en `EVFL+0x10` (actores, acciones, consultas, eventos, entradas);
  - punteros u64 en `EVFL+0x28/0x30/0x38/0x40` (actores, eventos, diccionario de entradas, entradas);
  - actor de 0x38 bytes: nombre `+0`, acciones `+0x18`, consultas `+0x20`, número de acciones `+0x30`, número de consultas `+0x32`;
  - evento de 0x30 bytes con el tipo en `+8`;
  - diccionario: `DIC ` + n, con la raíz en +8 y las entradas de 0x10 bytes (nombre en +8);
  - entrada de 0x20 bytes con el principal en `+0x1C`;
  - cadenas con prefijo de longitud u16.
  - Un fork guarda el join en `+0x0C`. La raíz del diccionario no es una entrada.

- [ ] **Step 1: Tests**

  En `tests/test_bfevfl.py`, con OOT_NUP:
  - `test_parse_get_stone_of_fire`: `Get_StoneOfFire.bfevfl.zs` tiene 274 eventos y 33 entradas. Desde `entry_points['Get_StoneOfFire_GetBombBag']`, la cadena de acciones es `EventTriggerParticipateEvent → EventTransition → EventNaviRequestBallonMessage → 0xFFFF`.
  - `test_all_flows_parse`: los 914 flujos de `Event/EventFlow/` se leen sin excepción y todo índice en `pointer_slots()` es `< len(events)` o `0xFFFF`.
  - `test_patch_roundtrip`: `patch_pointers(d, {})` devuelve `d` byte a byte. Además, parchear un slot y volver a leer da el nuevo índice en ese slot y el mismo valor en los demás.

- [ ] **Step 2:** Ejecutar `python -I -m unittest tests.test_bfevfl -v`. Se espera un FAIL de importación.

- [ ] **Step 3:** Implementar `randomizer/formats/bfevfl.py` con `struct`. Los slots de puntos de entrada usan el desplazamiento del campo `+0x1C`.

- [ ] **Step 4:** Volver a ejecutarlo. Se espera un PASS.

- [ ] **Step 5:** Commit con el mensaje `feat: BFEVFL reader and in-place pointer patcher`.

### Task 2: Cálculo del recorte (puro, sin juego)

**Files:**
- Create: `randomizer/evtrim.py`
- Test: `tests/test_evtrim.py`

**Interfaces:**
- Consumes: `Event` de la tarea 1.
- Produces: `compute_trim(events: list[Event], removable: set[int]) -> tuple[set[int], dict[int, int]]`. Devuelve `(removed, retarget)`, donde `retarget` asocia cada índice de evento quitado con su destino final (primer evento conservado de la cadena, o `0xFFFF`).

**Reglas:**
- Solo se pueden quitar acciones (kind 0) que estén en `removable`.
- La cadena se sigue por `next`.
- Un ciclo formado solo por eventos quitados acaba en `0xFFFF`.
- Si la rama de un fork se resolviera a su `join` o a `0xFFFF`, la primera acción de esa rama vuelve a conservarse y se recalcula.

- [ ] **Step 1: Tests**

  Los grafos se construyen a mano con `Event(...)`.
  - `test_linear_chain`: `0→1→2→FFFF` con `removable={1}` da `removed={1}` y `retarget={1:2}`.
  - `test_tail_to_end`: con `removable={1,2}`, `retarget[1]==0xFFFF`.
  - `test_cycle_of_removed`: un ciclo `1→2→1` totalmente quitable da `0xFFFF` y termina.
  - `test_non_action_never_removed`: un switch o fork incluido en `removable` no aparece en `removed`.
  - `test_fork_branch_kept`:
    - el fork 0 tiene las ramas [1, 3] y el join 5;
    - las cadenas son `1→2→5` y `3→4→5`;
    - con `removable={1,2,3}`, la rama 1 se resolvería al join, así que 1 se conserva (`1 not in removed`; 2 sí puede quitarse);
    - la rama 3 se resuelve a 4, así que `retarget[3]==4`.
  - `test_contraction_property`: un grafo aleatorio con semilla fija (50 eventos, sin forks) cumple que, para cada camino desde la entrada, la secuencia de acciones conservadas coincide con la del original filtrada. Se recorre con un límite de pasos.

- [ ] **Step 2:** Ejecutar `python -I -m unittest tests.test_evtrim -v`. Se espera un FAIL.

- [ ] **Step 3:** Implementar `compute_trim`.

- [ ] **Step 4:** Volver a ejecutarlo. Se espera un PASS.

- [ ] **Step 5:** Commit con el mensaje `feat: event-flow trim computation`.

### Task 3: Política de escenas y archivos del mod

**Files:**
- Create:
  - `randomizer/data/cutscenes.json`
  - `tools/build_cutscene_list.py`
  - `randomizer/cutscenes.py`
- Test: `tests/test_cutscenes.py`

**Interfaces:**
- Consumes:
  - `EventFlow` y `patch_pointers` (tarea 1);
  - `compute_trim` (tarea 2);
  - `GameData(nup)`, con `.nup.read`, `.nup.list()` y `.codec.compress/decompress(path, data)`;
  - `randomizer.formats.byml.load/dump`.
- Produces:
  - `ACTIVE_PHASE = 1`;
  - `load_policy() -> dict`;
  - `build_cutscene_files(game) -> dict[str, bytes]`: ruta romfs → bytes finales (comprimidos si acaba en `.zs`), en orden determinista.

**`cutscenes.json`:**
- `"intro_component_lists": ["Dm_Kokiri_0000"]`
- `"story_flows"`: `{ "<flujo sin extensión>": "*" | ["<entrada>", ...] }`
- `"actions"`: `{ "1": [[actor|"*", action], ...], "2": [...] }`

**Acciones de la fase 1** (pares exactos, spec §6b):

| Actor | Acción |
|---|---|
| `*` | `EventTalk` |
| `*` | `EventTriggerBalloonMessage` |
| `Npc_Navi` | `EventNaviRequestBallonMessage` |
| `EventSystemActor` | `EventWait` |
| `EventCamera` | `EventMoveToTargetPosCamera` |
| `EventCamera` | `EventMoveCameraAnimationInstructionsForFlowchart` |
| `EventCamera` | `EventBasedOnLookAtCamera` |
| `EventCamera` | `EventTriggerRequestCameraShake` |
| `EventCamera` | `EventSendEventTalkMessageToPlayerCamera` |
| `Player_Event` | `EventPlayerTurnAndLook` |
| `Player_Event` | `EventTriggerPlayerLookAtObject` |
| `*` | `EventNPCTurnToTarget` |
| `*` | `EventTriggerLookAtObject` |
| `Npc_Navi` | `EventNaviLookAtObject` |
| `PostProcessingActor` | `EventSetAdvancedDoFForFlowchart` |
| `PostProcessingActor` | `EventSetDoFForFlowchart` |
| `PostProcessingActor` | `EventNorifyCutChangeForGraphics` |
| `PostProcessingActor` | `EventEditLocationalLight` |
| `GameSystemActor` | `EventTriggerControllerRumble` |
| `DevelopEventSystemActor` | `EventDemoProductSupportComment` |
| `*` | `EventTriggerChangeEmotion` |
| `GameSystemActor` | `EventWaitTalkCameraInterpolationEnd` |

**Acciones de la fase 2:**

| Actor | Acción |
|---|---|
| `*` | `EventPlayAS` |
| `Player_Event` | `EventPlayerPlayASForFlowchart` |
| `Player_Event` | `EventPlayerMove` |
| `Player_Event` | `EventPlayerMoveToAnchor` |
| `SoundSystemActor` | `EventSoundStartSound` |
| `SoundSystemActor` | `EventTriggerSoundReadRiddle` |
| `Npc_Navi` | `EventNaviMoveAroundToPlayer` |
| `Npc_Navi` | `EventNaviMoveAtPos` |

**`story_flows`:**
- Lo genera `tools/build_cutscene_list.py <nup>` y se revisa a mano antes del commit.
- Entra `"*"` para cada flujo cuyo nombre empiece por `Dm_`, `Get_Stone`, `SageOf`, `AllSage`, `Meet_`, `Goto_`, `MelodyGet_`, `SubEvent_Get`, `Get_Epona`, `DoorOfTime`, `OpeningEvent`, `Defeat_Ganon` o `EscapeFromCrumblingGanonCastle`.
- Quedan fuera `DmF_` (Cucco/caída/game over) y `Dm_StaffCredit_*` / `Dm_Title_*`.
- Para los flujos de PNJ `Npc_Hylia_Zelda_*`, `Npc_Hylia_Impa_*`, `Npc_Kokiri_Saria_*`, `Npc_Goron_Darunia_*`, `Npc_Zora_Ruto_*`, `Npc_Gerudo_Nabooru_*`, `Npc_Hylia_Rauru*` y `Npc_Hylia_Sheik_*`, la herramienta escribe la lista de entradas cuyo nombre **no** acaba en `_Talk`, `_Near` ni `_Talk01`… La revisión manual ajusta esa lista. Lo revisado se describe en el mensaje del commit.

**Reglas de `build_cutscene_files`:**
- **Introducción:** se carga `Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml` y se borra `Components['SkipSetting']`. Si no tiene `SkipSetting`, no se incluye. Si el tamaño es mayor que el original, salta `ValueError`.
- **Flujos:** se parte de las acciones `removable` según las acciones de la fase `ACTIVE_PHASE`, sin incluir:
  - un `EventTalk` cuyo `next` sea un switch;
  - eventos alcanzables desde alguna entrada que **no** esté en la lista (para `"*"` todas las entradas cuentan como de historia).

  Después, `compute_trim`, y se convierte `retarget` en `new_targets` para cada slot cuyo índice actual esté en `removed`. Los flujos sin cambios no se incluyen.

- [ ] **Step 1: Tests (con OOT_NUP)**
  - `test_intro_skip_removed`: el bgyml devuelto se carga sin `SkipSetting` y su longitud es `<=` a la del original.
  - `test_flows_same_size`: cada flujo devuelto descomprimido tiene la misma longitud que el original.
  - `test_kept_actions_preserved`: en cada flujo devuelto, el multiconjunto de pares (actor, acción) de los eventos alcanzables desde cada entrada que no son de fase 1 es igual al del original.
  - `test_shared_events_untouched`: en un flujo de PNJ con entradas mixtas, los eventos alcanzables desde una entrada `_Talk` no cambian. Se comparan los slots.
  - `test_choice_talk_kept`: en ningún flujo devuelto se quita un `EventTalk` cuyo `next` original sea un switch.
  - `test_deterministic`: dos llamadas dan bytes idénticos.
  - `test_policy_shape` (sin juego): la fase 1 y la fase 2 no se solapan, y `ACTIVE_PHASE == 1`.

- [ ] **Step 2:** Ejecutar `python -I -m unittest tests.test_cutscenes -v`. Se espera un FAIL.

- [ ] **Step 3:** Ejecutar la herramienta, revisar `cutscenes.json` e implementar `randomizer/cutscenes.py`.

- [ ] **Step 4:** Volver a ejecutarlo. Se espera un PASS.

- [ ] **Step 5:** Commit con el mensaje `feat: cutscene trim policy and mod files`.

### Task 4: Opción en ajustes, generación, spoiler y página

**Files:**
- Modify:
  - `randomizer/fill.py` (`Settings`, `_settings_key`)
  - `randomizer/patch.py` (`write_mod`)
  - `randomizer/generate.py`
  - `randomizer/spoiler.py`
  - `randomizer/web/server.py`
  - `randomizer/web/static/index.html`
  - `randomizer/web/static/app.js`
  - `README.md`
- Test:
  - `tests/test_fill.py`
  - `tests/test_generate.py`
  - `tests/test_server.py`

**Interfaces:**
- Consumes: `build_cutscene_files(game)` de la tarea 3.
- Produces:
  - `Settings.skip_cutscenes: bool = False`;
  - `write_mod(game, placement, mod_root, loc_map, extra_files: dict[str, bytes] | None = None) -> list[str]`. Los extras se escriben tal cual y entran en la lista devuelta. Ya **no** vuelve antes de tiempo si hay extras pero no hay bancs, y en ese caso no escribe la RSTB.

**Cambios:**
- `_settings_key` borra `skip_cutscenes`.
- `generate` llama a `build_cutscene_files(game)` solo si la opción está activada.
- El spoiler añade en Ajustes la línea `Saltar cinemáticas: Sí|No`.
- El servidor acepta `skip_cutscenes` como bool estricto (si no, 400 `"skip_cutscenes debe ser true o false"`) y lo guarda en `last_settings`.
- En la página, la casilla `<input type="checkbox" id="skip-cutscenes">` lleva la etiqueta "Saltar cinemáticas" y va en `panel-general`, debajo de la semilla. Se carga desde `last_settings` solo si es booleano.

- [ ] **Step 1: Tests**
  - `test_skip_cutscenes_not_in_key` (fill): misma semilla con `skip_cutscenes` `True` y `False` da la misma colocación.
  - `test_generate_skip_cutscenes` (generate, OOT_NUP): con la opción, `changed_files` incluye `Event/EventSetting/EventSettingComponentList/Dm_Kokiri_0000.engine__event__EventSettingComponentList.bgyml` y algún `Event/EventFlow/…bfevfl.zs`, y el spoiler contiene `Saltar cinemáticas: Sí`.
  - `test_vanilla_with_skip_cutscenes` (generate, OOT_NUP): con `key_items_mode='vanilla'`, `spoiler=False` y `skip_cutscenes=True`, hay `mod_dir` y en `changed_files` no hay bancs ni RSTB.
  - `test_skip_cutscenes_strict_bool` (server): `"si"` da 400.
  - `test_last_settings_without_skip` (server): una configuración sin la clave se carga sin error.

- [ ] **Step 2:** Ejecutar `python -I -m unittest tests.test_fill tests.test_generate tests.test_server -v`. Se espera un FAIL en los nuevos.

- [ ] **Step 3:** Implementar los cambios y añadir al README una línea en Opciones explicando que solo se quitan los pasos visuales en fase 1.

- [ ] **Step 4:** Ejecutar `python -I -m unittest`. Se espera un PASS, con la misma expectedFailure documentada de antes.

- [ ] **Step 5:** Commit con el mensaje `feat: skip cutscenes option in settings, generation, spoiler and UI`.

### Task 5: Tandas de prueba en el juego

**Files:**
- Create:
  - `tools/make_cutscene_batch.py`
  - `docs/test-cutscenes.md`

**Interfaces:**
- Consumes: `build_cutscene_files`, `GameData`, `NupArchive`.
- Produces: `python -I tools/make_cutscene_batch.py <nup> <out_dir> --only intro|flows|all`, que escribe `<out_dir>/romfs/...` solo con los archivos de escenas (sin bancs ni RSTB).

- [ ] **Step 1:** Implementar la herramienta, que filtra el resultado de `build_cutscene_files` según `--only`.

- [ ] **Step 2:** Generar los mods de prueba en `test-mod/0400486024DEC000/` (ignorado por git):
  - `TestEscenas1` con `--only intro`;
  - `TestEscenas2` con `--only all`.

- [ ] **Step 3:** Escribir `docs/test-cutscenes.md` con lo que hay que comprobar en partida nueva:
  - **Tanda 1:** se puede saltar la introducción con el botón. Después aparecen Navi y Saria, y se puede entrar al Árbol Deku tras conseguir espada y escudo.
  - **Tanda 2:** las escenas del Árbol Deku hasta la Esmeralda Kokiri y de Zelda hasta la Canción de Zelda salen sin diálogos de historia; se reciben la Esmeralda, la Carta de Zelda y la canción, y se acaba en el mismo sitio.
  - Una sección de "Resultados" vacía.

- [ ] **Step 4:** Commit con el mensaje `test: in-game cutscene test batches`.
