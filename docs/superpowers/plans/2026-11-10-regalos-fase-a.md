# Regalos — Fase A: Plan de construcción

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poder cambiar el objeto que entrega una escena (parámetro de texto en un BFEVFL) y comprobar en Lichii si una escena puede entregar un objeto clave distinto. Es la puerta de la fase A del diseño.

**Architecture:**
- Se amplía el lector BFEVFL para que lea los contenedores de parámetros de las acciones y reescriba un parámetro de texto.
- Primero se intenta reutilizar una cadena que ya exista en el archivo. Si no existe, se amplía el archivo y se actualiza la RSTB con margen.
- Una herramienta genera el lote de prueba `TestLote7`: Saria entrega el Gancho en lugar de la Ocarina de las Hadas.

**Tech Stack:** Python 3.14, solo stdlib.

**Spec:** `docs/superpowers/specs/2026-11-10-regalos-design.md` (§4.1, §4.4 A y §7)

## Global Constraints

- Nunca se escribe en el `.nup` ni se hace commit de archivos del juego. Los tests con juego usan `OOT_NUP` y `@unittest.skipUnless(NUP_PATH, 'OOT_NUP no definido')`, y se ejecutan con `python -m unittest` (sin `-I`).
- Solo biblioteca estándar. Los mensajes de cara al usuario van en español y los commits no llevan líneas de atribución.
- Con todos los interruptores apagados, el mod y la clave del RNG son idénticos a los de hoy (spec §7).
- En esta fase no se toca el reparto (`fill.py`) ni la página: solo la herramienta y el lote de prueba.

## Review Focus

1. Un parámetro de texto compartido por varias acciones, o una cadena compartida en el pool: cambiar una acción no debe cambiar las demás. Test en la tarea 1.
2. Un flujo que también recorta "Saltar cinemáticas": los dos cambios conviven sobre los mismos bytes. Test en la tarea 1.
3. Un archivo ampliado: todos los punteros internos siguen siendo válidos y el lector vuelve a leer el archivo entero sin errores. Test en la tarea 1.
4. Un texto nuevo que ya existe en el pool: se reutiliza y el tamaño no cambia. Test en la tarea 1.
5. Un lote de prueba regenerado sobre uno existente: la herramienta reemplaza de forma segura, igual que `make_cutscene_batch.py`. Test en la tarea 2.

---

### Task 1: Leer y reescribir parámetros de texto en BFEVFL

**Files:**
- Modify: `randomizer/formats/bfevfl.py`
- Test: `tests/test_bfevfl.py`

**Interfaces:**
- Consumes: `EventFlow` y `patch_pointers` de este mismo módulo.
- Produces:
  - `EventFlow.action_params(index: int) -> dict[str, object]`: los parámetros de una acción o subflujo. Los textos van como `str`; el resto se convierte a valores Python.
  - `set_string_param(data: bytes, event_index: int, key: str, value: str) -> bytes`: devuelve el archivo con ese parámetro cambiado. Se reutiliza una cadena existente si la hay; si no, se amplía el archivo. Lanza `BfevflError` si el evento no tiene ese parámetro de texto.
  - `string_param_owners(data: bytes, event_index: int, key: str) -> list[int]`: los eventos que comparten el mismo hueco del parámetro, para detectar el riesgo 1.
- **El implementador investiga primero** el formato del contenedor de parámetros (la lista de parámetros que cuelga del evento) en flujos reales. Ejemplos de la exploración: `Dm_Kokiri_0155` eventos 51 y 52 (`Item_Ocarina_Fairy`) y `GatheringTokenGold` evento 250 (`TakenRewardActor: 'Obj_Rupee_Gold'`). El formato se documenta en el docstring.

- [ ] **Step 1: Tests (OOT_NUP)**
  - `test_read_gift_params`: `action_params` de `Dm_Kokiri_0155` en los eventos 51 y 52 contiene el valor `'Item_Ocarina_Fairy'` en alguna clave. El test descubre la clave y la fija.
  - `test_set_string_param_roundtrip`: cambiar ese parámetro a `'Item_Hookshot'` y volver a leer da `'Item_Hookshot'`. Todos los demás parámetros de todos los eventos y todos los `pointer_slots()` quedan iguales.
  - `test_reuse_existing_string`: si el valor nuevo ya está en el pool del archivo, la longitud no cambia.
  - `test_grow_file_valid`: con un valor que no existe en el pool, el archivo crece y `EventFlow(nuevo)` lee el mismo número de eventos. Además, `pointer_slots()` da los mismos índices.
  - `test_other_events_untouched`: si otro evento usa la misma cadena (`string_param_owners` devuelve más de uno), cambiar uno no altera el texto que lee el otro.
  - `test_coexists_with_trim`: aplicar `patch_pointers` (recorte) y después `set_string_param`, o al revés, da en ambos casos un archivo válido con los dos cambios.
- [ ] **Step 2:** Ejecutar `python -m unittest tests.test_bfevfl -v`. Se espera un FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Volver a ejecutar los tests y después la suite completa. Se espera un PASS.
- [ ] **Step 5:** Commit con el mensaje `feat: read and rewrite BFEVFL string params`.

### Task 2: Lote de prueba 7 (Saria entrega el Gancho)

**Files:**
- Create:
  - `tools/make_gift_batch.py`
  - `docs/test-batch-7.md`

**Interfaces:**
- Consumes: `set_string_param`, `string_param_owners`, `ZsCodec`, `NupArchive`, `Rstb` y `randomizer.patch.RSTB_PATH`.
- Produces: `python -I tools/make_gift_batch.py <nup> <out_dir>`, que escribe `<out_dir>/romfs/Event/EventFlow/Dm_Kokiri_0155.bfevfl.zs` con los parámetros de los eventos 51 y 52 cambiados de `Item_Ocarina_Fairy` a `Item_Hookshot`.
  - Si el archivo cambia de tamaño, se escribe también la RSTB con la entrada del flujo actualizada (`Event/EventFlow/Dm_Kokiri_0155.bfevfl`), con valor = valor original + (tamaño nuevo − tamaño original) redondeado hacia arriba a 0x100, más un margen de 0x1000.
  - El reemplazo es seguro, como en `tools/make_cutscene_batch.py`: solo reemplaza una carpeta vacía o que solo contenga `romfs`.
  - Si `string_param_owners` indica que el texto lo comparten eventos fuera de 51 y 52, la herramienta para con `FALLO: ...` y no escribe nada.

- [ ] **Step 1:** Implementar la herramienta y generar `test-mod/0400486024DEC000/TestLote7` (ignorado por git).
- [ ] **Step 2:** Escribir `docs/test-batch-7.md` en español, con casillas:
  - partida nueva y solo este mod activo;
  - salir del bosque y despedirse de Saria en el puente;
  - ¿recibes el Gancho en vez de la Ocarina?, ¿sale en el inventario y se puede usar?;
  - ¿la escena termina bien, sin cuelgue ni pantalla negra?;
  - ¿la Ocarina de las Hadas no aparece? (es lo esperado);
  - una sección de "Resultados" vacía.
- [ ] **Step 3:** Ejecutar la suite completa. Se espera un PASS.
- [ ] **Step 4:** Commit con el mensaje `test: gift test batch 7 (Saria gives Hookshot)`.

### Puerta (después de la tarea 2)

El usuario prueba `TestLote7` en Lichii.
- **Si funciona:** se escribe el plan de la fase B (ocarinas, Tarjeta Gerudo, recompensas de Skulltulas, ranas y Loach con la lógica y la página).
- **Si no funciona:** se para y se vuelve al usuario (spec §7).
