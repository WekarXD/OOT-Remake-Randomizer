# Randomizer OOT Remake

Randomizador local en Python para el remake de Ocarina of Time de Switch 2 (motor de TotK), pensado para jugarse en el emulador Lichii. Es una aplicacion web que corre en tu equipo y genera un mod que cambia de sitio los objetos clave.

No incluye ningun archivo del juego: hace falta tu propio volcado.

## Requisitos

- Python 3.14 o superior (usa `compression.zstd` de la biblioteca estandar).
- Tu propio volcado del juego en formato `.nup`, version 1.1.1 (v131072).
- El emulador Lichii.

## Uso

```
python -m randomizer
```

Abre el navegador con la interfaz. Opciones: `--port <numero>` (por defecto 8765) y `--no-browser` (no abre el navegador). Elige el `.nup`, la semilla y los ajustes, y pulsa generar. El mod se crea en una carpeta `Rando_<semilla>`.

## Instalar el mod en Lichii

1. Copia la carpeta `Rando_<semilla>` (con su `romfs`) a `load/0400486024DEC000/Rando_<semilla>/romfs/...` dentro de los datos de Lichii. Si Lichii ofrece una opción para abrir la carpeta de mods del juego (clic derecho sobre el juego), úsala; si no, busca la carpeta load/0400486024DEC000/ dentro de la carpeta de datos de Lichii (su ubicación depende de tu instalación).
2. Deja activo **un solo** mod `Rando_*` a la vez; quita o desactiva los demas.
3. Empieza una partida nueva (una partida ya guardada no refleja el cambio).

Para jugarlo siguiendo una lista de comprobacion, ver `docs/acceptance.md`.

## Limitaciones de la v1

- **Se mueven 9 objetos clave:** Espada Kokiri, Resortera, Arco, Martillo, Lente de la Verdad, Flechas de hielo, Guanteletes de oro, Bolsa de bombas y Gancho largo.
- **Se quedan en su sitio 6:** Bumerán, Gancho, Botas de hierro, Botas levitadoras, Guanteletes de plata y Escudo espejo, porque sus cofres llevan eventos de historia.
- Solo 104 de los 203 cofres estan asociados con la logica; el resto conserva su contenido original.
- Llaves, mapas, brujulas, canciones y objetos de PNJ no se randomizan.
- La imagen y el texto del cofre pueden seguir mostrando el objeto original (aceptado en la v1); lo que recibes es el objeto nuevo.
- Las Flechas de hielo tambien desbloquean el medidor de magia.
- Activar o desactivar "Generar registro de spoilers" cambia la colocacion para la misma semilla.
- La logica es la de OoTR sin glitches.

## Tests

```
REM cmd:
set OOT_NUP=C:utal\juego.nup
# PowerShell:
$env:OOT_NUP="C:utal\juego.nup"
python -m unittest
```

Con `OOT_NUP` definido no se salta ningun test. Hay un fallo esperado documentado: `test_vanilla_is_beatable`, porque la logica sin glitches de OoTR no puede demostrar superable la distribucion de llaves totalmente original; no es un error.

## Lote de mods de prueba

```
python -I spikes/nuplist.py "<juego.nup>" output/files.tsv
python -I tools/make_test_batch.py "<juego.nup>" output/files.tsv test-mod
```

Crea `test-mod/0400486024DEC000/TestLote1` y `TestLote2`. Instrucciones: `docs/test-batch-1.md`.

## Atribucion y licencia

La logica de ubicaciones y objetos procede del Ocarina of Time Randomizer (OoTR), commit 526b4c8, y se usa bajo GPL-3.0. Este proyecto se distribuye bajo GPL-3.0 (ver LICENSE).
