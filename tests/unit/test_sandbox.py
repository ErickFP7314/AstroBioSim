"""Tests del Modo Sandbox (dueña: Esmeralda) — `modes/sandbox.py` y su interfaz."""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import EColi
from astrobiosim.modes.base import ModoEstatico, ModoSimulacion
from astrobiosim.modes.sandbox import ModoSandbox
from astrobiosim.simulation import sembrar_estado, simular


def test_modo_sandbox_cumple_la_interfaz_de_modo() -> None:
    modo = ModoSandbox((10, 10), T=25.0, R=0.0, A_w=0.9)
    assert isinstance(modo, ModoSimulacion)  # runtime_checkable Protocol


def test_construye_campo_homogeneo_con_los_parametros_dados() -> None:
    shape = (8, 6)
    modo = ModoSandbox(shape, T=15.5, R=2.0, A_w=0.75)
    campo = modo.campo_actual()
    assert isinstance(campo, CampoAmbiental)
    assert campo.shape == shape
    assert np.all(campo.T == 15.5)
    assert np.all(campo.R == 2.0)
    assert np.all(campo.A_w == 0.75)


def test_campos_entrega_el_mismo_campo_en_cada_tick() -> None:
    modo = ModoSandbox((5, 5), T=10.0, R=0.0, A_w=0.8)
    it = modo.campos()
    primeros = [next(it) for _ in range(5)]
    for campo in primeros:
        np.testing.assert_array_equal(campo.T, primeros[0].T)
        np.testing.assert_array_equal(campo.R, primeros[0].R)
        np.testing.assert_array_equal(campo.A_w, primeros[0].A_w)


def test_r_negativa_rechazada() -> None:
    with pytest.raises(ValueError):
        ModoSandbox((5, 5), T=20.0, R=-1.0, A_w=0.9)


@pytest.mark.parametrize("a_w", [-0.1, 1.1])
def test_a_w_fuera_de_rango_rechazada(a_w: float) -> None:
    with pytest.raises(ValueError):
        ModoSandbox((5, 5), T=20.0, R=0.0, A_w=a_w)


# --------------------------------------------------------------------------
# Ajuste en caliente (sliders) — criterio "estáticos/ajustables"
# --------------------------------------------------------------------------
def test_set_parametros_solo_cambia_lo_provisto() -> None:
    modo = ModoSandbox((4, 4), T=20.0, R=1.0, A_w=0.9)
    modo.set_parametros(T=30.0)
    assert modo.parametros == (30.0, 1.0, 0.9)


def test_set_parametros_afecta_los_proximos_ticks_no_los_ya_entregados() -> None:
    modo = ModoSandbox((4, 4), T=20.0, R=0.0, A_w=0.9)
    it = modo.campos()
    campo_previo = next(it)
    modo.set_parametros(T=40.0)
    campo_nuevo = next(it)
    assert np.all(campo_previo.T == 20.0)
    assert np.all(campo_nuevo.T == 40.0)


# --------------------------------------------------------------------------
# Criterio: modificar un parámetro cambia el resultado de la corrida
# --------------------------------------------------------------------------
def test_cambiar_temperatura_cambia_el_resultado_de_la_corrida() -> None:
    especie = EColi()
    shape = (12, 12)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.3)

    modo_optimo = ModoSandbox(shape, T=especie.t_opt, R=0.0, A_w=1.0)
    modo_letal = ModoSandbox(shape, T=especie.t_sup_max + 10.0, R=0.0, A_w=1.0)

    res_optimo = simular(
        modo_optimo, especie, estado, np.random.default_rng(1), n_iteraciones=15
    )
    res_letal = simular(
        modo_letal, especie, estado, np.random.default_rng(1), n_iteraciones=15
    )

    # En el óptimo la población activa crece; fuera de supervivencia, se extingue.
    assert res_optimo.activa[-1] > res_optimo.activa[0]
    assert res_letal.activa[-1] == 0
    assert res_letal.muerta[-1] == res_letal.total


def test_cambiar_a_w_cambia_el_resultado_de_la_corrida() -> None:
    especie = EColi()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.3)

    modo_humedo = ModoSandbox(shape, T=especie.t_opt, R=0.0, A_w=1.0)
    modo_seco = ModoSandbox(
        shape, T=especie.t_opt, R=0.0, A_w=especie.a_w_sup_min / 2
    )

    res_humedo = simular(
        modo_humedo, especie, estado, np.random.default_rng(2), n_iteraciones=10
    )
    res_seco = simular(
        modo_seco, especie, estado, np.random.default_rng(2), n_iteraciones=10
    )

    assert res_humedo.activa[-1] > res_seco.activa[-1]
    assert res_seco.muerta[-1] == res_seco.total


# --------------------------------------------------------------------------
# DRY: comparte el mismo bucle que el Modo Analógico / ModoEstatico
# --------------------------------------------------------------------------
def test_comparte_el_orquestador_con_modo_estatico() -> None:
    """Un campo equivalente vía Sandbox o vía ModoEstatico da resultados idénticos.

    Esto confirma que `ModoSandbox` no reimplementa el bucle temporal: solo
    provee campos y es `simulation.simular` quien los itera, igual que con
    `ModoEstatico`/`ModoAnalogico` (DRY, criterio de aceptación del tablero).
    """
    especie = EColi()
    shape = (10, 10)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.25)

    modo_sandbox = ModoSandbox(shape, T=especie.t_opt, R=0.0, A_w=1.0)
    modo_estatico = ModoEstatico(modo_sandbox.campo_actual())

    res_sandbox = simular(
        modo_sandbox, especie, estado, np.random.default_rng(5), n_iteraciones=8
    )
    res_estatico = simular(
        modo_estatico, especie, estado, np.random.default_rng(5), n_iteraciones=8
    )

    np.testing.assert_array_equal(res_sandbox.muerta, res_estatico.muerta)
    np.testing.assert_array_equal(res_sandbox.latente, res_estatico.latente)
    np.testing.assert_array_equal(res_sandbox.activa, res_estatico.activa)


def test_conserva_la_poblacion_total_por_tick() -> None:
    especie = EColi()
    shape = (7, 7)
    estado = sembrar_estado(shape, rng=np.random.default_rng(0), fraccion_activa=0.2)
    modo = ModoSandbox(shape, T=especie.t_opt, R=0.0, A_w=1.0)

    res = simular(modo, especie, estado, np.random.default_rng(3), n_iteraciones=6)

    assert np.all(res.muerta + res.latente + res.activa == shape[0] * shape[1])
