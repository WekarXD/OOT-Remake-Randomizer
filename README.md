# Randomizer OOT Remake

Randomizador en Python para el remake de Ocarina of Time de Switch 2 (motor de TotK), pensado para jugarse en el emulador Lichii.

Estado: en desarrollo (v1). No incluye ningun archivo del juego; hace falta tu propio volcado (.nup).

## Lote de mods de prueba

```
python -I spikes/nuplist.py "<juego.nup>" output/files.tsv
python -I tools/make_test_batch.py "<juego.nup>" output/files.tsv test-mod
```

Crea `test-mod/0400486024DEC000/TestLote1` y `TestLote2`. Instrucciones de prueba: `docs/test-batch-1.md`.

## Atribucion

Inspirado en el Ocarina of Time Randomizer (OoTR) y su logica de ubicaciones/objetos. Licencia: GPL-3.0 (ver LICENSE).
