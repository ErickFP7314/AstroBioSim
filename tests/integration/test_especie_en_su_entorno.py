"""Integración motor biológico ↔ motor ambiental (contratos §3.1 y §3.2).

Este es el test que faltaba: cada motor pasaba sus tests por separado, pero al
cruzarlos *E. coli* daba 0 % de habitabilidad en su propio control y
*D. radiodurans* moría en Marte. Ningún test unitario podía verlo porque el bug
vivía exactamente en la frontera entre dos dueños distintos.

Regla que se protege acá: **ninguna especie puede quedar con 0 % de
supervivencia en su entorno asignado**. Que no crezca es un resultado válido
(y en Marte es el resultado correcto, ver ADR-0015); que se extinga en el tick 0
no lo es.
"""
from __future__ import annotations

import numpy as np
import pytest

from astrobiosim.core.environment import (
    EnceladoSubglacial,
    MarteSubsuelo,
    PlanetaSubsuelo,
    TierraSubsuelo,
)
from astrobiosim.core.microorganism import (
    DRadiodurans,
    EColi,
    MBurtonii,
    Microorganismo,
)

SHAPE = (50, 50)

#: Asignación especie ↔ entorno del estudio (ADR-0001, ADR-0011).
ASIGNACION: list[tuple[Microorganismo, PlanetaSubsuelo, str]] = [
    (EColi(), TierraSubsuelo(shape=SHAPE), "Tierra"),
    (DRadiodurans(), MarteSubsuelo(shape=SHAPE), "Marte"),
    (MBurtonii(), EnceladoSubglacial(shape=SHAPE), "Encelado"),
]
IDS = ["EColi/Tierra", "DRadiodurans/Marte", "MBurtonii/Encelado"]


@pytest.mark.parametrize(("especie", "entorno", "nombre"), ASIGNACION, ids=IDS)
def test_ninguna_especie_se_extingue_en_su_entorno(
    especie: Microorganismo, entorno: PlanetaSubsuelo, nombre: str
) -> None:
    """La regresión principal: 0 % de supervivencia es un fallo de calibración."""
    campo = entorno.campo_inicial()
    sobrevive = especie.condiciones_supervivencia(campo)
    fraccion = float(sobrevive.mean())
    assert fraccion > 0.0, (
        f"{type(especie).__name__} se extingue por completo en {nombre} "
        f"(supervivencia {fraccion:.1%}) — revisar umbrales vs. campo"
    )


def test_el_control_terrestre_crece_en_todo_el_subsuelo() -> None:
    """Si el control no prospera, no hay con qué comparar los otros dos."""
    campo = TierraSubsuelo(shape=SHAPE).campo_inicial()
    assert np.all(EColi().condiciones_crecimiento(campo))


def test_marte_en_bulk_es_habitable_pero_no_fertil() -> None:
    """ADR-0015: el regolito sostiene vida latente, no crecimiento activo."""
    especie = DRadiodurans()
    campo = MarteSubsuelo(shape=SHAPE).campo_inicial()
    assert not np.any(especie.condiciones_crecimiento(campo))  # nadie crece
    assert np.all(especie.condiciones_supervivencia(campo))  # nadie muere


def test_marte_se_vuelve_fertil_dentro_de_un_microrefugio_humedo() -> None:
    """El corazón de la pregunta de investigación: ¿basta un refugio para reactivar?"""
    especie = DRadiodurans()
    entorno = MarteSubsuelo(shape=SHAPE)
    campo = entorno.campo_inicial()

    assert not np.any(especie.condiciones_crecimiento(campo))

    # Un refugio por delicuescencia eleva A_w localmente, bajo la capa de UV.
    campo.A_w[20:25, 20:25] = 0.95
    crece = especie.condiciones_crecimiento(campo)
    assert np.any(crece), "un refugio húmedo bajo la zona UV debe reactivar el crecimiento"
    assert crece[22, 22]


def test_encelado_crece_incluso_en_los_nucleos_de_fumarola() -> None:
    """ADR-0011: con t_max = 29.5 la vida se agrupa en las ventilas, no las evita."""
    especie = MBurtonii()
    campo = EnceladoSubglacial(shape=SHAPE).campo_inicial()
    crece = especie.condiciones_crecimiento(campo)
    assert np.all(crece)
    # y el punto más caliente de la grilla también es fértil
    fila, col = np.unravel_index(np.argmax(campo.T), campo.T.shape)
    assert crece[fila, col]
