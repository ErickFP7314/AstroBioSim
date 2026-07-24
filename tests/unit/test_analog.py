"""Tests del Modo Analógico (dueño: Fidel) — `modes/analog.py` y su interfaz."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.data.loaders import cargar_atacama, cargar_ventilas
from astrobiosim.data.resampling import Entorno
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.modes.base import ModoSimulacion

_PROC = Path(__file__).resolve().parents[2] / "data" / "processed"
ATACAMA = _PROC / "datos_atacama_2025_EXTREMOS_REALES.csv"
VENTILAS = _PROC / "datos_ventilas_2025_procesados.csv"


def test_modo_analogico_cumple_la_interfaz_de_modo() -> None:
    modo = ModoAnalogico(cargar_atacama(str(ATACAMA)), Entorno.MARTE, (10, 10))
    assert isinstance(modo, ModoSimulacion)  # runtime_checkable Protocol


def test_entrega_un_campo_por_dia_del_dataset() -> None:
    df = cargar_atacama(str(ATACAMA))
    modo = ModoAnalogico(df, Entorno.MARTE, (12, 12))
    campos = list(modo)
    assert len(campos) == len(df) == 365
    assert all(isinstance(c, CampoAmbiental) and c.shape == (12, 12) for c in campos)


def test_rellena_el_hueco_de_ventilas_no_quedan_nan() -> None:
    """El dataset de ventilas tiene 8 NaN; el modo los interpola al construir."""
    modo = ModoAnalogico(cargar_ventilas(str(VENTILAS)), Entorno.ENCELADO, (10, 10))
    for campo in modo:
        assert not np.isnan(campo.T).any()
        assert not np.isnan(campo.A_w).any()
        assert np.all(campo.R == 0.0)


def test_modo_reciclable_repite_la_temporada() -> None:
    df = cargar_atacama(str(ATACAMA))
    modo = ModoAnalogico(df, Entorno.MARTE, (6, 6), ciclico=True)
    it = modo.campos()
    total = len(df)
    # tomar 1.5 temporadas no debe agotar el iterador
    tomados = [next(it) for _ in range(total + total // 2)]
    assert len(tomados) == total + total // 2


def test_finito_por_defecto_se_agota() -> None:
    df = cargar_atacama(str(ATACAMA))
    modo = ModoAnalogico(df, Entorno.MARTE, (6, 6))
    it = modo.campos()
    for _ in range(len(df)):
        next(it)
    with pytest.raises(StopIteration):
        next(it)


def test_reproducible_con_semilla() -> None:
    df = cargar_atacama(str(ATACAMA))
    a = list(ModoAnalogico(df, Entorno.MARTE, (8, 8), rng=np.random.default_rng(7)))
    b = list(ModoAnalogico(df, Entorno.MARTE, (8, 8), rng=np.random.default_rng(7)))
    for ca, cb in zip(a, b, strict=True):
        np.testing.assert_array_equal(ca.A_w, cb.A_w)
