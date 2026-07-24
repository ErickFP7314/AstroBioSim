"""Interfaz común de los modos de simulación (dueño: Fidel/Erick).

Un **modo** es un proveedor de campos ambientales: sabe entregar un
`CampoAmbiental` por tick. El orquestador (`simulation.py`, dueño Erick) itera
sobre `campos()` sin saber de dónde salen, de modo que el Modo Analógico (serie
real) y el Modo Sandbox (parámetros/sliders) comparten **el mismo bucle** (DRY):
el orquestador no se ramifica por modo.

Esto es la frontera entre `data/`+`modes/` y el orquestador. Cualquier modo nuevo
solo tiene que cumplir este `Protocol`.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from astrobiosim.core.environment import CampoAmbiental


@runtime_checkable
class ModoSimulacion(Protocol):
    """Contrato mínimo de un modo: entrega una secuencia de campos por tick."""

    def campos(self) -> Iterator[CampoAmbiental]:
        """Devuelve un iterador de `CampoAmbiental`, uno por tick de la corrida."""
        ...
