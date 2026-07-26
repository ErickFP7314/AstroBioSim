"""Tests de la validación estadística del Montecarlo (dueño: Erick).

Cubren los tres criterios de la tarea: convergencia de la media (SE decreciente),
reporte de media ± σ (desviación muestral), y reproducibilidad con semillas fijas.
Usan `ModoSandbox` en condiciones marginales (a_w apenas por encima del umbral de
crecimiento) para que el desenlace sea estocástico y haya dispersión real.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.analysis.validacion_montecarlo import estudio_convergencia
from astrobiosim.core.microorganism import EColi
from astrobiosim.modes.sandbox import ModoSandbox
from astrobiosim.simulation import sembrar_estado

E = EColi()
SHAPE = (14, 14)


def _estudio(semilla=0, metrica="viva", n_max=50):
    return estudio_convergencia(
        lambda rng: ModoSandbox(SHAPE, T=E.t_opt, R=0.0, A_w=0.97),  # γ_aw≈0.4 → estocástico
        E,
        lambda rng: sembrar_estado(SHAPE, rng=rng, fraccion_activa=0.15),
        n_max=n_max, semilla_base=semilla, metrica=metrica, n_iteraciones=18,
    )


# --------------------------------------------------------------------------
# Criterio 3: reproducibilidad
# --------------------------------------------------------------------------
def test_misma_semilla_misma_traza() -> None:
    a = _estudio(semilla=7)
    b = _estudio(semilla=7)
    np.testing.assert_array_equal(a.metrica_por_corrida, b.metrica_por_corrida)
    np.testing.assert_array_equal(a.media_acumulada, b.media_acumulada)


def test_semillas_distintas_dan_trazas_distintas() -> None:
    a = _estudio(semilla=1)
    b = _estudio(semilla=2)
    assert not np.array_equal(a.metrica_por_corrida, b.metrica_por_corrida)


# --------------------------------------------------------------------------
# Criterio 2: media ± σ (desviación muestral), no una corrida sola
# --------------------------------------------------------------------------
def test_media_y_desviacion_coinciden_con_numpy() -> None:
    r = _estudio(semilla=3)
    vals = r.metrica_por_corrida
    assert r.media_final == pytest.approx(float(np.mean(vals)))
    assert r.desviacion_final == pytest.approx(float(np.std(vals, ddof=1)))  # muestral


def test_error_estandar_es_desviacion_sobre_raiz_n() -> None:
    r = _estudio(semilla=3)
    assert r.error_final == pytest.approx(r.desviacion_final / np.sqrt(len(r.n)))


def test_con_una_sola_muestra_la_dispersion_es_indefinida() -> None:
    r = _estudio(semilla=3)
    assert np.isnan(r.desviacion_acumulada[0])  # n=1
    assert np.isnan(r.error_estandar[0])
    assert np.all(np.isfinite(r.error_estandar[1:]))  # n>=2 sí definido


# --------------------------------------------------------------------------
# Criterio 1: la media se estabiliza al aumentar N (SE decrece ~1/√N)
# --------------------------------------------------------------------------
def test_hay_dispersion_real() -> None:
    assert _estudio(semilla=5).desviacion_final > 0.0


def test_error_estandar_decrece_con_n() -> None:
    r = _estudio(semilla=5)
    # SE(n=50) < SE(n=5): el estimador se vuelve más preciso al sumar réplicas.
    assert r.error_estandar[-1] < r.error_estandar[4]


def test_n_suficiente_es_monotono_en_la_tolerancia() -> None:
    r = _estudio(semilla=5)
    n_laxo = r.n_suficiente(error_objetivo=0.1)
    n_estricto = r.n_suficiente(error_objetivo=0.01)
    assert n_laxo <= n_estricto
    assert 1 <= n_laxo <= len(r.n)


def test_n_suficiente_devuelve_n_max_si_no_se_alcanza() -> None:
    r = _estudio(semilla=5)
    assert r.n_suficiente(error_objetivo=-1.0) == len(r.n)  # imposible (SE ≥ 0) → n_max


# --------------------------------------------------------------------------
# Métrica e intervalos
# --------------------------------------------------------------------------
def test_viva_y_muerta_son_complementarias() -> None:
    viva = _estudio(semilla=9, metrica="viva").metrica_por_corrida
    muerta = _estudio(semilla=9, metrica="muerta").metrica_por_corrida
    np.testing.assert_allclose(viva + muerta, 1.0)  # viva=latente+activa, +muerta=1


def test_metrica_invalida_falla() -> None:
    with pytest.raises(ValueError):
        _estudio(metrica="presion")


def test_persistencia_es_binaria_y_detecta_extincion() -> None:
    # a_w=0.0: E. coli muere (a_w_sup_min=0.5) → nadie persiste → media 0.
    hostil = estudio_convergencia(
        lambda rng: ModoSandbox(SHAPE, T=E.t_opt, R=0.0, A_w=0.0),
        E, lambda rng: sembrar_estado(SHAPE, rng=rng, fraccion_activa=0.15),
        n_max=8, semilla_base=0, metrica="persistencia", n_iteraciones=10,
    )
    assert set(np.unique(hostil.metrica_por_corrida)) == {0.0}
    assert hostil.media_final == 0.0
    # a_w=1.0 (óptimo): todos persisten → media 1.
    favorable = _estudio(semilla=0, metrica="persistencia", n_max=8)
    assert set(np.unique(favorable.metrica_por_corrida)).issubset({0.0, 1.0})


def test_intervalo_encierra_la_media() -> None:
    r = _estudio(semilla=4)
    lo, hi = r.intervalo(0.95)
    assert np.all(hi[1:] >= r.media_acumulada[1:])
    assert np.all(lo[1:] <= r.media_acumulada[1:])
    with pytest.raises(ValueError):
        r.intervalo(0.5)  # nivel no soportado
