# Tokensanity (Skulltulas doradas en el reparto): diseño

Estado: borrador para aprobación. Forma parte del proyecto 2, las opciones "Shuffle" de OoTR para objetos por el mundo. Rama: `feat/v1`, o una rama nueva desde ella, a criterio de quien lo construya.

## 1. Qué es y por qué

El usuario quiere la opción **Tokensanity** del generador de OoTR. En OoTR, cada Skulltula dorada que entra en el reparto deja de soltar siempre su ficha y se convierte en un sitio donde puede aparecer cualquier objeto. Sus fichas van al montón de objetos que se reparten.

Hasta ahora no se podía hacer, porque los objetos clave (`Item_*`) soltados por el mundo no se pueden coger (lote 6). Los lotes 9 a 14 encontraron la forma de conseguirlo. El lote 14 se probó en Lichii el 2026-11-10 (`docs/test-batch-14.md`): una Skulltula suelta un **actor envoltorio** que es una copia de la ficha dorada con la identidad de un objeto clave. Flota donde estaba la Skulltula, se coge al pasar por encima o con el Bumerán o el Gancho, y el objeto llega al inventario y se puede usar.

## 2. Objetivos, no-objetivos y anti-objetivos

**Objetivos**

- Un selector **Tokensanity** en la sección "Shuffle" de la página, con los valores de OoTR:

  | Valor (OoTR) | En la página | Qué Skulltulas entran |
  |---|---|---|
  | `off` | Desactivado (por defecto) | Ninguna |
  | `dungeons` | Solo mazmorras | Las 44 de mazmorras |
  | `overworld` | Solo mundo exterior | Las 56 de fuera |
  | `all` | Todas | Las 100 |

- Una Skulltula que entra en el reparto puede contener cualquier objeto del montón: un objeto clave, el contenido de un cofre (rupias, munición, corazones…) o una ficha.
- Las fichas de esas Skulltulas entran en el montón y pueden acabar en un cofre o en otra Skulltula. El total de fichas en la partida sigue siendo 100.
- La lógica de OoTR, que ya está en el repositorio, recibe `tokensanity` con el valor elegido y garantiza que la semilla se puede completar. Eso incluye lo que hace falta para llegar a cada Skulltula y cuántas fichas piden las recompensas de la Casa de las Skulltulas.
- El registro de la partida tiene una sección "Skulltulas" con lo que hay en cada una.
- La misma semilla con los mismos ajustes da siempre el mismo mod.

**No-objetivos**

- Jarrones, cajas, colmenas, rupias sueltas y demás objetos del mundo. Van después, con su propio diseño. Lo que se construya aquí (envoltorios, registros) debería poder reutilizarse.
- Cambiar el aspecto del envoltorio. El objeto se ve con su modelo y con el brillo dorado de la ficha. Esto lo decidí yo: el usuario lo vio en el lote 14 y no lo pidió cambiar.
- Las opciones de OoTR que dependen de fichas, como el puente o el castillo de Ganon por fichas. No existen hoy en el randomizer.

**Anti-objetivos**

- Una partida bloqueada porque una Skulltula no suelta nada, suelta algo que no se puede coger o vuelve a soltarlo cada vez que entras.
- Que con Tokensanity en `off` cambie algún archivo del mod respecto a hoy.
- Escribir en el `.nup` o meter archivos del juego en el repositorio.

## 3. Hechos (exploración del 2026-11-10)

- **Hay 100 Skulltulas doradas.** Son actores `Enemy_Skulltula_Gold` en los Banc `*_Static.bcett.byml.zs`, con 100 `Hash` distintos repartidos en 114 colocaciones.
  - **Hay 14 Hash que aparecen en dos Banc,** por ejemplo la versión de niño y la de adulto, o el mapa "Alternative" de Kakariko o del Dominio Zora. Al cambiar una Skulltula hay que cambiar todas sus copias, igual que con los cofres.
  - **El número por zona coincide con OoTR.** Mazmorras: Árbol Deku 4, Dodongo 5, Jabu-Jabu 4, Bosque 5, Fuego 5, Agua 5, Sombras 5, Espíritu 5, Pozo 3 y Caverna de Hielo 3. Exterior: 56. El remake junta zonas: el Banc `HyruleField` (11) contiene también las del Lago Hylia y el Rancho Lon Lon.
  - **Datos que ayudan a identificarlas** (claves de `Dynamic`): `Enemy_Skulltula_Gold_Nocturnal` (30), `Enemy_Skulltula_Gold_IsMagicBeanSoil` (10), `DefaultDungeonRoomIndex` (44, en mazmorras) y otras de cómo aparecen.
- **La ficha se cambia con `Dynamic.Drop__DropActor`** en el actor de la Skulltula. Ninguna Skulltula lo trae puesto: sin él suelta su ficha. Confirmado en el Árbol Deku en los lotes 6 y 9 a 14. Los `Obj_*` normales también funcionan, como la rupia roja y la pieza de corazón del lote 6.
- **Receta del envoltorio que funciona (lote 14).** El script de prueba es `lote14.py`, en el scratchpad.
  1. **Pack.** `Pack/Actor/<Nuevo>.pack.zs` es una copia del pack de `Obj_Token_Gold`. En su ActorParam se sustituyen `ActorNameRef`, `ModelInfoRef`, `AnimationRef`, `GameParameterTableRef` y `PouchContentRef` por los del pack del objeto, y se añaden los archivos del pack del objeto que falten (fuera de `Actor/`). El `PouchContentParam` es una copia del del objeto con `DefaultAutoGet: True` (eso hace que se coja al pasar por encima), con nombre propio.
  2. **RSTB.** Una entrada nueva `[crc32(ruta sin .zs), tamaño + 0x1000]`, insertada en orden.
  3. **`RSDB/ActorInfo`.** Fila copia de la de `Obj_Token_Gold` con:
     - `__RowId` nuevo;
     - `ActorName` igual al `ActorName` de la fila del objeto, o el nombre del objeto si no tiene;
     - el modelo del objeto (`FmdbName`, `ModelProjectName`, `AnimationResources`, `ModelAabbMax/Min`);
     - montones al máximo de los dos + 0x10000.
  4. **`RSDB/GameActorInfo`.** Fila del token, más `ModelVariationAnims` del objeto.
  5. **`RSDB/PouchActorInfo`.** Fila copia de la del objeto con el `__RowId` nuevo. **Sin esta fila el objeto se coge, pero no llega al inventario** (lotes 11 a 13).
  6. **Orden.** Las tres tablas RSDB van ordenadas por `__RowId`. Su RSTB es tamaño nuevo + (RSTB original − tamaño original) + 0x1000.
  7. **Formato.** El pack se escribe con un escritor SARC: alineación de archivos 8 y de datos 0x20. Está probado en el scratchpad (`sarcw.py`); hoy el repositorio solo lee SARC.
- **Bolsa de bombas.** Fuera de su cofre original da la bolsa y 20 bombas, pero no se pueden lanzar (problema conocido del v1, commit 2ad8165). Por eso sigue fija en su cofre y no entra en el reparto.
- **OoTR.** Los ajustes vendidos tienen `tokensanity: "off"` y `gold_skulls_ignore_daytime: false`. Las ubicaciones se llaman "`<zona> GS <sitio>`" (por ejemplo "Kak GS Tree"). Las MQ no aplican, porque el remake no tiene Master Quest.
- **Cómo se cuentan las fichas.** En `RSDB/PouchActorInfo`, `Obj_Token_Gold` e `Item_Token_Gold` son un objeto acumulable del inventario (`PouchStockable`, `FixedMaxNum: 100`). Es decir, el contador es global y no son marcas por Skulltula. Las recompensas de la Casa de las Skulltulas piden en la lógica `(Gold_Skulltula_Token, N)` (`World/Overworld.json`). Falta confirmar en el juego que una ficha fuera de su sitio suma (§4).
- **Una Skulltula que está en dos Banc** (niño y adulto) es la misma ubicación de OoTR. La lógica de OoTR ya dice con qué edad, hora y objeto se llega a cada una. Igual que con los cofres, se acepta esa lógica para el remake.

## 4. Lo que falta por saber (se prueba en el juego al empezar)

**Resuelto en el lote 15 (2026-11-11, `docs/test-batch-15.md`).**

- 1 y 3: las fichas valen en cofres (`Obj_Token_Gold` o `Item_Token_Gold`) y como suelta explícita, y el contador sube.
- 2: tras recoger lo que suelta, la Skulltula no vuelve.
- 4: la nocturna funciona; la de tierra blanda queda sin probar.
- 5: si no se recoge el objeto, la Skulltula vuelve y lo suelta otra vez, así que no se pierde.
- 6: probados el Bumerán, el Gancho, las Botas de hierro, los Guanteletes de plata, el Martillo y el Escudo espejo.

El texto original sigue a continuación.

1. **Una ficha que sale de un cofre** (`Drop__DropActor: Obj_Token_Gold` en un cofre): ¿aparece, se coge y sube el contador? La ficha tiene un dato `GoldTokenGmdHash` que podría ligarla a su Skulltula.
2. **Una Skulltula que suelta otra cosa** (envoltorio, rupia): ¿se queda como "cogida" al salir y volver a entrar, y al cargar la partida, o vuelve a aparecer y a soltar el objeto? Si vuelve a aparecer y el objeto se puede coger otra vez, no bloquea la partida, pero hay que saberlo.
3. **Una ficha que sale de otra Skulltula:** ¿cuenta bien?
4. **Una Skulltula nocturna y una de tierra blanda** que sueltan un envoltorio: ¿se comportan igual que las del Árbol Deku?
5. **Salir sin coger lo que suelta:** si matas la Skulltula y sales sin coger el objeto, ¿sigue ahí al volver o se pierde? Si se pierde, un objeto clave en una Skulltula se podría perder para siempre.
6. **Envoltorios de todos los objetos clave que se reparten** (`KEY_ITEMS`, unos 14 sin la Bolsa de bombas): ¿aparecen y llegan al inventario? Solo se han probado el Bumerán y el Gancho. Las canciones y los objetos de misión no se reparten, así que no hacen falta.

Si una ficha no se puede poner en un cofre (punto 1), hay dos salidas: que las fichas solo vayan a Skulltulas, o hacer un envoltorio también para la ficha. Lo decide quien construya, según el resultado, y lo apunta.

Si en el punto 2 la Skulltula vuelve a aparecer y suelta el objeto otra vez, eso no bloquea la partida, pero choca con un anti-objetivo. En ese caso se para y se pregunta al usuario. Si en el punto 5 el objeto se pierde, también se para y se pregunta, porque podría hacer falta excluir los objetos clave de las Skulltulas.

## 5. Comportamiento

### 5.1 Identificar las Skulltulas

- Un archivo de datos versionado (`randomizer/data/gs_map.json`, como `location_map.json` para los cofres) asocia cada `Hash` con su ubicación de OoTR, sabiendo si es de mazmorra o de exterior y su estado (`confirmed` o `guessed`).
- Se construye zona por zona: el número cuadra, y dentro de cada zona se distinguen por nocturna, tierra blanda, sala de mazmorra y posición. Las que no se puedan distinguir se comprueban en el juego con un lote de prueba. Por ejemplo, cada Skulltula dudosa suelta un objeto distinto y reconocible.
- Una Skulltula sin asociar no entra en el reparto aunque la opción esté encendida, y conserva su ficha.

### 5.2 Reparto

- El reparto, que hoy es solo de cofres, pasa a manejar sitios de varios tipos: cofre y Skulltula. Para los cofres no cambia nada. La fase B de los regalos (plan en `docs/superpowers/plans/2026-11-10-regalos-fase-b.md`) añade otro tipo de sitio, así que quien construya debería generalizarlo una sola vez para los tres.
- Con Tokensanity encendido, las Skulltulas elegidas son sitios libres más. Sus fichas (`Obj_Token_Gold`) entran en el montón de contenido que se baraja, junto al resto del contenido de los cofres.
- Los objetos clave se colocan con el mismo *assumed fill* de hoy, que ya admite cualquier sitio alcanzable. También aplica la regla de no poner objetos clave en las zonas de `NO_KEY_TARGET_ZONES` (Agua, Fuego, Pozo, Centro de Entrenamiento).
- La lógica de OoTR se carga con `tokensanity` igual al valor elegido. Las ubicaciones GS que no entran (por la opción o por no estar asociadas) conservan su ficha original en `fixed`, y la lógica las cuenta para las recompensas de la casa.
- **Fichas en la lógica** (lo decidí yo). Hoy el contenido que no es clave se reparte a ciegas. Las fichas, en cambio, se colocan en `fixed` como `Gold Skulltula Token`, para que la lógica las cuente. Hay dos casos:
  - **Ninguna recompensa de la casa tiene un objeto clave** (hoy es así, sin la fase B de los regalos): las fichas no son necesarias para completar. Basta con colocarlas en los sitios libres que quedan y validar con `can_beat`.
  - **La fase B pone objetos clave en las recompensas:** las fichas pasan a ser progresión. Se colocan con *assumed fill* después de los objetos clave, para que al colocar cada objeto clave se den por tenidas.
- `tokensanity` forma parte de la clave del RNG, porque cambia el reparto. Con `off`, el resultado tiene que ser idéntico al de hoy.

### 5.3 Qué suelta cada Skulltula

- Un contenido que ya es un actor de suelo con fila en `PouchActorInfo` (`Obj_Rupee_*`, `Obj_Heart_Piece`, `Obj_Token_Gold`, etc.) se pone tal cual en `Drop__DropActor`.
- Cualquier otro, objetos clave y lo que no se pueda soltar directamente, recibe un **envoltorio** generado al montar el mod con la receta del §3: uno por objeto distinto, con nombre fijo `Obj_Rando_<Objeto>`. Como mucho son unas pocas decenas, así que no se espera ningún problema de límites. Quien construya decide qué contenidos de cofre necesitan envoltorio, mirando si tienen fila en `PouchActorInfo` y si son `Obj_*`.
- Los envoltorios, sus filas RSDB y sus entradas RSTB solo se escriben si alguna Skulltula los usa. Con `off` no se toca ningún RSDB.
- Un cofre que recibe una ficha usa `Obj_Token_Gold`, o lo que diga la prueba del §4.

### 5.4 Página y registro

- En la sección "Shuffle" de la pestaña Objetos: selector "Fichas de Skulltula (Tokensanity)" con los cuatro valores del §2, desactivado por defecto. Si la fase B de los regalos aún no ha creado la sección, se crea aquí.
- El registro añade una sección "Skulltulas" que lista cada ubicación GS que entra, con su contenido en español. Las fichas que acaban en cofres salen en la sección de cofres de siempre.

## 6. Fases (cada una con su prueba en Lichii)

1. **Prueba de lo pendiente del §4,** con un lote de prueba hecho a mano como los anteriores. Si algo bloquea la partida, se para y se replantea.
2. **Asociación de las 100 Skulltulas** (`gs_map.json`), con su lote de comprobación para las dudosas.
3. **Construcción.** Incluye:
   - escritor SARC con tests de ida y vuelta;
   - generador de envoltorios y filas RSDB/RSTB;
   - reparto con sitios Skulltula;
   - opción en la página;
   - registro;
   - una semilla de prueba con Tokensanity en `all` que el usuario juega en parte.

## 7. Hecho cuando

- La opción existe en la página y se refleja en el registro.
- Las fases 1 a 3 tienen su lote superado en Lichii.
- Los tests pasan, incluido que con `off` el mod generado es idéntico al de antes.
