# AstroBioSim

An interactive Python-based simulator that models the population viability of microorganisms in the subsurface environments of Earth, Mars, and Enceladus using cellular automata, evaluating their survival in relation to three critical variables: temperature (T), radiation (R), and water activity (A_w).

Final Project — 1st Winter School on Computational Methods.

![Preview of the system in operation](preview.png)

## Architecture

Two decoupled motors coordinated by a simulation orchestrator (see docs/adr/):

- **Biological engine** (`core/microorganism.py`) — an OOP hierarchy of species with
  their respective tolerance thresholds.
- **Environmental engine** (`core/environment.py`) — planetary environments that
  generate the environmental field `E = {T, R, A_w}` across the grid.
- **Motor de Autómata Celular** (`engine/`) — grilla 2D, vecindad de Moore,
  reglas de transición y eventos estocásticos Montecarlo.
- **Modos** (`modes/`) — Sandbox (sliders) y Analógico (datasets de Atacama).
- **UI** — backend `ui/api.py` (FastAPI) + frontend `frontend/` (React), desacoplados
  del motor (ver ADR-0009).
