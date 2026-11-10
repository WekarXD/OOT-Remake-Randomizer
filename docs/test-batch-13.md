# Lote de prueba 13: qué impide que el objeto llegue al inventario

En los lotes 11 y 12 los objetos flotaban y se cogían, pero no llegaban al inventario. La copia de la rupia del lote 10 parecía dar la Resortera (con el botón A), pero el usuario ya la tenía del cofre, así que no está claro que la diera. Este lote prueba de nuevo esa copia con un objeto que no se tiene, y prueba por separado cada diferencia con la ficha.

## Preparar

- [ ] Quita `TestLote12` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote13` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas.

## Qué cambia

| Skulltula | Sala | Suelta | Cómo está hecho |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Bumerán** | Copia de la ficha, pero con la forma de "atrapar" de los objetos normales (no la de la ficha) |
| B | Sótano | **Gancho** | Copia de la rupia, como en el lote 10, pero con la recogida al pasar por encima activada |
| C | Sótano | **Bolsa de bombas** | Exactamente la copia de la rupia del lote 10 (se coge con A). Es la prueba limpia |
| D | Sala del fondo del sótano | Su ficha normal | Nada (control) |

Con cada uno, prueba primero a **pasar por encima**. Si no se coge, prueba con el **botón A**.

## Comprobar

- [ ] **A:** ¿Flota o cae? ¿Se coge al pasar por encima o con A? ¿Sale el **Bumerán en el inventario**? ______
- [ ] **B:** ¿Flota o cae? ¿Se coge al pasar por encima o con A? ¿Sale el **Gancho en el inventario**? ______
- [ ] **C:** ¿Flota o cae? ¿Se coge al pasar por encima o con A? ¿Sale la **Bolsa de bombas** en el inventario? ______
- [ ] ¿Sale la animación de "has conseguido" en alguno? ______
- [ ] ¿El contador de fichas sube con A, B o C? ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

Resultados en el juego (2026-11-10):

- **A (ficha con la forma de atrapar normal, Bumerán):** flota y se coge al pasar por encima, pero no llega al inventario.
- **B (rupia con recogida automática, Gancho):** cae lentamente y no se puede coger.
- **C (copia exacta de la rupia del lote 10, Bolsa de bombas):** cae lentamente y no se puede coger. Por tanto, el lote 10 no demostraba nada: ninguna copia ha dado un objeto todavía.
- **D: ficha normal.**

Causa encontrada: hay un tercer registro, **`RSDB/PouchActorInfo`**, que dice qué actores pueden ir al inventario y cómo. La carta de Ruto del juego (`Obj_Bottle_Letter`) tiene ahí una fila, copia de la de `Item_Bottle_Letter`; la ficha y las rupias también. Las copias no estaban en él, así que el juego no sabía qué hacer al cogerlas. Se prueba en el lote 14.
