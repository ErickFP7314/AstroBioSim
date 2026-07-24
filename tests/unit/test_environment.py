"""Tests de `CampoAmbiental` y la jerarquía `PlanetaSubsuelo` (dueño: Jose).

`R` es irradiancia UV en W/m² (ADR-0014). El control terrestre modela un suelo
a capacidad de campo, no la humedad del aire (ADR-0014, nota de datos).
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import (
    FRACCION_UV,
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


def test_tierra_es_estable_humeda_sin_uv() -> None:
    campo = TierraSubsuelo(shape=(10, 10)).campo_inicial()
    assert campo.shape == (10, 10)
    assert np.all(campo.R == 0.0)
    # suelo a capacidad de campo: debe permitir crecer a E. coli (a_w_min = 0.95)
    assert np.all(campo.A_w >= 0.95)
    # subsuelo estable: sin variación entre celdas
    assert np.allclose(campo.T, campo.T[0, 0])


def test_marte_tiene_gradiente_termico_y_uv_con_la_profundidad() -> None:
    campo = MarteSubsuelo(shape=(20, 5)).campo_inicial()
    # más cálido y más irradiado en la superficie (fila 0) que en profundidad
    assert np.all(campo.T[0, :] > campo.T[-1, :])
    assert np.all(campo.R[0, :] > campo.R[-1, :])
    # monótono no creciente con la profundidad, en cada columna
    assert np.all(np.diff(campo.T, axis=0) <= 0)
    assert np.all(np.diff(campo.R, axis=0) <= 0)
    # A_w baja (real de Atacama), consistente en toda la grilla
    assert np.all(campo.A_w < 0.3)


def test_marte_uv_decae_mucho_mas_rapido_que_temperatura() -> None:
    entorno = MarteSubsuelo(shape=(30, 5))
    campo = entorno.campo_inicial()
    fila_media = entorno.shape[0] // 2
    fraccion_UV_restante = campo.R[fila_media, 0] / entorno.UV_SUPERFICIE
    fraccion_T_restante = (campo.T[fila_media, 0] - entorno.T_PROFUNDO_C) / (
        entorno.T_SUPERFICIE_C - entorno.T_PROFUNDO_C
    )
    assert fraccion_UV_restante < fraccion_T_restante


def test_marte_tiene_profundidad_minima_de_seguridad_uv() -> None:
    """ADR-0014: el UV deja de ser limitante a pocas celdas de profundidad."""
    entorno = MarteSubsuelo(shape=(30, 5))
    campo = entorno.campo_inicial()
    # a 5 celdas ya queda menos del 1 % del UV de superficie
    assert campo.R[5, 0] < 0.01 * entorno.UV_SUPERFICIE


def test_marte_uv_deriva_de_la_irradiancia_global_por_la_fraccion_uv() -> None:
    """El factor de conversión debe quedar explícito, no escondido (ADR-0014)."""
    entorno = MarteSubsuelo()
    assert entorno.UV_SUPERFICIE == pytest.approx(
        entorno.RADIACION_GLOBAL_W_M2 * FRACCION_UV
    )
    # el UV es una fracción pequeña de la insolación total, no la insolación total
    assert entorno.UV_SUPERFICIE < 0.1 * entorno.RADIACION_GLOBAL_W_M2


def test_marte_con_rng_genera_heterogeneidad_reproducible_en_a_w() -> None:
    """ADR-0015: el campo porta dispersión, no el mínimo colapsado a constante."""
    entorno = MarteSubsuelo(shape=(20, 20))
    determinista = entorno.campo_inicial()
    a = entorno.campo_inicial(rng=np.random.default_rng(7))
    b = entorno.campo_inicial(rng=np.random.default_rng(7))
    c = entorno.campo_inicial(rng=np.random.default_rng(8))

    assert np.allclose(determinista.A_w, entorno.A_W_MEDIA)  # sin rng: solo la media
    np.testing.assert_allclose(a.A_w, b.A_w)  # misma semilla, mismo campo
    assert not np.allclose(a.A_w, c.A_w)  # semilla distinta, campo distinto
    assert a.A_w.std() > 0.0  # hay heterogeneidad espacial
    assert np.all((a.A_w >= 0.0) & (a.A_w <= 1.0))  # A_w sigue siendo físico


def test_encelado_fondo_frio_agua_alta_sin_uv() -> None:
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


def test_encelado_los_nucleos_de_fumarola_son_habitables_para_m_burtonii() -> None:
    """ADR-0011: la vida se agrupa en las ventilas; el pico no debe pasar t_max=29.5."""
    campo = EnceladoSubglacial(shape=(20, 20)).campo_inicial()
    assert campo.T.max() < 29.5


def test_los_tres_entornos_son_cualitativamente_distintos() -> None:
    shape = (15, 15)
    tierra = TierraSubsuelo(shape=shape).campo_inicial()
    marte = MarteSubsuelo(shape=shape).campo_inicial()
    encelado = EnceladoSubglacial(shape=shape).campo_inicial()

    medias_T = [tierra.T.mean(), marte.T.mean(), encelado.T.mean()]
    medias_A_w = [tierra.A_w.mean(), marte.A_w.mean(), encelado.A_w.mean()]

    assert len(set(np.round(medias_T, 3))) == 3
    assert len(set(np.round(medias_A_w, 3))) == 3
    # Tierra y Encelado comparten UV=0; Marte se distingue por UV>0
    assert marte.R.mean() > 0
    assert tierra.R.mean() == encelado.R.mean() == 0.0
