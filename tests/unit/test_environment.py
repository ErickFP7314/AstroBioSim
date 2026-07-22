"""Tests de `CampoAmbiental` y la jerarquía `PlanetaSubsuelo` (dueño: Jose)."""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import (
    CampoAmbiental,
    EnceladoSubglacial,
    MarteSubsuelo,
    TierraSubsuelo,
)


def test_campo_ambiental_valida_formas_identicas() -> None:
    with pytest.raises(ValueError):
        CampoAmbiental(
            T=np.zeros((3, 3)), R=np.zeros((3, 3)), A_w=np.zeros((2, 2))
        )


def test_campo_ambiental_shape() -> None:
    campo = CampoAmbiental(T=np.zeros((4, 5)), R=np.zeros((4, 5)), A_w=np.zeros((4, 5)))
    assert campo.shape == (4, 5)


def test_tierra_es_estable_humeda_sin_radiacion() -> None:
    campo = TierraSubsuelo(shape=(10, 10)).campo_inicial()
    assert campo.shape == (10, 10)
    assert np.all(campo.R == 0.0)
    assert np.all(campo.A_w > 0.5)
    # subsuelo estable: sin variación entre celdas
    assert np.allclose(campo.T, campo.T[0, 0])


def test_marte_tiene_gradiente_termico_y_radiativo_con_la_profundidad() -> None:
    campo = MarteSubsuelo(shape=(20, 5)).campo_inicial()
    # más cálido y más irradiado en la superficie (fila 0) que en profundidad
    assert np.all(campo.T[0, :] > campo.T[-1, :])
    assert np.all(campo.R[0, :] > campo.R[-1, :])
    # monótono no creciente con la profundidad, en cada columna
    assert np.all(np.diff(campo.T, axis=0) <= 0)
    assert np.all(np.diff(campo.R, axis=0) <= 0)
    # A_w baja (real de Atacama), consistente en toda la grilla
    assert np.all(campo.A_w < 0.3)


def test_marte_radiacion_decae_mas_rapido_que_temperatura() -> None:
    entorno = MarteSubsuelo(shape=(30, 5))
    campo = entorno.campo_inicial()
    fila_media = entorno.shape[0] // 2
    # a media profundidad la radiación ya se atenuó casi del todo, no así el calor
    fraccion_R_restante = campo.R[fila_media, 0] / entorno.R_SUPERFICIE
    fraccion_T_restante = (campo.T[fila_media, 0] - entorno.T_PROFUNDO_C) / (
        entorno.T_SUPERFICIE_C - entorno.T_PROFUNDO_C
    )
    assert fraccion_R_restante < fraccion_T_restante


def test_encelado_fondo_frio_agua_alta_sin_radiacion() -> None:
    entorno = EnceladoSubglacial(shape=(20, 20))
    campo = entorno.campo_inicial()
    assert np.all(campo.R == 0.0)
    assert np.all(campo.A_w > 0.9)
    assert np.all(campo.T >= entorno.T_OCEANO_C)


def test_encelado_tiene_picos_localizados_cerca_de_fumarolas() -> None:
    entorno = EnceladoSubglacial(shape=(20, 20))
    campo = entorno.campo_inicial()
    # el pico máximo debe superar bastante al fondo oceánico
    assert campo.T.max() > entorno.T_OCEANO_C + entorno.DELTA_T_FUMAROLA * 0.9
    # lejos de toda fumarola, la temperatura vuelve a acercarse al fondo
    assert campo.T.min() < entorno.T_OCEANO_C + 1.0


def test_los_tres_entornos_son_cualitativamente_distintos() -> None:
    shape = (15, 15)
    tierra = TierraSubsuelo(shape=shape).campo_inicial()
    marte = MarteSubsuelo(shape=shape).campo_inicial()
    encelado = EnceladoSubglacial(shape=shape).campo_inicial()

    medias_T = [tierra.T.mean(), marte.T.mean(), encelado.T.mean()]
    medias_R = [tierra.R.mean(), marte.R.mean(), encelado.R.mean()]
    medias_A_w = [tierra.A_w.mean(), marte.A_w.mean(), encelado.A_w.mean()]

    assert len(set(np.round(medias_T, 3))) == 3
    assert len(set(np.round(medias_A_w, 3))) == 3
    # Tierra y Encelado comparten R=0; Marte se distingue por R>0
    assert marte.R.mean() > 0
    assert tierra.R.mean() == encelado.R.mean() == 0.0
    assert len(medias_R) == 3
