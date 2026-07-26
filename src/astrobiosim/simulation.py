"""Orquestador de la simulación (dueño: Erick) — punto de unión de los motores.

`simular` corre el bucle principal: por cada tick toma un `CampoAmbiental` del
**modo** (Analógico, Sandbox, estático…), le aplica los **eventos estocásticos**
de Jose, avanza el autómata con `paso` y registra el **historial poblacional**.
No conoce de dónde salen los campos (itera cualquier `ModoSimulacion`), así que
todos los modos comparten este único bucle (DRY, ADR-0017).

`simular_montecarlo` envuelve a `simular`: corre N réplicas independientes con
semillas distintas y agrega la media ± desviación por tick de las tres fracciones
poblacionales, para separar la señal del ruido estocástico.

Invariantes: actualización síncrona (delega en `paso`, doble buffer), aleatoriedad
**solo** vía el `rng` inyectado (misma semilla ⇒ misma corrida), y no muta el
`estado_inicial` recibido.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import islice

import numpy as np

from astrobiosim.core.microorganism import ACTIVA, LATENTE, MUERTA, Microorganismo
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.stochastic import EventoEstocastico
from astrobiosim.engine.transition_rules import ReglaTransicion
from astrobiosim.modes.base import ModoSimulacion


@dataclass(frozen=True)
class ResultadoSimulacion:
    """Historial poblacional de una corrida (una entrada por tick, incluido t=0).

    Attributes
    ----------
    muerta, latente, activa : np.ndarray
        Conteo de celdas en cada estado por tick, shape ``(n_iteraciones + 1,)``.
    grillas : list[np.ndarray] | None
        Estado completo (M, N) int8 por tick si se pidió `guardar_grillas`; si no,
        `None` (solo se guardan las curvas poblacionales).
    """

    muerta: np.ndarray
    latente: np.ndarray
    activa: np.ndarray
    grillas: list[np.ndarray] | None = None

    def __len__(self) -> int:
        return int(self.activa.shape[0])

    @property
    def viva(self) -> np.ndarray:
        """Celdas vivas (activa + latente) por tick."""
        return self.latente + self.activa

    @property
    def total(self) -> int:
        """Total de celdas de la grilla (constante)."""
        return int(self.muerta[0] + self.latente[0] + self.activa[0])

    def fracciones(self) -> np.ndarray:
        """Fracciones ``[muerta, latente, activa]`` por tick, shape (n+1, 3)."""
        conteos = np.stack(
            [self.muerta, self.latente, self.activa], axis=1
        ).astype(float)
        return conteos / conteos.sum(axis=1, keepdims=True)


def sembrar_estado(
    shape: tuple[int, int],
    *,
    rng: np.random.Generator,
    fraccion_activa: float = 0.15,
    patron: str = "uniforme",
) -> np.ndarray:
    """Genera un estado inicial (M, N) int8 con celdas `ACTIVA` sembradas.

    El orquestador recibe el estado inicial como parámetro; este helper cubre los
    dos patrones habituales. Toda aleatoriedad usa el `rng` inyectado.

    Parameters
    ----------
    shape : tuple[int, int]
        Dimensiones (M, N).
    rng : np.random.Generator
        Generador inyectado (regla de oro nº6).
    fraccion_activa : float
        Fracción de celdas vivas al arranque (0..1).
    patron : {"uniforme", "cluster"}
        `"uniforme"`: celdas `ACTIVA` dispersas al azar. `"cluster"`: un bloque
        central cuya área aproxima `fraccion_activa`.
    """
    m, n = shape
    estado = np.full(shape, MUERTA, dtype=np.int8)
    if patron == "uniforme":
        estado[rng.random(shape) < fraccion_activa] = ACTIVA
    elif patron == "cluster":
        lado = max(1, min(round((fraccion_activa * m * n) ** 0.5), m, n))
        i0, j0 = (m - lado) // 2, (n - lado) // 2
        estado[i0 : i0 + lado, j0 : j0 + lado] = ACTIVA
    else:
        raise ValueError(f"patron desconocido: {patron!r} ('uniforme' o 'cluster')")
    return estado


def simular(
    modo: ModoSimulacion,
    especie: Microorganismo,
    estado_inicial: np.ndarray,
    rng: np.random.Generator,
    *,
    n_iteraciones: int | None = None,
    eventos: Sequence[EventoEstocastico] = (),
    regla: ReglaTransicion | None = None,
    dt: float = 1.0,
    borde: str = "muerta",
    guardar_grillas: bool = False,
) -> ResultadoSimulacion:
    """Corre la simulación y devuelve el historial poblacional.

    Parameters
    ----------
    modo : ModoSimulacion
        Proveedor de `CampoAmbiental` por tick (Analógico, Sandbox, estático…).
    especie : Microorganismo
        Especie simulada.
    estado_inicial : np.ndarray
        Estado (M, N) en t=0. **No se modifica** (se copia).
    rng : np.random.Generator
        Generador inyectado; alimenta los eventos y la reproducción del autómata.
    n_iteraciones : int, optional
        Número de ticks. Si es `None`, corre hasta agotar el modo (útil para el
        Modo Analógico, que es finito). **Obligatorio para modos infinitos**
        (p. ej. `ModoEstatico`), o el bucle no termina.
    eventos : Sequence[EventoEstocastico]
        Eventos que perturban el campo cada tick, en orden, antes de `paso`.
    regla : ReglaTransicion, optional
        Regla de transición del autómata (ADR-0016). Default `ReglaLogistica`.
    dt : float
        Duración del tick en horas (cinética, ADR-0013). Default 1 h.
    borde : {"muerta", "toroidal"}
        Condición de borde del autómata.
    guardar_grillas : bool
        Si es `True`, guarda el estado completo por tick además de las curvas.

    Returns
    -------
    ResultadoSimulacion
        Curvas poblacionales (y grillas si se pidieron), con t=0 como primera
        entrada.
    """
    estado = np.asarray(estado_inicial, dtype=np.int8).copy()

    muerta = [int((estado == MUERTA).sum())]
    latente = [int((estado == LATENTE).sum())]
    activa = [int((estado == ACTIVA).sum())]
    grillas: list[np.ndarray] | None = [estado.copy()] if guardar_grillas else None

    campos = modo.campos()
    if n_iteraciones is not None:
        campos = islice(campos, n_iteraciones)

    for campo_base in campos:
        # Los eventos NO mutan el campo in situ (devuelven uno nuevo al disparar);
        # `paso` tampoco lo modifica. El estado siguiente sale del anterior (síncrono).
        campo = campo_base
        for evento in eventos:
            campo = evento.aplicar(campo, rng)
        estado = paso(estado, campo, especie, rng, regla=regla, dt=dt, borde=borde)

        muerta.append(int((estado == MUERTA).sum()))
        latente.append(int((estado == LATENTE).sum()))
        activa.append(int((estado == ACTIVA).sum()))
        if grillas is not None:
            grillas.append(estado.copy())

    return ResultadoSimulacion(
        muerta=np.asarray(muerta),
        latente=np.asarray(latente),
        activa=np.asarray(activa),
        grillas=grillas,
    )


# ==========================================================================
# Integración Montecarlo (Hito 3)
# ==========================================================================
@dataclass(frozen=True)
class ResultadoMontecarlo:
    """Agregado de N réplicas: media ± desviación por tick de las tres fracciones.

    Attributes
    ----------
    media, desviacion : np.ndarray
        Shape ``(n_iteraciones + 1, 3)``. Columnas en orden
        ``[MUERTA, LATENTE, ACTIVA]`` (coinciden con los valores de estado). La
        desviación es la **muestral** (``ddof=1``); es 0 si `n_corridas == 1`.
    n_corridas : int
        Número de réplicas agregadas.
    semillas : list[int] | None
        Semillas explícitas usadas, si se pasaron.
    semilla_base : int | None
        Semilla base usada para `SeedSequence.spawn`, si no se pasó lista.
    corridas : list[ResultadoSimulacion] | None
        Las N corridas crudas si se pidió `guardar_corridas` (para la validación
        de convergencia de Hito 4); si no, `None`.
    """

    media: np.ndarray
    desviacion: np.ndarray
    n_corridas: int
    semillas: list[int] | None = None
    semilla_base: int | None = None
    corridas: list[ResultadoSimulacion] | None = None

    def __len__(self) -> int:
        return int(self.media.shape[0])

    def curva(self, estado: int) -> tuple[np.ndarray, np.ndarray]:
        """(media, desviación) por tick de la fracción del estado dado.

        `estado` es `MUERTA`, `LATENTE` o `ACTIVA`.
        """
        return self.media[:, estado], self.desviacion[:, estado]


def simular_montecarlo(
    construir_modo: Callable[[np.random.Generator], ModoSimulacion],
    especie: Microorganismo,
    estado_inicial: np.ndarray | Callable[[np.random.Generator], np.ndarray],
    *,
    n_corridas: int = 30,
    semilla: int | None = None,
    semillas: Sequence[int] | None = None,
    construir_eventos: (
        Callable[[np.random.Generator], Sequence[EventoEstocastico]] | None
    ) = None,
    re_sembrar: bool = False,
    n_iteraciones: int | None = None,
    regla: ReglaTransicion | None = None,
    dt: float = 1.0,
    borde: str = "muerta",
    guardar_corridas: bool = False,
) -> ResultadoMontecarlo:
    """Corre N réplicas independientes de `simular` y agrega media ± desviación.

    Cada réplica recibe instancias **frescas** del modo y de los eventos (vía las
    factories), porque el modo lleva su propio `rng` y algunos eventos tienen
    estado interno (`SalmueraDelicuescente`); reusar instancias filtraría estado
    entre corridas. Los flujos aleatorios de cada réplica salen de una
    `SeedSequence` propia, así que **la misma base da el mismo agregado**.

    Parameters
    ----------
    construir_modo : Callable[[np.random.Generator], ModoSimulacion]
        Factory que arma un modo fresco por réplica, con el `rng` inyectado (lo
        usa, p. ej., el `ModoAnalogico` para la dispersión de `A_w`).
    especie : Microorganismo
        Especie simulada (igual en todas las réplicas).
    estado_inicial : np.ndarray | Callable[[np.random.Generator], np.ndarray]
        Estado inicial. Si es un arreglo, es **fijo** para todas las réplicas. Si
        es una factory `construir_estado(rng)`, se combina con `re_sembrar`.
    n_corridas : int
        Número de réplicas (default 30). Se ignora si se pasa `semillas`.
    semilla : int, optional
        Semilla base; se derivan `n_corridas` flujos con
        `SeedSequence(semilla).spawn(...)`.
    semillas : Sequence[int], optional
        Lista explícita de semillas (una por réplica); **tiene prioridad** sobre
        `semilla`/`n_corridas`.
    construir_eventos : Callable[[np.random.Generator], Sequence[EventoEstocastico]], optional
        Factory de eventos frescos por réplica. El `rng` se provee por uniformidad,
        pero los eventos reciben su aleatoriedad por tick del `rng` de `simular`,
        así que suele ir sin usar. Default sin eventos.
    re_sembrar : bool
        Solo aplica si `estado_inicial` es una factory. `False` (default): se
        llama **una vez** y el mismo estado se usa en todas las réplicas (la
        distribución mide solo la dinámica estocástica). `True`: se llama por
        réplica (la distribución también captura la incertidumbre del arranque).
    n_iteraciones, regla, dt, borde : ...
        Se pasan tal cual a cada `simular` (iguales en todas las réplicas).
    guardar_corridas : bool
        Si es `True`, conserva las N `ResultadoSimulacion` crudas.

    Returns
    -------
    ResultadoMontecarlo
    """
    if semillas is not None:
        semillas_out: list[int] | None = [int(s) for s in semillas]
        run_seqs = [np.random.SeedSequence(s) for s in semillas_out]
        setup_seq = np.random.SeedSequence(semillas_out)  # entropía ≠ a cada s_i
        semilla_base: int | None = None
    else:
        if n_corridas < 1:
            raise ValueError("n_corridas debe ser >= 1")
        spawn = np.random.SeedSequence(semilla).spawn(n_corridas + 1)
        run_seqs = list(spawn[:n_corridas])
        setup_seq = spawn[n_corridas]  # flujo aparte, no colisiona con las réplicas
        semillas_out = None
        semilla_base = semilla
    n = len(run_seqs)

    es_factory = callable(estado_inicial)
    if re_sembrar and not es_factory:
        raise ValueError(
            "re_sembrar=True requiere que `estado_inicial` sea una factory "
            "construir_estado(rng), no un arreglo fijo."
        )

    estado_fijo: np.ndarray | None = None
    if not re_sembrar:
        estado_fijo = (
            np.asarray(estado_inicial(np.random.default_rng(setup_seq)), dtype=np.int8)
            if es_factory
            else np.asarray(estado_inicial, dtype=np.int8)
        )

    fracciones: list[np.ndarray] = []
    corridas: list[ResultadoSimulacion] = []
    longitud: int | None = None

    for ss in run_seqs:
        rng_modo, rng_eventos, rng_estado, rng_dinamica = (
            np.random.default_rng(hijo) for hijo in ss.spawn(4)
        )
        modo = construir_modo(rng_modo)
        eventos = construir_eventos(rng_eventos) if construir_eventos is not None else ()
        estado = estado_inicial(rng_estado) if re_sembrar else estado_fijo

        resultado = simular(
            modo,
            especie,
            estado,
            rng_dinamica,
            n_iteraciones=n_iteraciones,
            eventos=eventos,
            regla=regla,
            dt=dt,
            borde=borde,
        )
        if longitud is None:
            longitud = len(resultado)
        elif len(resultado) != longitud:
            raise ValueError(
                "todas las réplicas deben tener el mismo nº de ticks; fijá "
                "`n_iteraciones` para modos infinitos (Sandbox/estático)."
            )
        fracciones.append(resultado.fracciones())
        if guardar_corridas:
            corridas.append(resultado)

    apilado = np.stack(fracciones, axis=0)  # (N, n+1, 3)
    media = apilado.mean(axis=0)
    desviacion = (
        apilado.std(axis=0, ddof=1) if n > 1 else np.zeros_like(media)
    )

    return ResultadoMontecarlo(
        media=media,
        desviacion=desviacion,
        n_corridas=n,
        semillas=semillas_out,
        semilla_base=semilla_base,
        corridas=corridas if guardar_corridas else None,
    )
