"""Tests de los eventos estocásticos (dueño: Jose)."""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.engine.stochastic import EmisionHidrotermalEncelado, MicroFisuraMarte


def _campo_uniforme(shape: tuple[int, int] = (10, 10)) -> CampoAmbiental:
    m, n = shape
    return CampoAmbiental(
        T=np.full((m, n), 2.4), R=np.zeros((m, n)), A_w=np.full((m, n), 0.98)
    )


def test_micro_fisura_nunca_dispara_con_probabilidad_cero() -> None:
    campo = _campo_uniforme()
    evento = MicroFisuraMarte(probabilidad_disparo=0.0)
    rng = np.random.default_rng(1)
    resultado = evento.aplicar(campo, rng)
    np.testing.assert_array_equal(resultado.A_w, campo.A_w)


def test_micro_fisura_solo_toca_a_w_dentro_del_radio() -> None:
    campo = _campo_uniforme()
    evento = MicroFisuraMarte(probabilidad_disparo=1.0, radio_celdas=2.0, caida_min=0.5, caida_max=0.5)
    rng = np.random.default_rng(7)
    resultado = evento.aplicar(campo, rng)

    # T y R no se tocan
    np.testing.assert_array_equal(resultado.T, campo.T)
    np.testing.assert_array_equal(resultado.R, campo.R)

    # algunas celdas bajaron A_w, otras quedaron igual
    assert np.any(resultado.A_w < campo.A_w)
    assert np.any(resultado.A_w == campo.A_w)
    assert np.all(resultado.A_w >= 0.0)


def test_micro_fisura_es_reproducible_con_la_misma_semilla() -> None:
    campo = _campo_uniforme()
    evento = MicroFisuraMarte(probabilidad_disparo=1.0)

    resultado_1 = evento.aplicar(campo, np.random.default_rng(42))
    resultado_2 = evento.aplicar(campo, np.random.default_rng(42))

    np.testing.assert_array_equal(resultado_1.A_w, resultado_2.A_w)


def test_emision_hidrotermal_nunca_dispara_con_probabilidad_cero() -> None:
    campo = _campo_uniforme()
    evento = EmisionHidrotermalEncelado(probabilidad_disparo=0.0)
    rng = np.random.default_rng(3)
    resultado = evento.aplicar(campo, rng)
    np.testing.assert_array_equal(resultado.T, campo.T)


def test_emision_hidrotermal_solo_toca_t_y_se_disipa_con_la_distancia() -> None:
    campo = _campo_uniforme()
    evento = EmisionHidrotermalEncelado(
        probabilidad_disparo=1.0, mu_delta_t=30.0, sigma_delta_t=0.0, sigma_espacial=2.0
    )
    rng = np.random.default_rng(11)
    resultado = evento.aplicar(campo, rng)

    # A_w y R no se tocan
    np.testing.assert_array_equal(resultado.A_w, campo.A_w)
    np.testing.assert_array_equal(resultado.R, campo.R)

    # hubo un pico de temperatura en algún punto
    assert resultado.T.max() > campo.T.max()

    fila_pico, col_pico = np.unravel_index(np.argmax(resultado.T), resultado.T.shape)
    delta_en_pico = resultado.T[fila_pico, col_pico] - campo.T[fila_pico, col_pico]
    esquina_opuesta = (0, 0) if (fila_pico, col_pico) != (0, 0) else (resultado.T.shape[0] - 1, 0)
    delta_lejos = resultado.T[esquina_opuesta] - campo.T[esquina_opuesta]

    # el pico decae con la distancia: lejos del centro, el delta es menor
    assert delta_lejos < delta_en_pico


def test_emision_hidrotermal_es_reproducible_con_la_misma_semilla() -> None:
    campo = _campo_uniforme()
    evento = EmisionHidrotermalEncelado(probabilidad_disparo=1.0)

    resultado_1 = evento.aplicar(campo, np.random.default_rng(99))
    resultado_2 = evento.aplicar(campo, np.random.default_rng(99))

    np.testing.assert_array_equal(resultado_1.T, resultado_2.T)
