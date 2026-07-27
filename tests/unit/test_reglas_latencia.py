"""Reglas de latencia por anhidrobiosis (dueño: Erick, ADR-0016).

Modelan el pedido biológico de Esmeralda: la latencia (dormancia reversible) es un
privilegio de las especies **anhidrobióticas**. Dos reglas opt-in del menú:

- **Rule A** (`latencia_anhidro`): solo las anhidrobióticas quedan LATENTE; las
  demás **mueren** al dejar de crecer (dinámica binaria ACTIVA/MUERTA).
- **Rule B** (`latencia_mortalidad`): todas pueden quedar LATENTE, pero la de las
  **no** anhidrobióticas **decae** con una mortalidad por tick; las anhidrobióticas
  persisten sin costo.
"""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import (
    ACTIVA,
    LATENTE,
    MUERTA,
    DRadiodurans,
    EColi,
    MBurtonii,
)
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.transition_rules import (
    REGLAS_DISPONIBLES,
    ReglaLatenciaAnhidrobiotica,
    ReglaLatenciaConMortalidad,
    ReglaLogistica,
)
from astrobiosim.modes.sandbox import ModoSandbox
from astrobiosim.simulation import sembrar_estado, simular

SHAPE = (12, 12)


def _campo(t: float, a_w: float, r: float = 0.0) -> CampoAmbiental:
    return CampoAmbiental(T=np.full(SHAPE, t), R=np.full(SHAPE, r), A_w=np.full(SHAPE, a_w))


def _todo_activa() -> np.ndarray:
    return np.full(SHAPE, ACTIVA, dtype=np.int8)


# Campos donde la especie SOBREVIVE pero NO crece (para forzar latencia):
_ECOLI_FRIO = (5.0, 0.99)      # T < t_min(7.5): frío, agua alta
_DRAD_SECO = (25.0, 0.30)      # a_w < a_w_min(0.90) pero > a_w_sup_min(0.0): seco


# --------------------------------------------------------------------------
# El flag biológico y el registro en el menú
# --------------------------------------------------------------------------
def test_solo_dradiodurans_es_anhidrobiotica() -> None:
    assert DRadiodurans().anhidrobiotico is True
    assert EColi().anhidrobiotico is False
    assert MBurtonii().anhidrobiotico is False


def test_reglas_nuevas_registradas_en_el_menu() -> None:
    assert "latencia_anhidro" in REGLAS_DISPONIBLES
    assert "latencia_mortalidad" in REGLAS_DISPONIBLES


# --------------------------------------------------------------------------
# Rule A: latencia solo para anhidrobióticas
# --------------------------------------------------------------------------
def test_ruleA_no_anhidrobiotica_muere_en_vez_de_quedar_latente() -> None:
    campo = _campo(*_ECOLI_FRIO)
    estado = _todo_activa()
    # Referencia: con la logística, E. coli quedaría LATENTE.
    log = paso(estado, campo, EColi(), np.random.default_rng(0), regla=ReglaLogistica())
    assert np.all(log == LATENTE)
    # Rule A: E. coli NO es anhidrobiótica → muere (no hay latencia para ella).
    a = paso(estado, campo, EColi(), np.random.default_rng(0), regla=ReglaLatenciaAnhidrobiotica())
    assert np.all(a == MUERTA)


def test_ruleA_anhidrobiotica_si_queda_latente() -> None:
    campo = _campo(*_DRAD_SECO)
    a = paso(_todo_activa(), campo, DRadiodurans(), np.random.default_rng(0),
             regla=ReglaLatenciaAnhidrobiotica())
    assert np.all(a == LATENTE)  # la anhidrobiótica SÍ duerme


def test_ruleA_en_optimo_crece_como_la_logistica() -> None:
    campo = _campo(EColi().t_opt, 1.0)
    a = paso(_todo_activa(), campo, EColi(), np.random.default_rng(0),
             regla=ReglaLatenciaAnhidrobiotica())
    assert np.all(a == ACTIVA)  # en el óptimo, crece igual


# --------------------------------------------------------------------------
# Rule B: latencia con mortalidad (dormancia con costo)
# --------------------------------------------------------------------------
def test_ruleB_mortalidad_total_mata_la_latencia_no_anhidrobiotica() -> None:
    campo = _campo(*_ECOLI_FRIO)
    b = paso(_todo_activa(), campo, EColi(), np.random.default_rng(0),
             regla=ReglaLatenciaConMortalidad(mortalidad_latente=1.0))
    assert np.all(b == MUERTA)  # con costo total, toda la latencia no anhidro muere


def test_ruleB_anhidrobiotica_inmune_al_costo_de_latencia() -> None:
    campo = _campo(*_DRAD_SECO)
    b = paso(_todo_activa(), campo, DRadiodurans(), np.random.default_rng(0),
             regla=ReglaLatenciaConMortalidad(mortalidad_latente=1.0))
    assert np.all(b == LATENTE)  # la anhidrobiótica no paga costo aunque sea 1.0


def test_ruleB_mortalidad_cero_deja_la_latencia_intacta() -> None:
    campo = _campo(*_ECOLI_FRIO)
    b = paso(_todo_activa(), campo, EColi(), np.random.default_rng(0),
             regla=ReglaLatenciaConMortalidad(mortalidad_latente=0.0))
    assert np.all(b == LATENTE)  # sin costo, se comporta como la logística


def test_ruleB_la_poblacion_no_anhidrobiotica_decae_con_el_tiempo() -> None:
    def viva_final(n: int) -> float:
        rng = np.random.default_rng(3)
        estado = sembrar_estado(SHAPE, rng=rng, fraccion_activa=0.6)
        r = simular(ModoSandbox(SHAPE, T=5.0, R=0.0, A_w=0.99), EColi(), estado, rng,
                    n_iteraciones=n, regla=ReglaLatenciaConMortalidad(mortalidad_latente=0.3))
        fr = r.fracciones()[-1]
        return float(fr[1] + fr[2])
    assert viva_final(20) < viva_final(3)  # la dormancia decae: la población baja


# --------------------------------------------------------------------------
# Notación formal (panel de la UI)
# --------------------------------------------------------------------------
def test_notacion_expone_los_simbolos_nuevos() -> None:
    assert r"\mathrm{anh}" in ReglaLatenciaAnhidrobiotica().notacion()
    assert r"q_{\mathrm{lat}}" in ReglaLatenciaConMortalidad().notacion()
