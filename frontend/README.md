# AstroBioSim — UI (backend FastAPI + dashboard React)

Interfaz del simulador (ADR-0009). El **backend** (`src/astrobiosim/ui/api.py`)
envuelve el orquestador y expone la simulación por HTTP/WebSocket; el **frontend**
(esta carpeta, React + Vite + TypeScript) la consume. La UI no tiene lógica de
simulación: solo envía configs y renderiza lo que devuelve el motor.

Diseño: dirección **"Espectro"** — instrumento científico oscuro con doble acento
cian + ámbar atado a los estados (cian = ACTIVA, ámbar = LATENTE), numéricos en
monospace.

## Cómo levantarlo (dos procesos)

**1. Backend** (desde la raíz del repo, con el paquete instalado — `pip install -e ".[dev]"`):

```bash
uvicorn astrobiosim.ui.api:app --reload
# sirve en http://localhost:8000
```

**2. Frontend** (desde `frontend/`):

```bash
npm install
npm run dev
# abre http://localhost:5173
```

Vite proxya `/api` (HTTP y WebSocket) hacia `:8000`, así que no hay que tocar CORS
ni URLs en desarrollo. Para producción: `npm run build` genera `dist/`.

## Endpoints del backend

| Método | Ruta | Qué hace |
|---|---|---|
| `GET`  | `/api/config` | Catálogos (especies, entornos, valores de estado) para poblar la UI |
| `WS`   | `/api/stream` | Recibe una config y emite un frame (grilla base64 + conteos) por tick |
| `POST` | `/api/montecarlo` | Corre N réplicas y devuelve media ± σ por tick de las tres fracciones |

El WebSocket manda **todos** los frames; el cliente los bufferea y controla la
reproducción (play / pausa / paso / velocidad) sobre ese buffer.

## Qué hay

- **Sandbox**: sliders de T / UV / A_w en vivo; corré y mirá cómo evoluciona la grilla.
- **Analógico**: elegí entorno (Tierra / Marte / Encelado) + especie y corre los
  365 días reales 2025; en Marte podés activar las salmueras (microrefugios).
- La **grilla** (canvas) muestra los tres estados; el panel derecho grafica las
  curvas poblacionales del run y, con el botón *Banda Montecarlo*, superpone la
  media ± σ sobre N réplicas.
