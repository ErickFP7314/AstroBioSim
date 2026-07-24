"""Tests de `resampling.py` (dueño: Fidel) — mapeo UV, limpieza y secuencia de campos."""
from __future__ import annotations

import numpy as np
import pandas as pd

from astrobiosim.core.environment import FRACCION_UV, CampoAmbiental
from astrobiosim.data.resampling import (
    Entorno,
    limpiar_ventilas,
    mapear_radiacion,
    secuencia_campos,
)


def _df_canonico(n=12, con_hueco=False):
    df = pd.DataFrame(
        {
            "t": pd.date_range("2025-01-01", periods=n, freq="D"),
            "temperature": np.linspace(5.0, 30.0, n),
            "a_w": np.linspace(0.2, 0.9, n),
            "radiation": np.linspace(300.0, 900.0, n),
        }
    )
    if con_hueco:
        df.loc[4:7, ["temperature", "a_w", "radiation"]] = np.nan  # 4 días NaN interiores
    return df


# --------------------------------------------------------------------------
# mapear_radiacion (ADR-0014)
# --------------------------------------------------------------------------
def test_superficies_convierten_la_irradiancia_global_a_banda_uv() -> None:
    rad = np.array([320.0, 850.0, 1150.0])
    for entorno in (Entorno.TIERRA, Entorno.MARTE):
        np.testing.assert_allclose(mapear_radiacion(rad, entorno), rad * FRACCION_UV)


def test_el_uv_es_una_fraccion_pequena_de_la_irradiancia_global() -> None:
    rad = np.array([844.0])
    uv = mapear_radiacion(rad, Entorno.MARTE)
    assert np.all(uv < 0.1 * rad)
    assert np.all(uv > 0.0)


def test_encelado_mapea_radiacion_a_cero() -> None:
    rad = np.array([320.0, 320.5, 319.8])
    resultado = mapear_radiacion(rad, Entorno.ENCELADO)
    np.testing.assert_array_equal(resultado, np.zeros_like(rad))
    assert resultado.shape == rad.shape


# --------------------------------------------------------------------------
# limpiar_ventilas: interpolación lineal acotada
# --------------------------------------------------------------------------
def test_limpiar_rellena_los_nan_interiores_sin_salir_de_rango() -> None:
    df = _df_canonico(con_hueco=True)
    limpio = limpiar_ventilas(df)
    assert limpio[["temperature", "a_w", "radiation"]].isna().sum().sum() == 0
    # el relleno queda entre los bordes reales del hueco (no inventa extremos)
    assert limpio["a_w"].between(df["a_w"].min(), df["a_w"].max()).all()
    # la interpolación lineal de una serie ya lineal reconstruye el valor exacto
    esperado = np.linspace(0.2, 0.9, len(df))
    np.testing.assert_allclose(limpio["a_w"].to_numpy(), esperado)


def test_limpiar_no_toca_las_filas_sin_nan_ni_el_df_original() -> None:
    df = _df_canonico(con_hueco=True)
    original = df.copy()
    limpio = limpiar_ventilas(df)
    pd.testing.assert_frame_equal(df, original)  # no muta la entrada
    ok = [i for i in range(len(df)) if i not in (4, 5, 6, 7)]
    np.testing.assert_array_equal(
        limpio.loc[ok, "temperature"].to_numpy(), df.loc[ok, "temperature"].to_numpy()
    )


# --------------------------------------------------------------------------
# secuencia_campos: reusa el modelo espacial de Jose (ADR-0017)
# --------------------------------------------------------------------------
def test_secuencia_da_un_campo_por_fila_en_rango_fisico() -> None:
    df = _df_canonico(10)
    campos = list(secuencia_campos(df, Entorno.MARTE, shape=(8, 8)))
    assert len(campos) == len(df)
    for c in campos:
        assert isinstance(c, CampoAmbiental)
        assert c.shape == (8, 8)
        assert np.all((c.A_w >= 0.0) & (c.A_w <= 1.0))
        assert np.all(c.R >= 0.0)


def test_marte_conserva_la_banda_de_profundidad_en_cada_tick() -> None:
    """El UV debe decaer con la profundidad; si fuera uniforme, esterilizaría todo."""
    df = _df_canonico(3)
    campo = next(secuencia_campos(df, Entorno.MARTE, shape=(20, 5)))
    assert campo.R[0, 0] > campo.R[-1, 0]  # más UV en superficie que en profundidad
    assert np.all(np.diff(campo.R, axis=0) <= 1e-9)  # monótono no creciente


def test_encelado_secuencia_mantiene_R_cero_y_fumarolas() -> None:
    df = _df_canonico(3)
    campo = next(secuencia_campos(df, Entorno.ENCELADO, shape=(20, 20)))
    assert np.all(campo.R == 0.0)
    assert campo.T.max() > campo.T.min()  # las fumarolas rompen la uniformidad


def test_secuencia_es_reproducible_con_la_misma_semilla() -> None:
    df = _df_canonico(5)
    a = list(secuencia_campos(df, Entorno.MARTE, (8, 8), rng=np.random.default_rng(1)))
    b = list(secuencia_campos(df, Entorno.MARTE, (8, 8), rng=np.random.default_rng(1)))
    for ca, cb in zip(a, b, strict=True):
        np.testing.assert_array_equal(ca.A_w, cb.A_w)
