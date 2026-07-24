"""Tests del autómata celular (dueño: Erick) — contrato §3.3, ADR-0012/0013/0016."""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import ACTIVA, LATENTE, MUERTA, EColi
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.transition_rules import (
    REGLAS_DISPONIBLES,
    ReglaConway,
    ReglaLogistica,
    cinetica_mu,
    contar_vecinos_moore,
    gamma_actividad_agua,
    gamma_temperatura,
    gamma_uv,
)


def _campo(t, r, a_w, shape):
    return CampoAmbiental(
        T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w)
    )


def _campo_optimo(especie, shape):
    """Campo en el óptimo de la especie: p_repro = 1 (crecimiento máximo)."""
    return _campo(especie.t_opt, 0.0, 1.0, shape)


# --------------------------------------------------------------------------
# Cinética continua (ADR-0013)
# --------------------------------------------------------------------------
def test_gamma_temperatura_vale_uno_en_el_optimo_y_cero_fuera() -> None:
    e = EColi()
    assert gamma_temperatura(np.array([e.t_opt]), e.t_min, e.t_opt, e.t_max)[0] == pytest.approx(1.0)
    fuera = gamma_temperatura(
        np.array([e.t_min - 1, e.t_min, e.t_max, e.t_max + 1]), e.t_min, e.t_opt, e.t_max
    )
    assert np.all(fuera == 0.0)


def test_gamma_temperatura_en_rango_cerrado_cero_uno() -> None:
    e = EColi()
    g = gamma_temperatura(np.linspace(-30, 70, 400), e.t_min, e.t_opt, e.t_max)
    assert np.all((g >= 0.0) & (g <= 1.0))


def test_gamma_agua_y_uv_en_los_bordes() -> None:
    assert gamma_actividad_agua(np.array([0.94]), 0.95)[0] == 0.0
    assert gamma_actividad_agua(np.array([1.0]), 0.95)[0] == pytest.approx(1.0)
    assert gamma_uv(np.array([0.0]), 2.0)[0] == pytest.approx(1.0)
    assert gamma_uv(np.array([2.0]), 2.0)[0] == 0.0


def test_mu_es_cero_fuera_de_crecimiento_y_maximo_en_el_optimo() -> None:
    e = EColi()
    optimo = cinetica_mu(e, _campo_optimo(e, (3, 3)))
    assert np.allclose(optimo, e.mu_opt)
    seco = cinetica_mu(e, _campo(e.t_opt, 0.0, 0.10, (3, 3)))  # a_w bajo umbral
    assert np.all(seco == 0.0)


# --------------------------------------------------------------------------
# Conteo de vecinos de Moore
# --------------------------------------------------------------------------
def test_vecinos_frontera_muerta_centro_lleno() -> None:
    m = np.ones((3, 3), dtype=bool)
    n = contar_vecinos_moore(m, "muerta")
    assert n[1, 1] == 8  # el centro tiene los 8 vecinos
    assert n[0, 0] == 3  # una esquina, solo 3 vecinos dentro de la grilla


def test_vecinos_toroidal_envuelve() -> None:
    m = np.zeros((3, 3), dtype=bool)
    m[0, 0] = True
    n = contar_vecinos_moore(m, "toroidal")
    # con wrap-around, la única celda activa es vecina de las 8 restantes
    assert n[0, 0] == 0
    assert np.sum(n) == 8


def test_borde_desconocido_falla() -> None:
    with pytest.raises(ValueError):
        contar_vecinos_moore(np.zeros((2, 2), dtype=bool), "otro")


# --------------------------------------------------------------------------
# paso(): invariantes del contrato §3.3
# --------------------------------------------------------------------------
def test_paso_no_modifica_el_estado_de_entrada() -> None:
    e = EColi()
    estado = np.full((5, 5), ACTIVA, dtype=np.int8)
    copia = estado.copy()
    paso(estado, _campo_optimo(e, (5, 5)), e, np.random.default_rng(0))
    np.testing.assert_array_equal(estado, copia)  # doble buffer: no in situ


def test_paso_devuelve_int8_con_estados_validos() -> None:
    e = EColi()
    estado = np.zeros((6, 6), dtype=np.int8)
    estado[2:4, 2:4] = ACTIVA
    nuevo = paso(estado, _campo_optimo(e, (6, 6)), e, np.random.default_rng(1))
    assert nuevo.dtype == np.int8
    assert set(np.unique(nuevo)).issubset({MUERTA, LATENTE, ACTIVA})


def test_paso_es_reproducible_con_la_misma_semilla() -> None:
    e = EColi()
    estado = np.zeros((8, 8), dtype=np.int8)
    estado[3:5, 3:5] = ACTIVA
    campo = _campo_optimo(e, (8, 8))
    a = paso(estado, campo, e, np.random.default_rng(42))
    b = paso(estado, campo, e, np.random.default_rng(42))
    np.testing.assert_array_equal(a, b)


# --------------------------------------------------------------------------
# paso(): semántica de los tres estados (ADR-0012)
# --------------------------------------------------------------------------
def test_ambiente_letal_mata_todo_de_forma_irreversible() -> None:
    e = EColi()
    estado = np.full((4, 4), ACTIVA, dtype=np.int8)
    letal = _campo(e.t_sup_max + 50.0, 0.0, 1.0, (4, 4))  # T por encima de supervivencia
    nuevo = paso(estado, letal, e, np.random.default_rng(0))
    assert np.all(nuevo == MUERTA)


def test_celda_latente_se_reactiva_si_vuelve_a_crecer() -> None:
    e = EColi()
    estado = np.full((3, 3), LATENTE, dtype=np.int8)
    nuevo = paso(estado, _campo_optimo(e, (3, 3)), e, np.random.default_rng(0))
    assert np.all(nuevo == ACTIVA)  # LATENTE → ACTIVA es reversible


def test_celda_ocupada_que_solo_sobrevive_queda_latente() -> None:
    e = EColi()
    estado = np.full((3, 3), ACTIVA, dtype=np.int8)
    # a_w entre supervivencia (0.50) y crecimiento (0.95): vive pero no crece
    campo = _campo(e.t_opt, 0.0, 0.70, (3, 3))
    nuevo = paso(estado, campo, e, np.random.default_rng(0))
    assert np.all(nuevo == LATENTE)


# --------------------------------------------------------------------------
# paso(): reproducción por contacto (regla logística por defecto)
# --------------------------------------------------------------------------
def test_nacimiento_seguro_con_ocho_vecinos_activos() -> None:
    """Sitio vacío rodeado de 8 ACTIVA en el óptimo: p = 1·(8/8) = 1, nace seguro."""
    e = EColi()
    estado = np.full((3, 3), ACTIVA, dtype=np.int8)
    estado[1, 1] = MUERTA
    nuevo = paso(estado, _campo_optimo(e, (3, 3)), e, np.random.default_rng(0))
    assert nuevo[1, 1] == ACTIVA


def test_las_celdas_latentes_no_engendran_vecinos() -> None:
    """Un sitio vacío rodeado solo de LATENTE no puede nacer (μ=0, sin ACTIVA)."""
    e = EColi()
    estado = np.full((3, 3), LATENTE, dtype=np.int8)
    estado[1, 1] = MUERTA
    # campo que mantiene a las vecinas LATENTE (sobrevive pero no crece) y al
    # sitio central tampoco lo deja crecer: sin ACTIVA alrededor, no hay parto
    campo = _campo(e.t_opt, 0.0, 0.70, (3, 3))
    nuevo = paso(estado, campo, e, np.random.default_rng(0))
    assert nuevo[1, 1] == MUERTA


# --------------------------------------------------------------------------
# Reglas intercambiables (ADR-0016)
# --------------------------------------------------------------------------
def test_conway_reproduce_el_blinker() -> None:
    """Con ambiente óptimo (p_repro=1), la regla de Conway es el Juego de la Vida:
    un blinker horizontal oscila a vertical y vuelve en dos pasos."""
    e = EColi()
    campo = _campo_optimo(e, (5, 5))
    regla = ReglaConway()
    estado = np.zeros((5, 5), dtype=np.int8)
    estado[2, 1:4] = ACTIVA  # blinker horizontal
    rng = np.random.default_rng(0)
    p1 = paso(estado, campo, e, rng, regla=regla)
    esperado_vertical = np.zeros((5, 5), dtype=np.int8)
    esperado_vertical[1:4, 2] = ACTIVA
    np.testing.assert_array_equal(p1, esperado_vertical)
    p2 = paso(p1, campo, e, rng, regla=regla)
    np.testing.assert_array_equal(p2, estado)  # vuelve al horizontal


def test_todas_las_reglas_del_menu_corren_y_tienen_notacion() -> None:
    e = EColi()
    estado = np.zeros((6, 6), dtype=np.int8)
    estado[2:4, 2:4] = ACTIVA
    campo = _campo_optimo(e, (6, 6))
    for regla in REGLAS_DISPONIBLES.values():
        nuevo = paso(estado, campo, e, np.random.default_rng(3), regla=regla)
        assert nuevo.shape == estado.shape
        assert isinstance(regla.notacion(), str) and regla.notacion()
        assert isinstance(regla.nombre, str) and regla.nombre


def test_regla_por_defecto_es_logistica() -> None:
    assert isinstance(REGLAS_DISPONIBLES["logistica"], ReglaLogistica)


def test_borde_toroidal_es_aceptado_por_paso() -> None:
    e = EColi()
    estado = np.zeros((5, 5), dtype=np.int8)
    estado[0, 0] = ACTIVA
    nuevo = paso(estado, _campo_optimo(e, (5, 5)), e, np.random.default_rng(0), borde="toroidal")
    assert nuevo.dtype == np.int8
