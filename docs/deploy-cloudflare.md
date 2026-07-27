# Deploy en Cloudflare Pages (100 % estático, sin backend)

AstroBioSim se despliega **entero como sitio estático** en Cloudflare Pages. No
hay backend: el motor Python (`astrobiosim`) corre **en el navegador del
visitante** vía **Pyodide** (CPython + NumPy/pandas compilados a WASM). El
frontend (React/Vite) manda las configs a un Web Worker que corre el motor y
devuelve los frames — la misma lógica que usaba el backend FastAPI, ahora del
lado del cliente (ver `src/astrobiosim/web/engine.py`, la fuente única).

## Qué se sirve

- El build de Vite (`frontend/dist/`): HTML, JS, CSS.
- `frontend/public/pyodide/` (copiado a `dist/pyodide/` en el build):
  - `astrobiosim-0.1.0-py3-none-any.whl` — el paquete, puro-Python (se importa
    desde `sys.path` en Pyodide).
  - `data/*.csv` — los 3 datasets 2025 que usa el Modo Analógico.
- **Pyodide + NumPy + pandas** se descargan del **CDN de jsdelivr** la primera vez
  (~15–20 MB) y quedan cacheados por el navegador. Es lo único que no vive en
  Cloudflare (es el runtime estándar de Pyodide); el sitio y el código sí.

## Opción A — Dashboard de Cloudflare (recomendada, sin CLI)

1. En el panel de Cloudflare: **Workers & Pages → Create → Pages → Connect to Git**.
2. Elegí el repo `AstroBioSim`.
3. Configuración de build:
   | Campo | Valor |
   |---|---|
   | **Root directory** | `frontend` |
   | **Build command** | `npm ci && npm run build` |
   | **Build output directory** | `dist` |
   | **Environment variables** | `NODE_VERSION = 20` (opcional, por las dudas) |
4. **Save and Deploy**. Cloudflare compila y publica; cada `git push` re-despliega.

> El build de Cloudflare corre en Node (no Python), y **no lo necesita**: el wheel
> y los CSV ya están **committeados** en `frontend/public/pyodide/`.

## Opción B — Wrangler CLI (vos hacés el login)

```bash
cd frontend && npm ci && npm run build && cd ..
npx wrangler login                    # abre tu navegador; login tuyo, sin tokens en el chat
npx wrangler pages deploy frontend/dist --project-name astrobiosim
```

## Regenerar los assets del navegador tras cambiar código Python

El wheel y los CSV están committeados (Cloudflare no corre Python). Si cambiás el
motor (`src/astrobiosim/…`), regeneralos y committeá:

```bash
./scripts/build_web_assets.sh        # reconstruye el wheel + copia los CSV
git add frontend/public/pyodide && git commit -m "chore: regenera assets web (Pyodide)"
```

## Notas

- **SPA fallback:** `frontend/public/_redirects` (`/* /index.html 200`) — inocuo,
  la app es de una sola vista.
- **Primera carga lenta** (descarga de Pyodide); las siguientes son instantáneas
  (caché del navegador). Se muestra una pantalla de progreso.
- **Dev local:** `cd frontend && npm run dev` — ya **no** hace falta levantar
  `uvicorn`; el motor corre en el navegador igual que en producción. El backend
  FastAPI (`astrobiosim.ui.api`) sigue existiendo y funcionando por si se lo
  quiere usar, pero la app no lo necesita.
