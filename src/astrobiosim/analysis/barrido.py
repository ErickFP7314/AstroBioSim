"""Barrido frecuencia × magnitud de microrefugios → mapa de persistencia (ADR-0015).

Responde la **pregunta de investigación** del proyecto: ¿con qué **frecuencia** y
**magnitud** mínimas deben aparecer microrefugios húmedos transitorios (salmueras
delicuescentes) para que una población persista en un subsuelo planetario, en vez
de extinguirse?

Ejes del barrido
----------------
- **Frecuencia** = ``probabilidad_disparo`` de :class:`SalmueraDelicuescente` (cada
  cuánto se abre un refugio por tick).
- **Magnitud** = eje **ELEGIBLE** (``a_w`` pico / ``duracion`` / ``radio``): ADR-0015
  no fija qué es "magnitud", así que se deja ajustable. Se colapsa el rango del
  parámetro elegido a un valor puntual determinista para un barrido limpio.

Variable de respuesta (ambos mapas)
-----------------------------------
Para cada punto (frecuencia, magnitud) se corre un ensamble Montecarlo con semillas
explícitas y se mide la **persistencia** de dos formas:
- ``prob_persistencia``: fracción de réplicas donde queda población viva
  (activa + latente > 0) al final de la corrida.
- ``fraccion_viva``: fracción viva media (activa + latente) al final.

El **umbral crítico** es el contorno donde ``prob_persistencia`` cruza 0.5: por
debajo la población se extingue, por encima persiste (:meth:`ResultadoBarrido.curva_critica`).
"""
from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from astrobiosim.core.microorganism import Microorganismo
from astrobiosim.data.resampling import Entorno
from astrobiosim.engine.stochastic import SalmueraDelicuescente
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.modes.base import ModoSimulacion
from astrobiosim.simulation import sembrar_estado, simular_montecarlo

#: Ejes válidos para la "magnitud" del microrefugio.
EjeMagnitud = Literal["a_w", "duracion", "radio"]
#: Qué población cuenta como "persistencia". `viva` = activa+latente (sobrevive,
#: aunque duerma); `activa` = solo creciendo (población VIABLE). Ojo: especies
#: anhidrobióticas como *D. radiodurans* (a_w_sup_min = 0) nunca mueren por
#: sequedad —sobreviven latentes—, así que con `viva` la persistencia es trivial;
#: el umbral crítico interesante para ellas está en `activa` (¿los refugios la
#: reactivan?). Ver ADR-0015.
Poblacion = Literal["viva", "activa"]

# fracciones() devuelve columnas [MUERTA, LATENTE, ACTIVA].
_COL_LATENTE, _COL_ACTIVA = 1, 2

#: Rangos por defecto de la magnitud según el eje (min, max), para la UI/script.
RANGOS_MAGNITUD: dict[str, tuple[float, float]] = {
    "a_w": (0.80, 0.99),        # atraviesa el a_w_min (0.90) de D. radiodurans
    "duracion": (1.0, 30.0),    # ticks de vida del refugio
    "radio": (1.0, 8.0),        # celdas de alcance
}
#: Rango por defecto de la frecuencia (probabilidad_disparo por tick).
RANGO_FRECUENCIA: tuple[float, float] = (0.0, 0.5)


@dataclass
class FabricaModoAnalogico:
    """Factory **picklable** de :class:`ModoAnalogico` (para el barrido en paralelo).

    Un ``lambda rng: ModoAnalogico(df, ...)`` no se puede enviar a otro proceso;
    esta clase sí (sus campos se serializan)."""

    df: pd.DataFrame
    entorno: Entorno
    shape: tuple[int, int]

    def __call__(self, rng: np.random.Generator) -> ModoSimulacion:
        return ModoAnalogico(self.df, self.entorno, self.shape, rng=rng)


def _construir_salmuera(
    frecuencia: float, magnitud: float, eje: EjeMagnitud, base: dict
) -> SalmueraDelicuescente:
    """Salmuera con ``frecuencia`` en ``probabilidad_disparo`` y ``magnitud`` en el
    eje elegido (colapsado a un valor puntual); el resto sale de ``base``."""
    kw = dict(base)
    kw["probabilidad_disparo"] = float(frecuencia)
    if eje == "a_w":
        kw["a_w_objetivo_min"] = kw["a_w_objetivo_max"] = float(magnitud)
    elif eje == "duracion":
        kw["duracion_min_ticks"] = kw["duracion_max_ticks"] = float(magnitud)
    elif eje == "radio":
        kw["radio_celdas"] = float(magnitud)
    else:  # pragma: no cover - validado antes
        raise ValueError(f"eje_magnitud desconocido: {eje!r} (a_w|duracion|radio)")
    return SalmueraDelicuescente(**kw)


def _fracciones_finales(res_mc, poblacion: Poblacion) -> np.ndarray:
    """Fracción de la población elegida al final de cada réplica del ensamble."""
    vals = []
    for corrida in res_mc.corridas:
        fr = corrida.fracciones()[-1]
        val = fr[_COL_ACTIVA] if poblacion == "activa" else fr[_COL_LATENTE] + fr[_COL_ACTIVA]
        vals.append(val)
    return np.asarray(vals, dtype=float)


def evaluar_punto(
    construir_modo: Callable[[np.random.Generator], ModoSimulacion],
    especie: Microorganismo,
    frecuencia: float,
    magnitud: float,
    *,
    eje_magnitud: EjeMagnitud = "a_w",
    shape: tuple[int, int] = (48, 48),
    fraccion_activa: float = 0.15,
    n_corridas: int = 30,
    semilla_base: int = 0,
    n_iteraciones: int | None = None,
    salmuera_base: dict | None = None,
    poblacion: Poblacion = "viva",
    umbral: float = 0.0,
) -> tuple[float, float]:
    """Evalúa UN punto del barrido y devuelve ``(prob_persistencia, fraccion_media)``.

    Corre un ensamble Montecarlo de ``n_corridas`` réplicas (cada una con su propio
    estado inicial y flujos de `rng`, desde ``semilla_base``) con una salmuera de la
    ``frecuencia`` y ``magnitud`` dadas. La persistencia se mide sobre la ``poblacion``
    elegida: ``prob_persistencia`` = fracción de réplicas con población final
    ``> umbral``; ``fraccion_media`` = fracción media final de esa población.
    """
    base = salmuera_base or {}

    def construir_eventos(_rng: np.random.Generator) -> list[SalmueraDelicuescente]:
        # Instancia fresca por réplica: la salmuera tiene estado interno (ADR-0015).
        return [_construir_salmuera(frecuencia, magnitud, eje_magnitud, base)]

    def estado_inicial(rng: np.random.Generator) -> np.ndarray:
        return sembrar_estado(shape, rng=rng, fraccion_activa=fraccion_activa)

    res = simular_montecarlo(
        construir_modo=construir_modo,
        especie=especie,
        estado_inicial=estado_inicial,
        construir_eventos=construir_eventos,
        n_corridas=n_corridas,
        semilla=semilla_base,
        re_sembrar=True,
        n_iteraciones=n_iteraciones,
        guardar_corridas=True,
    )
    fracs = _fracciones_finales(res, poblacion)
    return float(np.mean(fracs > umbral)), float(np.mean(fracs))


@dataclass(frozen=True)
class ResultadoBarrido:
    """Mapas de persistencia del barrido (filas = magnitud, columnas = frecuencia)."""

    frecuencias: np.ndarray        # (nf,) valores de probabilidad_disparo
    magnitudes: np.ndarray         # (nm,) valores del eje de magnitud
    eje_magnitud: str
    prob_persistencia: np.ndarray  # (nm, nf) fracción de réplicas con población > umbral
    fraccion_media: np.ndarray     # (nm, nf) fracción media final de la población elegida
    n_corridas: int
    semilla_base: int
    shape: tuple[int, int]
    fraccion_activa: float
    n_iteraciones: int | None
    poblacion: str = "viva"
    umbral: float = 0.0

    def curva_critica(self, nivel: float = 0.5) -> np.ndarray:
        """Umbral crítico: para cada frecuencia, la MÍNIMA magnitud con
        ``prob_persistencia >= nivel`` (``NaN`` si ninguna lo alcanza).

        Asume que más magnitud ⇒ no menos persistencia (monótona por columna),
        que es lo esperable en los tres ejes (más húmedo/largo/ancho ⇒ mejor)."""
        curva = np.full(len(self.frecuencias), np.nan)
        for j in range(len(self.frecuencias)):
            alcanza = np.where(self.prob_persistencia[:, j] >= nivel)[0]
            if alcanza.size:
                curva[j] = self.magnitudes[alcanza.min()]
        return curva

    def a_dataframe(self) -> pd.DataFrame:
        """Tabla larga: una fila por (frecuencia, magnitud) con ambas métricas."""
        filas = []
        for im, m in enumerate(self.magnitudes):
            for jf, f in enumerate(self.frecuencias):
                filas.append(
                    {
                        "frecuencia": float(f),
                        "magnitud": float(m),
                        "eje_magnitud": self.eje_magnitud,
                        "poblacion": self.poblacion,
                        "prob_persistencia": float(self.prob_persistencia[im, jf]),
                        "fraccion_media": float(self.fraccion_media[im, jf]),
                    }
                )
        return pd.DataFrame(filas)


# --- tarea picklable para el pool de procesos (top-level a propósito) ---
def _evaluar_tarea(args: tuple) -> tuple[float, float]:
    (construir_modo, especie, f, m, eje, shape, fraccion_activa,
     n_corridas, semilla_base, n_iteraciones, salmuera_base, poblacion, umbral) = args
    return evaluar_punto(
        construir_modo, especie, f, m,
        eje_magnitud=eje, shape=shape, fraccion_activa=fraccion_activa,
        n_corridas=n_corridas, semilla_base=semilla_base,
        n_iteraciones=n_iteraciones, salmuera_base=salmuera_base,
        poblacion=poblacion, umbral=umbral,
    )


def barrido_microrefugios(
    construir_modo: Callable[[np.random.Generator], ModoSimulacion],
    especie: Microorganismo,
    *,
    frecuencias: Sequence[float],
    magnitudes: Sequence[float],
    eje_magnitud: EjeMagnitud = "a_w",
    shape: tuple[int, int] = (48, 48),
    fraccion_activa: float = 0.15,
    n_corridas: int = 30,
    semilla_base: int = 0,
    n_iteraciones: int | None = None,
    salmuera_base: dict | None = None,
    poblacion: Poblacion = "viva",
    umbral: float = 0.0,
    n_procesos: int | None = None,
    progreso: Callable[[int, int], None] | None = None,
) -> ResultadoBarrido:
    """Corre el barrido frecuencia × magnitud y devuelve los mapas de persistencia.

    Parameters
    ----------
    construir_modo : Callable[[Generator], ModoSimulacion]
        Factory del modo (una fresca por réplica). Para el barrido en paralelo debe
        ser **picklable** (usar :class:`FabricaModoAnalogico`, no un lambda).
    frecuencias, magnitudes : Sequence[float]
        Valores de los dos ejes. El mapa resultante es ``(len(magnitudes),
        len(frecuencias))``.
    eje_magnitud : {"a_w", "duracion", "radio"}
        Qué parámetro del refugio representa la "magnitud".
    n_procesos : int, optional
        ``None`` o 1 ⇒ serial; ``>1`` ⇒ paraleliza los puntos en un pool de procesos
        (cada punto es independiente). No cambia los resultados (cada punto es
        determinista desde ``semilla_base``).
    progreso : Callable[[int, int], None], optional
        Callback ``(hechos, total)`` para reportar avance.

    Returns
    -------
    ResultadoBarrido
    """
    frec = np.asarray(frecuencias, dtype=float)
    magn = np.asarray(magnitudes, dtype=float)
    nf, nm = len(frec), len(magn)

    # Orden fila-mayor: primero varía la frecuencia (columna) dentro de cada magnitud.
    tareas = [
        (construir_modo, especie, float(f), float(m), eje_magnitud, shape,
         fraccion_activa, n_corridas, semilla_base, n_iteraciones, salmuera_base,
         poblacion, umbral)
        for m in magn
        for f in frec
    ]
    total = len(tareas)
    prob = np.empty(total)
    viva = np.empty(total)

    if n_procesos and n_procesos > 1:
        # `fork` no re-importa el __main__ (funciona desde script, notebook o stdin
        # en Linux) y arranca más rápido; si no está, cae al método por defecto.
        try:
            ctx = mp.get_context("fork")
        except ValueError:  # pragma: no cover - plataformas sin fork
            ctx = None
        with ProcessPoolExecutor(max_workers=n_procesos, mp_context=ctx) as pool:
            for i, (p, v) in enumerate(pool.map(_evaluar_tarea, tareas)):
                prob[i], viva[i] = p, v
                if progreso is not None:
                    progreso(i + 1, total)
    else:
        for i, tarea in enumerate(tareas):
            prob[i], viva[i] = _evaluar_tarea(tarea)
            if progreso is not None:
                progreso(i + 1, total)

    return ResultadoBarrido(
        frecuencias=frec,
        magnitudes=magn,
        eje_magnitud=eje_magnitud,
        prob_persistencia=prob.reshape(nm, nf),
        fraccion_media=viva.reshape(nm, nf),
        n_corridas=n_corridas,
        semilla_base=semilla_base,
        shape=shape,
        fraccion_activa=fraccion_activa,
        n_iteraciones=n_iteraciones,
        poblacion=poblacion,
        umbral=umbral,
    )
