# Pruebas de saltar escenas

Objetivo: comprobar en el juego que se pueden saltar las escenas de historia sin romper nada. Hay tres tandas, y cada una incluye todo lo de la anterior.

## Antes de empezar

- Copia la carpeta de la tanda desde `test-mod/0400486024DEC000/` (`TestEscenas1`, `TestEscenas2` o `TestEscenas3`) a la carpeta `load/0400486024DEC000/` de Lichii.
- Deja **solo un mod de prueba o de randomizador activo a la vez**. Quita o desactiva los demás (TestLote, RandoTest, etc.) antes de probar.
- Empieza siempre una **partida nueva**.
- **Las notas importan más que las casillas.** Si algo falla, apunta dónde y qué viste.

## Tanda 1: TestEscenas1 (solo la introducción)

- [ ] Al empezar la partida nueva, la introducción se puede saltar con el botón.
- [ ] Después de saltarla aparecen Navi y Saria como siempre.
- [ ] Consigo la espada y el escudo, y puedo entrar al Árbol Deku.

Notas: ______

## Tanda 2: TestEscenas2 (todas las escenas)

Desactiva TestEscenas1 y activa TestEscenas2. Otra vez partida nueva.

- [ ] Las escenas del Árbol Deku, hasta recibir la Esmeralda Kokiri, salen sin los diálogos de historia.
- [ ] Recibo la Esmeralda Kokiri.
- [ ] La charla con Zelda en el jardín del castillo es más corta. Solo siguen saliendo sus animaciones grabadas, el menú en el que eliges qué preguntarle y sus preguntas. Las escenas de alrededor (hasta la Canción de Zelda) también son más cortas.
- [ ] Recibo la Carta de Zelda.
- [ ] Aprendo la Canción de Zelda.
- [ ] Al terminar cada tramo me quedo en el mismo sitio donde acababa antes.

Además, durante toda la prueba fíjate en esto:

- [ ] **Cuelgues:** el juego no se congela ni se queda atascado en ninguna escena. Si pasa, apunta en qué escena o lugar.
- [ ] **Escenas sin terminar:** ¿Alguna escena se quedó sin terminar o con la pantalla en negro? Si pasa, apunta cuál y dónde.
- [ ] **Textos que desaparecen:** no falta ningún texto que debería salir (carteles, avisos del sistema, explicaciones de controles). Si falta alguno, apunta cuál y dónde.

Notas: ______

## Tanda 3: TestEscenas3 (todas las escenas y las conversaciones forzadas)

Desactiva TestEscenas2 y deja **solo TestEscenas3** activo. Partida nueva otra vez.

- [ ] **Mido:** al hablar con él no sale su texto de bloqueo, pero sigue sin dejarme pasar hasta que tengo la espada y el escudo.
- [ ] **Kokiri de la salida del bosque:** al chocar o hablar con él mientras bloquea ya no sale ninguna línea de texto (ronda 2b), pero sigue sin dejarme pasar hasta que termino el Árbol Deku. El globo pequeño que suelta al acercarte a la salida sigue saliendo: no se puede quitar con este método.
- [ ] **Deku del Árbol Deku que da la clave del orden:** su conversación vuelve a salir entera (ronda 2), y también la de sus hermanos y la de golpearlos.
- [ ] **Fijar el blanco:** el tutorial de los Kokiri sobre fijar el blanco ya no sale.
- [ ] Llego al Árbol Deku y lo termino.
- [ ] Llego al Castillo de Hyrule (Zelda) sin problemas.
- [ ] **Zelda en el jardín:** la primera vez que la ves, la escena sale **entera**, como en el juego original (ronda 2b: recortada dejaba a Link congelado). Si vuelves a hablar con ella (pulsando A), esa charla es más corta. Sigo recibiendo la Carta de Zelda y aprendiendo la Canción de Zelda.
- [ ] **Escenas que dejaban a Link congelado** (ronda 2b): ahora se ven enteras, con su texto, como en el juego original. Ninguna escena deja a Link quieto esperando sin texto. Son 12 escenas del Bosque Kokiri, el Árbol Deku, el Campo de Hyrule, el Castillo, el Rancho Lon Lon y Kakariko, entre ellas la muerte del Árbol Deku y Zelda en el jardín (flujos `Dm_Kokiri_0060/0130/0145/0155`, `Dm_Deku_0003`, `Dm_HrlField_0020`, `Dm_HrlCastle_0000/0020/0035/0050`, `Dm_LonLon_0020`, `Dm_Kakariko_0010`).
- [ ] Llego a Kakariko sin problemas.

Cosas que **siguen saliendo** (es normal, no son fallos):

- **El Gran Árbol Deku** sigue hablando en su primera charla, en la conversación larga y en su muerte (ronda 2b). Cada una de sus líneas va en paralelo con una animación; quitarla dejaría vacía esa parte de la escena, y el juego original nunca lo hace, así que no se toca. Su muerte ahora se ve entera.
- El aviso de Navi para "fijar el blanco" seguirá apareciendo. No se puede quitar con este método. Solo debe desaparecer el tutorial de los Kokiri.
- Las pistas de juego se quedan: los Dekus que dan claves, los avisos de Navi en mazmorras y el altar del Templo del Tiempo (ronda 2).

Avisos que ahora se recortan **en todo el juego**, no solo de niño. Apunta si alguno se comporta raro:

- [ ] Los sitios de tierra para plantar semillas mágicas (judías mágicas).
- [ ] El recordatorio de Navi sobre las Skulltulas doradas.
- [ ] Los soldados que te paran en Kakariko.

Y, como en la tanda 2:

- [ ] **Cuelgues:** el juego no se congela ni se queda atascado en ninguna escena. Si pasa, apunta dónde.
- [ ] **Pantallas negras:** ninguna escena se queda sin terminar o con la pantalla en negro. Si pasa, apunta cuál y dónde.
- [ ] **Objetos que faltan:** recibo todo lo que debería (Esmeralda Kokiri, Carta de Zelda, Canción de Zelda, espada, escudo...). Si falta algo, apunta qué y dónde.
- [ ] **Textos que desaparecen:** no falta ningún texto que debería salir (carteles, avisos del sistema, explicaciones de controles). Si falta alguno, apunta cuál y dónde.
- [ ] **Conversaciones forzadas que siguen saliendo:** apunta cuáles salen todavía y en qué lugar.

Notas: ______

## Resultados

