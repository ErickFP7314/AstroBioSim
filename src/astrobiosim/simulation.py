"""Orquestador de la simulación (dueño: Erick) — punto de unión de los motores.

`simular` corre el bucle principal: por cada tick toma un `CampoAmbiental` del
**modo** (Analógico, Sandbox, estático…), le aplica los **eventos estocásticos**
de Jose, avanza el autómata con `paso` y registra el **historial poblacional**.
No conoce de dónde salen los campos (itera cualquier `ModoSimulacion`), así que
todos los modos comparten este único bucle (DRY, ADR-0017).

Invariantes: actualización síncrona (delega en `paso`, doble buffer), aleatoriedad
**solo** vía el `rng` inyectado (misma semilla ⇒ misma corrida), y no muta el
`estado_inicial` recibido.
"""
from __future__ import annotations

from collections.abc import Sequence
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
        lado = max(1, min(int(round((fraccion_activa * m * n) ** 0.5)), m, n))
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
