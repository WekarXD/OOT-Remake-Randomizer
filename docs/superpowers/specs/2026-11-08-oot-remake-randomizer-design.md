# Randomizer para The Legend of Zelda: Ocarina of Time (remake Switch 2) — Diseño v1

Fecha: 2026-11-08 · Estado: borrador para aprobación

## 1. Qué es y por qué

Un randomizer de objetos para el remake de Ocarina of Time de Switch 2, jugado en el emulador **Lichii**. Cambia qué objeto da cada cofre para que cada partida sea distinta. A la vez, un **motor de lógica garantiza que la partida se puede terminar** sin glitches.

El usuario quiere jugar partidas randomizadas del remake al estilo de los randomizers clásicos de OoT (OoTR). Para el remake no existe ninguno.

**Cómo se usa:** una aplicación local con interfaz web. Eliges tu volcado del juego, ajustas qué se randomiza, pones o generas una semilla y pulsas **Generar**. Sale una carpeta de mod que Lichii carga, y un registro de spoilers.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos v1**
- Randomizar los **objetos clave que hoy están en cofres** (lista en §5.2) entre **cualquier cofre del juego**, incluidos los de rupias. Decisión del usuario.
- Que la lógica garantice que toda semilla generada se puede completar sin glitches.
- Reproducibilidad: la misma semilla, los mismos ajustes y la misma versión del randomizer dan exactamente el mismo resultado.
- Registro de spoilers con dónde ha ido cada objeto.
- Interfaz web local con pestañas, al estilo OoTR (maqueta "B" elegida por el usuario).

**No-objetivos v1** (el usuario quiere ampliarlo más adelante; la arquitectura no debe impedirlo)
- Objetos que se consiguen en eventos o de NPCs: ocarina, canciones, botellas, brazalete Goron, escamas, flechas de fuego y de luz, magia, medallones y piedras, piezas de corazón de minijuegos. Se quedan en su sitio de siempre.
- Llaves pequeñas, gran llave, mapas y brújulas: se quedan donde están.
- Vasijas, hierba, rocas, enemigos y otros sitios que sueltan algo pero no son cofres.
- Randomizar entradas, pistas, multiworld, lógica con glitches, consola real, modificar o reempaquetar el `.nup`.

**Anti-objetivos** (aunque "funcione", sería un fracaso)
- Generar una semilla imposible de completar.
- Modificar el `.nup` del usuario. Solo se lee.
- Que la aplicación incluya o distribuya archivos del juego. Siempre se derivan del volcado propio del usuario en su máquina.

## 3. Restricciones y hechos ya comprobados

Comprobado con prototipos que funcionan, en `spikes/`, y **probado en Lichii por el usuario**:

- **Entrada**: un único `.nup` (formato abierto de la comunidad, ver `a55uka/nup` SPEC.md). El del usuario es `The Legend of Zelda Ocarina of Time [0400486024DEC000][v131072].nup`, de ~25 GB. Contiene dos paquetes: el base (1.0.0) y la actualización v131072 (1.1.1), con los árboles RomFS completos. **Se usan siempre los archivos de la actualización** (`p1/` en `spikes/nuplist.py`). No está cifrado. Cada archivo está guardado en bruto o comprimido con zstd y se puede leer directamente por su offset, sin extraer los 24 GB.
- **Motor**: es el mismo que Tears of the Kingdom, con los mismos formatos.
- **Contenido de los cofres**: está en `romfs/Banc/<Zona>/*.bcett.byml.zs`. Son archivos BYML v7 comprimidos con zstd usando el diccionario `bcett.byml.zsdic`, que está dentro de `romfs/Pack/ZsDic.pack.zs` (un SARC comprimido con zstd sin diccionario). Cada cofre es un actor de `Actors[]` con:
  - `Gyaml`: tipo de actor (`Obj_TBox_A_01`, `Obj_TBox_A_02_NoBake`...),
  - `Hash`: identificador u64 del sitio,
  - `Dynamic.Drop__DropActor`: **el objeto que da**, como texto (por ejemplo `Item_Hookshot` o `TBox_Rupee_Blue`),
  - `Dynamic.GetEventName`: un evento opcional que se lanza al abrir el cofre.
- **Escritura**: `spikes/byml.py` lee y escribe BYML conservando los tipos exactos. Los 160 mapas pasan la prueba de ida y vuelta sin diferencias. El archivo resultante se recomprime con el mismo diccionario.
- **Tabla de tamaños**: si un mapa cambia de tamaño, hay que actualizar su entrada en `romfs/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs`. Es un RESTBL v1 comprimido con zstd sin diccionario, con pares `crc32(ruta sin .zs)` y u32 ordenados, más una pequeña tabla de nombres. Para los mapas, el valor es `redondeo_arriba_32(tamaño_descomprimido) + 264`, una fórmula que coincide exactamente en los 160 mapas.
- **Salida**: una carpeta LayeredFS `<NombreMod>/romfs/<misma ruta que en el juego>`, dentro de la carpeta de mods de Lichii `load/0400486024DEC000/`. Solo contiene los archivos modificados: los mapas tocados y la tabla de tamaños.
- **Probado en el juego**:
  1. Intercambiar el contenido de dos cofres del mismo mapa funciona.
  2. Poner en un mapa un objeto que no tenía (el Gancho en un cofre azul de la casa de Mido) funciona, reescribiendo el mapa entero y actualizando la tabla de tamaños.
- **Entorno**: Windows y Python 3.14, que trae `compression.zstd` de serie. En la sesión de diseño no se pudieron instalar paquetes de terceros con pip, pero el usuario sí puede.

## 4. Inventario de cofres (datos reales)

- 238 actores de cofre con `Drop__DropActor` en los 160 mapas, que corresponden a **203 `Hash` distintos**. Un mismo cofre físico puede aparecer en varios archivos (por ejemplo en los mapas `*_Child_*` y `*_Adult_*`) con el **mismo `Hash`**. **Un sitio lógico es un `Hash`**, y todas sus copias deben recibir siempre el mismo objeto.
- Tipos de cofre: `Obj_TBox_A_01` (+`_NoBake`, `_memo11`), `Obj_TBox_A_02` (+`_NoBake`), `Obj_TBox_A_03` (+`_NoBake`), `Obj_TBox_A_06`, `Obj_TBox_GlassTruth_A_01` (cofres invisibles) y `Obj_HrlCity_Shop_TBox_A_01/_02` (minijuego de los cofres en la Plaza del Mercado).
- El volcado completo de lo que suelta cada cosa está en `spikes/drops.json`.

## 5. Comportamiento v1

### 5.1 Sitios
- **Sitios que pueden recibir objetos clave**: todos los cofres (un sitio por `Hash`), excepto:
  - los cofres del minijuego de la Plaza del Mercado (`Obj_HrlCity_Shop_TBox_*`), *(decisión mía: su contenido depende del minijuego)*;
  - los cofres cuyo contenido original es un objeto de mazmorra (`Item_Dungeon_SmallKey`, `Item_Dungeon_BossKey`, `Item_Dungeon_Map`, `Item_Dungeon_Compass`, `Obj_MiniGame_SmallKey`, `Obj_Dungeon_SmallKey_*`). *Decisión mía: esos objetos no se mueven en v1, así que su cofre tampoco se puede ocupar.*
  - Si un sitio no se puede asociar con seguridad a una ubicación de la lógica (§6), queda fuera del reparto y conserva su contenido original.
- Para el usuario, el resultado es "objetos clave en cualquier cofre, incluidos los de rupias". Las excepciones anteriores se indican en la interfaz y en el registro de spoilers.

### 5.2 Objetos clave del reparto
Los que hoy están en cofres: `Item_Sword_Kokiri`, `Item_Range_SlingShot`, `Item_Boomerang`, `Item_Range_Bow`, `Item_Hookshot`, `Item_Longshot`, `Item_Hammer`, `Item_HeavyBoot`, `Item_HoverBoot`, `Item_Gauntlet_Silver`, `Item_Gauntlet_Gold`, `Item_GlassTruth`, `Item_Shield_Mirror`, `Item_Arrow_Ice` y `Item_BombBag_Small`. Son 15 sitios originales.

### 5.3 Reparto
- Los objetos clave se colocan con la lógica en cualquier sitio permitido.
- **No se pierde ni se duplica nada**: el resto de contenidos de los sitios del reparto (rupias, munición, corazones, escudos, etc.) se mezcla en los huecos que quedan, incluidos los cofres que originalmente tenían objetos clave. El total de objetos del juego no cambia.
- Pestaña Objetos: con "Excluir objetos", el usuario puede marcar objetos clave que se quedan en su cofre original.

### 5.4 Lógica
- Sin glitches. El resto del mundo se comporta como el juego original, con el bosque cerrado, la Puerta del Tiempo normal, las canciones en su sitio, etc. Los objetos de eventos son fijos y la lógica los trata como conseguidos en su sitio original, con sus requisitos.
- El usuario confirma que **la forma de avanzar del remake es igual que la del original**. Por eso **la lógica parte de la de OoTR** (`OoTRandomizer/OoT-Randomizer`, archivos de regiones y reglas, Python, GPL-3.0), configurada para reproducir el juego original salvo los objetos clave en cofres.
- Consecuencia de licencia: si se reutilizan sus archivos, este proyecto se publica como GPL-3.0.
- Hay que tener en cuenta los objetos progresivos y los que dependen de otros: el Gancho largo y el Gancho, los Guanteletes de plata/oro y el brazalete Goron (que es fijo, de un evento), y la Bolsa de bombas como requisito de las bombas. Ver riesgo R2.
- Toda semilla pasa una comprobación final: con el reparto generado, simular la partida desde el inicio y llegar a Ganon. Si falla, se reintenta con la misma semilla de forma determinista, o se aborta con un error claro.

### 5.5 Salida
- La carpeta del mod se llama `Rando_<semilla>` y se escribe en la carpeta de salida elegida, por defecto la de mods de Lichii para este juego.
- El registro de spoilers (legible, y también JSON) indica la semilla, los ajustes, la versión del randomizer, la versión del juego detectada y, para cada sitio, la ubicación de la lógica, el mapa y el objeto. Ahí se marca qué cofres no se pudieron asociar o se excluyeron.
- Generar nunca toca el `.nup`. Si ya existe una carpeta con el mismo nombre, se pregunta antes de sobrescribirla.

### 5.6 Interfaz (maqueta B, con pestañas)
Es una aplicación local: el usuario la arranca y se abre en el navegador.
- **General**: ruta del `.nup` (al elegirla, se valida y se muestra la versión del juego detectada; v1 solo admite la 1.1.1 / v131072), carpeta de salida, semilla con botón 🎲 y botón **Generar**.
- **Objetos**: "Objetos clave" con las opciones *Vanilla* o *Cualquier cofre* (por defecto *Cualquier cofre*) y "Excluir objetos" como casillas. Las futuras categorías (llaves, mapas y brújulas, canciones...) aparecen en gris como "próximamente".
- **Lógica**: "Sin glitches", fijo en v1 y solo informativo.
- **Spoiler**: activar o desactivar el registro, y ver el último generado.
- Al terminar: mensaje de éxito con la ruta del mod, enlace al registro y recordatorio de desactivar otros mods `Rando_*` del mismo juego, porque chocarían.

## 6. Asociar los cofres del remake con las ubicaciones de OoTR

Es la parte de datos más grande. Se hace una tabla versionada `Hash del remake → nombre de ubicación en OoTR` (por ejemplo `Deku Tree Slingshot Chest`) que se genera de forma semiautomática a partir del mapa (`Banc/<Zona>`), el contenido original, el `GetEventName` y la posición. Después se revisa a mano y los casos dudosos se marcan para comprobarlos jugando. Los cofres que no tengan equivalente en OoTR se tratan según §5.1.

## 7. Riesgos técnicos (comprobar al principio de la construcción)

- **R1. Eventos ligados a cofres.** **14 de los 15** cofres de objetos clave tienen un `GetEventName` de historia; el del Bumerán es el único que no. Algunos ejemplos: `SageOfWater_MelodyGet_Water` (Botas de hierro → Serenata del Agua), `SageOfSpirit_NaboorIsTakenAway` (Guanteletes de plata), `SageOfShdawo_GetHoverBoots`, `Get_StoneOfForest_GetSword`, `MiniGame_DampeRace_OpenGoalTBox`. Lo **esperado** es que el evento siga ligado al cofre (al sitio) y no al objeto. Hay que comprobar en el juego que (a) un cofre con evento da el objeto nuevo y no el original, y (b) el evento sigue haciendo lo suyo, como dar la canción o activar la historia.
  - **Decisión del usuario:** si un evento entrega el objeto original por su cuenta, **se editan los archivos de eventos** (`Event/EventFlow/*.bfevfl.zs`) en la v1 para que den el objeto nuevo, en lugar de dejar ese cofre fijo. Eso añade a la v1 leer y escribir BFEVFL y actualizar sus entradas en la tabla de tamaños.
  - **Decisión del usuario:** si solo falla lo visual (la escena o el texto muestran el objeto original pero recibes el nuevo), **se acepta en v1** y no hace falta arreglarlo ni excluir el sitio.
- **R2. Objetos progresivos y requisitos previos.** Hay que comprobar qué pasa si se consigue el Gancho largo sin el Gancho, los Guanteletes de oro sin los de plata, o el Escudo espejo o las Flechas de hielo antes de tiempo. La lógica tiene que modelar lo que haga el juego realmente, o el reparto tiene que evitar esas situaciones.
- **R3. Objetos de adulto en sitios de niño y al revés.** Lo resuelve la lógica de OoTR, pero conviene comprobar en el juego que un objeto de adulto conseguido de niño se guarda correctamente.
- **R4. Mods de Lichii.** La ruta exacta de mods y si hace falta activarlos en "Add-Ons" se ha deducido, no está documentado. Funcionó copiando `<Mod>/romfs/...` en la carpeta de mods del juego.

## 7b. Pruebas en el juego y público

- **Solo el usuario puede jugar en Lichii.** *Decisión mía:* el plan empieza con un **lote de mods de prueba pequeños y una lista de comprobación escrita** que cubren R1, R2 y R3 y los cofres dudosos de §6. Los resultados de ese lote deciden el alcance antes de cerrar la lógica y el reparto. Así se evitan muchas rondas de prueba de un solo cofre.
- **Público (decisión del usuario):** primero es para uso personal; si llega a funcionar bien, posiblemente se publique. Para la v1 eso significa:
  - se ejecuta desde el código con Python 3.14 y lo mínimo de dependencias externas, sin `.exe`;
  - el código no tiene rutas fijas de la máquina del usuario y valida el `.nup` (versión y archivos necesarios) con errores claros;
  - se prepara la licencia GPL-3.0 si se reutiliza la lógica de OoTR, con la atribución correspondiente;
  - la tabla `Hash → ubicación` solo contiene identificadores y nombres, no recursos del juego, así que se puede distribuir.

## 8. Cómo se comprueba que está hecho
- Tests automáticos: el BYML pasa la prueba de ida y vuelta en los 160 mapas; la fórmula de la tabla de tamaños coincide; el generador es determinista (misma semilla, mismo resultado); y la comprobación de que la semilla se puede completar pasa en cientos de semillas.
- El usuario juega una semilla completa en Lichii.

## 9. Lo que se deja a quien lo construya
- La estructura del código, el servidor web local (librería estándar o una dependencia pequeña), el formato exacto del registro de spoilers y el diseño visual de las pestañas.
- Cómo incorporar la lógica de OoTR (copiar sus datos o depender de ellos) y el algoritmo de reparto (por ejemplo "assumed fill", como OoTR).
- El formato de la semilla.
- Reutilizar o reescribir el código de `spikes/`. Funciona, pero se escribió como prototipo.
