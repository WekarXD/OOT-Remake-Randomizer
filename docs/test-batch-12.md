# Lote de prueba 12: la ficha dorada que da el objeto

En el lote 11 los objetos flotaban y se cogían como una ficha, pero no llegaban al inventario. El motivo es que, al cogerlos, se ejecutaba el "final" de la ficha (sumar una ficha) en vez del de los objetos del suelo (meter el objeto en el inventario).

En este lote, cada actor sigue siendo una copia de la ficha, pero lleva piezas del "final" genérico tomadas de la rupia roja. Cada Skulltula prueba una combinación distinta.

## Preparar

- [ ] Quita `TestLote11` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote12` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas.

## Qué cambia

| Skulltula | Sala | Suelta | Qué se cambia respecto a la ficha |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Bumerán** | Solo el "final" (`DeathRef` genérico) |
| B | Sótano | **Gancho** | El "final" y la escena de recogida de la rupia |
| C | Sótano | **Bolsa de bombas** | El "final" y el comportamiento (`AIInfoRef` genérico). Puede que caiga al suelo en vez de flotar |
| D | Sala del fondo del sótano | Su ficha normal | Nada (control) |

## Comprobar

- [ ] **A:** ¿Flota? ¿Cómo se coge? ¿Sale el **Bumerán en el inventario** y se puede lanzar? ______
- [ ] **B:** ¿Flota? ¿Cómo se coge? ¿Sale el **Gancho en el inventario**? ______
- [ ] **C:** ¿Flota o cae? ¿Cómo se coge? ¿Sale la **Bolsa de bombas** y puedes llevar bombas? ______
- [ ] ¿Sale el mensaje o la animación de "has conseguido" en alguno? ______
- [ ] ¿El contador de fichas sube con A, B o C? Debería subir solo con D. ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

Resultados en el juego (2026-11-10):

- **A, B y C: flotan con el brillo de la ficha y se cogen al pasar por encima, pero ninguno llega al inventario.** C también flota, aunque lleva el comportamiento genérico.
- **D: ficha normal.**

Conclusión: el "final" y el comportamiento no son la causa. Frente a la rupia del lote 10, que sí daba el objeto, quedan dos diferencias: la recogida automática (`DefaultAutoGet`) y la forma de "atrapar" de la ficha (`AttentionSender`), que puede lanzar la recogida especial de las fichas. Se prueban por separado en el lote 13.
