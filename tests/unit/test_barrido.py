"""Tests del barrido de microrefugios (dueño: Erick) — ADR-0015.

Usan `ModoSandbox` con campos controlados (sin datasets) para probar la mecánica
del umbral: un campo hostil sin refugios se extingue; con refugios fuertes, la
población persiste.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.analysis.barrido import (
    ResultadoBarrido,
    _construir_salmuera,
    barrido_microrefugios,
    evaluar_punto,
)
from astrobiosim.core.microorganism import EColi
from astrobiosim.modes.sandbox import ModoSandbox

E = EColi()


def _modo(a_w: float, shape=(12, 12)):
    """Factory de ModoSandbox con T óptima, sin UV y `a_w` fijo."""
    return lambda rng: ModoSandbox(shape, T=E.t_opt, R=0.0, A_w=a_w)


# --------------------------------------------------------------------------
# Mecánica del umbral
# --------------------------------------------------------------------------
def test_campo_favorable_persiste_sin_refugios() -> None:
    """A_w = 1.0 (óptimo): la población vive aunque no haya refugios (freq=0)."""
    prob, viva = evaluar_punto(
        _modo(1.0), E, frecuencia=0.0, magnitud=0.98,
        shape=(12, 12), n_corridas=3, n_iteraciones=10, semilla_base=1,
    )
    assert prob == 1.0
    assert viva > 0.0


def test_campo_hostil_sin_refugios_se_extingue() -> None:
    """A_w = 0.0 y freq=0 (sin salmuera): extinción total, persistencia nula."""
    prob, viva = evaluar_punto(
        _modo(0.0), E, frecuencia=0.0, magnitud=0.98,
        shape=(12, 12), n_corridas=3, n_iteraciones=10, semilla_base=1,
    )
    assert prob == 0.0
    assert viva == 0.0


def test_refugio_fuerte_rescata_un_campo_hostil() -> None:
    """En un campo hostil, un refugio amplio y frecuente sube la persistencia por
    encima del caso sin refugios (que es 0)."""
    comun = {
        "especie": E, "magnitud": 0.98, "shape": (12, 12), "n_corridas": 4,
        "n_iteraciones": 15, "semilla_base": 7,
        "salmuera_base": {"radio_celdas": 50.0, "umbral_extincion": 0.001},
    }
    sin, _ = evaluar_punto(_modo(0.0), frecuencia=0.0, **comun)
    con, viva_con = evaluar_punto(_modo(0.0), frecuencia=0.9, **comun)
    assert sin == 0.0
    assert con > sin  # el refugio cambia el desenlace
    assert viva_con > 0.0


# --------------------------------------------------------------------------
# Barrido completo: shapes, rangos, reproducibilidad
# --------------------------------------------------------------------------
def _barrido_chico(semilla=0):
    return barrido_microrefugios(
        _modo(0.0, shape=(10, 10)), E,
        frecuencias=[0.0, 0.9],
        magnitudes=[0.85, 0.98],
        eje_magnitud="a_w",
        shape=(10, 10),
        n_corridas=3,
        n_iteraciones=8,
        semilla_base=semilla,
        salmuera_base={"radio_celdas": 50.0},
    )


def test_barrido_shapes_y_rangos() -> None:
    r = _barrido_chico()
    assert r.prob_persistencia.shape == (2, 2)  # (magnitudes, frecuencias)
    assert r.fraccion_media.shape == (2, 2)
    assert np.all((r.prob_persistencia >= 0.0) & (r.prob_persistencia <= 1.0))
    assert np.all((r.fraccion_media >= 0.0) & (r.fraccion_media <= 1.0))


def test_barrido_reproducible_con_la_misma_semilla() -> None:
    a = _barrido_chico(semilla=5)
    b = _barrido_chico(semilla=5)
    np.testing.assert_array_equal(a.prob_persistencia, b.prob_persistencia)
    np.testing.assert_array_equal(a.fraccion_media, b.fraccion_media)


def test_frecuencia_cero_no_persiste_en_campo_hostil() -> None:
    """La columna de frecuencia 0 (sin refugios) es toda extinción."""
    r = _barrido_chico()
    col_freq0 = r.prob_persistencia[:, 0]  # frecuencias[0] == 0.0
    assert np.all(col_freq0 == 0.0)


# --------------------------------------------------------------------------
# Eje de magnitud ajustable
# --------------------------------------------------------------------------
def test_eje_a_w_fija_el_pico() -> None:
    s = _construir_salmuera(0.1, 0.93, "a_w", {})
    assert s.a_w_objetivo_min == 0.93 and s.a_w_objetivo_max == 0.93
    assert s.probabilidad_disparo == 0.1


def test_eje_duracion_fija_la_duracion() -> None:
    s = _construir_salmuera(0.1, 12.0, "duracion", {})
    assert s.duracion_min_ticks == 12.0 and s.duracion_max_ticks == 12.0


def test_eje_radio_fija_el_radio() -> None:
    s = _construir_salmuera(0.1, 5.0, "radio", {})
    assert s.radio_celdas == 5.0


def test_eje_desconocido_falla() -> None:
    with pytest.raises(ValueError):
        _construir_salmuera(0.1, 1.0, "presion", {})  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# curva_critica y a_dataframe (sobre un mapa sintético)
# --------------------------------------------------------------------------
def _resultado_sintetico() -> ResultadoBarrido:
    # prob crece con la magnitud (filas) para cada frecuencia (columnas)
    prob = np.array([[0.0, 0.2], [0.3, 0.7], [0.6, 0.9]])  # (3 magnitudes, 2 freq)
    return ResultadoBarrido(
        frecuencias=np.array([0.1, 0.4]),
        magnitudes=np.array([0.80, 0.90, 0.98]),
        eje_magnitud="a_w",
        prob_persistencia=prob,
        fraccion_media=prob * 0.5,
        n_corridas=10, semilla_base=0, shape=(10, 10),
        fraccion_activa=0.15, n_iteraciones=None,
    )


def test_curva_critica_toma_la_minima_magnitud_sobre_el_nivel() -> None:
    r = _resultado_sintetico()
    curva = r.curva_critica(nivel=0.5)
    # freq=0.1: primera magnitud con prob>=0.5 es 0.98; freq=0.4: es 0.90
    np.testing.assert_array_equal(curva, np.array([0.98, 0.90]))


def test_curva_critica_nan_si_nunca_alcanza_el_nivel() -> None:
    r = _resultado_sintetico()
    curva = r.curva_critica(nivel=0.99)  # ninguna prob llega a 0.99
    assert np.all(np.isnan(curva))


def test_a_dataframe_tiene_una_fila_por_punto() -> None:
    r = _resultado_sintetico()
    df = r.a_dataframe()
    assert len(df) == 3 * 2
    assert set(df.columns) == {
        "frecuencia", "magnitud", "eje_magnitud", "poblacion",
        "prob_persistencia", "fraccion_media",
    }


def test_poblacion_activa_es_mas_estricta_que_viva() -> None:
    """En un campo que solo permite SOBREVIVIR (latente) sin crecer, 'viva'
    persiste pero 'activa' no: la métrica distingue dormir de estar viable."""
    # a_w = 0.70: EColi sobrevive (latente) pero no crece (a_w_min > 0.70).
    comun = {
        "especie": E, "frecuencia": 0.0, "magnitud": 0.98, "shape": (12, 12),
        "n_corridas": 3, "n_iteraciones": 8, "semilla_base": 1,
    }
    prob_viva, _ = evaluar_punto(_modo(0.70), poblacion="viva", **comun)
    prob_activa, _ = evaluar_punto(_modo(0.70), poblacion="activa", **comun)
    assert prob_viva == 1.0      # sobrevive dormida
    assert prob_activa == 0.0    # pero no hay población creciendo
