#!/usr/bin/env python3
"""Re-deriva `MarteSubsuelo.A_W_MEDIA`/`A_W_SIGMA` (docs/parametros.md §2, deuda #1).

El dataset procesado (`data/processed/datos_atacama_2025_EXTREMOS_REALES.csv`) solo
trae `Actividad_Agua_Minima_aw`: el **mínimo diario**, una cota pesimista. Este
script recalcula la **media diaria real** a partir de la humedad relativa cruda
(resolución de 10 min) de la estación fuente, y no se guarda en el repo porque
`data/raw/` no se versiona (ver `data/README.md`).

Reproducir
----------
1. Ir a https://www.crc1211db.uni-koeln.de/wd/index.php?station=13 (estación 13,
   "Cerros de Calate", transecto centro — DOI individual 10.5880/CRC1211DB.4) y
   usar el botón "Download" con el rango 2025-01-01..2025-12-31. La estación solo
   tiene datos desde 2025-03-27 (mantenimiento) hasta 2025-12-06; el resto del año
   no está disponible para 2025 en esta estación.
2. Descomprimir el .zip y pasar la ruta del .txt a este script:
       python scripts/derivar_a_w_media_atacama.py ruta/al/station[13]_...txt

Fórmula: `a_w = RH_1 / 100` por lectura (ADR-0005; `RH_1` es el sensor de humedad
de aire primario, `RH_2` es un segundo sensor casi idéntico: correlación 0.995
sobre esta serie). Promedio diario, y luego media/sd de esos promedios diarios.

Validación: la media de los MÍNIMOS diarios de esta misma serie cruda (≈0.185) es
prácticamente igual al 0.187 documentado en `Actividad_Agua_Minima_aw` — confirma
que la estación 13 es consistente con el dataset procesado.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

CITA = (
    "Hoffmeister, D. (2018): Meteorological and soil measurements of the "
    "permanent weather stations in the Atacama desert, Chile. CRC1211 Database "
    "(CRC1211DB). DOI: 10.5880/CRC1211DB.1 (estación 13: 10.5880/CRC1211DB.4)."
)


def derivar(ruta: Path) -> None:
    df = pd.read_csv(ruta)
    df.columns = [c.split(" [")[0] for c in df.columns]
    df["DATETIME"] = pd.to_datetime(df["DATETIME"])
    df["a_w"] = df["RH_1"] / 100.0
    if not df["a_w"].between(0.0, 1.0).all():
        sys.exit("a_w fuera de [0, 1] tras RH_1 / 100 — revisar el archivo fuente.")

    diario = df.groupby(df["DATETIME"].dt.date)["a_w"].agg(["mean", "min"])

    print(CITA)
    print(f"\nRango cubierto: {df['DATETIME'].min()} .. {df['DATETIME'].max()}")
    print(f"Días con datos: {len(diario)}\n")
    print(f"A_W_MEDIA (media de la media diaria) = {diario['mean'].mean():.3f}")
    print(f"A_W_SIGMA (sd de la media diaria)     = {diario['mean'].std():.3f}")
    print(
        f"\nValidación — media de los MÍNIMOS diarios = {diario['min'].mean():.3f} "
        "(comparar con 0.187 de Actividad_Agua_Minima_aw)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ruta", type=Path, help="Ruta al .txt crudo de CRC1211DB")
    args = parser.parse_args()
    derivar(args.ruta)


if __name__ == "__main__":
    main()
