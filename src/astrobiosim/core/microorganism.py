"""Especie microbiana — contrato de frontera §3.2 (dueña: Esmeralda).

Jerarquía de especies con umbrales de tolerancia y evaluación vectorizada de
habitabilidad. Los umbrales de `r_letal` están en W/m² (flujo radiativo, no
dosis en Gy — ver ADR-0010) y están calibrados con literatura (Hito 4).
La especie de Encelado (`MBurtonii`) reemplaza a la termófila original según
ADR-0011; ver justificación en `docs/notas/encelado-especie-psicrofila.md`.
"""
from __future__ import annotations

from abc import ABC

import numpy as np

from astrobiosim.core.environment import CampoAmbiental


class Microorganismo(ABC):
    """Base abstracta de una especie definida por sus umbrales de tolerancia.

    Attributes
    ----------
    t_min, t_max : float
        Rango de temperatura tolerado (°C).
    r_letal : float
        Umbral letal de radiación, en W/m² (flujo; ver ADR-0010).
    a_w_min : float
        Actividad de agua mínima tolerada (0..1).
    mu_max : float
        Tasa de reproducción óptima (adimensional, relativa entre especies).
    """

    t_min: float
    t_max: float
    r_letal: float
    a_w_min: float
    mu_max: float

    def condiciones_habitables(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M, N): True donde TODAS las variables están en umbral.

        Parameters
        ----------
        campo : CampoAmbiental
            Campo ambiental sobre el que evaluar la habitabilidad.

        Returns
        -------
        np.ndarray
            Máscara booleana (M, N), vectorizada (sin bucles Python).
        """
        return (
            (campo.T >= self.t_min)
            & (campo.T <= self.t_max)
            & (campo.R <= self.r_letal)
            & (campo.A_w >= self.a_w_min)
        )


class EColi(Microorganismo):
    """Control terrestre: mesófila, sensible a radiación, necesita agua libre.

    Umbrales calibrados con literatura (Hito 4): rango térmico mesófilo
    típico, alta demanda de actividad de agua (no anhidrobiótica) y baja
    tolerancia a radiación relativa a los otros dos análogos.
    """

    t_min: float = 5.0
    t_max: float = 48.0
    r_letal: float = 200.0  # W/m² — sensible (calibrado Hito 4)
    a_w_min: float = 0.95
    mu_max: float = 2.1  # h⁻¹ — la más rápida de las tres (referencia relativa)


class DRadiodurans(Microorganismo):
    """Análogo Marte: radiorresistente y anhidrobiótica, tolera frío.

    Umbrales calibrados (Hito 4): extremófila que resiste radiación muy por
    encima de E. coli, incluso el pico solar de Atacama (~844 W/m², ver
    `environment.MarteSubsuelo`), y desecación marcada.
    """

    t_min: float = 4.0
    t_max: float = 40.0
    r_letal: float = 1500.0  # W/m² — resiste el pico solar de Atacama (ADR-0010)
    a_w_min: float = 0.75  # límite metabólico flexible en suelos secos
    mu_max: float = 0.26  # h⁻¹ — más lenta que E. coli (costo metabólico de extremófila)


class MBurtonii(Microorganismo):
    """Análogo Encelado (ADR-0011): metanógena psicrotolerante del océano subglacial.

    Reemplaza a la termófila *M. okinawensis* porque los datos de ventila dan
    T≈2.4°C. Umbrales calibrados con literatura (Hito 4); justificación de la
    especie en `docs/notas/encelado-especie-psicrofila.md`. `r_letal` se fija
    por resistencia basal de composición celular: Encelado mapea R≈0
    (ADR-0010), la radiación nunca es el factor limitante ahí, el estrés real
    es térmico/salino, sin embargo por rigor científico el r_letal de los mi-
    croorganismos están sujetos a irradiancia ambiental por ende a estimacio-
    nes. La interpretación es la siguiente: flujo radiativo ambiental solar 
    máximo (W/m²) que la superficie del planeta/luna emite y bajo el cual la 
    célula no resiste y muere instantáneamente.
    """

    t_min: float = -2.0
    t_max: float = 20.0
    r_letal: float = 700.0  # W/m² — resistencia basal por composición celular
    a_w_min: float = 0.98
    mu_max: float = 0.069  # h⁻¹ — la más lenta: metanógena psicrotolerante, crecimiento lento
