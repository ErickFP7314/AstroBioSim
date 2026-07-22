"""Eventos estocásticos — contrato de frontera §3.4 (dueño: Jose).

Los eventos concretos (`MicroFisuraMarte`, `EmisionHidrotermalEncelado`)
perturban SOLO el `CampoAmbiental` (nunca el estado biológico) y usan
exclusivamente el `rng` inyectado, nunca `np.random` global, para que la
simulación sea reproducible con una semilla fija.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from astrobiosim.core.environment import CampoAmbiental


class EventoEstocastico(ABC):
    """Perturbación aleatoria que actúa SOLO sobre el campo ambiental."""

    @abstractmethod
    def aplicar(
        self, campo: CampoAmbiental, rng: np.random.Generator
    ) -> CampoAmbiental:
        """Perturba y devuelve el campo (NO toca el estado biológico).

        Toda aleatoriedad usa el `rng` inyectado; nunca `np.random` global.
        """
        raise NotImplementedError


class MicroFisuraMarte(EventoEstocastico):
    """Desecación puntual del regolito marciano por una micro-fisura.

    Con probabilidad `probabilidad_disparo` por tick, se abre una fisura en
    una celda al azar de la grilla: `A_w` cae dentro de un radio de celdas
    por un factor muestreado uniformemente en
    [`caida_min`, `caida_max`] (fracción de A_w perdida). `T` y `R` no se
    tocan: la fisura libera vapor de agua, no cambia temperatura ni radiación.

    Parameters
    ----------
    probabilidad_disparo : float
        Probabilidad de que el evento ocurra en un tick dado (Bernoulli).
    radio_celdas : float
        Radio (en celdas) del área afectada por la desecación.
    caida_min, caida_max : float
        Rango de la fracción de `A_w` perdida dentro del radio (0..1).
    """

    def __init__(
        self,
        probabilidad_disparo: float = 0.05,
        radio_celdas: float = 3.0,
        caida_min: float = 0.3,
        caida_max: float = 0.7,
    ) -> None:
        self.probabilidad_disparo = probabilidad_disparo
        self.radio_celdas = radio_celdas
        self.caida_min = caida_min
        self.caida_max = caida_max

    def aplicar(
        self, campo: CampoAmbiental, rng: np.random.Generator
    ) -> CampoAmbiental:
        if rng.random() >= self.probabilidad_disparo:
            return campo

        m, n = campo.shape
        fila0 = rng.integers(0, m)
        col0 = rng.integers(0, n)
        intensidad = rng.uniform(self.caida_min, self.caida_max)

        filas, cols = np.indices((m, n), dtype=float)
        dist = np.sqrt((filas - fila0) ** 2 + (cols - col0) ** 2)
        dentro_del_radio = dist <= self.radio_celdas

        A_w_nuevo = campo.A_w.copy()
        A_w_nuevo[dentro_del_radio] *= 1.0 - intensidad
        A_w_nuevo = np.clip(A_w_nuevo, 0.0, 1.0)

        return CampoAmbiental(T=campo.T.copy(), R=campo.R.copy(), A_w=A_w_nuevo)


class EmisionHidrotermalEncelado(EventoEstocastico):
    """Pico de temperatura de una ventila hidrotermal que se disipa radialmente.

    Con probabilidad `probabilidad_disparo` por tick, una ventila en una
    posición al azar de la grilla emite un pico `ΔT ~ N(mu_delta_t,
    sigma_delta_t²)` que se suma a `T` con un kernel gaussiano de difusión de
    calor (decae con la distancia, alcance controlado por `sigma_espacial`).
    `A_w` y `R` no se tocan: es un evento puramente térmico.

    Parameters
    ----------
    probabilidad_disparo : float
        Probabilidad de que el evento ocurra en un tick dado (Bernoulli).
    mu_delta_t, sigma_delta_t : float
        Media y desvío del pico de temperatura ΔT (°C) en el centro de la ventila.
    sigma_espacial : float
        Radio de decaimiento (en celdas) del kernel gaussiano de disipación.
    """

    def __init__(
        self,
        probabilidad_disparo: float = 0.1,
        mu_delta_t: float = 25.0,
        sigma_delta_t: float = 5.0,
        sigma_espacial: float = 4.0,
    ) -> None:
        self.probabilidad_disparo = probabilidad_disparo
        self.mu_delta_t = mu_delta_t
        self.sigma_delta_t = sigma_delta_t
        self.sigma_espacial = sigma_espacial

    def aplicar(
        self, campo: CampoAmbiental, rng: np.random.Generator
    ) -> CampoAmbiental:
        if rng.random() >= self.probabilidad_disparo:
            return campo

        m, n = campo.shape
        fila0 = rng.integers(0, m)
        col0 = rng.integers(0, n)
        delta_pico = rng.normal(self.mu_delta_t, self.sigma_delta_t)

        filas, cols = np.indices((m, n), dtype=float)
        d2 = (filas - fila0) ** 2 + (cols - col0) ** 2
        kernel = np.exp(-d2 / (2 * self.sigma_espacial**2))

        T_nuevo = campo.T + delta_pico * kernel
        return CampoAmbiental(T=T_nuevo, R=campo.R.copy(), A_w=campo.A_w.copy())
