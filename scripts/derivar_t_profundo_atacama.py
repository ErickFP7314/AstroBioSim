#!/usr/bin/env python3
"""Re-deriva `MarteSubsuelo.T_PROFUNDO_C` (docs/parametros.md §2, deuda #2).

A diferencia de `derivar_a_w_media_atacama.py`, esta no necesita el crudo: el
dataset **procesado** (`data/processed/datos_atacama_2025_EXTREMOS_REALES.csv`,
ya versionado) trae `Temp_Maxima_Superficie_C` y `Temp_Minima_Superficie_C`
por día, suficiente para aproximar la media diaria con `(max + min) / 2` — la
aproximación meteorológica estándar cuando no hay serie continua.

`T_PROFUNDO_C` es la asíntota fría hacia la que amortigua la onda térmica
diurna del regolito: por definición es la media **anual**, no la media de los
mínimos diarios (esa era una cota pesimista, mismo sesgo de muestreo que
`A_W_MEDIA` antes de re-derivarse).

Uso
---
    python scripts/derivar_t_profundo_atacama.py
"""
from __future__ import annotations

import csv
from pathlib import Path

RUTA_DATASET = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "datos_atacama_2025_EXTREMOS_REALES.csv"
)


def derivar(ruta: Path = RUTA_DATASET) -> None:
    with ruta.open(newline="", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))

    maximos = [float(f["Temp_Maxima_Superficie_C"]) for f in filas]
    minimos = [float(f["Temp_Minima_Superficie_C"]) for f in filas]
    medias_diarias = [(a + b) / 2 for a, b in zip(maximos, minimos)]

    print(f"Días con datos: {len(filas)}")
    print(f"Media de máximos diarios (T_SUPERFICIE_C) = {sum(maximos) / len(maximos):.1f}")
    print(f"Media de mínimos diarios (valor previo, sesgado) = {sum(minimos) / len(minimos):.1f}")
    print(
        "Media ANUAL real ~ media de (max+min)/2 por día "
        f"(T_PROFUNDO_C) = {sum(medias_diarias) / len(medias_diarias):.1f}"
    )


if __name__ == "__main__":
    derivar()
