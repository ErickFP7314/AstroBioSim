# Flujo de trabajo y estrategia de ramas — AstroBioSim

## 1. Idea central

El proyecto se puede paralelizar porque los módulos se hablan por **contratos de
frontera** (`CLAUDE.md` §3). La clave para no bloquearse es: **primero se
mergean los *stubs* de esos contratos a `main`**, y recién entonces cada persona
trabaja en paralelo importando interfaces reales (aunque estén vacías).

### Grafo de dependencias
```
        CampoAmbiental (Jose, §3.1)  ← raíz: casi todos dependen de esto
          │
   ┌──────┼───────────────┬───────────────┐
   ▼      ▼               ▼               ▼
Microorg. Eventos       Datos           (consumen el campo)
(Esmeralda)(Jose §3.4)  (Fidel §3.5)
   │                                       
   └──────────────┐                        
                  ▼                        
        Autómata Celular (Erick §3.3)   ← depende de campo + especie
                  │
                  ▼
        simulation.py (Erick)  ← integra TODO
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   UI dashboard        notebook análisis
   (Erick)             (Esmeralda)
```
**Camino crítico:** `CampoAmbiental` → Autómata Celular → `simulation.py`. Por eso
la primera prioridad absoluta es que Jose deje el stub de `CampoAmbiental`.

## 2. Orden de trabajo por fases (hitos)

### Hito 0 — Bootstrap (los 4 juntos, 1 sola sesión)
- `git init`, estructura de carpetas (ya está) y **stubs de los 5 contratos** §3
  con las firmas correctas y `...` / `raise NotImplementedError`.
- Un solo PR que deja `main` compilando e importando. A partir de aquí todos
  branchean.
- **Salida:** `pytest` corre (aunque los tests estén marcados `xfail`/skip).

### Hito 1 — Fundaciones (paralelo)
| Quién | Rama | Entrega |
|------|------|---------|
| **Jose** | `feat/env-campo-ambiental` | `CampoAmbiental` funcional + 3 entornos con su campo inicial. **Prioridad 1** (desbloquea a todos). |
| **Esmeralda** | `feat/bio-especies` | `Microorganismo` + 3 especies + `condiciones_habitables`. |
| **Fidel** | `feat/data-loaders` | `cargar_atacama` + fallback sintético + DataFrame canónico. |
| **Erick** | `feat/engine-transicion` | Reglas de transición + `paso()` contra stubs de campo/especie. |

### Hito 2 — Dominio completo (paralelo)
| Quién | Rama | Entrega |
|------|------|---------|
| **Jose** | `feat/engine-estocastico` | `EventoEstocastico` + micro-fisura + emisión hidrotermal. |
| **Fidel** | `feat/data-resampling` + `feat/modes-analogico` | Remuestreo → `CampoAmbiental` + Modo Analógico. |
| **Erick** | `feat/simulation-orquestador` | `simulation.py` que une motores (necesita Hito 1 en `main`). |
| **Esmeralda** | `feat/modes-sandbox` | Modo Sandbox (parámetros estáticos/sliders). |

### Hito 3 — Superficies e integración
| Quién | Rama | Entrega |
|------|------|---------|
| **Erick** | `feat/simulation-orquestador` | Integración final Montecarlo en el bucle. |
| **Erick** | `feat/ui-dashboard` | Backend FastAPI (`ui/api.py`) + dashboard **React** en `frontend/` (consume solo la API del orquestador). Ver ADR-0009. |
| **Esmeralda** | `feat/notebook-analisis` | Notebook: corridas Montecarlo, curvas población media ± σ, comparación de los tres entornos. |

### Hito 4 — Validación y calibración (paralelo, cada uno su carrera)
- **Esmeralda:** calibra umbrales de especies con literatura.
- **Fidel:** valida biológicamente las salidas; documenta límites del mapeo de datos.
- **Jose:** sanidad física de gradientes y eventos; chequea diferenciación de Encelado.
- **Erick:** validación estadística de las corridas Montecarlo.
- Ramas: `fix/...` o `chore/calibracion-...` según corresponda.

## 3. Estrategia de ramas (GitHub Flow simplificado)

Para un equipo de 4 conviene lo simple: **una rama tronco (`main`) siempre verde
+ ramas de feature cortas**. Nada de Git Flow con `develop`/`release` (demasiada
ceremonia para este alcance).

### Ramas
- **`main`** — siempre estable: `pytest` pasa. **Nadie commitea directo**; solo se
  entra por PR.
- **`feat/<area>-<desc>`** — trabajo de una tarea. Corta y enfocada; se borra tras
  el merge.
- **`fix/<desc>`**, **`docs/<desc>`**, **`chore/<desc>`**, **`test/<desc>`** — según el tipo.

### Convención de nombres de rama
`<tipo>/<area>-<descripcion-corta>` — ej. `feat/engine-transicion`,
`fix/data-nan-humedad`, `docs/adr-encelado`. Áreas: `core`, `bio`, `env`,
`engine`, `data`, `modes`, `ui`, `sim`, `notebook`.

### Convención de commits (Conventional Commits)
`<tipo>(<scope>): <resumen en imperativo>` — ej.:
- `feat(engine): conteo de vecinos de Moore vectorizado`
- `test(bio): umbral de radiación de D. radiodurans`
- `docs(adr): registrar eliminación de presión`
- `fix(data): descartar filas con humedad fuera de [0,100]`

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

### Reglas de PR
1. PR pequeño, con **sus tests en verde** y descripción de qué contrato toca.
2. **Al menos 1 revisor.** Preferí que revise **quien consume tu interfaz**:
   - `CampoAmbiental` (Jose) → lo revisa **Erick** (lo consume en `paso`).
   - `Microorganismo` (Esmeralda) → lo revisa **Erick**.
   - Datos (Fidel) → lo revisa **Jose** (comparten el gradiente térmico).
   - Autómata/`simulation` (Erick) → lo revisan **todos** (toca a todos).
3. **No cruces fronteras** de otra carpeta en tu PR. Si necesitás cambiar una firma
   de §3, primero se acuerda en grupo y se escribe un **ADR** (como ADR-0008).
4. Merge preferido: **squash** (historial limpio, un commit por feature).

### Protección de `main` (si usan GitHub)
- Requerir PR + 1 aprobación.
- Requerir que pase el check de `pytest` (workflow de GitHub Actions).
- Prohibir push directo a `main`.

## 4. Ritual diario/semanal
- **Antes de codear:** `git switch main && git pull` y rebase de tu rama.
- **Integra seguido:** ramas de vida corta (< 2-3 días) para evitar conflictos en
  `simulation.py` y `config.py`.
- **`config.py` y `simulation.py`** se tocan con aviso previo (son compartidos).
- Cierre de hito: los 4 revisan que `main` corra la simulación de punta a punta.
