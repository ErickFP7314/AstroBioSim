# ADR-0009: Frontend React + backend FastAPI (reemplaza a ADR-0004)

- **Estado:** Aceptado
- **Fecha:** 2026-07-21
- **Reemplaza a:** ADR-0004 (Streamlit)

## Contexto
ADR-0004 proponía Streamlit para el dashboard. El equipo decidió construir la
interfaz con un **framework SPA de JavaScript** (React o Angular) en lugar de
Streamlit, para tener control total sobre la animación de la grilla, una UX más
pulida para el informe final y separación limpia entre presentación y cómputo.

Consecuencia técnica clave: una SPA de JS **no puede ejecutar NumPy**. A
diferencia de Streamlit (Python puro), este enfoque obliga a exponer la
simulación como un **servicio HTTP/WebSocket**. Esto agrega un componente
—el backend de API— pero **refuerza** la frontera UI/motor que ya exige
ADR-0001: el motor sigue siendo agnóstico de la UI.

## Decisión

1. **Frontend: React** (con Vite + TypeScript), no Angular.
2. **Backend: FastAPI** (+ Uvicorn) que envuelve el orquestador `simulation.py`
   y publica endpoints REST + un canal WebSocket para el stream de la grilla.
3. El código React vive en `frontend/` (fuera de `src/`, es otro runtime). La
   capa Python de frontera vive en `src/astrobiosim/ui/api.py`.

### Por qué React y no Angular
- **Curva de entrada.** El equipo es de biotecnología, física y matemática, no
  de frontend. React (componentes + hooks) se aprende incrementalmente; Angular
  impone de entrada TypeScript estricto, RxJS, inyección de dependencias y una
  CLI/estructura pesada. Para 4 personas y un plazo corto, menos ceremonia gana.
- **Visualización.** El núcleo de la UI es render de una grilla que cambia por
  tick + curvas poblacionales. React tiene el ecosistema más rico y directo para
  esto (canvas/`<canvas>` para la grilla, Recharts/Plotly.js para las curvas).
- **Peso.** Angular está pensado para apps de empresa grandes y de larga vida;
  aquí es sobredimensionado. React + Vite da recarga en caliente y un bundle
  mínimo con casi cero configuración.
- **Contratación de ayuda/documentación.** React tiene la comunidad y el
  material de aprendizaje más amplios, útil si alguien del equipo se traba.

Angular sería preferible con un equipo grande ya experto en TS/RxJS que valore
una estructura impuesta y opinionada; no es nuestro caso.

## Alternativas consideradas
1. **Angular.** Más estructura "de fábrica", pero curva de entrada alta y peso
   innecesario para el alcance. Descartado por costo de aprendizaje.
2. **Seguir con Streamlit (ADR-0004).** Python puro, cero backend extra, pero
   menos control sobre la animación y estética; el equipo prefirió la SPA.
3. **Flask en vez de FastAPI.** Válido, pero FastAPI da tipado, validación con
   Pydantic, WebSockets nativos y docs OpenAPI automáticas sin costo extra.

## Consecuencias
- (+) UI desacoplada y pulida; el motor queda expuesto como servicio reutilizable.
- (+) La frontera UI/motor (ADR-0001) se vuelve física: dos procesos, un contrato
  HTTP/WS en `ui/api.py`.
- (+) FastAPI aporta validación y documentación automática de la API.
- (−) **Mayor superficie:** hay que definir y versionar un contrato de API
  (nuevo trabajo respecto de Streamlit) y sumar `fastapi`/`uvicorn` +
  toolchain de Node/Vite para `frontend/`.
- (−) Dos runtimes que arrancar en desarrollo (Uvicorn + Vite dev server).
- **Dueño de la frontera UI:** Erick (ver ADR de reparto y `flujo-trabajo.md`,
  Hito 3), que también lidera `simulation.py` y por eso puede alinear API y motor.
