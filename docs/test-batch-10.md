# Lote de prueba 10: actores nuevos registrados

Es igual que el lote 9, pero ahora los actores nuevos están **dados de alta** en el registro de actores del juego (`RSDB/ActorInfo` y `RSDB/GameActorInfo`). En el lote 9 no lo estaban, y por eso no aparecía nada.

Cada actor nuevo es una copia de un objeto de suelo que ya funciona al soltarlo, pero que al cogerlo da un objeto clave.

## Preparar

- [ ] Quita `TestLote9` de Lichii y desactiva cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote10` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku.

## Qué cambia

| Skulltula | Sala | Debería soltar | Copia de |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Resortera** | Rupia roja (se coge al pasar por encima) |
| B | Sótano, la de la rupia roja del lote 6 | **Bumerán** | Carta de Ruto, pero con la forma de coger de la pieza de corazón |
| C | Sótano, la de la pieza de corazón del lote 6 | **Gancho** | Pieza de corazón (se coge con el botón de acción) |
| D | Sala del fondo del sótano | Su ficha normal | Sin cambios (control) |

Nota sobre A: si ya tienes la Resortera del cofre, fíjate al menos en si aparece algo y si sale el mensaje de "has conseguido". Si puedes, mata a la Skulltula A antes de abrir el cofre de la Resortera.

## Comprobar

- [ ] **A:** ¿Aparece algo? ¿Qué aspecto tiene? ¿Cae al suelo o flota? ¿Se coge? ¿Sale la Resortera en el inventario? ______
- [ ] **B:** ¿Aparece algo? ¿Cae o flota? ¿Se coge? ¿Sale el Bumerán y se puede lanzar? ______
- [ ] **C:** ¿Aparece algo? ¿Cae o flota? ¿Se coge? ¿Sale el Gancho en el inventario? ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? Si el juego no arranca o se cuelga al entrar al Árbol Deku, apúntalo también. ______

## Resultados

Resultados en el juego (2026-11-10). Para llegar a la primera Skulltula hubo que coger antes la Resortera, porque las colisiones del remake obligan a matar a las Skulltulas del camino.

- **A (copia de la rupia roja → Resortera): funciona.** Cae al suelo y se coge, pero con el botón A, no al pasar por encima. Cogerla teniéndola ya no da problemas.
- **B (copia de la carta → Bumerán):** se queda flotando y no se coge al pasar por encima. Por dónde se quedó, no se pudo coger.
- **C (copia de la pieza de corazón → Gancho):** se queda flotando con el brillo y la zona de recogida de la pieza de corazón. No se coge al pasar por encima.
- **D: ficha normal.** El juego no se colgó.

Conclusiones:

- Un actor nuevo dado de alta en el registro aparece y entrega el objeto clave de su fila (`ActorName`).
- Lo de cogerlo al pasar por encima depende de `DefaultAutoGet` en el `PouchContentParam`. Los objetos clave no lo tienen, y por eso hacía falta el botón A.
- Lo que quiere el usuario es que el objeto se quede flotando donde estaba la Skulltula y se coja al pasar por encima, con el Gancho o con el Bumerán. Eso es justo lo que hace la ficha dorada (`Obj_Token_Gold`), así que el lote 11 usa la ficha como base.
