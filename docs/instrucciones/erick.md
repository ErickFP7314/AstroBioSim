# Erick (Matemática) — Autómata Celular + dashboard

**Carpeta:** `src/astrobiosim/engine/cellular_automaton.py`,
`engine/transition_rules.py`, `ui/` (API FastAPI) + `frontend/` (React)
(además lidera `simulation.py`)
**Tests:** `tests/unit/test_transition.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

1. `transition_rules.py`: reglas **puras y vectorizadas**:
   - Muerte por estrés: `~especie.condiciones_habitables(campo)` mata celdas vivas.
   - Muerte por soledad/sobrepoblación: viva muere si vecinos `<2` o `>3`.
   - Reproducción: vacía nace si vecinos `==3` **y** condiciones habitables.
2. `cellular_automaton.py`: `paso(...)` del contrato §3.3 con **conteo de vecinos de
   Moore vectorizado** (convolución o suma de 8 desplazamientos) y **doble buffer**
   síncrono. Definí la condición de borde (por defecto frontera muerta) y documentala.
3. `simulation.py`: orquestador que, por iteración, aplica eventos (Jose) al campo,
   luego llama a `paso(...)`, y guarda el historial poblacional. Es el punto de unión
   de todos los motores.
4. `ui/api.py` (backend FastAPI, ADR-0009): envolvé el orquestador `simulation.py`
   como servicio. Endpoints REST para crear/consultar una corrida y un canal
   **WebSocket** para el stream de la grilla por tick (animación). La API es la
   **única** frontera con el frontend; el motor no sabe nada de HTTP.
5. `frontend/` (React + Vite + TypeScript): dashboard que consume la API —
   sliders del Modo Sandbox, arranque/pausa, render de la matriz de supervivencia
   (`<canvas>`) y curvas poblacionales. Nada de lógica de simulación en el cliente.
6. Tests: reproducción/muerte en configuraciones conocidas (p.ej. un "blinker" bajo
   condiciones óptimas); la actualización es síncrona (no depende del orden de barrido).

## Criterios de aceptación
- **Cero bucles Python** sobre celdas.
- Actualización **síncrona** verificable (doble buffer).
- Misma semilla ⇒ misma corrida.
- El dashboard React consume **solo** la API pública; el motor queda agnóstico de la UI.

## Qué reviso yo (rigor del modelo y de la API)
Con mi criterio de matemática verifico:
- ¿La **función de transición** implementada coincide con la formal (Moore, umbrales,
  las tres reglas)? ¿La vectorización es **equivalente** a la definición celda a celda?
- ¿La actualización es **realmente síncrona** (doble buffer) y no depende del orden?
- ¿Las **condiciones de borde** están definidas y justificadas?
- ¿La aleatoriedad es **reproducible** (una sola semilla, sin RNG global)?
- ¿La **API** mantiene la frontera limpia (el frontend no reimplementa el modelo)?
- **Nota:** el notebook de análisis lo construye Esmeralda; yo valido que su
  **estadística Montecarlo** sea correcta (nº de repeticiones, media ± desviación).
