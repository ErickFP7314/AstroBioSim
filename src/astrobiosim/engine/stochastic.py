"""Eventos estocásticos — contrato de frontera §3.4 (dueño: Jose).

Los eventos concretos (`MicroFisuraMarte`, `EmisionHidrotermalEncelado`,
`SalmueraDelicuescente`) perturban SOLO el `CampoAmbiental` (nunca el estado
biológico) y usan exclusivamente el `rng` inyectado, nunca `np.random`
global, para que la simulación sea reproducible con una semilla fija.
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

        `campo` es de **solo lectura**: la implementación NUNCA lo muta in
        situ y **siempre** devuelve un `CampoAmbiental` nuevo (una copia),
        también en los ticks donde el evento no dispara. Devolver el mismo
        objeto de entrada cuando no hay disparo es un aliasing que, si quien
        encadena eventos muta el resultado, corrompería el campo original de
        forma intermitente (depende de la semilla) — la peor clase de bug.
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
            return CampoAmbiental(T=campo.T.copy(), R=campo.R.copy(), A_w=campo.A_w.copy())

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
            return CampoAmbiental(T=campo.T.copy(), R=campo.R.copy(), A_w=campo.A_w.copy())

        m, n = campo.shape
        fila0 = rng.integers(0, m)
        col0 = rng.integers(0, n)
        delta_pico = rng.normal(self.mu_delta_t, self.sigma_delta_t)

        filas, cols = np.indices((m, n), dtype=float)
        d2 = (filas - fila0) ** 2 + (cols - col0) ** 2
        kernel = np.exp(-d2 / (2 * self.sigma_espacial**2))

        T_nuevo = campo.T + delta_pico * kernel
        return CampoAmbiental(T=T_nuevo, R=campo.R.copy(), A_w=campo.A_w.copy())


class SalmueraDelicuescente(EventoEstocastico):
    """Microrefugio húmedo transitorio (ADR-0015): contraparte de `MicroFisuraMarte`.

    Hasta ADR-0015 todos los eventos degradaban el ambiente, lo que sesgaba
    toda corrida hacia la extinción por construcción. Este evento modela el
    efecto observable de una salmuera delicuescente (percloratos en Marte,
    nódulos de halita en Atacama) **sin comprometerse con el mecanismo
    químico** (alternativa 3 de ADR-0015): con probabilidad
    `probabilidad_disparo` por tick, eleva `A_w` dentro de un radio de celdas
    hacia un `a_w_objetivo` muestreado del `rng`, y ese refugio se **disipa
    exponencialmente** con el tiempo hasta desvanecerse.

    A diferencia de `MicroFisuraMarte` y `EmisionHidrotermalEncelado`, que son
    instantáneos, este evento necesita **estado interno** (la lista de
    refugios activos, con su edad) porque el contrato §3.4 no pasa el número
    de tick a `aplicar()`. Eso tiene una consecuencia importante para quien
    orqueste corridas independientes (p. ej. un barrido Montecarlo, ADR-0015
    punto 4): **cada corrida debe usar su propia instancia** (igual que cada
    corrida usa su propio `rng`), o llamar a `reiniciar()` antes de arrancar
    una nueva; si no, el estado de una corrida se filtra a la siguiente y el
    sesgo introducido dependería de la semilla de forma silenciosa.

    `T` y `R` no se tocan: es, como su contraparte, un evento puramente
    hídrico.

    Parameters
    ----------
    probabilidad_disparo : float
        Probabilidad de que se abra un nuevo refugio en un tick dado
        (Bernoulli).
    radio_celdas : float
        Radio (en celdas) del área que alcanza cada refugio.
    a_w_objetivo_min, a_w_objetivo_max : float
        Rango del que se muestrea uniformemente el `A_w` pico de cada
        refugio. El mínimo (0.90) coincide con el `a_w_min` de
        *D. radiodurans* (`docs/parametros.md` §1.2): por debajo de eso el
        evento no reactivaría a la especie que motiva ADR-0015. El máximo
        (0.98) coincide con el `A_w` de las ventilas de Encelado — un techo
        físicamente plausible para agua líquida en un subsuelo, no un suelo
        saturado artificial.
    duracion_min_ticks, duracion_max_ticks : float
        Rango del que se muestrea uniformemente la constante de decaimiento
        (en ticks) de cada refugio: la intensidad decae como
        `exp(-edad / duracion)`. Es **parámetro**, no constante — pensado
        para que Erick lo barra (ADR-0015, entregable de persistencia).
    umbral_extincion : float
        Bajo este valor de intensidad, el refugio se considera disipado y se
        descarta del estado interno (evita que la lista crezca sin límite).
    """

    def __init__(
        self,
        probabilidad_disparo: float = 0.05,
        radio_celdas: float = 3.0,
        a_w_objetivo_min: float = 0.90,
        a_w_objetivo_max: float = 0.98,
        duracion_min_ticks: float = 3.0,
        duracion_max_ticks: float = 10.0,
        umbral_extincion: float = 0.02,
    ) -> None:
        self.probabilidad_disparo = probabilidad_disparo
        self.radio_celdas = radio_celdas
        self.a_w_objetivo_min = a_w_objetivo_min
        self.a_w_objetivo_max = a_w_objetivo_max
        self.duracion_min_ticks = duracion_min_ticks
        self.duracion_max_ticks = duracion_max_ticks
        self.umbral_extincion = umbral_extincion
        self._refugios: list[dict[str, float]] = []

    def reiniciar(self) -> None:
        """Descarta todos los refugios activos (nueva corrida independiente)."""
        self._refugios = []

    def aplicar(
        self, campo: CampoAmbiental, rng: np.random.Generator
    ) -> CampoAmbiental:
        m, n = campo.shape

        if rng.random() < self.probabilidad_disparo:
            self._refugios.append(
                {
                    "fila0": float(rng.integers(0, m)),
                    "col0": float(rng.integers(0, n)),
                    "a_w_objetivo": rng.uniform(
                        self.a_w_objetivo_min, self.a_w_objetivo_max
                    ),
                    "duracion": rng.uniform(
                        self.duracion_min_ticks, self.duracion_max_ticks
                    ),
                    "edad": 0.0,
                }
            )

        A_w_nuevo = campo.A_w.copy()
        if self._refugios:
            filas, cols = np.indices((m, n), dtype=float)

        refugios_vivos = []
        for refugio in self._refugios:
            intensidad = np.exp(-refugio["edad"] / refugio["duracion"])
            if intensidad >= self.umbral_extincion:
                dist = np.sqrt(
                    (filas - refugio["fila0"]) ** 2 + (cols - refugio["col0"]) ** 2
                )
                dentro_del_radio = dist <= self.radio_celdas
                elevado = A_w_nuevo + (refugio["a_w_objetivo"] - A_w_nuevo) * intensidad
                A_w_nuevo = np.where(
                    dentro_del_radio, np.maximum(A_w_nuevo, elevado), A_w_nuevo
                )
                refugio["edad"] += 1.0
                refugios_vivos.append(refugio)
        self._refugios = refugios_vivos

        A_w_nuevo = np.clip(A_w_nuevo, 0.0, 1.0)
        return CampoAmbiental(T=campo.T.copy(), R=campo.R.copy(), A_w=A_w_nuevo)
