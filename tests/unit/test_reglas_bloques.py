"""Tests del editor de reglas por bloques (dueño: Erick) — ADR-0018.

Cubre el intérprete `ReglaDesdeBloques` / `regla_desde_spec`: equivalencia exacta
con la regla logística fija, invariantes del motor (síncrono, estados válidos,
reproducible), la guardia de MUERTA absorbente y la validación del spec.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import ACTIVA, LATENTE, MUERTA, EColi
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.transition_rules import (
    PRESETS,
    VOCABULARIO,
    ReglaDesdeBloques,
    ReglaLogistica,
    regla_desde_spec,
)


def _campo(t, r, a_w, shape):
    return CampoAmbiental(T=np.full(shape, t), R=np.full(shape, r), A_w=np.full(shape, a_w))


def _campo_bandeado(e, shape):
    """Campo con tres bandas verticales: crece · solo sobrevive · letal.

    Sirve para ejercitar TODAS las ramas (ACTIVA, LATENTE, MUERTA) en una sola
    corrida y comparar reglas de forma no trivial.
    """
    n = shape[1]
    T = np.full(shape, e.t_opt, dtype=float)
    R = np.zeros(shape)
    A_w = np.full(shape, 1.0)
    t3 = n // 3
    A_w[:, t3 : 2 * t3] = 0.70  # sobrevive pero no crece → LATENTE
    T[:, 2 * t3 :] = e.t_sup_max + 50.0  # letal → MUERTA
    return CampoAmbiental(T=T, R=R, A_w=A_w)


def _estado_mixto(shape, semilla=7):
    rng = np.random.default_rng(semilla)
    return rng.integers(0, 3, size=shape, dtype=np.int8)


# --------------------------------------------------------------------------
# Equivalencia con la regla fija
# --------------------------------------------------------------------------
def test_preset_logistica_equivale_a_regla_logistica() -> None:
    """El preset 'logistica' en bloques reproduce EXACTO a `ReglaLogistica`
    (misma cascada, un único sorteo de `rng` por tick)."""
    e = EColi()
    shape = (12, 12)
    estado = _estado_mixto(shape)
    campo = _campo_bandeado(e, shape)
    regla_bloques = regla_desde_spec(PRESETS["logistica"])
    esperado = paso(estado, campo, e, np.random.default_rng(0), regla=ReglaLogistica())
    obtenido = paso(estado, campo, e, np.random.default_rng(0), regla=regla_bloques)
    np.testing.assert_array_equal(obtenido, esperado)


# --------------------------------------------------------------------------
# Invariantes del motor (§3.3)
# --------------------------------------------------------------------------
def test_no_modifica_el_estado_de_entrada() -> None:
    e = EColi()
    estado = _estado_mixto((8, 8))
    copia = estado.copy()
    paso(estado, _campo(e.t_opt, 0.0, 1.0, (8, 8)), e, np.random.default_rng(0),
         regla=regla_desde_spec(PRESETS["hibrida"]))
    np.testing.assert_array_equal(estado, copia)


def test_devuelve_int8_con_estados_validos() -> None:
    e = EColi()
    estado = _estado_mixto((10, 10))
    nuevo = paso(estado, _campo_bandeado(e, (10, 10)), e, np.random.default_rng(1),
                 regla=regla_desde_spec(PRESETS["conway"]))
    assert nuevo.dtype == np.int8
    assert set(np.unique(nuevo)).issubset({MUERTA, LATENTE, ACTIVA})


def test_es_reproducible_con_la_misma_semilla() -> None:
    e = EColi()
    estado = _estado_mixto((9, 9))
    campo = _campo(e.t_opt, 0.0, 1.0, (9, 9))
    regla = regla_desde_spec(PRESETS["logistica"])
    a = paso(estado, campo, e, np.random.default_rng(42), regla=regla)
    b = paso(estado, campo, e, np.random.default_rng(42), regla=regla)
    np.testing.assert_array_equal(a, b)


# --------------------------------------------------------------------------
# Guardia de MUERTA absorbente (ADR-0012): sin vecino ACTIVA no hay colonización
# --------------------------------------------------------------------------
def test_no_hay_generacion_espontanea_sin_vecino_activa() -> None:
    """Aunque el spec ordene 'vacía → ACTIVA' sin exigir vecinos, una celda
    vacía sin ningún vecino ACTIVA NO puede ocuparse (no se resucita)."""
    e = EColi()
    spec = {
        "nombre": "generación espontánea (prohibida por la guardia)",
        "clausulas": [
            {"cuando": [{"tipo": "estado", "cual": "vacia"}], "entonces": "ACTIVA"},
            {"cuando": [], "entonces": "MUERTA"},
        ],
    }
    regla = regla_desde_spec(spec)
    estado = np.full((5, 5), MUERTA, dtype=np.int8)  # todo vacío, cero vecinos ACTIVA
    nuevo = paso(estado, _campo(e.t_opt, 0.0, 1.0, (5, 5)), e, np.random.default_rng(0), regla=regla)
    assert np.all(nuevo == MUERTA)


def test_una_celda_vacia_con_vecino_activa_si_se_coloniza() -> None:
    e = EColi()
    spec = {
        "nombre": "colonización",
        "clausulas": [
            {"cuando": [{"tipo": "estado", "cual": "vacia"}], "entonces": "ACTIVA"},
            {"cuando": [], "entonces": "MUERTA"},
        ],
    }
    regla = regla_desde_spec(spec)
    estado = np.full((5, 5), MUERTA, dtype=np.int8)
    estado[2, 2] = ACTIVA
    nuevo = paso(estado, _campo(e.t_opt, 0.0, 1.0, (5, 5)), e, np.random.default_rng(0), regla=regla)
    assert nuevo[2, 1] == ACTIVA  # vecino directo del ACTIVA → colonizado
    assert nuevo[0, 0] == MUERTA  # esquina lejana, sin vecino ACTIVA → sigue vacía


# --------------------------------------------------------------------------
# Presets, round-trip y notación
# --------------------------------------------------------------------------
@pytest.mark.parametrize("clave", list(PRESETS))
def test_todos_los_presets_parsean_y_corren(clave: str) -> None:
    e = EColi()
    estado = _estado_mixto((7, 7))
    regla = regla_desde_spec(PRESETS[clave])
    nuevo = paso(estado, _campo_bandeado(e, (7, 7)), e, np.random.default_rng(3), regla=regla)
    assert nuevo.shape == estado.shape
    assert isinstance(regla.notacion(), str) and r"\begin{cases}" in regla.notacion()
    assert regla.nombre


def test_round_trip_spec_preserva_el_comportamiento() -> None:
    e = EColi()
    estado = _estado_mixto((8, 8))
    campo = _campo_bandeado(e, (8, 8))
    regla = regla_desde_spec(PRESETS["conway"])
    regla2 = regla_desde_spec(regla.a_spec())  # serializa y re-parsea
    a = paso(estado, campo, e, np.random.default_rng(5), regla=regla)
    b = paso(estado, campo, e, np.random.default_rng(5), regla=regla2)
    np.testing.assert_array_equal(a, b)


def test_regla_desde_spec_devuelve_el_tipo_correcto() -> None:
    regla = regla_desde_spec(PRESETS["logistica"])
    assert isinstance(regla, ReglaDesdeBloques)
    assert regla.nombre == "Logística (proceso de contacto)"


# --------------------------------------------------------------------------
# Validación del spec
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "spec",
    [
        "no soy un dict",
        {"clausulas": []},  # vacío
        {"clausulas": "no es lista"},
        {"clausulas": [{"cuando": [], "entonces": "ZOMBIE"}]},  # resultado inválido
        {"clausulas": [{"cuando": [{"tipo": "estado", "cual": "gaseosa"}], "entonces": "ACTIVA"}]},
        {"clausulas": [{"cuando": [{"tipo": "planeta"}], "entonces": "ACTIVA"}]},  # tipo inválido
        {"clausulas": [{"cuando": [{"tipo": "vecinos", "cual": "activa", "op": "≈", "n": 3}], "entonces": "ACTIVA"}]},
        {"clausulas": [{"cuando": [{"tipo": "vecinos", "cual": "activa", "op": ">", "n": 9}], "entonces": "ACTIVA"}]},
        {"clausulas": [{"cuando": [], "entonces": "MUERTA", "prob": "magia"}]},  # prob inválida
    ],
)
def test_specs_invalidos_lanzan_valueerror(spec: object) -> None:
    with pytest.raises(ValueError):
        regla_desde_spec(spec)


def test_vocabulario_expone_las_tres_familias() -> None:
    assert {"condiciones", "resultados", "probabilidades"} <= set(VOCABULARIO)
    tipos = {c["tipo"] for c in VOCABULARIO["condiciones"]}
    assert tipos == {"estado", "ambiente", "vecinos"}
