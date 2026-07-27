"""Frontera UI — API HTTP/WebSocket que expone el motor (dueño: Erick).

Ver ADR-0009 (React + FastAPI, reemplaza a Streamlit). Es una envoltura
**delgada** sobre `astrobiosim.web.engine` —la lógica real, framework-free, que
se comparte con el deploy Pyodide (100% estático en Cloudflare Pages)—. El motor
permanece agnóstico de HTTP.

Endpoints
---------
- ``GET  /api/config``      Catálogos (especies, entornos, reglas…) para la UI.
- ``WS   /api/stream``      Recibe una config y emite la grilla por tick.
- ``POST /api/montecarlo``  Corre N réplicas y devuelve media ± σ por tick.
- ``POST /api/regla/validar`` Valida un spec de bloques y devuelve su notación.

Correr en desarrollo::

    uvicorn astrobiosim.ui.api:app --reload
"""
from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from astrobiosim.web import engine


# --------------------------------------------------------------------------
# Config de una corrida (valida y aporta defaults; el motor real vive en engine)
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
    m: int = Field(default=60, ge=engine.LADO_MIN, le=engine.LADO_MAX)
    n: int = Field(default=60, ge=engine.LADO_MIN, le=engine.LADO_MAX)
    fraccion_activa: float = Field(default=0.15, ge=0.0, le=1.0)
    patron: Literal["uniforme", "cluster"] = "uniforme"
    semilla: int | None = 42
    n_iteraciones: int | None = None  # ticks (ambos modos; Analógico recicla la serie)
    # Eventos
    salmuera: bool = False  # microrefugios (solo tiene sentido en Marte)
    # Montecarlo
    n_corridas: int = Field(default=30, ge=1, le=engine.MC_MAX)
    # Regla (ADR-0016/0018): id de preset, spec de bloques inline (dict) o None.
    regla: str | dict | None = None


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
    return engine.catalogo()


@app.websocket("/api/stream")
async def stream(ws: WebSocket) -> None:
    """Corre una simulación y emite un frame (grilla + conteos) por tick.

    El cliente recibe todos los frames y controla la reproducción
    (play/pausa/paso/velocidad) sobre ese buffer.
    """
    await ws.accept()
    try:
        cfg = ConfigCorrida(**(await ws.receive_json())).model_dump()
        frames = engine.iter_frames(cfg)  # generador perezoso
        primero = next(frames)            # dispara la validación (regla, modo, datos)
    except Exception as exc:  # noqa: BLE001 — cualquier config/regla inválida
        await ws.send_json({"type": "error", "detail": f"config inválida: {exc}"})
        await ws.close()
        return

    try:
        await ws.send_json(primero)
        tick = 0
        for f in frames:
            tick = f["tick"]
            await ws.send_json(f)
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
    """Corre N réplicas y devuelve media ± σ por tick de las tres fracciones."""
    try:
        return engine.montecarlo(cfg.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/regla/validar")
def validar_regla(spec: dict) -> dict:
    """Valida un spec de bloques en construcción y devuelve su notación formal."""
    return engine.validar_regla(spec)
