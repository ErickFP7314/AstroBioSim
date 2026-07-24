"""Especie microbiana — contrato de frontera §3.2 (dueña: Esmeralda).

Cada especie se define por **dos** juegos de umbrales (ADR-0012), no por uno:

- **Crecimiento** — donde la célula se reproduce (μ > 0). Es el rango cardinal
  clásico de la microbiología: mínimo, óptimo y máximo por variable.
- **Supervivencia** — donde la célula sigue viva pero no se reproduce (μ = 0).
  Fuera de este rango la muerte es irreversible.

La separación existe porque los extremófilos del estudio sobreviven la
desecación en estado **anhidrobiótico** (vivos, sin metabolismo), y un umbral
único no puede representar eso: obligaría a matar a *D. radiodurans* en cuanto
deja de crecer, o a declarar crecimiento por debajo de `a_w ≈ 0.605`, que es el
límite inferior conocido de la división celular para cualquier organismo
terrestre (Stevenson et al., 2015).

La radiación `campo.R` es **irradiancia UV en W/m²** (ADR-0014), no dosis
ionizante: en la escala temporal de la simulación la dosis acumulada no
discrimina (0.077 Gy/año en superficie marciana frente a los ~5000 Gy que
tolera *D. radiodurans*), mientras que el UV esteriliza de inmediato.

Los tres puntos cardinales de temperatura (`t_min`, `t_opt`, `t_max`) alimentan
la cinética continua de ADR-0013, implementada en `engine/transition_rules.py`
(dueño: Erick).
"""
from __future__ import annotations

from abc import ABC

import numpy as np

from astrobiosim.core.environment import CampoAmbiental

#: Estados celulares del autómata (ADR-0012). `MUERTA` es un estado absorbente.
MUERTA: int = 0
LATENTE: int = 1
ACTIVA: int = 2

#: Exposición UV efectiva por tick, en segundos (~8 h de sol útil en un tick
#: diario, que es la resolución de los datasets).
#:
#: Hace falta porque la letalidad del UV es una **fluencia** (J/m²) mientras que
#: el campo `R` es una **irradiancia** (W/m²), que es lo que miden los datos. Los
#: umbrales de abajo se derivan como ``fluencia_publicada / SEGUNDOS_UV_POR_TICK``.
#: Si Erick cambia el Δt del autómata, **este valor tiene que cambiar con él** o
#: los umbrales dejan de significar lo que dicen. Ver `docs/parametros.md`.
SEGUNDOS_UV_POR_TICK: float = 8 * 3600

#: Factor entre la fluencia que **inhibe el crecimiento** y la que **mata**.
#: Convención del modelo (no dato de literatura): el estrés subletal frena la
#: división mucho antes de matar. Documentado en `docs/parametros.md`.
RAZON_INHIBICION_UV: float = 10.0


class Microorganismo(ABC):
    """Base abstracta de una especie, definida por umbrales cardinales.

    Attributes
    ----------
    t_min, t_opt, t_max : float
        Puntos cardinales de temperatura para el **crecimiento** (°C).
    a_w_min : float
        Actividad de agua mínima para **crecer** (0..1).
    uv_max : float
        Irradiancia UV máxima bajo la cual la especie **crece** (W/m²).
    t_sup_min, t_sup_max : float
        Rango de temperatura en el que la célula **sobrevive** sin crecer (°C).
    a_w_sup_min : float
        Actividad de agua mínima para **seguir viva** (0..1). Para especies
        anhidrobióticas puede ser ~0.
    uv_letal : float
        Irradiancia UV por encima de la cual la muerte es irreversible (W/m²).
    mu_opt : float
        Tasa de crecimiento en el óptimo (h⁻¹). Escala la cinética de ADR-0013.
    """

    # --- Umbrales de CRECIMIENTO (μ > 0) ---
    t_min: float
    t_opt: float
    t_max: float
    a_w_min: float
    uv_max: float

    # --- Umbrales de SUPERVIVENCIA (viva, μ = 0) ---
    t_sup_min: float
    t_sup_max: float
    a_w_sup_min: float
    uv_letal: float

    # --- Cinética (ADR-0013) ---
    mu_opt: float

    def condiciones_crecimiento(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M, N): True donde la especie **se reproduce**.

        Parameters
        ----------
        campo : CampoAmbiental
            Campo ambiental sobre el que evaluar. `campo.R` es UV en W/m².

        Returns
        -------
        np.ndarray
            Máscara booleana (M, N), vectorizada (sin bucles Python).
        """
        return (
            (campo.T >= self.t_min)
            & (campo.T <= self.t_max)
            & (campo.A_w >= self.a_w_min)
            & (campo.R <= self.uv_max)
        )

    def condiciones_supervivencia(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M, N): True donde la especie **sigue viva** (crezca o no).

        Es un superconjunto de `condiciones_crecimiento`: toda celda donde la
        especie crece es también una celda donde sobrevive.
        """
        return (
            (campo.T >= self.t_sup_min)
            & (campo.T <= self.t_sup_max)
            & (campo.A_w >= self.a_w_sup_min)
            & (campo.R <= self.uv_letal)
        )

    def condiciones_habitables(self, campo: CampoAmbiental) -> np.ndarray:
        """Alias retrocompatible de `condiciones_crecimiento` (contrato §3.2 original)."""
        return self.condiciones_crecimiento(campo)


class EColi(Microorganismo):
    """Control terrestre: mesófila, sensible al UV, necesita agua libre.

    Es el estándar de referencia, no un extremófilo: su `a_w_min = 0.95` es un
    dato duro y no se ajusta (las cepas que proliferan por debajo son rarezas de
    laboratorio). Tolera mal la desecación, de ahí un `a_w_sup_min` alto para lo
    que es una bacteria.
    """

    #: Fluencia UV₂₅₄ que la especie NO sobrevive (J/m², literatura).
    FLUENCIA_LETAL_J_M2: float = 870.0

    # Crecimiento
    t_min: float = 7.5
    t_opt: float = 37.0
    t_max: float = 47.0
    a_w_min: float = 0.95
    uv_max: float = FLUENCIA_LETAL_J_M2 / (RAZON_INHIBICION_UV * SEGUNDOS_UV_POR_TICK)

    # Supervivencia
    t_sup_min: float = -20.0
    t_sup_max: float = 55.0
    a_w_sup_min: float = 0.50  # desecación tolerada pobremente (estimación)
    uv_letal: float = FLUENCIA_LETAL_J_M2 / SEGUNDOS_UV_POR_TICK

    mu_opt: float = 2.1  # h⁻¹ — la más rápida de las tres


class DRadiodurans(Microorganismo):
    """Análogo Marte: resistente al UV y **anhidrobiótica**.

    Su `a_w_min = 0.90` es el límite de metabolismo **activo**; por debajo no
    muere, entra en anhidrobiosis. Esa es toda la razón de ser de ADR-0012: con
    un solo umbral habría que elegir entre matarla (falso) o declarar
    crecimiento bajo el límite de la vida (indefendible). Con dos umbrales, en
    Atacama queda `LATENTE`, que es lo que hace en la realidad.
    """

    #: Fluencia UV₂₅₄ que la especie NO sobrevive (J/m², literatura): 58× la de
    #: *E. coli*, que es de donde sale su fama de radiorresistente.
    FLUENCIA_LETAL_J_M2: float = 50_760.0

    # Crecimiento
    t_min: float = 4.0
    t_opt: float = 30.0  # mesófila, pese a su fama de extremófila
    t_max: float = 39.0
    a_w_min: float = 0.90  # límite de metabolismo activo
    uv_max: float = FLUENCIA_LETAL_J_M2 / (RAZON_INHIBICION_UV * SEGUNDOS_UV_POR_TICK)

    # Supervivencia
    t_sup_min: float = -25.0
    t_sup_max: float = 50.0
    a_w_sup_min: float = 0.0  # anhidrobiosis: sobrevive la desecación total
    uv_letal: float = FLUENCIA_LETAL_J_M2 / SEGUNDOS_UV_POR_TICK

    mu_opt: float = 0.26  # h⁻¹ — costo metabólico de la extremofilia


class MBurtonii(Microorganismo):
    """Análogo Encelado (ADR-0011): metanógena psicrotolerante del océano subglacial.

    Puntos cardinales publicados: óptimo 23.4 °C, máximo 29.5 °C, mínimo teórico
    -2.5 °C. Con `t_max = 29.5` los núcleos de las fumarolas (~27 °C) vuelven a
    ser habitables, que es la lectura ecológica de ADR-0011: la vida se agrupa
    en las ventilas, no las evita. Requiere agua líquida, así que su
    `a_w_sup_min` es alto: no es anhidrobiótica.
    """

    #: Fluencia UV₂₅₄ letal (J/m²), **inferida por analogía** — no hay medición
    #: publicada para *M. burtonii*. Cadena de inferencia:
    #:
    #: 1. Las metanógenas cubren un rango amplio de resistencia al UV. La
    #:    referencia sensible es *M. barkeri* (suelo no-permafrost), cuya respuesta
    #:    al UV es "comparable a *E. coli* y otros microorganismos radiosensibles".
    #:    De ahí sale la línea base de 870 J/m².
    #: 2. *M. soligelidi*, metanógena **adaptada al frío** (permafrost siberiano),
    #:    resiste **2.5–13.8× más UV** que *M. barkeri*, con F₁₀(UVC) comparable al
    #:    de *D. radiodurans*. La adaptación al frío correlaciona con más
    #:    resistencia al UV en este grupo.
    #: 3. *M. burtonii* también es una metanógena adaptada al frío (lago Ace,
    #:    Antártida), así que cae plausiblemente en ese rango enriquecido.
    #:
    #: Se toma el **extremo inferior** del rango (2.5×) por prudencia: si nos
    #: equivocamos, es hacia subestimar su resistencia, no hacia inflarla.
    #:
    #: Nota adicional: las metanógenas se inhiben con luz azul/UV cercano
    #: (370–430 nm), a diferencia de los anaerobios facultativos como *E. coli*.
    #: O sea que su inhibición del crecimiento podría empezar aún más abajo.
    #:
    #: En Encelado nunca se activa (UV = 0); solo importa en Modo Sandbox.
    FLUENCIA_LETAL_J_M2: float = 870.0 * 2.5

    # Crecimiento
    t_min: float = -2.5
    t_opt: float = 23.4
    t_max: float = 29.5
    a_w_min: float = 0.95  # medio marino; deja margen sobre el A_w=0.98 del campo
    uv_max: float = FLUENCIA_LETAL_J_M2 / (RAZON_INHIBICION_UV * SEGUNDOS_UV_POR_TICK)

    # Supervivencia
    t_sup_min: float = -20.0
    t_sup_max: float = 35.0
    a_w_sup_min: float = 0.80  # no es anhidrobiótica: necesita agua (estimación)
    uv_letal: float = FLUENCIA_LETAL_J_M2 / SEGUNDOS_UV_POR_TICK

    mu_opt: float = 0.069  # h⁻¹ — la más lenta: metanógena psicrotolerante
