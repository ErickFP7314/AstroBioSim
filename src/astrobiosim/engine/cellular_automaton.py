"""Paso del autómata celular — contrato de frontera §3.3 (dueño: Erick).

`paso()` es un tick del AC: calcula el estado siguiente **íntegro** a partir del
anterior (actualización síncrona, doble buffer) y **nunca** modifica el estado de
entrada. La lógica de decisión vive en `transition_rules` (regla intercambiable,
ADR-0016); acá se arma el contexto —máscaras ambientales, cinética y conteo de
vecinos— y se delega.
"""
from __future__ import annotations

import numpy as np

from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import ACTIVA, LATENTE, Microorganismo
from astrobiosim.engine.transition_rules import (
    DT_HORAS_DEFECTO,
    ReglaLogistica,
    ReglaTransicion,
    _Contexto,
    cinetica_mu,
    contar_vecinos_moore,
)


def paso(
    estado: np.ndarray,
    campo: CampoAmbiental,
    especie: Microorganismo,
    rng: np.random.Generator,
    *,
    regla: ReglaTransicion | None = None,
    dt: float = DT_HORAS_DEFECTO,
    borde: str = "muerta",
) -> np.ndarray:
    """Un tick del AC (actualización síncrona). Devuelve el nuevo estado (M, N) int8.

    Parameters
    ----------
    estado : np.ndarray
        Estado (M, N) en t, con valores en {MUERTA=0, LATENTE=1, ACTIVA=2}. No se
        modifica.
    campo : CampoAmbiental
        Campo ambiental en t. `campo.R` es irradiancia UV (ADR-0014).
    especie : Microorganismo
        Especie simulada; aporta sus umbrales de crecimiento y supervivencia y
        `mu_opt`.
    rng : np.random.Generator
        Generador inyectado (regla de oro nº6). Nunca `np.random` global.
    regla : ReglaTransicion, optional
        Regla de transición (ADR-0016). Por defecto `ReglaLogistica` (proceso de
        contacto). La UI puede pasar `ReglaConway`, `ReglaHibrida` o una propia.
    dt : float
        Duración del tick en horas (para `p_repro = clip(μ·dt, 0, 1)`). Default 1 h.
    borde : {"muerta", "toroidal"}
        Condición de borde para el conteo de vecinos de Moore. Default frontera
        muerta (la grilla es una ventana del subsuelo, no un mundo cerrado).

    Returns
    -------
    np.ndarray
        Nuevo estado (M, N) int8 en {0, 1, 2}.
    """
    if regla is None:
        regla = ReglaLogistica()

    estado = np.asarray(estado, dtype=np.int8)
    crece = especie.condiciones_crecimiento(campo)
    sobrevive = especie.condiciones_supervivencia(campo)
    p_repro = np.clip(cinetica_mu(especie, campo) * dt, 0.0, 1.0)

    n_activa = contar_vecinos_moore(estado == ACTIVA, borde)
    n_ocupada = contar_vecinos_moore(
        (estado == ACTIVA) | (estado == LATENTE), borde
    )

    ctx = _Contexto(
        estado=estado,
        crece=crece,
        sobrevive=sobrevive,
        p_repro=p_repro,
        n_activa=n_activa,
        n_ocupada=n_ocupada,
        rng=rng,
        anhidrobiotico=especie.anhidrobiotico,
    )
    return regla.aplicar(ctx).astype(np.int8)
