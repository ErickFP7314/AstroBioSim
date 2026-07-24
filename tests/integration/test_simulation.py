"""Tests del orquestador `simulation.py` (dueño: Erick) — acople de todos los motores."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from astrobiosim.core.environment import CampoAmbiental, MarteSubsuelo
from astrobiosim.core.microorganism import ACTIVA, MUERTA, DRadiodurans, EColi
from astrobiosim.data.loaders import cargar_atacama
from astrobiosim.data.resampling import Entorno
from astrobiosim.engine.stochastic import MicroFisuraMarte
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.modes.base import ModoEstatico
from astrobiosim.simulation import ResultadoSimulacion, sembrar_estado, simular

_ATACAMA = (
    Path(__file__).resolve().parents[2]
    / "data" / "processed" / "datos_atacama_2025_EXTREMOS_REALES.csv"
)


def _campo(t, r, a_w, shape):
    return CampoAmbiental(
        T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w)
    )


def _campo_optimo(especie, shape):
    return _campo(especie.t_opt, 0.0, 1.0, shape)


# --------------------------------------------------------------------------
# Bucle básico y forma del resultado
# --------------------------------------------------------------------------
def test_corre_n_iteraciones_y_devuelve_la_serie_con_t0() -> None:
    e = EColi()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    res = simular(
        ModoEstatico(_campo_optimo(e, shape)), e, estado,
        np.random.default_rng(1), n_iteraciones=12,
    )
    assert isinstance(res, ResultadoSimulacion)
    assert len(res) == 13  # 12 ticks + el estado inicial
    # la población total (celdas) se conserva
    assert np.all(res.muerta + res.latente + res.activa == shape[0] * shape[1])


def test_no_modifica_el_estado_inicial() -> None:
    e = EColi()
    shape = (8, 8)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0))
    copia = estado.copy()
    simular(ModoEstatico(_campo_optimo(e, shape)), e, estado,
            np.random.default_rng(2), n_iteraciones=5)
    np.testing.assert_array_equal(estado, copia)


def test_fracciones_suman_uno() -> None:
    e = EColi()
    shape = (9, 9)
    estado = sembrar_estado(shape, rng=np.random.default_rng(3))
    res = simular(ModoEstatico(_campo_optimo(e, shape)), e, estado,
                  np.random.default_rng(3), n_iteraciones=6)
    np.testing.assert_allclose(res.fracciones().sum(axis=1), 1.0)


# --------------------------------------------------------------------------
# Reproducibilidad
# --------------------------------------------------------------------------
def test_misma_semilla_misma_corrida() -> None:
    e = EColi()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.1)
    modo = ModoEstatico(_campo_optimo(e, shape))
    a = simular(modo, e, estado, np.random.default_rng(7), n_iteraciones=10,
                guardar_grillas=True)
    b = simular(modo, e, estado, np.random.default_rng(7), n_iteraciones=10,
                guardar_grillas=True)
    np.testing.assert_array_equal(a.activa, b.activa)
    for ga, gb in zip(a.grillas, b.grillas, strict=True):
        np.testing.assert_array_equal(ga, gb)


def test_semillas_distintas_dan_corridas_distintas() -> None:
    e = EColi()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.1)
    modo = ModoEstatico(_campo_optimo(e, shape))
    a = simular(modo, e, estado, np.random.default_rng(7), n_iteraciones=10)
    c = simular(modo, e, estado, np.random.default_rng(8), n_iteraciones=10)
    assert not np.array_equal(a.activa, c.activa)


# --------------------------------------------------------------------------
# Dinámica esperada
# --------------------------------------------------------------------------
def test_un_parche_optimo_coloniza_crece_la_poblacion_activa() -> None:
    e = EColi()
    shape = (15, 15)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0),
                            fraccion_activa=0.05, patron="cluster")
    res = simular(ModoEstatico(_campo_optimo(e, shape)), e, estado,
                  np.random.default_rng(1), n_iteraciones=15)
    # sin muerte por soledad ni por ambiente óptimo: la población solo crece
    assert res.activa[-1] > res.activa[0]
    assert np.all(np.diff(res.activa) >= 0)


def test_ambiente_letal_extingue_en_un_tick() -> None:
    e = EColi()
    shape = (10, 10)
    estado = np.full(shape, ACTIVA, dtype=np.int8)
    letal = _campo(e.t_sup_max + 50.0, 0.0, 1.0, shape)
    res = simular(ModoEstatico(letal), e, estado, np.random.default_rng(0),
                  n_iteraciones=1)
    assert res.activa[-1] == 0
    assert res.muerta[-1] == shape[0] * shape[1]


def test_guardar_grillas_almacena_el_estado_por_tick() -> None:
    e = EColi()
    shape = (7, 7)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0))
    res = simular(ModoEstatico(_campo_optimo(e, shape)), e, estado,
                  np.random.default_rng(1), n_iteraciones=4, guardar_grillas=True)
    assert res.grillas is not None
    assert len(res.grillas) == 5  # 4 ticks + inicial
    assert all(g.dtype == np.int8 and g.shape == shape for g in res.grillas)


# --------------------------------------------------------------------------
# Integración con el Modo Analógico y con eventos
# --------------------------------------------------------------------------
def test_corrida_analogica_de_extremo_a_extremo() -> None:
    e = DRadiodurans()
    shape = (20, 20)
    modo = ModoAnalogico(cargar_atacama(str(_ATACAMA)), Entorno.MARTE, shape,
                         rng=np.random.default_rng(0))
    estado = sembrar_estado(shape, rng=np.random.default_rng(1), fraccion_activa=0.3)
    res = simular(modo, e, estado, np.random.default_rng(2))  # sin n: agota el modo
    assert len(res) == 365 + 1  # un tick por día del dataset + t=0


def test_n_none_sin_modo_finito_agota_el_analogico() -> None:
    e = DRadiodurans()
    shape = (10, 10)
    modo = ModoAnalogico(cargar_atacama(str(_ATACAMA)), Entorno.MARTE, shape)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0))
    res = simular(modo, e, estado, np.random.default_rng(0), n_iteraciones=50)
    assert len(res) == 51  # islice acota a 50 ticks aunque el modo tenga 365


def test_eventos_se_aplican_y_siguen_reproducibles() -> None:
    e = DRadiodurans()
    shape = (16, 16)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.4)
    modo = ModoEstatico(MarteSubsuelo(shape=shape).campo_inicial())
    evento = MicroFisuraMarte(probabilidad_disparo=0.5)
    a = simular(modo, e, estado, np.random.default_rng(9), n_iteraciones=20,
                eventos=[evento])
    b = simular(modo, e, estado, np.random.default_rng(9), n_iteraciones=20,
                eventos=[evento])
    np.testing.assert_array_equal(a.activa, b.activa)


def test_estado_inicial_por_defecto_helper() -> None:
    rng = np.random.default_rng(0)
    estado = sembrar_estado((30, 30), rng=rng, fraccion_activa=0.2)
    frac = (estado == ACTIVA).mean()
    assert 0.15 < frac < 0.25  # ~20% de celdas activas
    assert set(np.unique(estado)).issubset({MUERTA, ACTIVA})
