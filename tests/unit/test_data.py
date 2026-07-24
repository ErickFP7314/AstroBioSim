"""Tests de los adaptadores de datos (dueño: Fidel) — contrato §3.5.

Cubre las dos rutas de cada loader: el CSV real 2025 y el fallback sintético que
se dispara cuando el archivo no existe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from astrobiosim.data.loaders import (
    COLUMNAS_ATACAMA,
    COLUMNAS_CANONICAS,
    cargar_atacama,
    cargar_control_tierra,
    cargar_ventilas,
)

_PROC = Path(__file__).resolve().parents[2] / "data" / "processed"
TIERRA = _PROC / "datos_tierra_control_2025.csv"
ATACAMA = _PROC / "datos_atacama_2025_EXTREMOS_REALES.csv"
VENTILAS = _PROC / "datos_ventilas_2025_procesados.csv"

REALES = [
    (cargar_control_tierra, TIERRA, COLUMNAS_CANONICAS),
    (cargar_atacama, ATACAMA, COLUMNAS_ATACAMA),
    (cargar_ventilas, VENTILAS, COLUMNAS_CANONICAS),
]
IDS = ["tierra", "atacama", "ventilas"]


# --------------------------------------------------------------------------
# Carga real: esquema canónico
# --------------------------------------------------------------------------
@pytest.mark.parametrize(("loader", "ruta", "columnas"), REALES, ids=IDS)
def test_columnas_canonicas_exactas(loader, ruta, columnas) -> None:
    df = loader(str(ruta))
    assert list(df.columns) == list(columnas)


@pytest.mark.parametrize(("loader", "ruta", "columnas"), REALES, ids=IDS)
def test_todas_las_fuentes_tienen_365_filas(loader, ruta, columnas) -> None:
    assert len(loader(str(ruta))) == 365


@pytest.mark.parametrize(("loader", "ruta", "columnas"), REALES, ids=IDS)
def test_a_w_siempre_en_rango(loader, ruta, columnas) -> None:
    df = loader(str(ruta))
    assert df["a_w"].dropna().between(0.0, 1.0).all()


@pytest.mark.parametrize(("loader", "ruta", "columnas"), REALES, ids=IDS)
def test_t_es_datetime_sin_zona_horaria(loader, ruta, columnas) -> None:
    df = loader(str(ruta))
    assert pd.api.types.is_datetime64_dtype(df["t"])
    assert df["t"].dt.tz is None


def test_ventilas_descarta_salinidad_y_preserva_el_hueco() -> None:
    df = cargar_ventilas(str(VENTILAS))
    assert "Salinidad_psu" not in df.columns
    # el hueco real de 8 días (17–24 ago) NO se rellena en el loader
    assert df["a_w"].isna().sum() == 8
    assert df["temperature"].isna().sum() == 8


def test_atacama_temperature_es_media_de_los_extremos() -> None:
    df = cargar_atacama(str(ATACAMA))
    esperado = (df["temperature_min"] + df["temperature_max"]) / 2.0
    pd.testing.assert_series_equal(df["temperature"], esperado, check_names=False)


def test_tierra_a_w_es_directa_del_dataset() -> None:
    """`a_w` viene tal cual (0..1): ya NO se calcula humidity/100."""
    crudo = pd.read_csv(TIERRA)
    df = cargar_control_tierra(str(TIERRA))
    pd.testing.assert_series_equal(
        df["a_w"], crudo["Actividad_Agua_aw"], check_names=False
    )


# --------------------------------------------------------------------------
# Fallback sintético
# --------------------------------------------------------------------------
def test_fallback_se_activa_si_el_csv_no_existe(tmp_path) -> None:
    df = cargar_atacama(str(tmp_path / "no_existe.csv"))
    assert list(df.columns) == list(COLUMNAS_ATACAMA)
    assert len(df) == 365


@pytest.mark.parametrize(("loader", "columnas"), [
    (cargar_control_tierra, COLUMNAS_CANONICAS),
    (cargar_atacama, COLUMNAS_ATACAMA),
    (cargar_ventilas, COLUMNAS_CANONICAS),
], ids=IDS)
def test_fallback_respeta_interfaz_canonica_y_rango_fisico(loader, columnas, tmp_path) -> None:
    df = loader(str(tmp_path / "x.csv"), rng=np.random.default_rng(1))
    assert list(df.columns) == list(columnas)
    assert df["a_w"].between(0.0, 1.0).all()
    assert (df["radiation"] >= 0.0).all()
    # el fallback es limpio: no inventa NaN
    assert not df.drop(columns="t").isna().to_numpy().any()


def test_fallback_es_reproducible_con_la_misma_semilla(tmp_path) -> None:
    ruta = str(tmp_path / "x.csv")
    a = cargar_control_tierra(ruta, rng=np.random.default_rng(7))
    b = cargar_control_tierra(ruta, rng=np.random.default_rng(7))
    pd.testing.assert_frame_equal(a, b)
    distinta = cargar_control_tierra(ruta, rng=np.random.default_rng(8))
    assert not a["temperature"].equals(distinta["temperature"])


def test_fallback_atacama_respeta_min_menor_o_igual_que_max(tmp_path) -> None:
    df = cargar_atacama(str(tmp_path / "x.csv"), rng=np.random.default_rng(3))
    assert (df["temperature_min"] <= df["temperature_max"]).all()
    esperado = (df["temperature_min"] + df["temperature_max"]) / 2.0
    pd.testing.assert_series_equal(df["temperature"], esperado, check_names=False)
