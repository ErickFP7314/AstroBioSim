# AstroBioSim

Simulador interactivo en Python que modela la **viabilidad poblacional de
microorganismos** en subsuelos de **Tierra, Marte y Encelado** mediante
**Autómatas Celulares**, evaluando su supervivencia frente a tres variables
críticas: **temperatura (T), radiación (R) y actividad de agua (A_w)**.

Proyecto final — *1era Escuela de Invierno en Métodos Computacionales*.

## Arquitectura

Dos motores desacoplados coordinados por un orquestador de simulación
(ver `docs/adr/`):

- **Motor biológico** (`core/microorganism.py`) — jerarquía POO de especies con
  sus umbrales de tolerancia.
- **Motor ambiental** (`core/environment.py`) — entornos planetarios que producen
  el campo ambiental `E = {T, R, A_w}` sobre la grilla.
- **Motor de Autómata Celular** (`engine/`) — grilla 2D, vecindad de Moore,
  reglas de transición y eventos estocásticos Montecarlo.
- **Modos** (`modes/`) — Sandbox (sliders) y Analógico (datasets de Atacama).
- **UI** — backend `ui/api.py` (FastAPI) + frontend `frontend/` (React), desacoplados
  del motor (ver ADR-0009).

## Estructura del repositorio

```
src/astrobiosim/   Código fuente Python (core, engine, data, modes, ui/api.py)
frontend/          Dashboard React (Vite + TypeScript) — se agrega en Hito 3
tests/             Tests unitarios e de integración (pytest)
notebooks/         Análisis retrospectivo (Jupyter)
data/              Datasets crudos y procesados
docs/adr/          Decisiones arquitectónicas (ADR)
openspec/          Artefactos de planificación (proposal, specs, design, tasks)
```

## Instalación (desarrollo)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Ejecución

```bash
uvicorn astrobiosim.ui.api:app --reload   # backend API (FastAPI) — desde Hito 3
pytest                                     # tests
# Frontend (desde Hito 3):  cd frontend && npm install && npm run dev
```

## Documentación clave
- `openspec/project.md` — contexto y convenciones.
- `openspec/changes/bootstrap-simulator/` — plan del MVP.
- `docs/adr/README.md` — índice de decisiones arquitectónicas.
- `docs/division-trabajo.md` — reparto de trabajo del equipo.
