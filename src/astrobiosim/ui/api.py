"""Frontera UI — API HTTP/WebSocket que expone el orquestador (dueño: Erick).

Ver ADR-0009: reemplaza a Streamlit (ADR-0004). El backend (FastAPI) publica
la simulación como servicio; el frontend React (`frontend/`) la consume. El
motor permanece agnóstico de la UI: esta capa SOLO llama a la API pública del
orquestador (`simulation.py`).

STUB de Hito 0 — sin dependencia dura de FastAPI todavía. La app real va en
`feat/ui-dashboard` (Hito 3). Contrato tentativo de endpoints:

    POST /simulacion      -> crea una corrida (especie, entorno, semilla, params)
    GET  /simulacion/{id} -> estado/historial poblacional
    WS   /simulacion/{id} -> stream de la grilla por tick (para animación)
"""
from __future__ import annotations

# TODO(erick, Hito 3): montar la app FastAPI y conectar con el orquestador.
