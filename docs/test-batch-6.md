# Lote de prueba 6: ¿qué pueden soltar las Skulltulas doradas?

Objetivo: saber si una Skulltula dorada puede soltar otro objeto en lugar de su ficha. Hay dos casos:

- un **objeto importante** (`Item_*`, como el Gancho);
- un **objeto "de suelo"** (`Obj_*`, como una rupia o una pieza de corazón).

El resultado decide qué se puede repartir en Skulltulas, jarrones, cajas y colmenas.

## Preparar

- [ ] Desactiva cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote6` a `load/0400486024DEC000/` en Lichii.
- [ ] Empieza una **partida nueva**: el mod solo cambia el Árbol Deku, así que puedes ir directo a por él.

## Qué cambia

Hay cuatro Skulltulas doradas en el Árbol Deku. Las salas son mi suposición a partir de los datos.

| Skulltula | Sala (creo) | Debería soltar |
|---|---|---|
| A | Sala de la brújula (piso de arriba, en la pared de enredaderas) | **Gancho** |
| B | Sótano, primera sala (una de las dos) | **Rupia roja** |
| C | Sótano, primera sala (la otra) | **Pieza de corazón** |
| D | Sala del fondo del sótano | Su ficha normal (sin cambios, de control) |

## Comprobar

Para cada Skulltula apunta qué ha soltado y si te lo has podido quedar:

- [ ] **A:** ¿Gancho? ¿Aparece en el inventario y se puede usar? ______
- [ ] **B:** ¿Rupia roja? ¿Sube el contador en 20? ______
- [ ] **C:** ¿Pieza de corazón? ¿Sube el contador de piezas? ______
- [ ] **D:** ¿Ficha de Skulltula normal? ______
- [ ] Si alguna ha soltado su ficha normal en vez del objeto nuevo, o nada, o el juego se ha colgado, apunta cuál. ______

Si tienes tiempo:

- [ ] Sal del Árbol Deku y vuelve a entrar. ¿Vuelven a aparecer las Skulltulas A, B o C? ______

## Resultados

