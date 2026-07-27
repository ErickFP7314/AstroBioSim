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

import operator
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
    T: np.ndarray,
    t_min: float,
    t_opt: float,
    t_max: float,
    *,
    sensibilidad: float = 1.0,
) -> np.ndarray:
    """Factor térmico CTMI (Rosso et al. 1993) ∈ [0, 1]; 1 en `t_opt`, 0 fuera.

    Usa los tres puntos cardinales sin parámetros libres. Es numéricamente
    delicado cerca de los extremos: fuera de ``(t_min, t_max)`` se fuerza a 0.
    El parámetro `sensibilidad` permite ponderar la respuesta a desviaciones térmicas.
    """
    T = np.asarray(T, dtype=float)
    num = (T - t_max) * (T - t_min) ** 2
    den = (t_opt - t_min) * (
        (t_opt - t_min) * (T - t_opt) - (t_opt - t_max) * (t_opt + t_min - 2.0 * T)
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(den != 0.0, num / den, 0.0)
    g = np.where((T > t_min) & (T < t_max), g, 0.0)
    g = np.clip(g, 0.0, 1.0)
    if sensibilidad != 1.0:
        g = g ** sensibilidad
    return g


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


def cinetica_mu(
    especie: Microorganismo,
    campo: CampoAmbiental,
    *,
    sensibilidad: float | None = None,
) -> np.ndarray:
    """Tasa de crecimiento por celda (h⁻¹): μ_opt · γ_T · γ_aw · γ_UV (ADR-0013)."""
    sens_t = (
        sensibilidad
        if sensibilidad is not None
        else getattr(especie, "sensibilidad_t", 1.0)
    )
    return (
        especie.mu_opt
        * gamma_temperatura(
            campo.T, especie.t_min, especie.t_opt, especie.t_max, sensibilidad=sens_t
        )
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
    #: ¿La especie tiene dormancia biológica real (anhidrobiótica)? Escalar por
    #: corrida. Lo usan las reglas que restringen la latencia a las anhidrobióticas;
    #: las clásicas lo ignoran. Default `False` para que construir un `_Contexto`
    #: sin especie (tests directos) siga funcionando.
    anhidrobiotico: bool = False


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


class ReglaLatenciaAnhidrobiotica(ReglaTransicion):
    """Latencia SOLO para especies anhidrobióticas (modelo biológico de Esmeralda).

    Idéntica a la logística, pero la latencia deja de ser universal: solo las
    especies con dormancia real (``anhidrobiotico=True``, p. ej. *D. radiodurans*)
    pueden quedar LATENTE al salir de sus condiciones de crecimiento. Una especie
    **no** anhidrobiótica (*E. coli*, *M. burtonii*) que deja de crecer **muere** —no
    se preserva dormida—, así que su dinámica es efectivamente binaria
    ACTIVA/MUERTA y su población **disminuye** en condiciones desfavorables, que es
    lo biológicamente correcto para un organismo sin anhidrobiosis.

    Consecuencia de diseño: para las no anhidrobióticas esta regla **ignora los
    umbrales de supervivencia** (la célula muere en cuanto no crece), a diferencia
    de la logística, que las dejaba latentes dentro de la ventana de supervivencia.
    Sigue siendo una regla **opt-in** del menú: no cambia el default.
    """

    nombre = "Latencia solo anhidrobióticos (D. radiodurans)"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        nuevo, ocupada = self._base(ctx)
        viva = ocupada & ctx.sobrevive
        nuevo[viva & ctx.crece] = ACTIVA  # incluye LATENTE→ACTIVA si vuelve a crecer
        if ctx.anhidrobiotico:
            nuevo[viva & ~ctx.crece] = LATENTE  # solo las anhidrobióticas duermen
        # Si NO es anhidrobiótica, las celdas que no crecen quedan MUERTA (por _base).
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
            r"\text{LATENTE} & \mathrm{ocup}\wedge \mathrm{sup}\wedge\neg\,\mathrm{cre}"
            r"\wedge \mathrm{anh}\\"
            r"\text{ACTIVA} & \text{vac}\wedge \mathrm{cre}\wedge "
            r"U<p_{\mathrm{rep}}\,\tfrac{n_A}{8}\\"
            r"\text{MUERTA} & \text{en otro caso}\end{cases}"
        )


@dataclass
class ReglaLatenciaConMortalidad(ReglaTransicion):
    """Latencia con costo: la dormancia de las NO anhidrobióticas es mortal.

    Todas las especies pueden quedar LATENTE al salir del crecimiento, pero la
    dormancia tiene un **costo de mortalidad** para las que no son anhidrobióticas:
    cada tick, una célula LATENTE de una especie con ``anhidrobiotico=False`` muere
    con probabilidad ``mortalidad_latente``. Las anhidrobióticas (*D. radiodurans*)
    persisten sin costo. Así la población de *E. coli*/*M. burtonii* **decae
    gradualmente** durante una dormancia prolongada (en vez de preservarse intacta),
    mientras la extremófila aguanta — el contraste que motiva ADR-0015. Opt-in: no
    cambia el default.
    """

    #: Probabilidad de que una célula LATENTE **no anhidrobiótica** muera por tick.
    #: **[EST]** — placeholder a calibrar con Esmeralda (ver `docs/parametros.md`).
    mortalidad_latente: float = 0.05
    nombre: str = "Latencia con mortalidad (dormancia con costo)"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        nuevo, ocupada = self._base(ctx)
        viva = ocupada & ctx.sobrevive
        nuevo[viva & ctx.crece] = ACTIVA
        latente = viva & ~ctx.crece
        nuevo[latente] = LATENTE
        if not ctx.anhidrobiotico and self.mortalidad_latente > 0.0:
            muere = latente & (ctx.rng.random(ctx.estado.shape) < self.mortalidad_latente)
            nuevo[muere] = MUERTA  # la latencia no anhidrobiótica decae con el tiempo
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
            r"\text{MUERTA} & \mathrm{ocup}\wedge \mathrm{sup}\wedge\neg\,\mathrm{cre}"
            r"\wedge\neg\,\mathrm{anh}\wedge U<q_{\mathrm{lat}}\\"
            r"\text{LATENTE} & \mathrm{ocup}\wedge \mathrm{sup}\wedge\neg\,\mathrm{cre}\\"
            r"\text{ACTIVA} & \text{vac}\wedge \mathrm{cre}\wedge "
            r"U<p_{\mathrm{rep}}\,\tfrac{n_A}{8}\\"
            r"\text{MUERTA} & \text{en otro caso}\end{cases}"
        )


#: Reglas listas para el menú desplegable de la UI (clave estable → instancia).
REGLAS_DISPONIBLES: dict[str, ReglaTransicion] = {
    "logistica": ReglaLogistica(),
    "conway": ReglaConway(),
    "hibrida": ReglaHibrida(),
    "latencia_anhidro": ReglaLatenciaAnhidrobiotica(),
    "latencia_mortalidad": ReglaLatenciaConMortalidad(),
}


# ==========================================================================
# 4. Reglas por bloques — editor visual de la UI (ADR-0018)
# ==========================================================================
# Una regla se arma como una lista ordenada de CLÁUSULAS "SI <condición> →
# <estado>". Se evalúan de arriba hacia abajo y **la primera que matchea gana**
# (misma semántica de cascada que la `notacion()` de las reglas de arriba). Las
# condiciones son máscaras booleanas sobre el `_Contexto`, así que el intérprete
# sigue siendo vectorizado y síncrono. El frontend NO ejecuta nada: manda el
# spec JSON y el motor lo convierte en una `ReglaTransicion`.

#: Comparadores permitidos para el conteo de vecinos (nombre → función NumPy).
_OPERADORES = {
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    ">=": operator.ge,
    ">": operator.gt,
}
_ESTADOS_CELDA = ("vacia", "ocupada", "activa", "latente")
_AMBIENTE = ("crece", "sobrevive")
_VECINOS = ("activa", "ocupada")
_RESULTADO_A_INT = {"MUERTA": MUERTA, "LATENTE": LATENTE, "ACTIVA": ACTIVA}
_INT_A_RESULTADO = {v: k for k, v in _RESULTADO_A_INT.items()}
#: Modos de probabilidad por cláusula (para las transiciones estocásticas).
#: - ``contacto``: p_repro · nº vecinos ACTIVA / 8 (proceso de contacto).
#: - ``mu``:       p_repro a secas (cinética pura, como el nacimiento de Conway).
_PROBS = ("contacto", "mu")


class Condicion(ABC):
    """Predicado vectorizado: dada la `_Contexto`, devuelve una máscara (M, N)."""

    @abstractmethod
    def evaluar(self, ctx: _Contexto) -> np.ndarray:
        """Máscara booleana (M, N): True en las celdas que cumplen la condición."""

    @abstractmethod
    def a_dict(self) -> dict:
        """Serializa la condición al formato del spec JSON."""

    @abstractmethod
    def notacion(self) -> str:
        """Fragmento LaTeX de la condición, para el panel de notación formal."""


@dataclass(frozen=True)
class CondEstado(Condicion):
    """El estado actual de la celda: vacía (MUERTA), ocupada, ACTIVA o LATENTE."""

    cual: str

    def evaluar(self, ctx: _Contexto) -> np.ndarray:
        e = ctx.estado
        if self.cual == "vacia":
            return e == MUERTA
        if self.cual == "ocupada":
            return (e == ACTIVA) | (e == LATENTE)
        if self.cual == "activa":
            return e == ACTIVA
        return e == LATENTE  # "latente" (validado al construir)

    def a_dict(self) -> dict:
        return {"tipo": "estado", "cual": self.cual}

    def notacion(self) -> str:
        return {
            "vacia": r"\text{vac}",
            "ocupada": r"\text{ocup}",
            "activa": r"\text{act}",
            "latente": r"\text{lat}",
        }[self.cual]


@dataclass(frozen=True)
class CondAmbiente(Condicion):
    """El ambiente permite `crecer` o `sobrevivir` (o su negación)."""

    cual: str
    valor: bool = True

    def evaluar(self, ctx: _Contexto) -> np.ndarray:
        base = ctx.crece if self.cual == "crece" else ctx.sobrevive
        return base if self.valor else ~base

    def a_dict(self) -> dict:
        return {"tipo": "ambiente", "cual": self.cual, "valor": self.valor}

    def notacion(self) -> str:
        simbolo = r"\mathrm{cre}" if self.cual == "crece" else r"\mathrm{sup}"
        return simbolo if self.valor else rf"\neg\,{simbolo}"


@dataclass(frozen=True)
class CondVecinos(Condicion):
    """Conteo de vecinos de Moore (ACTIVA u ocupados) comparado con un umbral."""

    cual: str
    op: str
    n: int

    def evaluar(self, ctx: _Contexto) -> np.ndarray:
        arr = ctx.n_activa if self.cual == "activa" else ctx.n_ocupada
        return _OPERADORES[self.op](arr, self.n)

    def a_dict(self) -> dict:
        return {"tipo": "vecinos", "cual": self.cual, "op": self.op, "n": self.n}

    def notacion(self) -> str:
        sub = "A" if self.cual == "activa" else "O"
        return rf"n_{sub}{self.op}{self.n}"


@dataclass(frozen=True)
class Clausula:
    """Una fila del editor: SI (todas las condiciones) → `resultado`.

    `prob` opcional hace la transición estocástica: la cláusula solo matchea
    donde además una tirada aleatoria cae bajo la probabilidad (ver `_PROBS`).
    Sin condiciones = "en otro caso" (matchea siempre lo que quede libre).
    """

    condiciones: tuple[Condicion, ...]
    resultado: int
    prob: str | None = None

    def a_dict(self) -> dict:
        d: dict = {
            "cuando": [c.a_dict() for c in self.condiciones],
            "entonces": _INT_A_RESULTADO[self.resultado],
        }
        if self.prob is not None:
            d["prob"] = self.prob
        return d


@dataclass
class ReglaDesdeBloques(ReglaTransicion):
    """Regla armada desde el editor de bloques (cascada de cláusulas, ADR-0018).

    Se evalúan las cláusulas en orden y **la primera que matchea** fija el estado
    siguiente de cada celda; lo que no matchea ninguna queda ``MUERTA``. Respeta
    todos los invariantes del motor: vectorizada, síncrona, `rng` inyectado y
    ``MUERTA`` absorbente (una celda vacía solo se ocupa por **colonización** de
    un vecino ACTIVA, nunca por generación espontánea — se fuerza al final de
    `aplicar`, sea cual sea el spec del usuario).
    """

    clausulas: tuple[Clausula, ...]
    nombre: str = "Regla personalizada"

    def aplicar(self, ctx: _Contexto) -> np.ndarray:
        forma = ctx.estado.shape
        nuevo = np.full(forma, MUERTA, dtype=np.int8)
        libre = np.ones(forma, dtype=bool)  # celdas aún no asignadas por una cláusula
        for cl in self.clausulas:
            cumple = np.ones(forma, dtype=bool)
            for cond in cl.condiciones:
                cumple &= cond.evaluar(ctx)
            if cl.prob is not None:
                cumple = cumple & (ctx.rng.random(forma) < self._probabilidad(cl, ctx))
            aplica = cumple & libre
            nuevo[aplica] = cl.resultado
            libre &= ~aplica
        # Invariante ADR-0012: MUERTA es absorbente. Reponer una celda vacía es
        # COLONIZACIÓN por un vecino que se reproduce (ACTIVA), no resurrección;
        # sin un vecino ACTIVA, una celda vacía no puede ocuparse.
        sin_colono = (ctx.estado == MUERTA) & (nuevo != MUERTA) & (ctx.n_activa == 0)
        nuevo[sin_colono] = MUERTA
        return nuevo

    @staticmethod
    def _probabilidad(cl: Clausula, ctx: _Contexto) -> np.ndarray:
        if cl.prob == "contacto":
            return ctx.p_repro * (ctx.n_activa / 8.0)
        return ctx.p_repro  # "mu"

    def a_spec(self) -> dict:
        """Devuelve el spec JSON equivalente (para round-trip y la UI)."""
        return {"nombre": self.nombre, "clausulas": [c.a_dict() for c in self.clausulas]}

    def notacion(self) -> str:
        filas = []
        for cl in self.clausulas:
            partes = [c.notacion() for c in cl.condiciones]
            if cl.prob == "contacto":
                partes.append(r"U<p_{\mathrm{rep}}\,n_A/8")
            elif cl.prob == "mu":
                partes.append(r"U<p_{\mathrm{rep}}")
            cond = r"\wedge ".join(partes) if partes else r"\text{en otro caso}"
            filas.append(rf"\text{{{_INT_A_RESULTADO[cl.resultado]}}} & {cond}")
        cuerpo = r"\\".join(filas)
        return r"S_{i,j}^{t+1}=\begin{cases}" + cuerpo + r"\end{cases}"


def _condicion_desde_dict(d: object, ctx: str) -> Condicion:
    """Parsea y valida una condición del spec. `ctx` describe dónde va (errores)."""
    if not isinstance(d, dict) or "tipo" not in d:
        raise ValueError(f"{ctx}: condición inválida {d!r} (falta 'tipo')")
    tipo = d["tipo"]
    if tipo == "estado":
        cual = d.get("cual")
        if cual not in _ESTADOS_CELDA:
            raise ValueError(f"{ctx}: 'cual' de estado debe ser uno de {list(_ESTADOS_CELDA)}")
        return CondEstado(cual)
    if tipo == "ambiente":
        cual = d.get("cual")
        if cual not in _AMBIENTE:
            raise ValueError(f"{ctx}: 'cual' de ambiente debe ser uno de {list(_AMBIENTE)}")
        return CondAmbiente(cual, bool(d.get("valor", True)))
    if tipo == "vecinos":
        cual = d.get("cual")
        if cual not in _VECINOS:
            raise ValueError(f"{ctx}: 'cual' de vecinos debe ser uno de {list(_VECINOS)}")
        op = d.get("op")
        if op not in _OPERADORES:
            raise ValueError(f"{ctx}: 'op' debe ser uno de {list(_OPERADORES)}")
        n = d.get("n")
        if not isinstance(n, int) or isinstance(n, bool) or not (0 <= n <= 8):
            raise ValueError(f"{ctx}: 'n' de vecinos debe ser un entero en [0, 8]")
        return CondVecinos(cual, op, n)
    raise ValueError(f"{ctx}: tipo de condición desconocido {tipo!r}")


def regla_desde_spec(spec: object) -> ReglaDesdeBloques:
    """Construye una `ReglaDesdeBloques` desde un spec JSON, validándolo.

    Parameters
    ----------
    spec : dict
        ``{"nombre": str, "clausulas": [{"cuando": [cond...], "entonces": str,
        "prob": str | None}, ...]}``. Ver `VOCABULARIO` para los valores válidos.

    Raises
    ------
    ValueError
        Si el spec está mal formado (tipo, valor, rango o estructura inválidos).
    """
    # Toda malformación del spec se reporta como ValueError (un único tipo de
    # excepción para el contrato público: la API y los tests dependen de él); por
    # eso los chequeos de tipo también lanzan ValueError y no TypeError.
    if not isinstance(spec, dict):
        raise ValueError("el spec de la regla debe ser un objeto")  # noqa: TRY004
    clausulas_raw = spec.get("clausulas")
    if not isinstance(clausulas_raw, list) or not clausulas_raw:
        raise ValueError("el spec necesita al menos una cláusula en 'clausulas'")
    clausulas: list[Clausula] = []
    for i, cl in enumerate(clausulas_raw):
        ctx = f"cláusula {i}"
        if not isinstance(cl, dict):
            raise ValueError(f"{ctx}: debe ser un objeto")  # noqa: TRY004
        cuando = cl.get("cuando", [])
        if not isinstance(cuando, list):
            raise ValueError(f"{ctx}: 'cuando' debe ser una lista de condiciones")  # noqa: TRY004
        conds = tuple(_condicion_desde_dict(c, ctx) for c in cuando)
        res = cl.get("entonces")
        if res not in _RESULTADO_A_INT:
            raise ValueError(f"{ctx}: 'entonces' debe ser uno de {list(_RESULTADO_A_INT)}")
        prob = cl.get("prob")
        if prob is not None and prob not in _PROBS:
            raise ValueError(f"{ctx}: 'prob' debe ser null o uno de {list(_PROBS)}")
        clausulas.append(Clausula(conds, _RESULTADO_A_INT[res], prob))
    nombre = str(spec.get("nombre") or "Regla personalizada")
    return ReglaDesdeBloques(tuple(clausulas), nombre)


#: Vocabulario de bloques que expone la API para que el frontend arme el editor
#: sin hardcodear nada (cada entrada = un desplegable).
VOCABULARIO: dict = {
    "condiciones": [
        {
            "tipo": "estado",
            "label": "Estado de la celda",
            "campos": {
                "cual": [
                    {"id": "vacia", "label": "vacía (MUERTA)"},
                    {"id": "ocupada", "label": "ocupada (ACTIVA o LATENTE)"},
                    {"id": "activa", "label": "ACTIVA"},
                    {"id": "latente", "label": "LATENTE"},
                ]
            },
        },
        {
            "tipo": "ambiente",
            "label": "El ambiente",
            "campos": {
                "cual": [
                    {"id": "crece", "label": "permite crecer"},
                    {"id": "sobrevive", "label": "permite sobrevivir"},
                ],
                "valor": [
                    {"id": True, "label": "sí"},
                    {"id": False, "label": "no"},
                ],
            },
        },
        {
            "tipo": "vecinos",
            "label": "Vecinos (Moore)",
            "campos": {
                "cual": [
                    {"id": "activa", "label": "ACTIVA"},
                    {"id": "ocupada", "label": "ocupados"},
                ],
                "op": [{"id": o, "label": o} for o in _OPERADORES],
                "n": [{"id": k, "label": str(k)} for k in range(9)],
            },
        },
    ],
    "resultados": [
        {"id": "ACTIVA", "label": "ACTIVA"},
        {"id": "LATENTE", "label": "LATENTE"},
        {"id": "MUERTA", "label": "MUERTA"},
    ],
    "probabilidades": [
        {"id": None, "label": "siempre (determinista)"},
        {"id": "contacto", "label": "reproducción por contacto (p·nA/8)"},
        {"id": "mu", "label": "cinética (p)"},
    ],
}

#: Las tres reglas fijas expresadas como spec, para usarlas de PLANTILLA en el
#: editor (el usuario carga una y la modifica). La `logistica` es equivalente
#: exacta a `ReglaLogistica`; conway/hibrida son puntos de partida (la guardia
#: de MUERTA absorbente puede diferir del original ante vecinos solo LATENTE).
PRESETS: dict[str, dict] = {
    "logistica": {
        "nombre": "Logística (proceso de contacto)",
        "clausulas": [
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                ],
                "entonces": "ACTIVA",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                ],
                "entonces": "LATENTE",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "vacia"},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                    {"tipo": "vecinos", "cual": "activa", "op": ">", "n": 0},
                ],
                "entonces": "ACTIVA",
                "prob": "contacto",
            },
            {"cuando": [], "entonces": "MUERTA"},
        ],
    },
    "conway": {
        "nombre": "Conway (Juego de la Vida, B3/S23)",
        "clausulas": [
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                    {"tipo": "vecinos", "cual": "ocupada", "op": ">=", "n": 2},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "<=", "n": 3},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                ],
                "entonces": "ACTIVA",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                    {"tipo": "vecinos", "cual": "ocupada", "op": ">=", "n": 2},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "<=", "n": 3},
                ],
                "entonces": "LATENTE",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "vacia"},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "==", "n": 3},
                ],
                "entonces": "ACTIVA",
                "prob": "mu",
            },
            {"cuando": [], "entonces": "MUERTA"},
        ],
    },
    "hibrida": {
        "nombre": "Híbrida (contacto + tope de hacinamiento k=6)",
        "clausulas": [
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "<=", "n": 6},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                ],
                "entonces": "ACTIVA",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "ocupada"},
                    {"tipo": "ambiente", "cual": "sobrevive", "valor": True},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "<=", "n": 6},
                ],
                "entonces": "LATENTE",
            },
            {
                "cuando": [
                    {"tipo": "estado", "cual": "vacia"},
                    {"tipo": "ambiente", "cual": "crece", "valor": True},
                    {"tipo": "vecinos", "cual": "activa", "op": ">", "n": 0},
                    {"tipo": "vecinos", "cual": "ocupada", "op": "<=", "n": 6},
                ],
                "entonces": "ACTIVA",
                "prob": "contacto",
            },
            {"cuando": [], "entonces": "MUERTA"},
        ],
    },
}
