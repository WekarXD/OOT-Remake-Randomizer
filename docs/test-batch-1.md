# Lote de pruebas 1

Objetivo: comprobar tres cosas con mods sencillos antes de seguir con el randomizador.

## Antes de empezar

- Desactiva o quita los mods anteriores **RandoTest** y **RandoTest_Gancho**.
- Usa **solo un TestLote a la vez** (activa uno, prueba, desactiva, y luego el otro).
- Copia la carpeta del lote desde `test-mod/0400486024DEC000/` (TestLote1 o TestLote2) a la carpeta de mods de Lichii para el juego.
- Para cada prueba anota: el objeto recibido, el texto o escena que aparece, si sale en el inventario o menu, y si se puede usar.

## TestLote1 (partida de nino, Bosque Kokiri)

La casa de Mido tiene 4 cofres; cada uno corresponde a una de las filas de Mido de abajo. No sabemos de antemano que cofre es cual: abre los cuatro y anota que recibes en cada uno.

### Prueba 1: Espada Kokiri (R1)
- Donde: zona oculta (pasadizo/crawlspace) del Bosque Kokiri, cofre de la Espada Kokiri.
- Normalmente da la Espada Kokiri; ahora el cofre contiene una rupia verde.
- Que hacer: abrir el cofre. Anotar si igualmente recibes la espada (evento "Get_StoneOfForest_GetSword") o solo la rupia.
- Anotar: objeto recibido: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK (recibes la rupia, no la espada)   [ ] FALLO (recibes la espada igualmente)

### Prueba 2: Gancho largo sin Gancho (R2)
- Donde: casa de Mido, un cofre (antes rupia verde).
- Que hacer: abrirlo sin tener el Gancho. Mirar si lo recibes, si sale en el menu y si se puede usar.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK   [ ] FALLO

### Prueba 3: Guanteletes de oro sin brazalete ni plata (R2)
- Donde: casa de Mido, otro cofre (antes rupia azul).
- Que hacer: abrirlo sin tener los guanteletes anteriores.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK   [ ] FALLO

### Prueba 4: Escudo de espejo siendo nino (R3)
- Donde: casa de Mido, otro cofre (antes rupia azul).
- Que hacer: abrirlo de nino. Mirar si se queda en el inventario o se pierde (por ejemplo al cambiar de pantalla o guardar y recargar).
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______  se pierde: ______
- [ ] OK (se conserva)   [ ] FALLO (se pierde)

### Prueba 5: Flechas de hielo sin arco (R2/R3)
- Donde: casa de Mido, el ultimo cofre (antes rupia azul).
- Que hacer: abrirlo sin arco. Mirar si aparece algo en el menu y si se puede usar.
- Anotar: objeto: ______  texto/escena: ______  en inventario: ______  usable: ______
- [ ] OK   [ ] FALLO

## TestLote2 (hace falta partida guardada de adulto)

### Prueba 6: Serenata del Agua (R1)
- Donde: Caverna de Hielo (Ice Cavern), el cofre del final (normalmente las Botas de hierro).
- Ahora el cofre contiene una rupia azul.
- Que hacer: llegar al final y abrir el cofre. Comprobar si igualmente se aprende la Serenata del Agua y si recibes las Botas de hierro.
- Anotar: objeto: ______  escena/texto: ______  Serenata aprendida: ______
- [ ] OK (rupia, sin botas)   [ ] FALLO (da las botas o falla el evento)

## Notas finales

Cuando termines, pasa los resultados y cualquier detalle raro (textos, cierres del juego, escenas que se quedan colgadas).
