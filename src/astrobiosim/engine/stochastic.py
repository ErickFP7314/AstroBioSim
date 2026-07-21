"""Eventos estocásticos — contrato de frontera §3.4 (dueño: Jose).

STUB de Hito 0. Los eventos concretos (`MicroFisuraMarte`,
`EmisionHidrotermalEncelado`) van en `feat/engine-estocastico`.
"""
from __future__ import annotations

from abc import ABC

import numpy as np

from astrobiosim.core.environment import CampoAmbiental


class EventoEstocastico(ABC):
    """Perturbación aleatoria que actúa SOLO sobre el campo ambiental."""

    def aplicar(
        self, campo: CampoAmbiental, rng: np.random.Generator
    ) -> CampoAmbiental:
        """Perturba y devuelve el campo (NO toca el estado biológico).

        Toda aleatoriedad usa el `rng` inyectado; nunca `np.random` global.
        """
        raise NotImplementedError("Jose: implementar en feat/engine-estocastico (§3.4)")
