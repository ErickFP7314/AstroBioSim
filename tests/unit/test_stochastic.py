"""Tests de los eventos estocásticos (dueño: Jose)."""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental, MarteSubsuelo
from astrobiosim.core.microorganism import DRadiodurans
from astrobiosim.engine.stochastic import (
    EmisionHidrotermalEncelado,
    MicroFisuraMarte,
    SalmueraDelicuescente,
)


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


def test_micro_fisura_devuelve_copia_nueva_aunque_no_dispare() -> None:
    campo = _campo_uniforme()
    evento = MicroFisuraMarte(probabilidad_disparo=0.0)
    resultado = evento.aplicar(campo, np.random.default_rng(1))
    assert resultado is not campo
    assert resultado.A_w is not campo.A_w


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


def test_emision_hidrotermal_devuelve_copia_nueva_aunque_no_dispare() -> None:
    campo = _campo_uniforme()
    evento = EmisionHidrotermalEncelado(probabilidad_disparo=0.0)
    resultado = evento.aplicar(campo, np.random.default_rng(3))
    assert resultado is not campo
    assert resultado.T is not campo.T


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


def test_salmuera_nunca_dispara_con_probabilidad_cero() -> None:
    campo = _campo_uniforme()
    evento = SalmueraDelicuescente(probabilidad_disparo=0.0)
    resultado = evento.aplicar(campo, np.random.default_rng(1))
    np.testing.assert_array_equal(resultado.A_w, campo.A_w)


def test_salmuera_devuelve_copia_nueva_aunque_no_dispare() -> None:
    campo = _campo_uniforme()
    evento = SalmueraDelicuescente(probabilidad_disparo=0.0)
    resultado = evento.aplicar(campo, np.random.default_rng(1))
    assert resultado is not campo
    assert resultado.A_w is not campo.A_w


def test_salmuera_sube_a_w_dentro_del_radio_sin_tocar_t_ni_r() -> None:
    campo = CampoAmbiental(
        T=np.full((10, 10), 7.8), R=np.zeros((10, 10)), A_w=np.full((10, 10), 0.19)
    )
    evento = SalmueraDelicuescente(
        probabilidad_disparo=1.0,
        radio_celdas=2.0,
        a_w_objetivo_min=0.95,
        a_w_objetivo_max=0.95,
    )
    resultado = evento.aplicar(campo, np.random.default_rng(7))

    np.testing.assert_array_equal(resultado.T, campo.T)
    np.testing.assert_array_equal(resultado.R, campo.R)
    assert np.any(resultado.A_w > campo.A_w)
    assert np.any(resultado.A_w == campo.A_w)
    assert np.all(resultado.A_w <= 1.0)


def test_salmuera_es_reproducible_con_la_misma_semilla() -> None:
    campo = _campo_uniforme()
    resultado_1 = SalmueraDelicuescente(probabilidad_disparo=1.0).aplicar(
        campo, np.random.default_rng(42)
    )
    resultado_2 = SalmueraDelicuescente(probabilidad_disparo=1.0).aplicar(
        campo, np.random.default_rng(42)
    )
    np.testing.assert_array_equal(resultado_1.A_w, resultado_2.A_w)


def test_salmuera_decae_con_el_tiempo_y_desaparece() -> None:
    # Igual que en `simulation.simular`: cada tick le pasa al evento el campo
    # BASE del entorno (constante en este caso), nunca la salida del tick
    # anterior. Lo único que persiste entre ticks es el estado interno del
    # propio evento (la lista de refugios y su edad).
    campo = CampoAmbiental(
        T=np.full((10, 10), 7.8), R=np.zeros((10, 10)), A_w=np.full((10, 10), 0.19)
    )
    evento = SalmueraDelicuescente(
        probabilidad_disparo=1.0,
        radio_celdas=2.0,
        a_w_objetivo_min=0.95,
        a_w_objetivo_max=0.95,
        duracion_min_ticks=2.0,
        duracion_max_ticks=2.0,
    )
    rng = np.random.default_rng(5)

    # Primer tick: dispara (probabilidad 1.0), el refugio está en su pico.
    resultado_1 = evento.aplicar(campo, rng)
    pico = resultado_1.A_w.max()
    assert pico > campo.A_w.max()

    # Ticks siguientes: no vuelve a disparar (prob. 0), el refugio ya creado decae.
    evento.probabilidad_disparo = 0.0
    resultado_2 = evento.aplicar(campo, rng)
    resultado_3 = evento.aplicar(campo, rng)

    assert resultado_2.A_w.max() < resultado_1.A_w.max()
    assert resultado_3.A_w.max() < resultado_2.A_w.max()

    # Con suficientes ticks, el refugio se disipa por completo (vuelve a la base).
    campo_final = campo
    for _ in range(20):
        campo_final = evento.aplicar(campo, rng)
    assert np.allclose(campo_final.A_w, campo.A_w, atol=1e-6)


def test_salmuera_reiniciar_descarta_refugios_activos() -> None:
    campo = _campo_uniforme()
    evento = SalmueraDelicuescente(probabilidad_disparo=1.0)
    resultado = evento.aplicar(campo, np.random.default_rng(3))
    assert evento._refugios  # hay un refugio activo tras disparar

    evento.reiniciar()
    assert evento._refugios == []

    evento.probabilidad_disparo = 0.0
    resultado_tras_reinicio = evento.aplicar(resultado, np.random.default_rng(9))
    np.testing.assert_array_equal(resultado_tras_reinicio.A_w, resultado.A_w)


def test_salmuera_reactiva_crecimiento_de_d_radiodurans_en_marte() -> None:
    """Criterio de aceptación del tablero (Hito 2, ADR-0015)."""
    marte = MarteSubsuelo(shape=(10, 10))
    campo = marte.campo_inicial()
    especie = DRadiodurans()

    assert not np.any(especie.condiciones_crecimiento(campo))  # bulk: 0 % activa

    evento = SalmueraDelicuescente(
        probabilidad_disparo=1.0,
        radio_celdas=3.0,
        a_w_objetivo_min=0.95,
        a_w_objetivo_max=0.95,
    )
    campo_con_refugio = evento.aplicar(campo, np.random.default_rng(11))

    assert np.any(especie.condiciones_crecimiento(campo_con_refugio))
