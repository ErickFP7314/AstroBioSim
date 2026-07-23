"""Tests de la jerarquía `Microorganismo` (dueña: Esmeralda) — contrato §3.2."""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import DRadiodurans, EColi, MBurtonii, Microorganismo

ESPECIES = [EColi(), DRadiodurans(), MBurtonii()]
IDS = ["EColi", "DRadiodurans", "MBurtonii"]


def _campo_uniforme(
    t: float, r: float, a_w: float, shape: tuple[int, int] = (2, 2)
) -> CampoAmbiental:
    return CampoAmbiental(T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w))


def _campo_optimo(especie: Microorganismo, shape: tuple[int, int] = (2, 2)) -> CampoAmbiental:
    """Campo cómodamente dentro de los umbrales de la especie (todo habitable)."""
    t_medio = (especie.t_min + especie.t_max) / 2
    return _campo_uniforme(t_medio, r=0.0, a_w=1.0, shape=shape)


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_todo_dentro_de_umbral_es_habitable(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    assert np.all(especie.condiciones_habitables(campo))


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_temperatura_por_debajo_del_minimo_mata(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.T[0, 0] = especie.t_min - 1.0
    mask = especie.condiciones_habitables(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_temperatura_por_encima_del_maximo_mata(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.T[0, 0] = especie.t_max + 1.0
    mask = especie.condiciones_habitables(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_radiacion_por_encima_del_letal_mata(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.R[0, 0] = especie.r_letal + 1.0
    mask = especie.condiciones_habitables(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_actividad_de_agua_por_debajo_del_minimo_mata(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.A_w[0, 0] = especie.a_w_min - 0.05
    mask = especie.condiciones_habitables(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


def test_las_tres_especies_heredan_de_microorganismo() -> None:
    for especie in ESPECIES:
        assert isinstance(especie, Microorganismo)


def test_no_existe_atributo_ni_logica_de_presion() -> None:
    for especie in ESPECIES:
        assert not hasattr(especie, "p_min")
        assert not hasattr(especie, "p_max")
        assert not hasattr(especie, "presion")
