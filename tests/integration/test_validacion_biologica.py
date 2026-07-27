"""Validación biológica de las salidas de las 3 corridas análogas (dueño: Fidel).

Comprueba que las corridas guiadas por los datos reales 2025 producen dinámicas
poblacionales \\emph{biológicamente plausibles}, no artefactos numéricos. Cubre los
tres criterios de la tarjeta:

1. **Sin artefactos** — ninguna de las 3 corridas (cada especie en su entorno)
   se extingue de golpe ni satura de forma irreal: la población viva nunca cae a
   cero y la fracción activa evoluciona de a poco (proceso de contacto espacial),
   nunca a saltos discontinuos.
2. **Banda UV documentada en el adaptador (ADR-0014)** — `mapear_radiacion`
   convierte la irradiancia global a la banda UV con el factor documentado
   `FRACCION_UV` en Marte, y la anula en Tierra/Encelado (el subsuelo/hielo
   bloquea el UV). Reemplaza el viejo proxy W/m² vs Gy.
3. **Hostil < control** — el entorno más hostil (Marte) da menor supervivencia que
   el control (Tierra). Se aísla el efecto del *entorno* corriendo la **misma**
   especie (*E. coli*) en ambos: prospera en Tierra y se extingue en Marte.

Son tests de integración: usan los datasets reales de `data/processed/` y el
orquestador completo (modo Analógico → eventos → autómata).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from astrobiosim.core.environment import FRACCION_UV
from astrobiosim.core.microorganism import DRadiodurans, EColi, MBurtonii, Microorganismo
from astrobiosim.data.loaders import cargar_atacama, cargar_control_tierra, cargar_ventilas
from astrobiosim.data.resampling import Entorno, mapear_radiacion
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.simulation import sembrar_estado, simular

_DATA = Path(__file__).resolve().parents[2] / "data" / "processed"
SHAPE = (30, 30)
N_TICKS = 60

#: Las 3 corridas del estudio: (nombre, loader, archivo, entorno, especie).
CORRIDAS = [
    ("Tierra", cargar_control_tierra, "datos_tierra_control_2025.csv", Entorno.TIERRA, EColi()),
    ("Marte", cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv", Entorno.MARTE, DRadiodurans()),
    ("Encelado", cargar_ventilas, "datos_ventilas_2025_procesados.csv", Entorno.ENCELADO, MBurtonii()),
]
IDS = ["EColi/Tierra", "DRadiodurans/Marte", "MBurtonii/Encelado"]


def _fracciones(loader, archivo: str, entorno: Entorno, especie: Microorganismo,
                *, semilla: int = 0, n: int = N_TICKS) -> np.ndarray:
    """Corre una corrida análoga y devuelve las fracciones [MUERTA, LATENTE, ACTIVA] por tick."""
    df = loader(str(_DATA / archivo))
    rng = np.random.default_rng(semilla)
    modo = ModoAnalogico(df, entorno, SHAPE, rng=rng)
    estado = sembrar_estado(SHAPE, rng=rng, fraccion_activa=0.15)
    return simular(modo, especie, estado, rng, n_iteraciones=n).fracciones()


# --------------------------------------------------------------------------
# Criterio 1: sin artefactos (extinción instantánea / saturación irreal)
# --------------------------------------------------------------------------
@pytest.mark.parametrize(("nombre", "loader", "archivo", "entorno", "especie"), CORRIDAS, ids=IDS)
def test_ninguna_corrida_se_extingue_instantaneamente(nombre, loader, archivo, entorno, especie) -> None:
    """La población viva (activa+latente) nunca cae a cero: cada especie sobrevive
    en su entorno asignado (que no crezca es válido; extinguirse no)."""
    fr = _fracciones(loader, archivo, entorno, especie)
    viva = fr[:, 1] + fr[:, 2]
    assert np.all(viva > 0.0), (
        f"{IDS[[c[0] for c in CORRIDAS].index(nombre)]}: la población viva llega a 0 "
        f"(mín {viva.min():.3f}) — extinción, no supervivencia"
    )


@pytest.mark.parametrize(("nombre", "loader", "archivo", "entorno", "especie"), CORRIDAS, ids=IDS)
def test_ninguna_corrida_satura_de_golpe(nombre, loader, archivo, entorno, especie) -> None:
    """La fracción activa evoluciona gradualmente (frente de colonización): ningún
    salto discontinuo entre ticks consecutivos, que sería un artefacto numérico."""
    fr = _fracciones(loader, archivo, entorno, especie)
    salto_maximo = float(np.max(np.abs(np.diff(fr[:, 2]))))
    assert salto_maximo < 0.5, (
        f"{nombre}: la fracción activa salta {salto_maximo:.2f} en un tick "
        f"(> 0.5) — saturación/colapso irreal"
    )


def test_marte_da_supervivencia_latente_no_extincion_ni_crecimiento() -> None:
    """El resultado correcto de Marte (ADR-0015): *D. radiodurans* sobrevive
    **dormida** (latente > 0) sin crecimiento activo, no se extingue ni satura."""
    fr = _fracciones(cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv",
                     Entorno.MARTE, DRadiodurans())
    assert fr[-1, 1] > 0.0, "en Marte debe quedar población LATENTE (sobrevive dormida)"
    assert fr[-1, 2] == pytest.approx(0.0, abs=0.02), "el regolito en bulk no sostiene crecimiento ACTIVO"


# --------------------------------------------------------------------------
# Criterio 2: banda UV + factor documentados en el adaptador (ADR-0014)
# --------------------------------------------------------------------------
def test_adaptador_convierte_a_banda_uv_con_el_factor_documentado() -> None:
    """`mapear_radiacion` es donde vive la conversión: Marte multiplica la
    irradiancia global por `FRACCION_UV`; Tierra y Encelado la anulan (subsuelo/
    hielo bloquean el UV). ADR-0014 reemplaza el proxy W/m² vs Gy."""
    global_wm2 = np.array([200.0, 844.2, 1000.0])
    marte = mapear_radiacion(global_wm2, Entorno.MARTE)
    np.testing.assert_allclose(marte, global_wm2 * FRACCION_UV)
    assert 42.0 <= float(mapear_radiacion(np.array([844.2]), Entorno.MARTE)[0]) <= 55.0  # rango UV publicado
    for entorno in (Entorno.TIERRA, Entorno.ENCELADO):
        np.testing.assert_array_equal(mapear_radiacion(global_wm2, entorno), np.zeros_like(global_wm2))


def test_factor_uv_esta_documentado_como_constante_nombrada() -> None:
    """El factor no es un número mágico: es la constante `FRACCION_UV`, con valor
    físicamente razonable (UV-A+UV-B ≈ pequeña fracción de la global)."""
    assert 0.0 < FRACCION_UV < 0.2
    assert "FRACCION_UV" in mapear_radiacion.__doc__  # el adaptador lo nombra y justifica


# --------------------------------------------------------------------------
# Criterio 3: el entorno más hostil produce menor supervivencia que el control
# --------------------------------------------------------------------------
def test_entorno_hostil_da_menos_supervivencia_que_el_control() -> None:
    """Aísla el efecto del *entorno*: la MISMA especie (*E. coli*) prospera en el
    control (Tierra) y se extingue en el entorno hostil (Marte, regolito seco)."""
    tierra = _fracciones(cargar_control_tierra, "datos_tierra_control_2025.csv", Entorno.TIERRA, EColi())
    marte = _fracciones(cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv", Entorno.MARTE, EColi())
    viva_tierra = float(tierra[-1, 1] + tierra[-1, 2])
    viva_marte = float(marte[-1, 1] + marte[-1, 2])
    assert viva_marte < viva_tierra, (
        f"el entorno hostil (Marte, viva={viva_marte:.3f}) no da menos supervivencia "
        f"que el control (Tierra, viva={viva_tierra:.3f})"
    )
    assert viva_tierra > 0.0  # el control efectivamente prospera (si no, no hay con qué comparar)
