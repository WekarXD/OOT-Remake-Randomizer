# Lote de prueba 11: objetos clave con el comportamiento de la ficha dorada

Lo que se busca es que el objeto se quede flotando donde estaba la Skulltula y que se pueda coger al pasar por encima, con el Gancho o con el Bumerán, igual que una ficha.

Cada actor nuevo es una copia de la **ficha dorada** (`Obj_Token_Gold`) con el modelo y la identidad de un objeto clave. Además lleva activada la recogida automática (`DefaultAutoGet`), que los objetos clave no traen.

## Preparar

- [ ] Quita `TestLote10` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote11` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva** y ve al Árbol Deku. Son las mismas Skulltulas de los lotes 9 y 10.

## Qué cambia

| Skulltula | Sala | Debería soltar |
|---|---|---|
| A | Sala de la brújula (piso de arriba) | **Bumerán** |
| B | Sótano (la que soltó el Bumerán en el lote 10) | **Gancho** |
| C | Sótano (la que soltó el Gancho en el lote 10) | **Bolsa de bombas** |
| D | Sala del fondo del sótano | Su ficha normal (control) |

Si puedes, coge el objeto de A, B o C de formas distintas: uno pasando por encima, otro con el Bumerán cuando lo tengas, y otro con el botón A.

## Comprobar

- [ ] **A:** ¿Aparece el Bumerán? ¿Flota donde estaba la Skulltula? ¿Se coge al pasar por encima? ¿Sale en el inventario y se puede lanzar? ______
- [ ] **B:** ¿Aparece el Gancho? ¿Flota? ¿Cómo lo has cogido? ¿Sale en el inventario? ______
- [ ] **C:** ¿Aparece la Bolsa de bombas? ¿Flota? ¿Cómo la has cogido? ¿Puedes llevar bombas? ______
- [ ] ¿Alguno se ha cogido con el Bumerán desde lejos? ______
- [ ] ¿El contador de fichas ha subido al coger A, B o C? Debería subir solo con D. ______
- [ ] **D:** ¿Ficha normal? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

(Pendiente de rellenar tras probarlo.)
