"""Reglas de transición del autómata — contrato de frontera §3.3 (dueño: Erick).

Dos piezas separables:

1. **Cinética continua** (ADR-0013): la tasa de crecimiento por celda,
   ``μ = μ_opt · γ_T(T) · γ_aw(a_w) · γ_UV(UV)``, con ``γ_T`` por el modelo
   cardinal con inflexión (CTMI, Rosso et al. 1993). De ahí sale la probabilidad
   de reproducción por tick, ``p_repro = clip(μ · Δt, 0, 1)``.

2. **Regla de transición intercambiable** (ADR-0016): una `ReglaTransicion`
   decide, a partir de las máscaras ambientales y el conteo de vecinos, el estado
   siguiente de cada celda. Se ofrecen tres reglas (`ReglaLogistica` por defecto,
   `ReglaConway`, `ReglaHibrida`) y cada una sabe describirse en **notación formal
   de autómatas celulares** (`notacion()`), para el panel de la UI. El editor
   visual por bloques (Hito 3) produce nuevas `ReglaTransicion` sin tocar el motor.

Todas las reglas respetan los invariantes: actualización **síncrona** (el estado
siguiente se calcula íntegro a partir del anterior), **vectorizada** (sin bucles
sobre celdas), **`MUERTA` absorbente** (la muerte es irreversible; repoblar un
sitio es colonización por un vecino, no resurrección) y aleatoriedad **solo** vía
el `rng` inyectado.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import ACTIVA, LATENTE, MUERTA, Microorganismo

#: Duración física de un tick, en horas. Δt = 1 h da un buen gradiente de
#: `p_repro` entre especies (E. coli ≈ 1, D. radiodurans ≈ 0.23, M. burtonii
#: ≈ 0.07 en el óptimo). `μ_opt` está en h⁻¹, así que `μ·Δt` es adimensional.
DT_HORAS_DEFECTO: float = 1.0


# ==========================================================================
# 1. Cinética continua (ADR-0013)
# ==========================================================================
def gamma_temperatura(
    T: np.ndarray, t_min: float, t_opt: float, t_max: float
) -> np.ndarray:
    """Factor térmico CTMI (Rosso et al. 1993) ∈ [0, 1]; 1 en `t_opt`, 0 fuera.

    Usa los tres puntos cardinales sin parámetros libres. Es numéricamente
    delicado cerca de los extremos: fuera de ``(t_min, t_max)`` se fuerza a 0.
    """
    T = np.asarray(T, dtype=float)
    num = (T - t_max) * (T - t_min) ** 2
    den = (t_opt - t_min) * (
        (t_opt - t_min) * (T - t_opt) - (t_opt - t_max) * (t_opt + t_min - 2.0 * T)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(den != 0.0, num / den, 0.0)
    g = np.where((T > t_min) & (T < t_max), g, 0.0)
    return np.clip(g, 0.0, 1.0)


def gamma_actividad_agua(a_w: np.ndarray, a_w_min: float) -> np.ndarray:
    """Factor de agua ∈ [0, 1]: 0 bajo `a_w_min`, sube lineal hasta 1 en a_w=1."""
    a_w = np.asarray(a_w, dtype=float)
    g = (a_w - a_w_min) / (1.0 - a_w_min)
    return np.clip(np.where(a_w >= a_w_min, g, 0.0), 0.0, 1.0)


def gamma_uv(uv: np.ndarray, uv_max: float) -> np.ndarray:
    """Factor UV ∈ [0, 1]: 1 sin UV, baja lineal hasta 0 en `uv_max` (ADR-0014)."""
    uv = np.asarray(uv, dtype=float)
    if uv_max <= 0.0:
        return np.where(uv <= 0.0, 1.0, 0.0)
    return np.clip(1.0 - uv / uv_max, 0.0, 1.0)


def cinetica_mu(especie: Microorganismo, campo: CampoAmbiental) -> np.ndarray:
    """Tasa de crecimiento por celda (h⁻¹): μ_opt · γ_T · γ_aw · γ_UV (ADR-0013)."""
    return (
        especie.mu_opt
        * gamma_temperatura(campo.T, especie.t_min, especie.t_opt, especie.t_max)
        * gamma_actividad_agua(campo.A_w, especie.a_w_min)
        * gamma_uv(campo.R, especie.uv_max)
    )


# ==========================================================================
# 2. Conteo de vecinos de Moore (vectorizado)
# ==========================================================================
def contar_vecinos_moore(mascara: np.ndarray, borde: str = "muerta") -> np.ndarray:
    """Cuenta los 8 vecinos de Moore `True` de cada celda, sin bucles.

    Parameters
    ----------
    mascara : np.ndarray
        Máscara booleana (M, N).
    borde : {"muerta", "toroidal"}
        `"muerta"`: las celdas fuera de la grilla cuentan como 0. `"toroidal"`:
        los bordes se conectan (wrap-around).
    """
    m = mascara.astype(np.int64)
    if borde == "toroidal":
        total = np.zeros_like(m)
        for df in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if df == 0 and dc == 0:
                    continue
                total += np.roll(np.roll(m, df, axis=0), dc, axis=1)
        return total
    if borde != "muerta":
        raise ValueError(f"borde desconocido: {borde!r} (usa 'muerta' o 'toroidal')")
    p = np.pad(m, 1)  # frontera muerta: relleno de ceros alrededor
    return (
        p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:]
        + p[1:-1, :-2] + p[1:-1, 2:]
        + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]
    )


# ==========================================================================
# 3. Reglas de transición intercambiables (ADR-0016)
# ==========================================================================
@dataclass(frozen=True)
class _Contexto:
    """Todo lo que una regla necesita para decidir el estado siguiente.

    Se calcula una vez por tick en `paso()` y se pasa a la regla; así la regla no
    vuelve a tocar el campo ni la especie (separación limpia de responsabilidades).
    """

    estado: np.ndarray  # (M, N) int8, estado en t
    crece: np.ndarray  # bool: el ambiente permite reproducirse
    sobrevive: np.ndarray  # bool: el ambiente permite seguir vivo (⊇ crece)
    p_repro: np.ndarray  # float [0,1]: prob. de reproducción por tick
    n_activa: np.ndarray  # int: vecinos ACTIVA
    n_ocupada: np.ndarray  # int: vecinos ocupados (ACTIVA o LATENTE)
    rng: np.random.Generator


class ReglaTransicion(ABC):
    """Estrategia que calcula el estado siguiente del autómata.

    Intercambiable: `paso()` acepta cualquier `ReglaTransicion`, y el editor de
    reglas de la UI (Hito 3) puede crear nuevas sin tocar el motor. Cada regla
    expone su definición en `notacion()` para el panel de notación formal.
    """

    #: Nombre legible para el menú desplegable de la UI.
    nombre: str = "regla"

    @abstractmethod
    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        """Devuelve el nuevo estado (M, N) int8, calculado desde `ctx` (síncrono)."""

    @abstractmethod
    def notacion(self) -> str:
        """Definición de la regla en notación formal de AC (LaTeX), para la UI."""

    @staticmethod
    def _base(ctx: _Contexto) -> tuple[np.ndarray, np.ndarray]:
        """Clasificación ambiental común: arranca todo en MUERTA y ubica las
        celdas ocupadas que sobreviven en ACTIVA/LATENTE. Devuelve (nuevo, vacia)."""
        nuevo = np.full_like(ctx.estado, MUERTA)
        ocupada = (ctx.estado == ACTIVA) | (ctx.estado == LATENTE)
        return nuevo, ocupada


class ReglaLogistica(ReglaTransicion):
    """Proceso de contacto: la reproducción depende de μ y de vecinos ACTIVA.

    Sin muerte por soledad; la única muerte es ambiental. Es la regla por defecto
    porque es la más defendible biológicamente y hace que `μ` gobierne de verdad.
    """

    nombre = "Logística (proceso de contacto)"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        nuevo, ocupada = self._base(ctx)
        viva = ocupada & ctx.sobrevive
        nuevo[viva & ctx.crece] = ACTIVA  # incluye LATENTE→ACTIVA si ya crece
        nuevo[viva & ~ctx.crece] = LATENTE
        vacia = ctx.estado == MUERTA
        puede_nacer = vacia & ctx.crece & (ctx.n_activa > 0)
        prob = ctx.p_repro * (ctx.n_activa / 8.0)
        nace = puede_nacer & (ctx.rng.random(ctx.estado.shape) < prob)
        nuevo[nace] = ACTIVA
        return nuevo

    def notacion(self) -> str:
        return (
            r"S_{i,j}^{t+1}=\begin{cases}"
            r"\text{MUERTA} & \neg\,\mathrm{sup}(E_{i,j})\\"
            r"\text{ACTIVA} & \mathrm{ocup}\wedge \mathrm{cre}(E_{i,j})\\"
            r"\text{LATENTE} & \mathrm{ocup}\wedge \mathrm{sup}\wedge\neg\,\mathrm{cre}\\"
            r"\text{ACTIVA} & \text{vac}\wedge \mathrm{cre}\wedge "
            r"U<p_{\mathrm{rep}}\,\tfrac{n_A}{8}\\"
            r"\text{MUERTA} & \text{en otro caso}\end{cases}"
        )


class ReglaConway(ReglaTransicion):
    """Juego de la Vida (B3/S23) filtrado por el ambiente.

    Se conserva por familiaridad y valor visual, pero los umbrales 2-3/3 son del
    autómata, no de la microbiología: `p_repro` moja el nacimiento y el ambiente
    manda por encima.
    """

    nombre = "Conway (Juego de la Vida, B3/S23)"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        nuevo, ocupada = self._base(ctx)
        estable = (ctx.n_ocupada == 2) | (ctx.n_ocupada == 3)
        viva = ocupada & ctx.sobrevive & estable
        nuevo[viva & ctx.crece] = ACTIVA
        nuevo[viva & ~ctx.crece] = LATENTE
        vacia = ctx.estado == MUERTA
        nace = (
            vacia
            & ctx.crece
            & (ctx.n_ocupada == 3)
            & (ctx.rng.random(ctx.estado.shape) < ctx.p_repro)
        )
        nuevo[nace] = ACTIVA
        return nuevo

    def notacion(self) -> str:
        return (
            r"S_{i,j}^{t+1}=\begin{cases}"
            r"\text{MUERTA} & \neg\,\mathrm{sup}(E_{i,j})\\"
            r"\{\text{ACTIVA},\text{LATENTE}\} & \mathrm{ocup}\wedge n_O\in\{2,3\}\\"
            r"\text{ACTIVA} & \text{vac}\wedge \mathrm{cre}\wedge n_O=3\wedge "
            r"U<p_{\mathrm{rep}}\\"
            r"\text{MUERTA} & \text{en otro caso}\end{cases}"
        )


@dataclass
class ReglaHibrida(ReglaTransicion):
    """Contacto para nacer + muerte por sobrepoblación (`> k` vecinos ocupados).

    No hay muerte por soledad. El tope `k` evita que la grilla se sature por
    completo, manteniendo la dinámica de frentes de colonización.
    """

    k_hacinamiento: int = 6
    nombre: str = "Híbrida (contacto + tope de hacinamiento)"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        nuevo, ocupada = self._base(ctx)
        sin_hacinar = ctx.n_ocupada <= self.k_hacinamiento
        viva = ocupada & ctx.sobrevive & sin_hacinar
        nuevo[viva & ctx.crece] = ACTIVA
        nuevo[viva & ~ctx.crece] = LATENTE
        vacia = ctx.estado == MUERTA
        puede_nacer = vacia & ctx.crece & (ctx.n_activa > 0) & sin_hacinar
        prob = ctx.p_repro * (ctx.n_activa / 8.0)
        nace = puede_nacer & (ctx.rng.random(ctx.estado.shape) < prob)
        nuevo[nace] = ACTIVA
        return nuevo

    def notacion(self) -> str:
        return (
            r"S_{i,j}^{t+1}=\begin{cases}"
            r"\text{MUERTA} & \neg\,\mathrm{sup}\ \vee\ n_O>k\\"
            r"\text{ACTIVA} & \mathrm{ocup}\wedge \mathrm{cre}\wedge n_O\le k\\"
            r"\text{LATENTE} & \mathrm{ocup}\wedge \mathrm{sup}\wedge\neg\,\mathrm{cre}"
            r"\wedge n_O\le k\\"
            r"\text{ACTIVA} & \text{vac}\wedge \mathrm{cre}\wedge n_A>0\wedge "
            r"U<p_{\mathrm{rep}}\tfrac{n_A}{8}\\"
            r"\text{MUERTA} & \text{en otro caso}\end{cases}"
        )


#: Reglas listas para el menú desplegable de la UI (clave estable → instancia).
REGLAS_DISPONIBLES: dict[str, ReglaTransicion] = {
    "logistica": ReglaLogistica(),
    "conway": ReglaConway(),
    "hibrida": ReglaHibrida(),
}
