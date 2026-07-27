"""Análisis de sensibilidad de los umbrales biológicos (dueño: Erick).

Responde los tres criterios de la tarea (ADR-0013): **blinda el resultado del
barrido frente a la incertidumbre de los umbrales de especie**.

1. **Cada umbral se varía sobre su rango de incertidumbre.** El ancho del rango
   sale de la **procedencia** del parámetro en ``docs/parametros.md`` (§1):

   - ``[LIT]`` — dato publicado, poca incertidumbre. Puntos cardinales de
     temperatura ±2 °C; ``a_w_min`` ±0.02 (acotado al piso duro 0.605); fluencia
     UV ±20 %.
   - ``[ANA]`` — inferido por analogía. La única (*M. burtonii*, UV) trae su rango
     **documentado**: 2.5×–13.8× la fluencia de *M. barkeri* (el nominal toma el
     extremo conservador 2.5×).
   - ``[EST]`` — estimación sin cita, la **más ancha**: umbrales de supervivencia
     de temperatura ±10 °C y ``a_w_sup_min`` ±0.20. Son la deuda §4.4.
   - ``a_w_sup_min`` de *D. radiodurans* es ``[LIT]`` = 0 (anhidrobiosis total):
     **no tiene incertidumbre** y se excluye del barrido (es, en sí, un hallazgo).

2. **Qué parámetro domina el desenlace.** Barrido *one-at-a-time* (OAT): se varía
   un umbral por vez dejando el resto en su valor nominal, y se mide el **rango de
   respuesta** de la persistencia. El de mayor rango es el dominante
   (:meth:`ResultadoSensibilidad.ranking`).

3. **Si las conclusiones se sostienen en todo el rango.** La conclusión del barrido
   ("persiste" ⇔ ``prob_persistencia ≥ 0.5``) es **robusta** respecto de un umbral
   si su rango de respuesta **no cruza** 0.5 (:meth:`RespuestaParametro.cruza`).

La sensibilidad se mide en el **mismo escenario del barrido** (misma especie,
entorno y salmuera), reutilizando :func:`astrobiosim.analysis.barrido.evaluar_punto`:
solo se sustituye la especie por una **copia perturbada**. Con ``frecuencia=0`` el
escenario colapsa al ambiente puro (sin microrefugios).
"""
from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from astrobiosim.analysis.barrido import EjeMagnitud, Poblacion, evaluar_punto
from astrobiosim.core.microorganism import (
    RAZON_INHIBICION_UV,
    SEGUNDOS_UV_POR_TICK,
    Microorganismo,
)
from astrobiosim.modes.base import ModoSimulacion

#: Procedencia de cada umbral por especie (``docs/parametros.md`` §1). Agrupa los
#: tres puntos cardinales de temperatura bajo ``"t"``, los dos de supervivencia
#: bajo ``"t_sup"`` y las dos derivadas de UV bajo ``"uv"``.
_PROCEDENCIA: dict[str, dict[str, str]] = {
    "EColi":        {"t": "LIT", "a_w_min": "LIT", "uv": "LIT", "t_sup": "EST", "a_w_sup_min": "EST"},
    "DRadiodurans": {"t": "LIT", "a_w_min": "LIT", "uv": "LIT", "t_sup": "EST", "a_w_sup_min": "LIT"},
    "MBurtonii":    {"t": "LIT", "a_w_min": "LIT", "uv": "ANA", "t_sup": "EST", "a_w_sup_min": "EST"},
}

#: Piso duro de la actividad de agua de **crecimiento** (Stevenson et al., 2015):
#: ningún ``a_w_min`` perturbado puede bajar de aquí (contrato §3.2).
A_W_MIN_PISO: float = 0.605
#: Base de la fluencia UV de *M. barkeri* (metanógena sensible), sobre la que se
#: define el rango [ANA] de *M. burtonii* (``docs/parametros.md`` §1.3).
_FLUENCIA_BASE_METANOGENA: float = 870.0


def especie_perturbada(especie: Microorganismo, **overrides: float) -> Microorganismo:
    """Copia de ``especie`` con uno o más umbrales sustituidos.

    Crea una **instancia nueva** de la misma clase (los umbrales son atributos de
    clase; los ``overrides`` los sombrean como atributos de instancia). No muta la
    especie original ni su clase, y la copia es *picklable* (viaja al pool de
    procesos del barrido paralelo).

    Parameters
    ----------
    especie : Microorganismo
        Especie base (sin tocar).
    **overrides : float
        Pares ``atributo=valor`` a sustituir (p. ej. ``a_w_sup_min=0.4``).

    Returns
    -------
    Microorganismo
        Nueva instancia con los umbrales perturbados.

    Raises
    ------
    AttributeError
        Si algún ``atributo`` no existe en la especie (typo).
    """
    nueva = type(especie)()
    for nombre, valor in overrides.items():
        if not hasattr(especie, nombre):
            raise AttributeError(f"{type(especie).__name__} no tiene el umbral {nombre!r}")
        setattr(nueva, nombre, float(valor))
    return nueva


def _override_escalar(atributo: str) -> Callable[[float], dict[str, float]]:
    """Builder de overrides para un umbral escalar (el valor ES el umbral)."""
    def construir(valor: float) -> dict[str, float]:
        return {atributo: valor}
    return construir


def _override_uv(fluencia: float) -> dict[str, float]:
    """Overrides de las DOS derivadas de UV a partir de la fluencia letal (J/m²).

    ``uv_letal`` y ``uv_max`` se derivan juntas de la misma fluencia
    (``docs/parametros.md`` §1.3), así que se perturban acopladas: barrer una sola
    rompería la relación ``uv_max = uv_letal / RAZON_INHIBICION_UV``.
    """
    return {
        "uv_max": fluencia / (RAZON_INHIBICION_UV * SEGUNDOS_UV_POR_TICK),
        "uv_letal": fluencia / SEGUNDOS_UV_POR_TICK,
    }


@dataclass(frozen=True)
class ParametroIncertidumbre:
    """Un umbral con su rango de incertidumbre y cómo aplicarlo a la especie."""

    nombre: str                                   # etiqueta legible del umbral
    procedencia: str                              # LIT | DER | ANA | CONV | EST
    nominal: float                                # valor calibrado
    lo: float                                     # extremo inferior del rango
    hi: float                                     # extremo superior del rango
    _overrides: Callable[[float], dict[str, float]]  # valor -> overrides de instancia

    def overrides(self, valor: float) -> dict[str, float]:
        """Overrides de instancia para poner el umbral en ``valor``."""
        return self._overrides(valor)

    def valores(self, n_puntos: int) -> np.ndarray:
        """``n_puntos`` valores equiespaciados en ``[lo, hi]`` (incluye los extremos)."""
        return np.linspace(self.lo, self.hi, n_puntos)


def parametros_inciertos(especie: Microorganismo) -> list[ParametroIncertidumbre]:
    """Lista de umbrales inciertos de ``especie`` con su rango según procedencia.

    Los valores nominales se leen de la propia especie (fuente única de verdad:
    ``core/microorganism.py``); los rangos salen de la procedencia en
    ``docs/parametros.md`` §1. Excluye ``a_w_sup_min`` cuando es ``[LIT]`` = 0
    (anhidrobiosis de *D. radiodurans*: sin incertidumbre).
    """
    tipo = type(especie).__name__
    if tipo not in _PROCEDENCIA:
        raise ValueError(f"especie desconocida: {tipo} (esperaba una de {list(_PROCEDENCIA)})")
    proc = _PROCEDENCIA[tipo]
    params: list[ParametroIncertidumbre] = []

    # Puntos cardinales de temperatura de CRECIMIENTO — [LIT], ±2 °C.
    for atributo in ("t_min", "t_opt", "t_max"):
        nom = float(getattr(especie, atributo))
        params.append(ParametroIncertidumbre(
            atributo, proc["t"], nom, nom - 2.0, nom + 2.0, _override_escalar(atributo)))

    # a_w mínima de CRECIMIENTO — [LIT], ±0.02, acotada al piso duro 0.605.
    nom = float(especie.a_w_min)
    params.append(ParametroIncertidumbre(
        "a_w_min", proc["a_w_min"], nom,
        max(A_W_MIN_PISO, nom - 0.02), min(1.0, nom + 0.02), _override_escalar("a_w_min")))

    # Fluencia UV letal (acopla uv_max y uv_letal). [ANA] trae su rango documentado.
    nom = float(especie.FLUENCIA_LETAL_J_M2)
    if proc["uv"] == "ANA":                       # M. burtonii: 2.5×–13.8× M. barkeri
        lo, hi = _FLUENCIA_BASE_METANOGENA * 2.5, _FLUENCIA_BASE_METANOGENA * 13.8
    else:                                         # [LIT]: ±20 %
        lo, hi = nom * 0.8, nom * 1.2
    params.append(ParametroIncertidumbre(
        "uv (fluencia letal)", proc["uv"], nom, lo, hi, _override_uv))

    # Rango de temperatura de SUPERVIVENCIA — [EST], ±10 °C (deuda §4.4).
    for atributo in ("t_sup_min", "t_sup_max"):
        nom = float(getattr(especie, atributo))
        params.append(ParametroIncertidumbre(
            atributo, proc["t_sup"], nom, nom - 10.0, nom + 10.0, _override_escalar(atributo)))

    # a_w mínima de SUPERVIVENCIA. [EST] ±0.20 (acotada a [0, a_w_min]); si es
    # [LIT]=0 (anhidrobiosis) no tiene incertidumbre y se omite.
    nom = float(especie.a_w_sup_min)
    if proc["a_w_sup_min"] == "EST":
        params.append(ParametroIncertidumbre(
            "a_w_sup_min", "EST", nom,
            max(0.0, nom - 0.20), min(float(especie.a_w_min), nom + 0.20),
            _override_escalar("a_w_sup_min")))

    return params


@dataclass(frozen=True)
class RespuestaParametro:
    """Respuesta de la persistencia al barrer UN umbral sobre su rango."""

    nombre: str
    procedencia: str
    nominal: float
    valores: np.ndarray            # (n_puntos,) puntos barridos en [lo, hi]
    prob_persistencia: np.ndarray  # (n_puntos,) fracción de réplicas que persisten
    fraccion_media: np.ndarray     # (n_puntos,) fracción viva media final

    @property
    def rango_respuesta(self) -> float:
        """Amplitud de la respuesta = ``max(prob) − min(prob)``. Mide la dominancia:
        cuánto mueve el desenlace la incertidumbre de este umbral."""
        return float(np.nanmax(self.prob_persistencia) - np.nanmin(self.prob_persistencia))

    def cruza(self, nivel: float = 0.5) -> bool:
        """``True`` si el rango de respuesta **atraviesa** ``nivel`` (0.5 por defecto):
        entonces la incertidumbre de este umbral **puede invertir** la conclusión
        de persistencia — la conclusión NO es robusta respecto de él."""
        lo = float(np.nanmin(self.prob_persistencia))
        hi = float(np.nanmax(self.prob_persistencia))
        return lo < nivel <= hi


@dataclass(frozen=True)
class ResultadoSensibilidad:
    """Resultado del análisis OAT: respuesta de cada umbral + nominal de referencia."""

    especie: str
    prob_nominal: float             # persistencia con todos los umbrales nominales
    fraccion_nominal: float
    respuestas: list[RespuestaParametro]
    n_corridas: int
    n_puntos: int
    semilla_base: int
    nivel: float = field(default=0.5)

    def ranking(self) -> list[RespuestaParametro]:
        """Respuestas ordenadas por dominancia (mayor rango de respuesta primero)."""
        return sorted(self.respuestas, key=lambda r: r.rango_respuesta, reverse=True)

    @property
    def dominante(self) -> RespuestaParametro:
        """Umbral que más mueve el desenlace."""
        return self.ranking()[0]

    def conclusiones_robustas(self) -> bool:
        """``True`` si **ningún** umbral, dentro de su rango de incertidumbre, cruza
        el nivel: la conclusión de persistencia del barrido se sostiene en todo el
        espacio de incertidumbre biológica."""
        return not any(r.cruza(self.nivel) for r in self.respuestas)

    def umbrales_criticos(self) -> list[RespuestaParametro]:
        """Umbrales cuya incertidumbre **sí** puede invertir la conclusión."""
        return [r for r in self.respuestas if r.cruza(self.nivel)]

    def a_dataframe(self) -> pd.DataFrame:
        """Tabla larga: una fila por (umbral, valor) con ambas métricas."""
        filas = []
        for r in self.respuestas:
            for v, p, f in zip(r.valores, r.prob_persistencia, r.fraccion_media):
                filas.append({
                    "umbral": r.nombre,
                    "procedencia": r.procedencia,
                    "nominal": r.nominal,
                    "valor": float(v),
                    "prob_persistencia": float(p),
                    "fraccion_media": float(f),
                })
        return pd.DataFrame(filas)


# --- tarea picklable para el pool de procesos (top-level a propósito) ---
def _tarea(args: tuple) -> tuple[float, float]:
    (construir_modo, especie, frecuencia, magnitud, eje, salmuera_base, shape,
     fraccion_activa, n_corridas, semilla_base, n_iteraciones, poblacion, umbral) = args
    return evaluar_punto(
        construir_modo, especie, frecuencia, magnitud,
        eje_magnitud=eje, shape=shape, fraccion_activa=fraccion_activa,
        n_corridas=n_corridas, semilla_base=semilla_base,
        n_iteraciones=n_iteraciones, salmuera_base=salmuera_base,
        poblacion=poblacion, umbral=umbral,
    )


def analisis_sensibilidad(
    construir_modo: Callable[[np.random.Generator], ModoSimulacion],
    especie: Microorganismo,
    *,
    parametros: Sequence[ParametroIncertidumbre] | None = None,
    n_puntos: int = 5,
    frecuencia: float = 0.0,
    magnitud: float = 0.98,
    eje_magnitud: EjeMagnitud = "a_w",
    salmuera_base: dict | None = None,
    shape: tuple[int, int] = (48, 48),
    fraccion_activa: float = 0.15,
    n_corridas: int = 30,
    semilla_base: int = 0,
    n_iteraciones: int | None = None,
    poblacion: Poblacion = "viva",
    umbral: float = 0.0,
    nivel: float = 0.5,
    n_procesos: int | None = None,
    progreso: Callable[[int, int], None] | None = None,
) -> ResultadoSensibilidad:
    """Análisis de sensibilidad OAT de los umbrales de ``especie``.

    Para cada umbral incierto se lo barre sobre su rango de incertidumbre (``n_puntos``
    valores) dejando el resto en su valor nominal, y se mide la persistencia en el
    escenario del barrido (misma salmuera). Se corre además el caso **nominal** (todos
    los umbrales sin tocar) como referencia.

    Parameters
    ----------
    construir_modo : Callable[[Generator], ModoSimulacion]
        Factory del modo (picklable si ``n_procesos > 1``: usar
        :class:`~astrobiosim.analysis.barrido.FabricaModoAnalogico`).
    especie : Microorganismo
        Especie base, sin perturbar.
    parametros : sequence of ParametroIncertidumbre, optional
        Umbrales a barrer. Por defecto :func:`parametros_inciertos(especie)`.
    n_puntos : int
        Nº de valores por umbral (incluye los extremos del rango).
    frecuencia, magnitud, eje_magnitud, salmuera_base
        Escenario de microrefugios (igual que en :func:`barrido.evaluar_punto`).
        Con ``frecuencia=0`` no hay refugios (ambiente puro).
    n_procesos : int, optional
        ``>1`` paraleliza los puntos (cada uno es independiente y determinista).

    Returns
    -------
    ResultadoSensibilidad
    """
    params = list(parametros) if parametros is not None else parametros_inciertos(especie)
    if n_puntos < 2:
        raise ValueError("n_puntos debe ser >= 2 para barrer un rango")

    escenario = (frecuencia, magnitud, eje_magnitud, salmuera_base, shape,
                 fraccion_activa, n_corridas, semilla_base, n_iteraciones, poblacion, umbral)

    # Índice de tareas: primero el nominal, luego (parámetro, punto).
    especies = [especie]                              # [0] = nominal
    indice: list[tuple[int, int]] = []                # (i_param, i_punto) por tarea
    matriz_valores: list[np.ndarray] = []
    for ip, p in enumerate(params):
        vals = p.valores(n_puntos)
        matriz_valores.append(vals)
        for jp, v in enumerate(vals):
            especies.append(especie_perturbada(especie, **p.overrides(v)))
            indice.append((ip, jp))

    tareas = [(construir_modo, esp, *escenario) for esp in especies]
    total = len(tareas)
    prob = np.empty(total)
    frac = np.empty(total)

    if n_procesos and n_procesos > 1:
        try:
            ctx = mp.get_context("fork")     # no re-importa __main__ (script/notebook/stdin)
        except ValueError:                   # pragma: no cover - plataformas sin fork
            ctx = None
        with ProcessPoolExecutor(max_workers=n_procesos, mp_context=ctx) as pool:
            for i, (p_, f_) in enumerate(pool.map(_tarea, tareas)):
                prob[i], frac[i] = p_, f_
                if progreso is not None:
                    progreso(i + 1, total)
    else:
        for i, tarea in enumerate(tareas):
            prob[i], frac[i] = _tarea(tarea)
            if progreso is not None:
                progreso(i + 1, total)

    # Reconstruir por parámetro (la tarea 0 es el nominal; el resto van en orden).
    respuestas: list[RespuestaParametro] = []
    cursor = 1
    for ip, p in enumerate(params):
        vals = matriz_valores[ip]
        k = len(vals)
        respuestas.append(RespuestaParametro(
            nombre=p.nombre, procedencia=p.procedencia, nominal=p.nominal,
            valores=vals, prob_persistencia=prob[cursor:cursor + k].copy(),
            fraccion_media=frac[cursor:cursor + k].copy(),
        ))
        cursor += k

    return ResultadoSensibilidad(
        especie=type(especie).__name__,
        prob_nominal=float(prob[0]),
        fraccion_nominal=float(frac[0]),
        respuestas=respuestas,
        n_corridas=n_corridas,
        n_puntos=n_puntos,
        semilla_base=semilla_base,
        nivel=nivel,
    )
