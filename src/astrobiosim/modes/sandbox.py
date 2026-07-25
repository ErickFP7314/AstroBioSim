"""Modo Sandbox — parámetros ambientales estáticos/ajustables (dueña: Esmeralda).

Construye un `CampoAmbiental` homogéneo M×N a partir de T, R (irradiancia UV,
ADR-0014) y A_w fijados manualmente, sin depender de ningún dataset. Es el
proveedor de campos más simple posible: sin estructura espacial propia (a
diferencia de `PlanetaSubsuelo`) ni serie temporal (a diferencia de
`ModoAnalogico`) — solo repite, tick a tick, el campo construido con los
parámetros vigentes.

Como el resto de los modos, `ModoSandbox` solo implementa `campos()` (protocolo
`ModoSimulacion` de `modes/base`): el orquestador (`simulation.simular`) es
quien itera y aplica eventos/autómata. No hay un segundo bucle temporal acá
(DRY, ADR-0017) — Analógico y Sandbox comparten el mismo `simular()`.

Los parámetros son ajustables en caliente vía `set_parametros`: cada tick de
`campos()` reconstruye el campo con los valores vigentes en ese momento, así
que una UI de sliders (dueño Erick) puede mover T/R/A_w entre ticks de una
corrida en curso (ADR-0003: "en Modo Sandbox las capas son homogéneas, o
editadas por sliders").
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np

from astrobiosim.core.environment import CampoAmbiental


class ModoSandbox:
    """Campo ambiental homogéneo fijado manualmente (sin dataset).

    Parameters
    ----------
    shape : tuple[int, int]
        Dimensiones (M, N) de la grilla.
    T : float
        Temperatura (°C), uniforme en toda la grilla.
    R : float
        Irradiancia UV (W/m²) — ADR-0014, uniforme en toda la grilla. No
        puede ser negativa.
    A_w : float
        Actividad de agua (0..1), uniforme en toda la grilla.
    """

    def __init__(
        self,
        shape: tuple[int, int] = (50, 50),
        *,
        T: float,
        R: float,
        A_w: float,
    ) -> None:
        self._shape = shape
        self.set_parametros(T=T, R=R, A_w=A_w)

    def set_parametros(
        self,
        *,
        T: float | None = None,
        R: float | None = None,
        A_w: float | None = None,
    ) -> None:
        """Actualiza los parámetros vigentes (ajuste en caliente, p. ej. sliders).

        Solo cambian los parámetros provistos; los demás conservan su valor
        actual. El efecto se ve a partir del próximo `CampoAmbiental` que
        entregue `campos()` — no altera los ya entregados.
        """
        if T is not None:
            self._T = float(T)
        if R is not None:
            if R < 0:
                raise ValueError(f"R (irradiancia UV) no puede ser negativa: {R!r}")
            self._R = float(R)
        if A_w is not None:
            if not 0.0 <= A_w <= 1.0:
                raise ValueError(f"A_w debe estar en [0, 1]: {A_w!r}")
            self._A_w = float(A_w)

    @property
    def parametros(self) -> tuple[float, float, float]:
        """Valores vigentes `(T, R, A_w)`."""
        return self._T, self._R, self._A_w

    def campo_actual(self) -> CampoAmbiental:
        """Construye el `CampoAmbiental` homogéneo con los parámetros vigentes."""
        m, n = self._shape
        return CampoAmbiental(
            T=np.full((m, n), self._T),
            R=np.full((m, n), self._R),
            A_w=np.full((m, n), self._A_w),
        )

    def campos(self) -> Iterator[CampoAmbiental]:
        """Un `CampoAmbiental` por tick, reconstruido con los parámetros vigentes.

        Es infinito, como `ModoEstatico`: el orquestador acota la corrida con
        `n_iteraciones`.
        """
        while True:
            yield self.campo_actual()

    def __iter__(self) -> Iterator[CampoAmbiental]:
        return self.campos()
