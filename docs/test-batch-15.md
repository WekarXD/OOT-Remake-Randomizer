# Lote de prueba 15: Tokensanity, fase 1

Prueba en el juego lo que falta por saber antes de construir Tokensanity (diseño: `docs/superpowers/specs/2026-11-10-tokensanity-design.md`, §4). Los objetos de las Skulltulas son copias de la ficha dorada, como en el lote 14 (A).

## Preparar

- [ ] Quita `TestLote14` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/TestLote15` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva**. Apunta antes de empezar cuántas fichas tienes (0).

## Qué cambia

| Sitio | Dónde | Suelta o contiene | Qué se prueba |
|---|---|---|---|
| Cofre de arriba a la izquierda | Casa de Mido (los dos cofres de la fila de atrás, que daban rupias azules) | Ficha (`Obj_Token_Gold`) | Ficha en un cofre |
| Cofre de arriba a la derecha | Casa de Mido | Ficha (`Item_Token_Gold`) | Ficha en un cofre, otra forma |
| Skulltula nocturna | Bosque Kokiri, de noche, en la casa del Sabelotodo | **Guanteletes de plata** | Skulltula nocturna |
| Skulltula de tierra blanda | Bosque Kokiri, en la tierra blanda (hay que soltar insectos de una botella; si no tienes botella, sáltatela) | **Lente de la Verdad** | Skulltula de tierra blanda |
| A | Árbol Deku, sala de la brújula | **Botas de hierro** | Volver a entrar |
| B | Árbol Deku, sótano | **Su ficha**, puesta a mano | Ficha que suelta una Skulltula por la vía nueva |
| C | Árbol Deku, sótano | **Martillo** | Salir sin cogerlo |
| D | Árbol Deku, sala del fondo del sótano | **Escudo espejo** | Guardar y cargar |

Los objetos de adulto (botas, guanteletes, martillo, escudo espejo) no se pueden usar de niño. Basta con que aparezcan en el inventario o en el equipo.

## Comprobar

- [ ] **Cofres de Mido:** ¿qué sale de cada uno? ¿Sube el contador de fichas (debería quedar en 2)? ______
- [ ] **Skulltula nocturna:** ¿aparece de noche? ¿Suelta los Guanteletes de plata? ¿Llegan al equipo? ______
- [ ] **Tierra blanda** (si puedes): ¿sale la Skulltula? ¿Suelta la Lente? ¿Llega al inventario? ______
- [ ] **A:** coge las Botas, sal de la sala y vuelve a entrar. ¿La Skulltula vuelve a aparecer? ¿Suelta otra vez las botas? ______
- [ ] **B:** ¿sale la ficha y sube el contador? Sal y vuelve: ¿vuelve a aparecer la Skulltula? ______
- [ ] **C:** mata la Skulltula y **no cojas** el Martillo. Sal de la sala y vuelve. ¿Sigue el Martillo flotando? ¿Vuelve la Skulltula? Luego cógelo: ¿llega al inventario? ______
- [ ] **D:** coge el Escudo espejo, **guarda la partida, sal y cárgala**. ¿Sigue el escudo en el equipo? ¿Vuelve a aparecer la Skulltula de D? ______
- [ ] **Contador final:** ¿cuántas fichas tienes al terminar? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

(Pendiente de rellenar tras probarlo.)
