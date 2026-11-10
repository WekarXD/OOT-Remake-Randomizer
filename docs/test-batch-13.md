# Lote de prueba 13: qué impide que el objeto llegue al inventario

En los lotes 11 y 12 los objetos flotaban y se cogían, pero no llegaban al inventario. La copia de la rupia del lote 10 sí daba el objeto (la Resortera), aunque había que pulsar A. Este lote prueba por separado cada diferencia entre las dos.

## Preparar

- [ ] Quita `TestLote12` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote13` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas.

## Qué cambia

| Skulltula | Sala | Suelta | Cómo está hecho |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Bumerán** | Copia de la ficha, pero con la forma de "atrapar" de los objetos normales (no la de la ficha) |
| B | Sótano | **Gancho** | Copia de la rupia, como en el lote 10, pero con la recogida al pasar por encima activada |
| C | Sótano | **Bolsa de bombas** | Como B, más la física de la ficha (para ver si así flota) |
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

(Pendiente de rellenar tras probarlo.)
