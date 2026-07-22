"""Campo ambiental — contrato de frontera §3.1 (dueño: Jose).

Además del contrato (`CampoAmbiental`), este módulo define la jerarquía
`PlanetaSubsuelo` que construye el campo **inicial** (t=0) de cada entorno para
el Modo Sandbox. Es un modelo teórico calibrado con los datasets reales 2025
(Tierra: Valles de Fresno; Marte: Atacama CRC1211DB; Encelado: ventilas
hidrotermales — ver ADR-0010/0011), NO el pipeline de datos históricos fila a
fila (eso es `data/resampling.secuencia_campos`, dueño Fidel, Modo Analógico).

Convención de grilla (M, N): la fila 0 es la superficie; el eje de filas (M)
representa profundidad creciente. Para Encelado, sin embargo, la grilla es un
corte horizontal cerca del piso oceánico (no hay "profundidad" vertical
relevante), por eso su campo usa un kernel radial en vez del eje de filas.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class CampoAmbiental:
    """Tres capas escalares alineadas a la grilla M×N. Todas la misma forma.

    Parameters
    ----------
    T : np.ndarray
        Temperatura (°C), shape (M, N).
    R : np.ndarray
        Radiación: flujo (W/m²), proxy operativo — ver ADR-0010; shape (M, N).
    A_w : np.ndarray
        Actividad de agua (0..1), shape (M, N).
    """

    T: np.ndarray
    R: np.ndarray
    A_w: np.ndarray

    def __post_init__(self) -> None:
        self.T = np.asarray(self.T, dtype=float)
        self.R = np.asarray(self.R, dtype=float)
        self.A_w = np.asarray(self.A_w, dtype=float)
        if not (self.T.shape == self.R.shape == self.A_w.shape):
            raise ValueError(
                "T, R y A_w deben tener la misma forma (M, N); recibido "
                f"T={self.T.shape}, R={self.R.shape}, A_w={self.A_w.shape}"
            )

    @property
    def shape(self) -> tuple[int, int]:
        """Forma (M, N) de las capas."""
        return self.T.shape


class PlanetaSubsuelo(ABC):
    """Entorno base: construye el `CampoAmbiental` inicial de un subsuelo planetario.

    Parameters
    ----------
    shape : tuple[int, int]
        Dimensiones (M, N) de la grilla. Default 50×50 (sin restricción física
        particular; ajustable por instancia).
    """

    def __init__(self, shape: tuple[int, int] = (50, 50)) -> None:
        self.shape = shape

    @property
    def _profundidad(self) -> np.ndarray:
        """Índice de profundidad por fila (0..M-1), shape (M, 1) para broadcast."""
        m, _ = self.shape
        return np.arange(m, dtype=float).reshape(m, 1)

    @abstractmethod
    def campo_inicial(self) -> CampoAmbiental:
        """Construye el `CampoAmbiental` en t=0 de este entorno."""
        raise NotImplementedError


class TierraSubsuelo(PlanetaSubsuelo):
    """Subsuelo terrestre de control: térmicamente estable, húmedo, sin radiación.

    A la profundidad de un subsuelo somero (control) la señal diurna ya está
    amortiguada casi por completo, así que se modela como un campo uniforme.
    """

    T_SUBSUELO_C: float = 15.0  # estable; entre el mínimo y la media anual de Fresno
    A_W_ALTA: float = 0.75  # dentro del rango real (0.16..0.93), franja alta
    R_SUBSUELO: float = 0.0  # el suelo bloquea la radiación solar incidente

    def campo_inicial(self) -> CampoAmbiental:
        m, n = self.shape
        T = np.full((m, n), self.T_SUBSUELO_C)
        R = np.full((m, n), self.R_SUBSUELO)
        A_w = np.full((m, n), self.A_W_ALTA)
        return CampoAmbiental(T=T, R=R, A_w=A_w)


class MarteSubsuelo(PlanetaSubsuelo):
    """Regolito marciano (análogo Atacama): gradiente térmico y radiativo con la profundidad.

    Modela la onda térmica diurna amortiguándose exponencialmente con la
    profundidad hacia una temperatura de equilibrio más fría (modelo estándar
    de skin depth en regolito). `T_SUPERFICIE`/`T_PROFUNDO` son la media real de
    los máximos/mínimos diarios de Atacama (CRC1211DB, ADR-0010). La radiación
    decae mucho más rápido que el calor porque la luz no penetra el regolito
    más allá de una capa muy fina (`ESCALA_RADIATIVA` << `ESCALA_TERMICA`).
    """

    T_SUPERFICIE_C: float = 36.9  # media de Temp_Maxima_Superficie_C (Atacama 2025)
    T_PROFUNDO_C: float = 7.8  # media de Temp_Minima_Superficie_C (asíntota fría)
    R_SUPERFICIE: float = 844.0  # media de Radiacion_Solar_Maxima_W_m2 (Atacama 2025)
    A_W_BAJA: float = 0.187  # media de Actividad_Agua_Minima_aw (Atacama 2025)

    def __init__(
        self,
        shape: tuple[int, int] = (50, 50),
        escala_termica: float | None = None,
        escala_radiativa: float | None = None,
    ) -> None:
        super().__init__(shape)
        m, _ = shape
        self.escala_termica = escala_termica if escala_termica is not None else m / 6
        self.escala_radiativa = (
            escala_radiativa if escala_radiativa is not None else self.escala_termica / 4
        )

    def campo_inicial(self) -> CampoAmbiental:
        m, n = self.shape
        z = self._profundidad  # (M, 1), broadcast a (M, N)
        T = self.T_PROFUNDO_C + (self.T_SUPERFICIE_C - self.T_PROFUNDO_C) * np.exp(
            -z / self.escala_termica
        )
        R = self.R_SUPERFICIE * np.exp(-z / self.escala_radiativa)
        T = np.broadcast_to(T, (m, n)).copy()
        R = np.broadcast_to(R, (m, n)).copy()
        A_w = np.full((m, n), self.A_W_BAJA)
        return CampoAmbiental(T=T, R=R, A_w=A_w)


class EnceladoSubglacial(PlanetaSubsuelo):
    """Océano subglacial de Encelado: fondo frío + picos hidrotermales localizados.

    `T_OCEANO`/`A_W_OCEANO` son la media real de las ventilas (ADR-0010/0011).
    `R=0` en toda la grilla: el hielo blinda por completo la radiación externa
    (ADR-0008) y el IR de las ventilas es calor, no dosis ionizante. Las
    fumarolas son fuentes puntuales cuyo pico de temperatura decae radialmente
    con un kernel gaussiano (mismo modelo que usa el evento estocástico
    `EmisionHidrotermalEncelado`, pero fijo en vez de aleatorio).
    """

    T_OCEANO_C: float = 2.4  # media de Temp_Ventila_C (ventilas 2025)
    A_W_OCEANO: float = 0.98  # media de Actividad_Agua_aw (ventilas 2025)
    R_ENCELADO: float = 0.0  # protección total del hielo (ADR-0008/0010)
    DELTA_T_FUMAROLA: float = 25.0  # pico sobre el fondo; cerca del óptimo de M. burtonii (~23°C)
    SIGMA_ESPACIAL: float = 4.0  # radio de decaimiento gaussiano, en celdas

    #: Posiciones de fumarolas como fracción (fila, col) de la grilla.
    FUMAROLAS_FRACCION: tuple[tuple[float, float], ...] = (
        (0.3, 0.3),
        (0.5, 0.7),
        (0.7, 0.4),
    )

    def campo_inicial(self) -> CampoAmbiental:
        m, n = self.shape
        filas, cols = np.indices((m, n), dtype=float)
        T = np.full((m, n), self.T_OCEANO_C)
        for frac_fila, frac_col in self.FUMAROLAS_FRACCION:
            f0 = frac_fila * (m - 1)
            c0 = frac_col * (n - 1)
            d2 = (filas - f0) ** 2 + (cols - c0) ** 2
            T = T + self.DELTA_T_FUMAROLA * np.exp(-d2 / (2 * self.SIGMA_ESPACIAL**2))
        R = np.full((m, n), self.R_ENCELADO)
        A_w = np.full((m, n), self.A_W_OCEANO)
        return CampoAmbiental(T=T, R=R, A_w=A_w)
