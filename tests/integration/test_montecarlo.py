"""Tests de la integración Montecarlo (dueño: Erick) — `simular_montecarlo`."""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import ACTIVA, DRadiodurans, EColi
from astrobiosim.engine.stochastic import SalmueraDelicuescente
from astrobiosim.modes.base import ModoEstatico
from astrobiosim.simulation import (
    ResultadoMontecarlo,
    sembrar_estado,
    simular_montecarlo,
)


def _campo(t, r, a_w, shape):
    return CampoAmbiental(
        T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w)
    )


def _modo_optimo(especie, shape):
    """Factory de modo estático en el óptimo de la especie."""
    campo = _campo(especie.t_opt, 0.0, 1.0, shape)
    return lambda rng: ModoEstatico(campo)


# --------------------------------------------------------------------------
# Forma del resultado
# --------------------------------------------------------------------------
def test_devuelve_media_y_desviacion_por_tick_de_las_tres_fracciones() -> None:
    e = DRadiodurans()  # μ_opt=0.26 -> reproducción estocástica (no satura)
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    res = simular_montecarlo(
        _modo_optimo(e, shape), e, estado,
        n_corridas=20, semilla=1, n_iteraciones=15,
    )
    assert isinstance(res, ResultadoMontecarlo)
    assert res.n_corridas == 20
    assert res.media.shape == (16, 3) and res.desviacion.shape == (16, 3)
    # las tres fracciones medias suman 1 en cada tick
    np.testing.assert_allclose(res.media.sum(axis=1), 1.0)
    # setup estocástico: hay dispersión entre corridas en algún tick
    assert res.desviacion.max() > 0.0


def test_curva_accede_a_una_fraccion() -> None:
    e = DRadiodurans()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    res = simular_montecarlo(_modo_optimo(e, shape), e, estado,
                             n_corridas=10, semilla=2, n_iteraciones=8)
    media, sd = res.curva(ACTIVA)
    assert media.shape == (9,) and sd.shape == (9,)
    np.testing.assert_array_equal(media, res.media[:, ACTIVA])


# --------------------------------------------------------------------------
# Reproducibilidad
# --------------------------------------------------------------------------
def test_misma_semilla_base_mismo_agregado() -> None:
    e = DRadiodurans()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    kw = {"n_corridas": 15, "semilla": 42, "n_iteraciones": 12}
    a = simular_montecarlo(_modo_optimo(e, shape), e, estado, **kw)
    b = simular_montecarlo(_modo_optimo(e, shape), e, estado, **kw)
    np.testing.assert_array_equal(a.media, b.media)
    np.testing.assert_array_equal(a.desviacion, b.desviacion)


def test_semilla_base_distinta_agregado_distinto() -> None:
    e = DRadiodurans()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    a = simular_montecarlo(_modo_optimo(e, shape), e, estado, n_corridas=15, semilla=42, n_iteraciones=12)
    c = simular_montecarlo(_modo_optimo(e, shape), e, estado, n_corridas=15, semilla=43, n_iteraciones=12)
    assert not np.array_equal(a.media, c.media)


def test_lista_explicita_de_semillas_reproducible() -> None:
    e = DRadiodurans()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    semillas = [11, 22, 33, 44]
    a = simular_montecarlo(_modo_optimo(e, shape), e, estado, semillas=semillas, n_iteraciones=10)
    b = simular_montecarlo(_modo_optimo(e, shape), e, estado, semillas=semillas, n_iteraciones=10)
    assert a.n_corridas == 4 and a.semillas == semillas
    np.testing.assert_array_equal(a.media, b.media)


# --------------------------------------------------------------------------
# Factories: instancias frescas por réplica (sin fuga de estado)
# --------------------------------------------------------------------------
def test_las_factories_se_llaman_una_vez_por_corrida() -> None:
    e = EColi()
    shape = (8, 8)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0))
    campo = _campo(e.t_opt, 0.0, 1.0, shape)
    llamadas = {"modo": 0, "eventos": 0}

    def cm(rng):
        llamadas["modo"] += 1
        return ModoEstatico(campo)

    def ce(rng):
        llamadas["eventos"] += 1
        return [SalmueraDelicuescente()]

    simular_montecarlo(cm, e, estado, n_corridas=5, semilla=0,
                       construir_eventos=ce, n_iteraciones=3)
    assert llamadas == {"modo": 5, "eventos": 5}  # una instancia fresca por réplica


def test_evento_con_estado_no_filtra_entre_corridas() -> None:
    """Con la salmuera (con estado) vía factory, el agregado es reproducible:
    si el estado se filtrara entre réplicas, dos llamadas iguales podrían diferir."""
    e = DRadiodurans()
    shape = (16, 16)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.3)
    campo = _campo(e.t_opt, 0.0, 0.19, shape)  # Marte-like: no crece sin salmuera

    def cm(rng):
        return ModoEstatico(campo)

    def ce(rng):
        return [SalmueraDelicuescente(probabilidad_disparo=0.3,
                                      a_w_objetivo_min=0.95, a_w_objetivo_max=0.98)]

    kw = {"n_corridas": 8, "semilla": 7, "construir_eventos": ce, "n_iteraciones": 20}
    a = simular_montecarlo(cm, e, estado, **kw)
    b = simular_montecarlo(cm, e, estado, **kw)
    np.testing.assert_array_equal(a.media, b.media)
    # la salmuera reactiva algo de crecimiento en promedio
    assert a.media[:, ACTIVA].max() > 0.0


# --------------------------------------------------------------------------
# Estado inicial: fijo vs re-sembrado
# --------------------------------------------------------------------------
def test_estado_fijo_no_hay_dispersion_en_t0() -> None:
    e = DRadiodurans()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    res = simular_montecarlo(_modo_optimo(e, shape), e, estado,
                             n_corridas=10, semilla=1, n_iteraciones=10)
    assert np.all(res.desviacion[0] == 0.0)  # t=0 idéntico en todas las réplicas


def test_re_sembrar_varia_el_estado_inicial() -> None:
    e = DRadiodurans()
    shape = (14, 14)

    def construir_estado(rng):
        return sembrar_estado(shape, rng=rng, fraccion_activa=0.2)

    res = simular_montecarlo(_modo_optimo(e, shape), e, construir_estado,
                             n_corridas=12, semilla=1, re_sembrar=True, n_iteraciones=8)
    assert res.desviacion[0].max() > 0.0  # el arranque ya varía entre réplicas


def test_re_sembrar_con_estado_fijo_falla() -> None:
    e = EColi()
    estado = sembrar_estado((8, 8), rng=np.random.default_rng(0))
    with pytest.raises(ValueError):
        simular_montecarlo(_modo_optimo(e, (8, 8)), e, estado,
                           n_corridas=3, re_sembrar=True, n_iteraciones=2)


# --------------------------------------------------------------------------
# Casos borde
# --------------------------------------------------------------------------
def test_una_sola_corrida_desviacion_cero() -> None:
    e = EColi()
    shape = (8, 8)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0))
    res = simular_montecarlo(_modo_optimo(e, shape), e, estado,
                             n_corridas=1, semilla=0, n_iteraciones=5)
    assert res.n_corridas == 1
    assert np.all(res.desviacion == 0.0)


def test_guardar_corridas_conserva_las_crudas() -> None:
    e = DRadiodurans()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    res = simular_montecarlo(_modo_optimo(e, shape), e, estado,
                             n_corridas=6, semilla=0, n_iteraciones=7, guardar_corridas=True)
    assert res.corridas is not None and len(res.corridas) == 6
