# Lote de pruebas 1

Objetivo: comprobar tres cosas con mods sencillos antes de seguir con el randomizador.

## Antes de empezar

- Desactiva o quita los mods anteriores **RandoTest** y **RandoTest_Gancho**.
- Usa **solo un TestLote a la vez** (activa uno, prueba, desactívalo y luego el otro).
- Copia la carpeta del lote desde `test-mod/0400486024DEC000/` (TestLote1 o TestLote2) a la carpeta de mods de Lichii para el juego.
- Para cada prueba anota: el objeto recibido, el texto o la escena que aparece, si sale en el inventario o el menú, y si se puede usar.
- **Las notas importan más que las casillas.** Una casilla sola no nos sirve si no sabemos qué pasó.
- Significado de las casillas en cada prueba: **OK** = recibo el objeto nuevo indicado y aparece en el menú o inventario; **FALLO** = no recibo nada, recibo el objeto original, el objeto no aparece/no se puede usar, o el juego se cuelga. Si pasa algo distinto, descríbelo en las notas.

## TestLote1 (partida de niño, Bosque Kokiri)

### Cofres de la casa de Mido

La casa de Mido tiene 4 cofres. No se te dice cuál es cuál: ábrelos todos e identifica cada uno por lo que te da. Rellena la tabla (si los cofres no están donde se indica, anota dónde los encuentras):

| Cofre (posición en la casa) | Lo que me dio |
|---|---|
| Cofre 1: ______ | ______ |
| Cofre 2: ______ | ______ |
| Cofre 3: ______ | ______ |
| Cofre 4: ______ | ______ |

Posibles objetos nuevos: Gancho largo, Guanteletes de oro, Escudo espejo, Flechas de hielo. Si algún cofre te da una rupia (azul o verde) u otra cosa, apúntalo tal cual.

### Prueba 1: Espada Kokiri (R1)
- Dónde: zona oculta (pasadizo estrecho) del Bosque Kokiri, cofre de la Espada Kokiri.
- Normalmente da la Espada Kokiri; ahora el cofre contiene una rupia verde.
- Qué hacer: abrir el cofre. Anotar si igualmente recibes la espada o solo la rupia.
- Anotar: objeto recibido: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK (recibo la rupia verde)   [ ] FALLO (recibo la espada igualmente, o nada, o se cuelga)

### Prueba 2: Gancho largo sin Gancho (R2)
- Dónde: casa de Mido, el cofre que dé el Gancho largo.
- Qué hacer: abrirlo sin tener el Gancho. Mirar si lo recibes, si sale en el menú y si se puede usar.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK (recibo el Gancho largo y sale en el menú)   [ ] FALLO

### Prueba 3: Guanteletes de oro sin brazalete ni plata (R2)
- Dónde: casa de Mido, el cofre que dé los Guanteletes de oro.
- Qué hacer: abrirlo sin tener los guanteletes anteriores.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK (recibo los guanteletes y aparecen en el menú)   [ ] FALLO

### Prueba 4: Escudo espejo siendo niño (R3)
- Dónde: casa de Mido, el cofre que dé el Escudo espejo.
- Qué hacer: abrirlo de niño. Mirar si se queda en el inventario o se pierde (por ejemplo al cambiar de pantalla o al guardar y recargar).
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______  se pierde: ______
- [ ] OK (lo recibo y se conserva)   [ ] FALLO (no lo recibo, se pierde o se cuelga)

### Prueba 5: Flechas de hielo sin arco (R2/R3)
- Dónde: casa de Mido, el cofre que dé las Flechas de hielo.
- Qué hacer: abrirlo sin arco. Mirar si aparece algo en el menú y si se puede usar.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK (recibo las flechas y aparecen en el menú)   [ ] FALLO

## TestLote2 (hace falta partida guardada de adulto)

### Prueba 6: Serenata del Agua (R1)
- Dónde: Caverna de Hielo, el cofre del final (normalmente las Botas de hierro).
- Ahora el cofre contiene una rupia azul.
- Qué hacer: llegar al final y abrir el cofre. Comprobar si igualmente se aprende la Serenata del Agua y si recibes las Botas de hierro.
- Anotar: objeto: ______  escena/texto: ______  Serenata aprendida: ______
- [ ] OK (recibo la rupia azul y la Serenata se aprende)   [ ] FALLO (recibo las botas, no se aprende la Serenata o se cuelga)

## Notas finales

Cuando termines, pasa los resultados y cualquier detalle raro (textos, cierres del juego, escenas que se quedan colgadas).

## Resultados

### TestLote1 (partida de niño, Bosque Kokiri)
- **Casa de Mido**: los cuatro objetos nuevos se recibieron y se pueden usar:
  - Gancho largo, sin tener antes el Gancho.
  - Guanteletes de oro, sin tener antes los guanteletes anteriores.
  - Escudo espejo, siendo niño.
  - Flechas de hielo, siendo niño. Además, desbloquearon la barra de magia.
- **Cofre de la Espada Kokiri** (R1): dio la rupia verde, pero su evento siguió mostrando la escena de la espada y dando la espada. La espada se puede usar, pero no sale en el inventario. Por eso este cofre necesita tratar su evento.

### TestLote3 (cofre de la espada sin evento)
- Se quitó el evento (`GetEventName`) del cofre de la Espada Kokiri y se puso el Bumerán dentro. El cofre dio el Bumerán y **no** dio la espada. Un evento que solo entrega el objeto se puede quitar sin problemas.
- La parte del Árbol Deku no se pudo probar: la partida antigua había perdido la espada que daba el evento.

### TestLote2 (partida de adulto)
- Pendiente.
