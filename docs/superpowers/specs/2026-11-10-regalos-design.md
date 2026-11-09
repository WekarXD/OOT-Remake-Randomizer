# Regalos de personajes y escenas en el reparto — Diseño

Estado: borrador para aprobación. Proyecto 1 de 2 para añadir las opciones "Shuffle" del generador de OoTR (v9.1.0). El proyecto 2 (objetos menores por el mundo) va después, con su propio diseño. Rama: `feat/v1` (o una rama nueva desde ella, a criterio de quien lo construya).

## 1. Qué es y por qué

El usuario quiere las opciones Shuffle de OoTR en el randomizer del remake. Hoy los objetos clave solo se reparten en cofres.

La prueba `TestLote6` demostró que los objetos clave (`Item_*`) no se pueden soltar por el mundo. Se dibujan, pero no se pueden coger (`docs/test-batch-6.md`). Así que la única forma de tener más sitios para objetos clave son los **regalos de personajes y escenas**. El objeto que entrega un personaje es un parámetro de texto dentro de su flujo de eventos (`.bfevfl`), por ejemplo `{'ActorName': 'Item_Ocarina_Fairy'}`.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos.** Que cada una de estas opciones de OoTR aparezca como interruptor en la página, desactivado por defecto. Con el interruptor encendido, esos sitios entran en el reparto:

| Opción (nombre OoTR) | Sitios (exploración del 2026-11-10) |
|---|---|
| Shuffle Ocarinas | Ocarina de las Hadas (`Dm_Kokiri_0155`, eventos 51 y 52) y Ocarina del Tiempo (`Dm_MelodyGet_Time`, eventos 106 y 255) |
| Shuffle Gerudo Card | `Dm_Gerudo_0025` evento 120, `Item_Token_Gerudo` |
| Shuffle Magic Beans | Vendedor de judías, `Npc_Hylia_047_Child` (con `SimpleShop`; se puede comprar varias veces) |
| Shuffle Expensive Merchants | Medigoron (`Shop_Sword_Giant`), vendedor de la alfombra (`Npc_Hylia_044_Adult`), abuela de las pociones (`Npc_Hylia_053_Adult`) |
| Shuffle 100 Skulltula Reward (+ las de 10 a 50) | `GatheringTokenGold` eventos 245 a 250 |
| Shuffle Hyrule Loach Reward | `MiniGame_Fishing` eventos 655 a 660 (rama del pez Loach por confirmar) |
| Pieza de corazón de las ranas | `MiniGame_FrogTenors` evento 247 |
| Shuffle Child / Adult Trade Sequence Items | Ver §4.4. Va en la última fase. |

- La lógica de OoTR ya vendida en el repositorio decide si la semilla se puede completar, con esos ajustes encendidos.
- La misma semilla con los mismos ajustes da siempre el mismo mod.

**No-objetivos**
- Objetos menores por el mundo (Skulltulas, jarrones, cajas, colmenas, rupias sueltas, Deku vendedores): son el proyecto 2.
- Vacas, objetos "maravilla" y notas sueltas de ocarina: no se pueden hacer así o el remake no los tiene.
- Cambiar el modelo o el texto que muestra la escena: vale el objeto que se recibe, igual que en los cofres (aceptado en la v1).

**Anti-objetivos**
- Una partida bloqueada porque un regalo no se entrega, se entrega dos veces o te quita un objeto que no debe.
- Que con todos los interruptores apagados cambie algo respecto a hoy.
- Escribir en el `.nup` o meter archivos del juego en el repositorio.

## 3. Hechos y riesgos conocidos

- Los regalos son parámetros de texto en acciones como `SUB Dm_SY_GetInEvent:* {'ActorName': ...}`, `PouchSystemActor.EventTriggerAddOrRemovePouchContent {'Actor': ...}` o `SimpleShop {'ActorName': ...}`. Hay pruebas en `scratchpad/shuffle-recon` (`flows_dump.txt`), regenerables con el lector BFEVFL.
- Hoy solo sabemos reescribir índices u16 en su sitio. Cambiar un texto puede requerir:
  - apuntar a una cadena que ya exista en el archivo;
  - o añadirla y mover lo que haga falta, con lo que cambia el tamaño. Entonces hay que actualizar la RSTB del flujo, y su fórmula no se conoce.
- Riesgos que la construcción tiene que resolver o descartar:
  1. **Regalos repetibles** (judías, pesca): el objeto del reparto se da una sola vez.
  2. **Cobros** (judías, mercaderes): el precio va ligado al objeto (`PriceParam`).
  3. **Intercambios:** cada entrega va emparejada con una retirada `Num:-1` del objeto anterior.
  4. **Escenas compartidas** (`SimpleShop` evento 63, `Dm_SY_GetInEvent`): no se puede cambiar algo que usan otras escenas.
  5. **Que un `Item_*` entregado por escena funcione en el juego:** la Tarjeta Gerudo y la Ocarina lo hacen en el juego original, pero un objeto distinto en ese sitio hay que probarlo.

## 4. Comportamiento

### 4.1 Herramienta de parámetros de texto
- Módulo nuevo que reescribe el parámetro de texto de una acción concreta (flujo, evento, clave) y devuelve el archivo nuevo, comprimido igual que los demás.
- Si cambia el tamaño, actualiza la entrada RSTB del flujo con un valor seguro, mayor o igual que el necesario.
- Tests de ida y vuelta: leer, cambiar y volver a leer da el texto nuevo, y el resto del flujo queda igual.
- Si el mismo flujo lo modifica también "Saltar cinemáticas", los dos cambios se aplican sobre los mismos bytes y se escribe un solo archivo. El recorte de escenas solo cambia índices, así que ambos casos pueden convivir.

### 4.2 Sitios y lógica
- Cada sitio nuevo se asocia a su ubicación de OoTR (`locations.json`) en un archivo de datos versionado: flujo, evento, clave del parámetro y objeto original.
- La lógica de OoTR se carga con los ajustes correspondientes (`shuffle_ocarinas`, `shuffle_gerudo_card`, `shuffle_beans`, `shuffle_expensive_merchants`, `shuffle_100_skulltula_rupees` y similares para las recompensas de Skulltulas, `shuffle_loach_reward`, `shuffle_frog_song_rupees`, `shuffle_child_trade` / `adult_trade_shuffle`; los nombres exactos salen de los ajustes de OoTR vendidos). Con un ajuste apagado, su sitio conserva el objeto original.
- Los objetos originales de esos sitios entran en el conjunto de objetos que se reparten cuando su opción está encendida.

### 4.3 Página y spoiler
- Nueva sección "Shuffle" en la pestaña Objetos, con un interruptor por opción, en español y con el nombre de OoTR entre paréntesis.
- Los ajustes forman parte de la clave del RNG, porque cambian el reparto.
- El spoiler lista los sitios nuevos con su objeto.

### 4.4 Fases (cada una con su prueba en Lichii antes de seguir)
- **A.** Herramienta de texto, más una prueba en el juego: la recompensa de 10 Skulltulas da otro objeto clave. Si un `Item_*` entregado así no funciona, se para y se replantea.
- **B.** Ocarinas, Tarjeta Gerudo, recompensas de Skulltulas, pieza de corazón de las ranas y Loach.
- **C.** Judías y mercaderes caros: regalos repetibles y cobros.
- **D.** Intercambios de niño y de adulto.

## 5. Hecho cuando

- Las opciones existen en la página y en el spoiler.
- Cada fase tiene su lote de prueba superado en Lichii.
- Los tests pasan.
- Una semilla con todo encendido se puede jugar hasta Ganon siguiendo la lógica.

## 6. Lo que se deja a quien lo construya

- Cómo reescribir textos en BFEVFL (reutilizar cadenas o ampliar el archivo).
- La lista exacta de sitios y la confirmación de cada uno en los datos.
- Cómo hacer que un regalo repetible dé el objeto del reparto solo una vez, por ejemplo con un indicador que ya exista. Si no hay forma segura, ese sitio queda fuera y se documenta.
- Si una opción resulta inviable en su fase, se documenta y se deja fuera sin bloquear las demás.

## 7. Decisiones tras la revisión (decisión mía, no del usuario)

- **Qué objetos pueden ir en un regalo:** solo los que se entregan como `Item_*`:
  - los objetos clave del reparto actual;
  - los `Item_*` originales de los sitios activados (ocarinas, Tarjeta Gerudo, espada de Medigoron…).

  Los originales menores (rupias de la pesca o de las 100 Skulltulas, pieza de corazón de las ranas) se tratan como el contenido de un cofre con rupias en la v1: el sitio puede recibir un objeto clave, y su objeto menor se resuelve como ya hace hoy el reparto. Esto se fija en la fase A con un test.
- **Si la fase A falla** (un `Item_*` distinto no se entrega bien por escena), se para el proyecto y se vuelve al usuario. Las fases B, C y D se planifican pero no se construyen hasta superar la A.
- **RSTB:** se prefiere reutilizar una cadena que ya exista en el flujo, para que el tamaño no cambie. Si hay que ampliar el archivo, se usa un valor RSTB con margen generoso, porque la tabla es un límite superior y ya se ha comprobado que valores mayores funcionan.
- **Fases C y D** (regalos repetibles, cobros e intercambios): empiezan con una investigación corta. Si no hay forma segura (indicador existente, parámetro por personaje), el sitio queda fuera y se documenta.
- **Escenas compartidas:** solo se cambia lo que pertenece a un único personaje o sitio. Si el parámetro está en un evento compartido sin forma de distinguir quién lo llama, ese sitio queda fuera.
- **Lógica:** cada sitio debe existir en el `locations.json` vendido, y cada ajuste en los ajustes de OoTR vendidos. Si falta alguno, el sitio queda fuera y se documenta.
- **Compatibilidad:** con todos los interruptores apagados, la clave del RNG y el mod generado son idénticos a los de hoy. Los ajustes nuevos solo entran en la clave cuando están encendidos. Hay un test que lo comprueba.
