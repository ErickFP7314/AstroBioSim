"""Campo ambiental — contrato de frontera §3.1 (dueño: Jose).

Además del contrato (`CampoAmbiental`), este módulo define la jerarquía
`PlanetaSubsuelo` que construye el campo **inicial** (t=0) de cada entorno para
el Modo Sandbox. Es un modelo teórico calibrado con los datasets reales 2025
(Tierra: Valles de Fresno; Marte: Atacama CRC1211DB; Encelado: ventilas
hidrotermales — ver ADR-0010/0011), NO el pipeline de datos históricos fila a
fila (eso es `data/resampling.secuencia_campos`, dueño Fidel, Modo Analógico).

`R` es **irradiancia UV en W/m²** (ADR-0014), no flujo radiativo total ni dosis
ionizante. El cambio importa: la insolación global es mayoritariamente visible e
infrarroja y no esteriliza, mientras que el UV sí, y además se atenúa en el
regolito mucho más rápido que el calor. Eso hace que el eje de profundidad tenga
significado biológico: existe una **profundidad mínima de seguridad UV**.

Convención de grilla (M, N): la fila 0 es la superficie; el eje de filas (M)
representa profundidad creciente. Para Encelado, sin embargo, la grilla es un
corte horizontal cerca del piso oceánico (no hay "profundidad" vertical
relevante), por eso su campo usa un kernel radial en vez del eje de filas.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

#: Fracción UV (UV-A + UV-B) de la irradiancia solar global. Se documenta acá,
#: y no escondida dentro de un entorno, porque es el factor de conversión que
#: ADR-0014 exige dejar explícito.
FRACCION_UV: float = 0.05


@dataclass
class CampoAmbiental:
    """Tres capas escalares alineadas a la grilla M×N. Todas la misma forma.

    Parameters
    ----------
    T : np.ndarray
        Temperatura (°C), shape (M, N).
    R : np.ndarray
        Irradiancia UV (W/m²) — ver ADR-0014; shape (M, N).
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
    def campo_inicial(self, rng: np.random.Generator | None = None) -> CampoAmbiental:
        """Construye el `CampoAmbiental` en t=0 de este entorno.

        Parameters
        ----------
        rng : np.random.Generator, optional
            Generador inyectado (regla de oro nº6). Si es `None` el campo es
            determinista y usa solo los valores medios; si se provee, los
            entornos que declaran dispersión la muestrean con él (ADR-0015).
        """
        raise NotImplementedError


class TierraSubsuelo(PlanetaSubsuelo):
    """Subsuelo terrestre de control: térmicamente estable, húmedo, sin UV.

    A la profundidad de un subsuelo somero la señal diurna ya está amortiguada
    casi por completo, así que se modela como un campo uniforme a la **media
    anual** del dataset (19.85 °C), que es el valor al que amortigua la onda
    térmica.

    **Corrección (ADR-0014 y nota de datos):** la columna `Actividad_Agua_aw`
    del dataset de control (media 0.55, rango 0.16–0.93, sd 0.23) es **humedad
    relativa del aire**, no actividad de agua del suelo — su origen es el
    `A_w = HR / 100` que documentó ADR-0008, y un suelo no puede oscilar así de
    un día para otro. Para un modelo de **subsuelo** el valor correcto es el de
    un suelo a capacidad de campo, `a_w ≈ 0.99`. El 0.75 anterior hacía que
    *E. coli* —cuyo mínimo de 0.95 es un dato duro— no creciera en su propio
    control.
    """

    T_SUBSUELO_C: float = 19.8  # media anual del dataset (la onda diurna amortigua acá)
    A_W_SUBSUELO: float = 0.99  # suelo a capacidad de campo (NO la HR del aire)
    UV_SUBSUELO: float = 0.0  # el suelo bloquea el UV por completo

    def campo_inicial(self, rng: np.random.Generator | None = None) -> CampoAmbiental:
        m, n = self.shape
        T = np.full((m, n), self.T_SUBSUELO_C)
        R = np.full((m, n), self.UV_SUBSUELO)
        A_w = np.full((m, n), self.A_W_SUBSUELO)
        return CampoAmbiental(T=T, R=R, A_w=A_w)


class MarteSubsuelo(PlanetaSubsuelo):
    """Regolito marciano (análogo Atacama): gradientes térmico y UV con la profundidad.

    Modela la onda térmica diurna amortiguándose exponencialmente con la
    profundidad hacia una temperatura de equilibrio más fría (modelo estándar de
    skin depth en regolito). El **UV** se atenúa mucho más rápido que el calor
    (`RAZON_ATENUACION_UV`): el regolito lo extingue en milímetros a
    centímetros, así que basta con bajar unas pocas celdas para que deje de ser
    limitante. Ese es el borde superior de la ventana habitable marciana de
    ADR-0015; el inferior lo pone la disponibilidad de agua.

    **Sesgo de muestreo corregido (ADR-0015):** la única columna disponible es
    `Actividad_Agua_Minima_aw`, es decir el **mínimo diario** — una cota
    inferior pesimista, no el valor típico. Colapsarlo a una constante
    garantizaba la extinción. Acá se conserva como media con su dispersión real
    (sd = 0.080; el máximo observado de la serie llega a 0.518) y la
    heterogeneidad espacial la genera el modelo cuando se le inyecta un `rng`.
    Queda pendiente que Fidel re-extraiga la `a_w` **media**, no la mínima.
    """

    T_SUPERFICIE_C: float = 36.9  # media de Temp_Maxima_Superficie_C (Atacama 2025)
    T_PROFUNDO_C: float = 7.8  # media de Temp_Minima_Superficie_C (asíntota fría)
    RADIACION_GLOBAL_W_M2: float = 844.2  # media de Radiacion_Solar_Maxima_W_m2
    UV_SUPERFICIE: float = RADIACION_GLOBAL_W_M2 * FRACCION_UV  # ≈ 42.2 W/m²
    A_W_MEDIA: float = 0.187  # media del MÍNIMO diario (cota inferior, ver docstring)
    A_W_SIGMA: float = 0.080  # dispersión real de esa serie (ADR-0015)

    #: El UV se atenúa esta cantidad de veces más rápido que el calor.
    RAZON_ATENUACION_UV: float = 10.0

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
            escala_radiativa
            if escala_radiativa is not None
            else self.escala_termica / self.RAZON_ATENUACION_UV
        )

    def campo_inicial(self, rng: np.random.Generator | None = None) -> CampoAmbiental:
        m, n = self.shape
        z = self._profundidad  # (M, 1), broadcast a (M, N)
        T = self.T_PROFUNDO_C + (self.T_SUPERFICIE_C - self.T_PROFUNDO_C) * np.exp(
            -z / self.escala_termica
        )
        R = self.UV_SUPERFICIE * np.exp(-z / self.escala_radiativa)
        T = np.broadcast_to(T, (m, n)).copy()
        R = np.broadcast_to(R, (m, n)).copy()

        A_w = np.full((m, n), self.A_W_MEDIA)
        if rng is not None:
            A_w = A_w + rng.normal(0.0, self.A_W_SIGMA, size=(m, n))
        A_w = np.clip(A_w, 0.0, 1.0)
        return CampoAmbiental(T=T, R=R, A_w=A_w)


class EnceladoSubglacial(PlanetaSubsuelo):
    """Océano subglacial de Encelado: fondo frío + picos hidrotermales localizados.

    `T_OCEANO`/`A_W_OCEANO` son la media real de las ventilas (ADR-0010/0011).
    `R = 0` en toda la grilla: el hielo blinda por completo la radiación externa
    y los ~320 W/m² de `Radiacion_Infrarroja_W_m2` del dataset son **calor**, no
    UV ni dosis ionizante (ADR-0014), así que no entran en el campo `R`. Las
    fumarolas son fuentes puntuales cuyo pico de temperatura decae radialmente
    con un kernel gaussiano (mismo modelo que usa el evento estocástico
    `EmisionHidrotermalEncelado`, pero fijo en vez de aleatorio).

    **Corrección de artefacto de resolución:** el radio de decaimiento estaba
    fijado en celdas, así que en grillas chicas las tres fumarolas se solapaban
    y sus gaussianas se sumaban hasta 43 °C — un pico que no viene de la física
    sino del tamaño de la grilla, y que además sacaba a *M. burtonii* de su
    `t_max`. Ahora el radio es una **fracción de la grilla**
    (`SIGMA_FRACCION`), de modo que el campo es equivalente a cualquier
    resolución; a la grilla por defecto (50×50) da los mismos 4.0 de antes.
    """

    T_OCEANO_C: float = 2.4  # media de Temp_Ventila_C (ventilas 2025)
    A_W_OCEANO: float = 0.98  # media de Actividad_Agua_aw (ventilas 2025)
    UV_ENCELADO: float = 0.0  # blindaje total del hielo (ADR-0008/0014)
    #: Pico sobre el fondo oceánico. El máximo resultante (~27.4 °C) queda bajo
    #: el `t_max = 29.5` de *M. burtonii*, así que los núcleos de fumarola son
    #: habitables: la vida se agrupa en las ventilas, no las evita (ADR-0011).
    DELTA_T_FUMAROLA: float = 25.0
    #: Radio de decaimiento gaussiano, como fracción del lado menor de la grilla.
    #: A 50×50 (default) equivale a los 4.0 celdas originales.
    SIGMA_FRACCION: float = 0.08

    #: Posiciones de fumarolas como fracción (fila, col) de la grilla.
    FUMAROLAS_FRACCION: tuple[tuple[float, float], ...] = (
        (0.3, 0.3),
        (0.5, 0.7),
        (0.7, 0.4),
    )

    @property
    def sigma_espacial(self) -> float:
        """Radio de decaimiento en celdas, proporcional al tamaño de la grilla."""
        m, n = self.shape
        return self.SIGMA_FRACCION * min(m, n)

    def campo_inicial(self, rng: np.random.Generator | None = None) -> CampoAmbiental:
        m, n = self.shape
        filas, cols = np.indices((m, n), dtype=float)
        sigma = self.sigma_espacial
        T = np.full((m, n), self.T_OCEANO_C)
        for frac_fila, frac_col in self.FUMAROLAS_FRACCION:
            f0 = frac_fila * (m - 1)
            c0 = frac_col * (n - 1)
            d2 = (filas - f0) ** 2 + (cols - c0) ** 2
            T = T + self.DELTA_T_FUMAROLA * np.exp(-d2 / (2 * sigma**2))
        R = np.full((m, n), self.UV_ENCELADO)
        A_w = np.full((m, n), self.A_W_OCEANO)
        return CampoAmbiental(T=T, R=R, A_w=A_w)
