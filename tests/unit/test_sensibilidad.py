"""Tests del análisis de sensibilidad de umbrales (dueño: Erick).

Cubren los tres criterios de la tarea: (1) cada umbral se barre sobre su rango de
incertidumbre según procedencia, (2) se identifica el umbral dominante, (3) se
decide si la conclusión de persistencia se sostiene en todo el rango.

El escenario de dominancia usa `ModoSandbox` con ``A_w`` fijo **entre** los valores
que barre ``a_w_sup_min``, de modo que ese umbral —y solo ese— invierte el desenlace
de forma determinista (sin crecimiento ni eventos: la persistencia es 0 o 1).
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.analysis.sensibilidad import (
    ParametroIncertidumbre,
    RespuestaParametro,
    analisis_sensibilidad,
    especie_perturbada,
    parametros_inciertos,
)
from astrobiosim.core.microorganism import (
    RAZON_INHIBICION_UV,
    SEGUNDOS_UV_POR_TICK,
    DRadiodurans,
    EColi,
    MBurtonii,
)
from astrobiosim.modes.sandbox import ModoSandbox

SHAPE = (12, 12)


def _sensibilidad(especie, *, A_w=0.60, T=None, R=0.0, n_puntos=5, semilla=0, params=None):
    T = especie.t_opt if T is None else T
    return analisis_sensibilidad(
        lambda rng: ModoSandbox(SHAPE, T=T, R=R, A_w=A_w),
        especie,
        parametros=params,
        n_puntos=n_puntos, frecuencia=0.0, shape=SHAPE,
        fraccion_activa=0.2, n_corridas=6, semilla_base=semilla, n_iteraciones=6,
    )


# --------------------------------------------------------------------------
# especie_perturbada: no muta la base, aplica overrides, valida el nombre
# --------------------------------------------------------------------------
def test_especie_perturbada_no_muta_la_original() -> None:
    base = EColi()
    p = especie_perturbada(base, a_w_sup_min=0.31)
    assert p.a_w_sup_min == 0.31
    assert base.a_w_sup_min == 0.50          # la original intacta
    assert EColi().a_w_sup_min == 0.50       # la clase intacta
    assert p.t_opt == base.t_opt             # lo no perturbado cae a la clase


def test_especie_perturbada_rechaza_umbral_inexistente() -> None:
    with pytest.raises(AttributeError):
        especie_perturbada(EColi(), presion_min=1.0)


# --------------------------------------------------------------------------
# Criterio 1: rangos de incertidumbre por procedencia
# --------------------------------------------------------------------------
def test_ecoli_tiene_umbral_de_supervivencia_est() -> None:
    params = {p.nombre: p for p in parametros_inciertos(EColi())}
    assert "a_w_sup_min" in params                       # E. coli: [EST], se barre
    assert params["a_w_sup_min"].procedencia == "EST"
    # rango acotado a [0, a_w_min]
    assert params["a_w_sup_min"].lo >= 0.0
    assert params["a_w_sup_min"].hi <= EColi().a_w_min


def test_dradiodurans_excluye_a_w_sup_min_anhidrobiotico() -> None:
    # a_w_sup_min = 0 [LIT] (anhidrobiosis): sin incertidumbre, no se barre.
    nombres = {p.nombre for p in parametros_inciertos(DRadiodurans())}
    assert "a_w_sup_min" not in nombres
    assert "t_min" in nombres and "uv (fluencia letal)" in nombres


def test_a_w_min_no_baja_del_piso_duro() -> None:
    for especie in (EColi(), DRadiodurans(), MBurtonii()):
        p = next(x for x in parametros_inciertos(especie) if x.nombre == "a_w_min")
        assert p.lo >= 0.605                              # contrato §3.2


def test_uv_mburtonii_usa_rango_ana_documentado() -> None:
    p = next(x for x in parametros_inciertos(MBurtonii()) if x.nombre.startswith("uv"))
    assert p.procedencia == "ANA"
    # nominal = 2.5× (extremo conservador); rango documentado 2.5×–13.8× de 870 J/m².
    assert p.nominal == pytest.approx(870.0 * 2.5)
    assert p.lo == pytest.approx(870.0 * 2.5)
    assert p.hi == pytest.approx(870.0 * 13.8)


def test_override_uv_acopla_las_dos_derivadas() -> None:
    p = next(x for x in parametros_inciertos(EColi()) if x.nombre.startswith("uv"))
    ov = p.overrides(1000.0)
    assert ov["uv_letal"] == pytest.approx(1000.0 / SEGUNDOS_UV_POR_TICK)
    assert ov["uv_max"] == pytest.approx(1000.0 / (RAZON_INHIBICION_UV * SEGUNDOS_UV_POR_TICK))


def test_valores_barren_el_rango_completo() -> None:
    p = ParametroIncertidumbre("x", "LIT", 5.0, 3.0, 7.0, lambda v: {"x": v})
    vals = p.valores(5)
    assert vals[0] == 3.0 and vals[-1] == 7.0 and len(vals) == 5


# --------------------------------------------------------------------------
# Criterio 2: identifica el umbral dominante
# --------------------------------------------------------------------------
def test_a_w_sup_min_domina_cuando_es_el_que_decide() -> None:
    # A_w = 0.60 cae entre los valores barridos de a_w_sup_min (0.30..0.70):
    # por debajo del umbral la célula sobrevive (LATENTE), por encima muere.
    r = _sensibilidad(EColi(), A_w=0.60)
    assert r.dominante.nombre == "a_w_sup_min"
    assert r.dominante.rango_respuesta == pytest.approx(1.0)   # persistencia va de 1 a 0
    # los umbrales de temperatura, con A_w constante, no mueven nada.
    temp = next(x for x in r.respuestas if x.nombre == "t_opt")
    assert temp.rango_respuesta == pytest.approx(0.0)


def test_ranking_ordena_por_dominancia_descendente() -> None:
    r = _sensibilidad(EColi(), A_w=0.60)
    rangos = [x.rango_respuesta for x in r.ranking()]
    assert rangos == sorted(rangos, reverse=True)


# --------------------------------------------------------------------------
# Criterio 3: robustez de la conclusión
# --------------------------------------------------------------------------
def test_conclusion_no_robusta_si_un_umbral_cruza() -> None:
    r = _sensibilidad(EColi(), A_w=0.60)
    assert not r.conclusiones_robustas()                       # a_w_sup_min cruza 0.5
    criticos = {x.nombre for x in r.umbrales_criticos()}
    assert "a_w_sup_min" in criticos


def test_cruza_detecta_el_straddle_de_0_5() -> None:
    straddle = RespuestaParametro("x", "EST", 0.5, np.array([0.4, 0.5]),
                                  np.array([0.0, 1.0]), np.array([0.0, 0.5]))
    assert straddle.cruza(0.5)
    estable = RespuestaParametro("y", "LIT", 0.5, np.array([0.4, 0.5]),
                                 np.array([0.8, 0.9]), np.array([0.4, 0.45]))
    assert not estable.cruza(0.5)


# --------------------------------------------------------------------------
# Reproducibilidad y forma de salida
# --------------------------------------------------------------------------
def test_reproducible_con_semilla_fija() -> None:
    a = _sensibilidad(EColi(), A_w=0.90, semilla=7)
    b = _sensibilidad(EColi(), A_w=0.90, semilla=7)
    for ra, rb in zip(a.respuestas, b.respuestas):
        np.testing.assert_array_equal(ra.prob_persistencia, rb.prob_persistencia)
    assert a.prob_nominal == b.prob_nominal


def test_dataframe_tiene_una_fila_por_umbral_y_punto() -> None:
    r = _sensibilidad(EColi(), A_w=0.90, n_puntos=4)
    df = r.a_dataframe()
    assert len(df) == len(r.respuestas) * 4
    assert set(df.columns) >= {"umbral", "procedencia", "valor", "prob_persistencia"}


def test_n_puntos_invalido_falla() -> None:
    with pytest.raises(ValueError):
        _sensibilidad(EColi(), n_puntos=1)
