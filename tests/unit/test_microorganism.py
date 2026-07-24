"""Tests de la jerarquía `Microorganismo` (dueña: Esmeralda) — contrato §3.2.

Cubre la separación crecimiento / supervivencia de ADR-0012: no basta con que
la máscara de crecimiento sea correcta, hay que verificar que la de
supervivencia es un **superconjunto** y que las especies anhidrobióticas
sobreviven donde no crecen.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import (
    ACTIVA,
    LATENTE,
    MUERTA,
    DRadiodurans,
    EColi,
    MBurtonii,
    Microorganismo,
)

ESPECIES = [EColi(), DRadiodurans(), MBurtonii()]
IDS = ["EColi", "DRadiodurans", "MBurtonii"]


def _campo_uniforme(
    t: float, r: float, a_w: float, shape: tuple[int, int] = (2, 2)
) -> CampoAmbiental:
    return CampoAmbiental(T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w))


def _campo_optimo(especie: Microorganismo, shape: tuple[int, int] = (2, 2)) -> CampoAmbiental:
    """Campo cómodamente dentro de los umbrales de crecimiento de la especie."""
    return _campo_uniforme(especie.t_opt, r=0.0, a_w=1.0, shape=shape)


# --------------------------------------------------------------------------
# Máscara de crecimiento: una prueba por variable y por especie
# --------------------------------------------------------------------------


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_todo_dentro_de_umbral_crece(especie: Microorganismo) -> None:
    assert np.all(especie.condiciones_crecimiento(_campo_optimo(especie)))


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_temperatura_por_debajo_del_minimo_no_crece(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.T[0, 0] = especie.t_min - 1.0
    mask = especie.condiciones_crecimiento(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_temperatura_por_encima_del_maximo_no_crece(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.T[0, 0] = especie.t_max + 1.0
    mask = especie.condiciones_crecimiento(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_uv_por_encima_del_maximo_no_crece(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.R[0, 0] = especie.uv_max + 1.0
    mask = especie.condiciones_crecimiento(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_actividad_de_agua_por_debajo_del_minimo_no_crece(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    campo.A_w[0, 0] = especie.a_w_min - 0.05
    mask = especie.condiciones_crecimiento(campo)
    assert not mask[0, 0]
    assert mask[0, 1] and mask[1, 0] and mask[1, 1]


# --------------------------------------------------------------------------
# Separación crecimiento / supervivencia (ADR-0012)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_supervivencia_es_superconjunto_de_crecimiento(especie: Microorganismo) -> None:
    """Toda celda donde la especie crece es una celda donde sobrevive."""
    rng = np.random.default_rng(20260723)
    campo = CampoAmbiental(
        T=rng.uniform(-40.0, 70.0, size=(20, 20)),
        R=rng.uniform(0.0, 150.0, size=(20, 20)),
        A_w=rng.uniform(0.0, 1.0, size=(20, 20)),
    )
    crece = especie.condiciones_crecimiento(campo)
    sobrevive = especie.condiciones_supervivencia(campo)
    assert np.all(sobrevive[crece])


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_umbrales_de_supervivencia_no_son_mas_estrictos(especie: Microorganismo) -> None:
    assert especie.t_sup_min <= especie.t_min
    assert especie.t_sup_max >= especie.t_max
    assert especie.a_w_sup_min <= especie.a_w_min
    assert especie.uv_letal >= especie.uv_max


def test_d_radiodurans_sobrevive_la_desecacion_pero_no_crece() -> None:
    """El caso que motivó ADR-0012: anhidrobiosis en el regolito de Atacama."""
    especie = DRadiodurans()
    campo = _campo_uniforme(t=especie.t_opt, r=0.0, a_w=0.187)  # a_w real de Atacama
    assert not np.any(especie.condiciones_crecimiento(campo))
    assert np.all(especie.condiciones_supervivencia(campo))


def test_e_coli_no_sobrevive_la_desecacion_extrema() -> None:
    """El control no es anhidrobiótico: la sequedad de Atacama sí lo mata."""
    especie = EColi()
    campo = _campo_uniforme(t=especie.t_opt, r=0.0, a_w=0.187)
    assert not np.any(especie.condiciones_crecimiento(campo))
    assert not np.any(especie.condiciones_supervivencia(campo))


# --------------------------------------------------------------------------
# Contrato e invariantes
# --------------------------------------------------------------------------


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_puntos_cardinales_ordenados(especie: Microorganismo) -> None:
    """ADR-0013 (CTMI) exige t_min < t_opt < t_max estrictamente."""
    assert especie.t_min < especie.t_opt < especie.t_max


@pytest.mark.parametrize("especie", ESPECIES, ids=IDS)
def test_condiciones_habitables_es_alias_de_crecimiento(especie: Microorganismo) -> None:
    campo = _campo_optimo(especie)
    np.testing.assert_array_equal(
        especie.condiciones_habitables(campo), especie.condiciones_crecimiento(campo)
    )


def test_los_tres_estados_son_distintos_y_muerta_es_cero() -> None:
    assert len({MUERTA, LATENTE, ACTIVA}) == 3
    assert MUERTA == 0  # celda vacía / muerta debe ser el valor falsy


def test_las_tres_especies_heredan_de_microorganismo() -> None:
    for especie in ESPECIES:
        assert isinstance(especie, Microorganismo)


def test_no_existe_atributo_ni_logica_de_presion() -> None:
    for especie in ESPECIES:
        assert not hasattr(especie, "p_min")
        assert not hasattr(especie, "p_max")
        assert not hasattr(especie, "presion")


def test_a_w_min_de_crecimiento_respeta_el_limite_de_la_vida() -> None:
    """Ninguna especie puede declarar crecimiento bajo a_w ≈ 0.605 (ADR-0012)."""
    for especie in ESPECIES:
        assert especie.a_w_min >= 0.605, (
            f"{type(especie).__name__}.a_w_min={especie.a_w_min} está por debajo del "
            "límite conocido de división celular (Stevenson et al., 2015)"
        )
