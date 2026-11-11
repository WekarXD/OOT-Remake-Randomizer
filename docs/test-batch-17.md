# Lote de prueba 17: primera semilla con Tokensanity

Es la primera semilla con Tokensanity en "Todas", con "Saltar cinemáticas" desactivado. Las Skulltulas pueden soltar objetos clave, rupias, etc., y las fichas están repartidas por cofres y Skulltulas. El registro completo está en `spoiler.txt`, dentro de la carpeta del mod (contiene todo lo que hay en cada sitio).

## Intento 1: semilla `TestTokens1` (bloqueada)

- Los cofres de Mido y el de la Espada Kokiri daban lo esperado.
- **No se podía avanzar en el Árbol Deku.** Para subir al piso de la sala de la brújula hay que matar las Skulltulas normales de las enredaderas, y de niño eso pide un arma a distancia. La Resortera estaba justo en ese piso, en el cofre lateral de la sala de la brújula. La lógica de OoTR da ese piso por accesible sin nada.
- **Arreglo:** hay reglas propias del remake (`REMAKE_RULES` en `randomizer/logic/world.py`). Para pedir a la Resortera, el Arco o el Gancho hay:
  - los dos cofres de la sala de la brújula;
  - la Skulltula dorada de la sala de la brújula;
  - la bajada al sótano (se abre saltando desde ese piso sobre la telaraña).

## Intento 2: semilla `TestTokens2`

### Preparar

- [ ] Quita `Rando_TestTokens1` y cualquier otro mod `Rando_*`, `TestLote*` y `TestEscenas*`.
- [ ] Copia `test-mod/0400486024DEC000/Rando_TestTokens2` a `load/0400486024DEC000/`.
- [ ] Empieza una **partida nueva**.

### Qué comprobar (inicio de partida)

| Sitio | Debería dar |
|---|---|
| Cofre de la Espada Kokiri (el del laberinto pequeño del Bosque Kokiri) | **Ficha** |
| Casa de Mido: arriba izquierda, arriba derecha y abajo izquierda | **Ficha** en cada uno |
| Casa de Mido, abajo a la derecha | **Espada Kokiri** |
| Gruta de la tormenta del Bosque Kokiri (la de la canción de la tormenta, para más adelante) | Ficha |
| Árbol Deku, sala de la Resortera (piso 2, hace falta el Escudo Deku de la tienda), cofre lateral | **Resortera** |
| Árbol Deku, sala de la Resortera, cofre grande | Bombas |
| Árbol Deku, sala de la brújula, cofre lateral | Escudo Deku |
| Árbol Deku, Skulltula de la sala de la brújula | Su ficha |
| Árbol Deku, cofre del sótano | Ficha |
| Árbol Deku, Skulltula de la reja del sótano | **Rupia azul** |
| Árbol Deku, Skulltula de las enredaderas del sótano | **Rupia morada** |
| Árbol Deku, Skulltula de la sala del fondo del sótano | Su ficha |
| Bosque Kokiri, Skulltula de la casa del Sabelotodo (de noche, niño) | Rupia roja |

Objetos clave en Skulltulas, si llegas más lejos:

- Cueva de los Dodongos, Skulltula de las enredaderas encima de las escaleras: **Gancho largo**.
- Cráter de la Montaña de la Muerte, Skulltula del sitio de las judías: **Guanteletes de oro**.
- Templo del Espíritu, Skulltula de la valla metálica: **Martillo**.

### Comprobar

- [ ] ¿Los cofres de la tabla dan lo que dice? ¿El contador de fichas sube con las fichas de los cofres? ______
- [ ] ¿Con la Resortera puedes matar las Skulltulas de las enredaderas y subir a la sala de la brújula? ______
- [ ] ¿Las Skulltulas del sótano sueltan la rupia azul y la morada, y se pueden coger? ______
- [ ] ¿Alguna Skulltula ha soltado algo distinto de lo esperado, o nada? ¿Cuál? ______
- [ ] ¿Hay algún otro sitio al que la lógica te mande y no se pueda llegar? ______
- [ ] ¿Se ha colgado el juego o ha salido una pantalla negra? ¿Cuándo? ______

## Resultados

(Pendiente de rellenar tras probarlo.)
