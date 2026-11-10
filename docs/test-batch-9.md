# Lote de prueba 9: objetos clave dentro de un objeto "de suelo"

Objetivo: que una Skulltula dorada (y luego jarrones, rupias, etc.) pueda soltar un objeto clave **y que se pueda coger**.

En el lote 6 el Gancho se veía pero no se podía coger. El motivo es que los objetos clave (`Item_*`) son solo un modelo para las escenas y no tienen la parte que permite recogerlos.

Los objetos del suelo (`Obj_*`) sí la tienen, y algunos ya "envuelven" un objeto clave. Por ejemplo, la carta de Ruto del lago es un `Obj_Bottle_Letter` que, al cogerlo, te da el objeto `Item_Bottle_Letter`.

En este lote se prueban tres formas de hacerlo. Dos de ellas son actores **nuevos**, creados copiando uno del juego y cambiando el objeto que dan.

## Preparar

- [ ] Desactiva cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote9` a `load/0400486024DEC000/` en Lichii.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas del lote 6.

## Qué cambia

| Skulltula | Sala (la del lote 6) | Debería soltar | Cómo |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Carta de Ruto** (botella con carta) | El objeto del juego tal cual (`Obj_Bottle_Letter`) |
| B | Sótano, la que soltó la rupia roja | **Bumerán** | Actor nuevo: copia de la carta de Ruto que da el Bumerán |
| C | Sótano, la que soltó la pieza de corazón | **Gancho** | Actor nuevo: copia de la pieza de corazón que da el Gancho |
| D | Sala del fondo del sótano | Su ficha normal | Sin cambios (control) |

## Comprobar

Para cada una, apunta qué se ve al morir y si se puede coger. Puede que haga falta el botón de acción, como con la pieza de corazón.

- [ ] **A:** ¿Aparece la botella con la carta? ¿Se puede coger? ¿Sale en el inventario? ______
- [ ] **B:** ¿Aparece algo? ¿Qué aspecto tiene? ¿Se puede coger? ¿Sale el Bumerán en el inventario y se puede lanzar? ______
- [ ] **C:** ¿Aparece algo? ¿Qué aspecto tiene? ¿Se puede coger? ¿Sale el Gancho en el inventario? (de niño no se puede usar; basta con que aparezca) ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra en algún momento? ¿Cuándo? ______

## Resultados

(Pendiente de rellenar tras probarlo.)
