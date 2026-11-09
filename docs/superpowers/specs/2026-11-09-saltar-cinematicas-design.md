# Opción "Saltar cinemáticas" — Diseño

Estado: borrador para aprobación. Parte del randomizer v1 (rama `feat/v1`, diseño base en `2026-11-08-oot-remake-randomizer-design.md`).

## 1. Qué es y por qué

El usuario prueba semillas del randomizer en Lichii empezando siempre partidas nuevas. Las cinemáticas largas y las charlas de la historia le hacen perder mucho tiempo:

- Algunas el juego deja saltarlas con un botón.
- Otras hay que verlas enteras. La que ha citado es **la primera escena**, la introducción del Bosque Kokiri.
- Las conversaciones no se pueden saltar.

Quiere una opción más en la página, **"Saltar cinemáticas"**, para jugar más rápido. Primero para las pruebas de aceptación y después en cualquier semilla.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos**
- Con la opción activada, la introducción del Bosque Kokiri se puede saltar con el botón de saltar del juego.
- Con la opción activada, las escenas de la historia montadas como flujos de eventos se reproducen sin sus pasos que solo muestran:
  - diálogos;
  - cámara y animaciones;
  - esperas y efectos visuales.
  Se conservan todos los pasos que cambian la partida.
- La historia avanza exactamente igual que si se hubiera visto la escena:
  - los mismos indicadores de partida quedan activados;
  - se reciben los mismos objetos y canciones;
  - se acaba en el mismo sitio y la misma zona.

**No-objetivos**
- No se tocan las charlas normales de personajes (tiendas, aldeanos, minijuegos), los mensajes de Navi, los carteles ni los textos al recibir un objeto.
- No se acelera el texto ni se cambia la velocidad de los vídeos.
- Los créditos finales y la pantalla de título se quedan como están.

**Anti-objetivos (sería un fracaso aunque "funcione")**
- Que una partida se quede bloqueada o pierda un objeto, canción o indicador por haber saltado una escena.
- Que activar la opción cambie dónde se colocan los objetos: la misma semilla debe dar la misma colocación con la opción activada o no.
- Escribir en el `.nup` o meter archivos del juego en el repositorio.

## 3. Hechos comprobados (exploración del 2026-11-09)

- **Flujos de eventos:** `romfs/Event/EventFlow/*.bfevfl.zs`, 914 archivos (487 con prefijo `Dm_`). El formato es BFEVFL con el flowchart `EVFL` en `u64(u64(0x28))`.
  - Los actores ocupan 0x38 bytes cada uno y los eventos 0x30.
  - Un evento de tipo acción (tipo 0) guarda en `+0x0A` el `u16` del evento siguiente, y en `+0x0C` y `+0x0E` el índice del actor y de la acción.
  - Un switch (tipo 1) guarda su lista de casos en `+0x18`; cada caso ocupa 0x10 bytes, con el valor (u32) y el evento (u16 en +4).
  - Un fork (tipo 2) guarda su lista de ramas (u16) en `+0x10` y el join en `+0x0C`.
  - Un join (tipo 3) y un subflujo (tipo 4) guardan el siguiente en `+0x0A`.
  - Los puntos de entrada ocupan 0x20 bytes, con el evento principal en `+0x1C`.
  - Hay un lector de exploración en el scratchpad de la sesión (`evflib.py`). Es desechable y hay que reescribirlo con tests.
- **Ajustes de eventos:** `RSDB/EventSetting.Product.111.rstbl.byml.zs` tiene 2380 filas. Cada una lleva su `EventSettingComponentList`, su flujo y su punto de entrada.
- **Bloqueo de salto:** solo 3 listas de componentes incluyen `SkipSetting/DisableSkip` (`IsDisableSkip: True`):
  - `Dm_Kokiri_0000`: la introducción, que es la escena que citó el usuario;
  - `Dm_Title_0005`;
  - `Dm_StaffCredit_0005`.

  Están en `Event/EventSetting/EventSettingComponentList/<nombre>.engine__event__EventSettingComponentList.bgyml`, en BYML sin comprimir.
- **Acciones más usadas en todos los flujos** (por número de apariciones):

  | Acción | Veces |
  |---|---|
  | `Npc_EventStarter.EventTalk` | 5038 |
  | `EventWait` | 3226 |
  | `GameDataActor.EventTriggerSetGameDataBool` | 3058 |
  | `EventCamera.EventMoveToTargetPosCamera` | 2086 |
  | `Player_Event.EventPlayerPlayASForFlowchart` | 1493 |
  | `EventTalk` de personajes concretos | muchas |

  Cambian la partida, entre otras: `EventTriggerSetGameData*`, `EventTriggerAddOrSubGameDataInt`, `PouchSystemActor.EventTriggerAddOrRemovePouchContent`, `EventTransition`, `EventReserveBancChange`, los `Warp*`, `EventTriggerRequestAutoSave` y `EventTriggerSetEventBool`.
- Las escenas se pueden recortar sin tocar la tabla RSTB **si el archivo no cambia de tamaño**. Para eso basta con reescribir en su sitio los índices de evento (u16).

## 4. Comportamiento

### 4.1 Opción
- Nuevo ajuste `skip_cutscenes: bool` en `Settings`, desactivado por defecto.
- En la página va como casilla "Saltar cinemáticas", en la pestaña General.
- Se guarda en la configuración del usuario como el resto de opciones.
- **No forma parte de la clave de ajustes del RNG** (como `spoiler`): no cambia la colocación.
- El spoiler indica si estaba activada.
- En modo Vanilla de objetos clave con la opción activada, el mod se genera igualmente, solo con los cambios de escenas. El aviso de "sin cambios" solo sale si no hay ningún cambio.

### 4.2 Desbloquear el salto de la introducción
- Con la opción activada, el mod incluye `Dm_Kokiri_0000…EventSettingComponentList.bgyml` sin el componente `SkipSetting`. Su entrada RSTB no se toca: el archivo nuevo es más pequeño, y el valor RSTB es un límite superior de búfer. Si alguna vez saliera más grande, la generación falla.
- `Dm_Title_0005` y `Dm_StaffCredit_0005` no se tocan.

### 4.3 Recortar escenas de la historia
- **Qué escenas:** una lista fija y versionada de flujos/puntos de entrada "de historia" en `randomizer/data/`.
  - La construye una herramienta (`tools/`) a partir de los prefijos `Dm_`, `Get_Stone*`, `Sage*`, `Meet_*`, `Goto_*`, `MelodyGet_*`, `SubEvent_Get*`, `Get_Epona`, `DoorOfTime`, `OpeningEvent` y los puntos de entrada de historia de los flujos de Zelda, Impa, Saria, Darunia, Ruto, Nabooru, Rauru y Sheik.
  - Después se revisa a mano.
  - Las charlas normales de personajes quedan fuera.
- **Qué pasos se quitan:** solo acciones de una **lista blanca de acciones que solo muestran**:
  - diálogos (`EventTalk`, burbujas);
  - cámara;
  - animaciones (`EventPlayAS`, `EventPlayerPlayASForFlowchart`);
  - esperas (`EventWait`);
  - giros y miradas;
  - profundidad de campo y luz;
  - vibración;
  - sonido y música;
  - movimientos de Navi.

  Cualquier acción que no esté en la lista blanca se conserva. Fundidos, transiciones, teletransportes y cambios de zona se conservan siempre.
- **Diálogos con elección:** un `EventTalk` cuyo resultado lee un nodo de decisión (switch) posterior **no** se quita.
- **Cómo:** se reescriben en su sitio todos los índices que apuntan a una acción quitada para que apunten a la primera acción conservada que la sigue, en cadena. Eso incluye:
  - el "siguiente" de acciones, joins y subflujos;
  - los casos de los switch;
  - las ramas de los forks;
  - el evento principal de los puntos de entrada.

  Ningún evento cambia de tamaño ni de posición, así que el archivo mantiene su tamaño y no hay cambios de RSTB. Si una cadena quitada acaba en "fin" (0xFFFF), se apunta a "fin".

### 4.4 Salida
- Los flujos modificados van recomprimidos a `romfs/Event/EventFlow/...`, igual que los bancs.
- La generación sigue siendo determinista: misma semilla y opciones dan los mismos bytes.

## 5. Pruebas

- Tests unitarios:
  - lector y reescritor BFEVFL: ida y vuelta sin cambios byte a byte;
  - un recorte que conserva todas las acciones que cambian la partida en cada punto de entrada;
  - clave de ajustes sin `skip_cutscenes`;
  - casilla en la página.
- **Pruebas en el juego por tandas** (mods de prueba como los `TestLote`), empezando por:
  1. la introducción (salto con botón; ver §6b);
  2. el Árbol Deku hasta la Esmeralda Kokiri, con la fase 1;
  3. Zelda y la Canción de Zelda;
  4. los sabios.

  Cada tanda tiene una guía en `docs/` con lo que se debe recibir y dónde se debe acabar.

## 6. Hecho cuando

- La introducción se salta con el botón.
- Una partida nueva con la opción activada llega a la Esmeralda Kokiri y a la Canción de Zelda sin diálogos de historia y sin perder nada.
- Los tests pasan.
- La semilla de aceptación se regenera con la opción y el usuario la juega.

## 6b. Decisiones tomadas tras la revisión (decisión mía, no del usuario)

- **Salto de la introducción, primero como prueba.** No se sabe si el botón de saltar del motor ejecuta o se salta las acciones que quedan en `Dm_Kokiri_0000`.
  - La primera tanda es solo la introducción, con el salto desbloqueado.
  - El usuario comprueba que después todo sigue igual: Navi, la charla con Saria y la entrada al Árbol Deku.
  - Si se pierde algo, la introducción pasa a recortarse como en §4.3 en vez de desbloquear el salto.
- **La lista blanca se amplía por fases, cada una probada en el juego antes de la siguiente.**
  - **Fase 1:** diálogos (`EventTalk` sin elección, burbujas), esperas (`EventWait`), cámara, giros y miradas, profundidad de campo y luz, vibración y comentarios de desarrollo (`EventDemoProductSupportComment`).
  - **Fase 2:** animaciones del jugador y de los personajes (`EventPlayAS`, `EventPlayerPlayASForFlowchart`, `EventPlayerMove*`), sonido y música, y movimientos de Navi. Esta fase solo entra si la fase 1 no rompe nada. Las animaciones pueden mover al jugador hasta una marca, así que van aparte.
- **Forks y joins:** nunca se quitan ni se reestructuran. Si recortar una rama de un fork la dejara vacía (apuntando directamente al join o a "fin"), esa rama no se recorta.
- **Cofres con eventos del randomizer:** el reparto actual no edita flujos; solo quita `GetEventName` en los bancs. El recorte es la única edición de BFEVFL, así que no hay conflicto. Recortar `Get_StoneOfForest_GetSword` y similares solo quita su parte visual.
- **Qué comprueban los tests:** por cada punto de entrada, el grafo recortado tiene que ser igual al original con los nodos quitados "contraídos". Es decir, cada camino del original, quitando las acciones de la lista blanca, es un camino del recortado y al revés. Además, ninguna acción fuera de la lista blanca desaparece.
- **Compresión:** los flujos se leen y escriben con el mismo `ZsCodec` (diccionario según la ruta) que los bancs. Van al mod en la misma ruta `romfs/Event/EventFlow/<nombre>.bfevfl.zs`. Los `.bgyml` de ajustes van sin comprimir.

## 7. Lo que se deja a quien lo construya

- La lista exacta de puntos de entrada de historia y de acciones de la lista blanca, partiendo de §4.3 y de los datos.
- Cómo detectar qué switch depende de un diálogo con elección (por ejemplo, consultas de resultado de diálogo inmediatamente después del `EventTalk`).
- Si un punto de entrada resulta peligroso de recortar en las pruebas, se saca de la lista: es mejor ver una escena que bloquear la partida.

## 8. Ampliación 1 (2026-11-09, aprobada por el usuario)

Resultado de la tanda 2 en el juego: llega al Árbol Deku sin cuelgues ni pérdidas. Pero siguen saliendo conversaciones que el usuario quiere quitar, como Mido cortando el paso o el tutorial de fijar el blanco. Estaban fuera por el no-objetivo de §2 (charlas de personajes y mensajes de Navi).

**Nueva regla, que sustituye ese no-objetivo:**
- **Se recortan las conversaciones que saltan solas o cortan el paso**, aunque estén en flujos de personajes (`Npc_*`) o de Navi (`NaviHint` y similares).
  - Ejemplos: Mido bloqueando, los Kokiri que explican controles, los avisos forzados de Navi (por ejemplo `NaviLockOnHint`), Saria en el puente, Zelda en el jardín, Impa.
- **Se quedan las que elige el jugador:**
  - hablar con un personaje acercándose a él;
  - tiendas;
  - minijuegos;
  - pedir una pista a Navi con su botón.
- **Lo que la charla comprueba o da se conserva:**
  - las comprobaciones (switch), los objetos y los indicadores no se quitan nunca;
  - siguen valiendo todas las reglas de §4.3, §6b y la revisión final: bucles, diálogos con elección y punteros a "fin".
- **Alcance de esta ampliación:** primero, la infancia (Bosque Kokiri, Árbol Deku, Campo de Hyrule, Mercado, Castillo y Kakariko). El resto vendrá en otra ampliación, tras probar esta.
- **Cómo se elige:** una lista revisada a mano de pares (flujo, entrada) en `cutscenes.json`, apoyada por una herramienta que encuentra las conversaciones forzadas (cómo se disparan en los bancs y en EventSetting).
  - Ante la duda, una conversación se deja.
- **Prueba en el juego:** `TestEscenas3`, desde partida nueva hasta el Árbol Deku y el Castillo/Kakariko.

### 8.1 Ronda 2 (2026-11-09, tras jugar la semilla de aceptación)

- **Las pistas de juego no se recortan nunca.** El Deku del Árbol Deku que da la clave del orden perdía la charla porque `Get_StoneOfForest` era "*".
  - `tools/build_cutscene_list.py` tiene una lista `KEEP_TALKS` de pares (flujo, entrada) que se quedan: los Dekus del Árbol Deku, Navi ante la puerta de Darunia, el altar de las piedras, pistas de Navi en mazmorras, el minijuego del Deku de las dianas y enseñar máscaras.
  - Un flujo "*" con alguna de ellas pasa a ser la lista de sus demás entradas. También salen las entradas de flujos de historia a las que llaman como subflujo, en cadena. El recorte ya protege todo lo que se alcanza desde una entrada no listada, así que `cutscenes.py` no cambia.
  - Ante la duda, una charla se deja.
- **El Kokiri que corta la salida** (`Npc_Kokiri_007_Child`): se añade `Near_FirstReaction` (globo lanzado por un activador de zona). Es un solo globo que acaba en "fin", así que la regla de punteros a fin lo conserva. Lo que el Kokiri sigue diciendo al chocar con él son diálogos seguidos de un switch (azar, indicadores), que la regla de diálogos con elección conserva; cambiar eso es cambiar una regla de seguridad y queda para decidir.
