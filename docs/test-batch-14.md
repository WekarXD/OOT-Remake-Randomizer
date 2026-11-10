# Lote de prueba 14: dar de alta los objetos en el registro del inventario

En los lotes 11 a 13 los objetos flotaban y se cogían como una ficha, pero no llegaban al inventario. Faltaba darlos de alta en el registro del inventario (`RSDB/PouchActorInfo`), donde sí están la carta de Ruto, la ficha y las rupias. En este lote, cada copia lleva su fila en ese registro, igual que la del objeto que da.

Las tres son copias de la ficha dorada y deberían flotar y cogerse al pasar por encima, como en los lotes 11 a 13. Cada una usa una variante distinta de las ya probadas, para ver cuál funciona mejor.

## Preparar

- [ ] Quita `TestLote13` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote14` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas.

## Qué cambia

| Skulltula | Sala | Suelta | Variante |
|---|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Bumerán** | Ficha tal cual (como el lote 11) |
| B | Sótano | **Gancho** | Ficha con el "final" genérico (como A del lote 12) |
| C | Sótano | **Bolsa de bombas** | Ficha con final, comportamiento y forma de atrapar genéricos (como A del lote 13) |
| D | Sala del fondo del sótano | Su ficha normal | Control |

## Comprobar

- [ ] **A:** ¿Flota? ¿Se coge al pasar por encima? ¿Sale el **Bumerán en el inventario** y se puede lanzar? ______
- [ ] **B:** ¿Flota? ¿Se coge? ¿Sale el **Gancho en el inventario**? ______
- [ ] **C:** ¿Flota? ¿Se coge? ¿Sale la **Bolsa de bombas** y puedes llevar bombas? ______
- [ ] ¿Sale la animación o el mensaje de "has conseguido"? ______
- [ ] ¿El contador de fichas sube con A, B o C? Debería subir solo con D. ______
- [ ] Si tienes el Bumerán, ¿puedes atrapar alguno desde lejos con él? ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

Resultados en el juego (2026-11-10): **funciona.**

- **A (ficha tal cual, Bumerán):** flota, se coge al pasar por encima, sale en el inventario y se puede usar.
- **B (ficha con final genérico, Gancho):** flota, se puede coger con el Bumerán y sale en el inventario.
- **C (ficha con todo genérico, Bolsa de bombas):** flota, se coge con el Bumerán y sale en el inventario con 20 bombas, pero no se pueden lanzar. Es el mismo fallo ya conocido del v1: la Bolsa de bombas fuera de su cofre original nunca deja lanzar bombas (commit 2ad8165). No tiene que ver con las Skulltulas.
- **D: ficha normal.**

Conclusión: para que un objeto del mundo dé un objeto clave hacen falta cuatro cosas:

1. Un actor nuevo, copia de `Obj_Token_Gold` con el modelo, el nombre y el `PouchContentParam` del objeto (más `DefaultAutoGet`).
2. Su entrada en el RSTB.
3. Sus filas en `RSDB/ActorInfo`, `RSDB/GameActorInfo` y **`RSDB/PouchActorInfo`** (copia de la fila del objeto).
4. Apuntar a él en `Drop__DropActor`.

La variante más sencilla, la ficha tal cual (A), basta.
