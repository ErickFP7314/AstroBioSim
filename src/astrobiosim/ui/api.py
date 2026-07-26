"""Frontera UI — API HTTP/WebSocket que expone el orquestador (dueño: Erick).

Ver ADR-0009 (React + FastAPI, reemplaza a Streamlit). Esta capa es la **única**
frontera con el frontend: envuelve `simulation.simular` / `simular_montecarlo`
como servicio y el motor permanece agnóstico de HTTP.

Endpoints
---------
- ``GET  /api/config``      Catálogos (especies, entornos, estados) para poblar la UI.
- ``WS   /api/stream``      Recibe una config de corrida y emite la grilla por tick.
- ``POST /api/montecarlo``  Corre N réplicas y devuelve media ± σ por tick.

Correr en desarrollo::

    uvicorn astrobiosim.ui.api:app --reload
"""
from __future__ import annotations

import asyncio
import base64
from itertools import islice
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from astrobiosim.core.microorganism import (
    ACTIVA,
    LATENTE,
    MUERTA,
    DRadiodurans,
    EColi,
    MBurtonii,
    Microorganismo,
)
from astrobiosim.data.loaders import (
    cargar_atacama,
    cargar_control_tierra,
    cargar_ventilas,
)
from astrobiosim.data.resampling import Entorno
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.stochastic import SalmueraDelicuescente
from astrobiosim.engine.transition_rules import (
    PRESETS,
    REGLAS_DISPONIBLES,
    VOCABULARIO,
    ReglaTransicion,
    regla_desde_spec,
)
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.modes.base import ModoSimulacion
from astrobiosim.modes.sandbox import ModoSandbox
from astrobiosim.simulation import sembrar_estado, simular_montecarlo

_RAIZ = Path(__file__).resolve().parents[3]
_DATA = _RAIZ / "data" / "processed"

# --------------------------------------------------------------------------
# Catálogos (id → clase / metadatos)
# --------------------------------------------------------------------------
_ESPECIES: dict[str, type[Microorganismo]] = {
    "ecoli": EColi,
    "dradiodurans": DRadiodurans,
    "mburtonii": MBurtonii,
}
_ESPECIE_LABEL = {
    "ecoli": "E. coli",
    "dradiodurans": "D. radiodurans",
    "mburtonii": "M. burtonii",
}
_ENTORNOS: dict[str, Entorno] = {
    "tierra": Entorno.TIERRA,
    "marte": Entorno.MARTE,
    "encelado": Entorno.ENCELADO,
}
_ENTORNO_LABEL = {"tierra": "Tierra", "marte": "Marte", "encelado": "Encelado"}
_LOADER = {
    "tierra": (cargar_control_tierra, "datos_tierra_control_2025.csv"),
    "marte": (cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv"),
    "encelado": (cargar_ventilas, "datos_ventilas_2025_procesados.csv"),
}

_LADO_MIN, _LADO_MAX = 10, 120
_ITER_SANDBOX_DEFECTO, _ITER_MAX = 200, 800
_MC_MAX = 60


# --------------------------------------------------------------------------
# Config de una corrida (lo que envía el frontend)
# --------------------------------------------------------------------------
class ConfigCorrida(BaseModel):
    """Parámetros de una corrida. `modo` decide de dónde sale el campo."""

    modo: Literal["sandbox", "analogico"] = "sandbox"
    especie: Literal["ecoli", "dradiodurans", "mburtonii"] = "dradiodurans"
    entorno: Literal["tierra", "marte", "encelado"] = "marte"
    # Sandbox: campo homogéneo
    T: float = 20.0  # °C
    R: float = 0.0  # UV, W/m²
    A_w: float = 0.9  # 0..1
    # Grilla y estado inicial
    m: int = Field(default=60, ge=_LADO_MIN, le=_LADO_MAX)
    n: int = Field(default=60, ge=_LADO_MIN, le=_LADO_MAX)
    fraccion_activa: float = Field(default=0.15, ge=0.0, le=1.0)
    patron: Literal["uniforme", "cluster"] = "uniforme"
    semilla: int | None = 42
    n_iteraciones: int | None = None  # Sandbox; en Analógico se ignora (365)
    # Eventos
    salmuera: bool = False  # microrefugios (solo tiene sentido en Marte)
    # Montecarlo
    n_corridas: int = Field(default=30, ge=1, le=_MC_MAX)
    # Regla de transición (ADR-0016/0018): id de preset ("logistica"/"conway"/
    # "hibrida"), spec de bloques inline (dict) o None → logística por defecto.
    regla: str | dict | None = None


# --------------------------------------------------------------------------
# Helpers: construir las piezas del motor a partir de la config
# --------------------------------------------------------------------------
def _shape(cfg: ConfigCorrida) -> tuple[int, int]:
    return (cfg.m, cfg.n)


def _especie(cfg: ConfigCorrida) -> Microorganismo:
    return _ESPECIES[cfg.especie]()


def _n_iter(cfg: ConfigCorrida) -> int | None:
    if cfg.modo == "analogico":
        return None  # la serie completa (finita)
    return min(cfg.n_iteraciones or _ITER_SANDBOX_DEFECTO, _ITER_MAX)


def _construir_modo(cfg: ConfigCorrida, rng: np.random.Generator) -> ModoSimulacion:
    if cfg.modo == "sandbox":
        return ModoSandbox(_shape(cfg), T=cfg.T, R=cfg.R, A_w=cfg.A_w)
    loader, archivo = _LOADER[cfg.entorno]
    df = loader(str(_DATA / archivo))
    return ModoAnalogico(df, _ENTORNOS[cfg.entorno], _shape(cfg), rng=rng)


def _construir_eventos(cfg: ConfigCorrida) -> list:
    if cfg.salmuera and cfg.entorno == "marte":
        return [
            SalmueraDelicuescente(
                probabilidad_disparo=0.1, a_w_objetivo_min=0.95, a_w_objetivo_max=0.98
            )
        ]
    return []


def _estado_inicial(cfg: ConfigCorrida, rng: np.random.Generator) -> np.ndarray:
    return sembrar_estado(
        _shape(cfg), rng=rng, fraccion_activa=cfg.fraccion_activa, patron=cfg.patron
    )


def _regla(cfg: ConfigCorrida) -> ReglaTransicion | None:
    """Resuelve `cfg.regla` a una `ReglaTransicion` (o None → logística por defecto).

    Raises
    ------
    ValueError
        Si el id de preset no existe o el spec de bloques está mal formado.
    """
    r = cfg.regla
    if r is None:
        return None  # paso()/simular usan ReglaLogistica por defecto
    if isinstance(r, str):
        if r not in REGLAS_DISPONIBLES:
            raise ValueError(f"regla desconocida: {r!r} (usa {list(REGLAS_DISPONIBLES)})")
        return REGLAS_DISPONIBLES[r]
    return regla_desde_spec(r)  # spec de bloques inline (ADR-0018)


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = FastAPI(title="AstroBioSim API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/config")
def config() -> dict:
    """Catálogos para poblar los selectores y la leyenda de la UI."""
    especies = []
    for eid, cls in _ESPECIES.items():
        e = cls()
        especies.append(
            {
                "id": eid,
                "label": _ESPECIE_LABEL[eid],
                "t_min": e.t_min,
                "t_opt": e.t_opt,
                "t_max": e.t_max,
                "a_w_min": e.a_w_min,
                "uv_max": round(e.uv_max, 4),
                "mu_opt": e.mu_opt,
            }
        )
    # Reglas fijas como plantilla editable + su notación formal (ADR-0018).
    reglas = []
    for clave, spec in PRESETS.items():
        r = regla_desde_spec(spec)
        reglas.append({"id": clave, "nombre": r.nombre, "spec": spec, "notacion": r.notacion()})
    return {
        "especies": especies,
        "entornos": [
            {"id": k, "label": v} for k, v in _ENTORNO_LABEL.items()
        ],
        # valores enteros de estado (ADR-0012), para decodificar la grilla
        "estados": {"MUERTA": MUERTA, "LATENTE": LATENTE, "ACTIVA": ACTIVA},
        "limites": {
            "lado": [_LADO_MIN, _LADO_MAX],
            "iter_max": _ITER_MAX,
            "mc_max": _MC_MAX,
        },
        # Editor de reglas por bloques (ADR-0018): plantillas + vocabulario.
        "reglas": reglas,
        "vocabulario": VOCABULARIO,
    }


@app.post("/api/regla/validar")
def validar_regla(spec: dict) -> dict:
    """Valida un spec de bloques en construcción y devuelve su notación formal.

    Devuelve ``{"valida": bool, "notacion": str | None, "error": str | None}``.
    El frontend lo usa para dar feedback en vivo mientras se arma la regla.
    """
    try:
        regla = regla_desde_spec(spec)
    except ValueError as exc:
        return {"valida": False, "notacion": None, "error": str(exc)}
    return {"valida": True, "notacion": regla.notacion(), "error": None}


def _frame(tick: int, estado: np.ndarray) -> dict:
    e = np.ascontiguousarray(estado, dtype=np.int8)
    return {
        "type": "frame",
        "tick": tick,
        "shape": list(e.shape),
        "grid": base64.b64encode(e.tobytes()).decode("ascii"),
        "n": {
            "m": int((e == MUERTA).sum()),
            "l": int((e == LATENTE).sum()),
            "a": int((e == ACTIVA).sum()),
        },
    }


@app.websocket("/api/stream")
async def stream(ws: WebSocket) -> None:
    """Corre una simulación y emite un frame (grilla + conteos) por tick.

    El cliente recibe todos los frames y controla la reproducción
    (play/pausa/paso/velocidad) sobre ese buffer.
    """
    await ws.accept()
    try:
        cfg = ConfigCorrida(**(await ws.receive_json()))
        regla = _regla(cfg)
    except Exception as exc:  # noqa: BLE001 — cualquier config/regla inválida
        await ws.send_json({"type": "error", "detail": f"config inválida: {exc}"})
        await ws.close()
        return

    # Flujos aleatorios independientes desde la semilla (reproducible).
    ss = np.random.SeedSequence(cfg.semilla)
    rng_modo, rng_estado, rng_din = (
        np.random.default_rng(hijo) for hijo in ss.spawn(3)
    )
    modo = _construir_modo(cfg, rng_modo)
    especie = _especie(cfg)
    eventos = _construir_eventos(cfg)
    estado = _estado_inicial(cfg, rng_estado)

    campos = modo.campos()
    n_iter = _n_iter(cfg)
    if n_iter is not None:
        campos = islice(campos, n_iter)

    try:
        await ws.send_json(_frame(0, estado))
        tick = 0
        for campo_base in campos:
            campo = campo_base
            for evento in eventos:
                campo = evento.aplicar(campo, rng_din)
            estado = paso(estado, campo, especie, rng_din, regla=regla)
            tick += 1
            await ws.send_json(_frame(tick, estado))
            await asyncio.sleep(0.004)  # cede el loop; el cliente marca el ritmo
        await ws.send_json({"type": "done", "ticks": tick})
    except WebSocketDisconnect:
        return
    finally:
        try:
            await ws.close()
        except RuntimeError:
            pass


@app.post("/api/montecarlo")
def montecarlo(cfg: ConfigCorrida) -> dict:
    """Corre N réplicas y devuelve media ± σ por tick de las tres fracciones.

    Columnas de `media`/`desviacion`: ``[MUERTA, LATENTE, ACTIVA]``.
    """
    try:
        regla = _regla(cfg)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    estado0 = _estado_inicial(cfg, np.random.default_rng(cfg.semilla))
    usa_eventos = bool(_construir_eventos(cfg))
    res = simular_montecarlo(
        construir_modo=lambda rng: _construir_modo(cfg, rng),
        especie=_especie(cfg),
        estado_inicial=estado0,
        construir_eventos=(lambda rng: _construir_eventos(cfg)) if usa_eventos else None,
        n_corridas=min(cfg.n_corridas, _MC_MAX),
        semilla=cfg.semilla,
        n_iteraciones=_n_iter(cfg),
        regla=regla,
    )
    return {
        "n_corridas": res.n_corridas,
        "media": res.media.tolist(),
        "desviacion": res.desviacion.tolist(),
    }
