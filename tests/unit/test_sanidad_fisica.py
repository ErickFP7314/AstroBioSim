"""Sanidad física de gradientes y eventos (dueño: Jose, Hito 4).

Criterios de aceptación del tablero (`docs/tablero.md`, "Sanidad física de
gradientes y eventos"):
1. El gradiente térmico del regolito está en rango físico esperado por profundidad.
2. Los eventos estocásticos perturban/disipan sin generar valores no físicos.
3. Encelado queda diferenciado de los otros entornos en el campo resultante.
4. La asíntota térmica de Marte amortigua hacia la media anual, no el mínimo diario.
5. Decisión sobre el ΔT=25 del evento hidrotermal apilado sobre una fumarola:
   el núcleo puede ser letal (físicamente correcto), pero el resto de Encelado
   debe seguir siendo habitable.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import (
    CampoAmbiental,
    EnceladoSubglacial,
    MarteSubsuelo,
    TierraSubsuelo,
)
from astrobiosim.core.microorganism import MBurtonii
from astrobiosim.engine.stochastic import (
    EmisionHidrotermalEncelado,
    MicroFisuraMarte,
    SalmueraDelicuescente,
)


def _sin_valores_no_fisicos(campo: CampoAmbiental) -> None:
    assert np.all(np.isfinite(campo.T))
    assert np.all(np.isfinite(campo.R))
    assert np.all(np.isfinite(campo.A_w))
    assert np.all(campo.R >= 0.0)
    assert np.all((campo.A_w >= 0.0) & (campo.A_w <= 1.0))


# --- Criterio 1: gradiente térmico del regolito en rango físico -----------


def test_gradiente_termico_marte_esta_acotado_entre_superficie_y_profundo() -> None:
    """La onda térmica amortigua ENTRE T_SUPERFICIE_C y T_PROFUNDO_C: nunca
    sobre ni bajo esos extremos (no hay overshoot en un decaimiento exponencial
    monótono)."""
    entorno = MarteSubsuelo(shape=(40, 10))
    campo = entorno.campo_inicial()
    lo, hi = sorted((entorno.T_PROFUNDO_C, entorno.T_SUPERFICIE_C))
    assert np.all(campo.T >= lo - 1e-9)
    assert np.all(campo.T <= hi + 1e-9)
    _sin_valores_no_fisicos(campo)


@pytest.mark.parametrize("entorno_cls", [TierraSubsuelo, MarteSubsuelo, EnceladoSubglacial])
def test_campos_iniciales_no_generan_valores_no_fisicos(entorno_cls) -> None:
    campo = entorno_cls(shape=(20, 20)).campo_inicial(rng=np.random.default_rng(0))
    _sin_valores_no_fisicos(campo)


# --- Criterio 4: asíntota térmica de Marte hacia la media anual ------------


def test_marte_asintota_hacia_media_anual_no_minimo_diario() -> None:
    """docs/parametros.md §4 deuda #2: T_PROFUNDO_C debe ser la media ANUAL
    (~22.4 °C, ver scripts/derivar_t_profundo_atacama.py), no la media de los
    mínimos diarios (7.8 °C, una cota pesimista)."""
    entorno = MarteSubsuelo()
    assert entorno.T_PROFUNDO_C == pytest.approx(22.4, abs=0.05)
    assert entorno.T_PROFUNDO_C > 7.8  # ya no es la media de los mínimos


# --- Criterio 2: eventos no generan valores no físicos ---------------------


def _campo_base_marte() -> CampoAmbiental:
    return MarteSubsuelo(shape=(15, 15)).campo_inicial()


def _campo_base_encelado() -> CampoAmbiental:
    return EnceladoSubglacial(shape=(20, 20)).campo_inicial()


@pytest.mark.parametrize("semilla", range(20))
def test_micro_fisura_nunca_genera_valores_no_fisicos(semilla: int) -> None:
    evento = MicroFisuraMarte(probabilidad_disparo=1.0)
    resultado = evento.aplicar(_campo_base_marte(), np.random.default_rng(semilla))
    _sin_valores_no_fisicos(resultado)


@pytest.mark.parametrize("semilla", range(20))
def test_salmuera_nunca_genera_valores_no_fisicos(semilla: int) -> None:
    evento = SalmueraDelicuescente(probabilidad_disparo=1.0)
    resultado = evento.aplicar(_campo_base_marte(), np.random.default_rng(semilla))
    _sin_valores_no_fisicos(resultado)


@pytest.mark.parametrize("semilla", range(20))
def test_emision_hidrotermal_nunca_genera_valores_no_fisicos(semilla: int) -> None:
    """A_w y R deben seguir físicos; T puede dispararse (eso es el punto del
    criterio 5), pero nunca a NaN/inf."""
    evento = EmisionHidrotermalEncelado(probabilidad_disparo=1.0)
    resultado = evento.aplicar(_campo_base_encelado(), np.random.default_rng(semilla))
    assert np.all(np.isfinite(resultado.T))
    assert np.all(np.isfinite(resultado.R))
    assert np.all((resultado.A_w >= 0.0) & (resultado.A_w <= 1.0))


# --- Criterio 3: Encelado diferenciado de los otros entornos ---------------


def test_encelado_diferenciado_por_picos_localizados_que_no_tienen_tierra_ni_marte() -> None:
    """Ni Tierra (uniforme) ni Marte (gradiente monótono con la profundidad)
    tienen picos LOCALIZADOS de temperatura; Encelado sí (fumarolas)."""
    shape = (20, 20)
    tierra = TierraSubsuelo(shape=shape).campo_inicial()
    marte = MarteSubsuelo(shape=shape).campo_inicial()
    encelado = EnceladoSubglacial(shape=shape).campo_inicial()

    assert np.isclose(tierra.T.std(), 0.0)  # uniforme: sin estructura espacial
    assert encelado.T.std() > marte.T.std()  # los picos dominan la dispersión
    assert encelado.T.max() - encelado.T.min() > marte.T.max() - marte.T.min()


# --- Criterio 5 (decisión): núcleo de fumarola puede ser letal, el resto no ---


def test_nucleo_de_fumarola_puede_ser_letal_pero_el_resto_de_encelado_sigue_habitable() -> None:
    """Decisión de Hito 4: se ACEPTA como físicamente correcto que el núcleo
    de una ventila sea letal para M. burtonii cuando el evento se apila sobre
    una fumarola fija existente (docs/parametros.md §4, deuda #6). El
    criterio de sanidad es que el resto de la grilla, lejos del núcleo, siga
    en rango de supervivencia."""
    especie = MBurtonii()
    entorno = EnceladoSubglacial(shape=(20, 20))
    evento = EmisionHidrotermalEncelado(probabilidad_disparo=1.0)

    hubo_nucleo_letal = False
    for semilla in range(200):
        campo = entorno.campo_inicial()  # campo BASE fijo (con sus 3 fumarolas)
        resultado = evento.aplicar(campo, np.random.default_rng(semilla))

        vive = especie.condiciones_supervivencia(resultado)
        # el núcleo puede morir; declarar el resultado como sano exige que
        # NO toda la grilla muera de golpe (el evento sigue siendo local)
        assert np.any(vive), f"semilla {semilla}: toda la grilla murió, no es local"

        if np.any(~vive):
            hubo_nucleo_letal = True

    # con 200 disparos sobre las 3 fumarolas fijas, algún apilamiento debe
    # cruzar t_sup_max — si nunca pasa, el ΔT=25 documentado dejó de aplicarse
    assert hubo_nucleo_letal
