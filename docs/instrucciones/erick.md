# Erick (Matemática) — Autómata Celular + dashboard

**Carpeta:** `src/astrobiosim/engine/cellular_automaton.py`,
`engine/transition_rules.py`, `ui/` (API FastAPI) + `frontend/` (React)
(además lidera `simulation.py`)
**Tests:** `tests/unit/test_transition.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

> ⚠️ **La tarea 1 de abajo quedó OBSOLETA por ADR-0012 y ADR-0013** y está
> reescrita acá mismo. Las tareas 2 a 6 siguen vigentes, con el detalle de que
> `paso()` ahora devuelve tres estados y recibe `rng`. **Leé también la sección
> "🔄 Actualización 2026-07-23" al final del archivo antes de implementar.**

1. `transition_rules.py`: reglas **puras y vectorizadas**, con **tres estados**
   (`MUERTA=0`, `LATENTE=1`, `ACTIVA=2`) y **tasa continua**:
   - Clasificación por celda (ADR-0012):
     dentro de `especie.condiciones_crecimiento(campo)` → `ACTIVA`;
     fuera de crecimiento pero dentro de `condiciones_supervivencia(campo)` →
     `LATENTE`; fuera de supervivencia → `MUERTA`. `MUERTA` es **absorbente**:
     aplicá esa máscara al final, pisando todo lo demás.
   - Reproducción (ADR-0013): una celda vacía nace con probabilidad
     `p_repro = clip(μ·Δt, 0, 1)`, muestreada con el `rng` **inyectado**, donde
     `μ = μ_opt · γ_T(T) · γ_aw(a_w) · γ_UV(UV)` y `γ_T` es el CTMI. El conteo de
     vecinos de Moore para reproducir cuenta **solo celdas `ACTIVA`**.
   - Los umbrales de Conway (muere con `<2` o `>3` vecinos) quedan **a decidir**:
     con la cinética continua puede que sobren. Ver pregunta 10 al final.

   <details><summary>Versión original (histórico — no implementar)</summary>

   - Muerte por estrés: `~especie.condiciones_habitables(campo)` mata celdas vivas.
   - Muerte por soledad/sobrepoblación: viva muere si vecinos `<2` o `>3`.
   - Reproducción: vacía nace si vecinos `==3` **y** condiciones habitables.

   </details>

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

## Mapa: tarea → historia de usuario (Trello)
Tablero: https://trello.com/b/cK8VP1aj — etiqueta 🟣 **Erick**. Los criterios de
aceptación de cada historia están en el checklist de su tarjeta.

| Tarea de este archivo | Historia de usuario | Hito |
|---|---|---|
| Tareas 1-2 (`transition_rules.py` + `paso()`) | **Autómata Celular: reglas de transición + paso()** | Hito 1 |
| Tarea 3 (`simulation.py`, acople de motores) | **Orquestador: simulation.py** | Hito 2 |
| Tarea 3 (Montecarlo dentro del bucle) | **Integración Montecarlo en el bucle** | Hito 3 |
| Tareas 4-5 (`ui/api.py` FastAPI + `frontend/` React) | **UI: backend FastAPI + dashboard React** | Hito 3 |
| Sección "Qué reviso yo" (estadística Montecarlo) | **Validación estadística de Montecarlo** | Hito 4 |

## Preguntas para configurar tu agente de IA
Respondé esto antes de que tu Claude implemente; si no, asumirá defaults que quizá no querés:
1. **Grilla:** dimensiones M×N por defecto (coordinar con Jose — es el mismo tamaño de campo).
2. **Condición de borde:** ¿frontera muerta (default) o toroidal? Justificá la elección.
3. **Reglas de transición:** ¿se mantienen los umbrales tipo Conway (vive con 2-3 vecinos, nace con 3) o se ajustan?
4. **Estado inicial:** ¿lo define Esmeralda y el orquestador lo recibe como parámetro, o lo genera el CA?
5. **Montecarlo:** ¿nº de repeticiones por defecto y cómo se derivan las semillas (una base + offsets deterministas)?
6. **UI ↔ motor:** ¿WebSocket (stream por tick) o polling REST? ¿Qué velocidad/FPS de animación?
7. **Interactividad:** ¿el dashboard cambia parámetros en vivo (Sandbox) o solo lanza/consulta corridas?
8. **Persistencia:** ¿se guarda el historial completo de grillas por tick o solo las curvas poblacionales?

---

# 🔄 Actualización 2026-07-23 — ADR-0012 a 0015

> Es el bloque que más te toca: **dos de los cuatro ADRs son matemática pura y son
> tuyos.** Nada de tu código estaba escrito todavía, así que no hay que corregir,
> solo implementar sobre la base nueva.

## Lo que cambia en tu contrato (§3.3)

- El estado deja de ser binario: `int8` con `{MUERTA=0, LATENTE=1, ACTIVA=2}`.
- `paso()` ahora recibe **`rng`** (la reproducción pasa a ser estocástica).
- El conteo de vecinos de Moore para reproducir cuenta **solo celdas `ACTIVA`**.
- `condiciones_habitables` sigue existiendo como alias, pero usá los métodos nuevos:
  `condiciones_crecimiento` y `condiciones_supervivencia`.

## Tus tareas nuevas

1. **[Hito 1] `paso()` con tres estados.** La transición, vectorizada y síncrona:
   ```
   dentro de crecimiento                     -> ACTIVA
   fuera de crecimiento, dentro de superviv. -> LATENTE
   fuera de supervivencia                    -> MUERTA  (absorbente)
   MUERTA                                    -> MUERTA
   ```
   Cuidado con el orden: `MUERTA` es absorbente, así que la máscara de muertas
   previas se aplica **al final**, pisando cualquier otra transición.
2. **[Hito 1 — la más interesante] `transition_rules.py` con cinética continua**
   (ADR-0013). Reemplaza la máscara binaria por
   `μ = μ_opt · γ_T(T) · γ_aw(a_w) · γ_UV(UV)`, con `γ_T` por CTMI:
   ```
                 (T − T_max)(T − T_min)²
   γ_T(T) = ─────────────────────────────────────────────────────────
            (T_opt − T_min)·[ (T_opt − T_min)(T − T_opt)
                              − (T_opt − T_max)(T_opt + T_min − 2T) ]
   ```
   y `0` fuera de `(T_min, T_max)`. Después `p_repro = clip(μ·Δt, 0, 1)`, muestreada
   con el `rng` inyectado. **Testeá los bordes** (`T = T_min`, `T_opt`, `T_max`): el
   CTMI es numéricamente delicado ahí y el denominador puede anularse.
3. **[Hito 3] El barrido de parámetros** — el entregable con más peso académico del
   proyecto (ADR-0015). Barrido `frecuencia × magnitud` del evento
   `SalmueraDelicuescente` de Jose, sobre ensambles Montecarlo con semillas
   explícitas, midiendo **persistencia de la población** (fracción activa/latente/
   muerta) como variable de respuesta. La salida es la respuesta a la pregunta de
   investigación: ¿dónde está el umbral crítico de agua transitoria?
4. **[Hito 3] La UI muestra tres estados**, no dos: el `<canvas>` necesita tres
   colores y las curvas pasan de una a tres series.
5. **[Hito 4] Análisis de sensibilidad.** Qué parámetro domina el desenlace, variando
   cada uno sobre su rango de incertidumbre en literatura. Es lo que blinda el
   resultado frente a que los umbrales de Esmeralda tengan error.

## Preguntas nuevas para tu agente

9. **Δt:** ¿cuánto tiempo físico representa un tick? `μ_opt` está en h⁻¹, así que
   `p_repro = μ·Δt` necesita que Δt esté definido en horas.
10. **Reglas de Conway:** con la cinética continua, ¿siguen aplicando los umbrales de
    2-3 vecinos, o la reproducción pasa a depender solo de `μ` y de haber un vecino
    vacío?
11. **Latencia y vecindad:** ¿una celda `LATENTE` ocupa espacio (bloquea que nazca
    otra ahí)? Yo diría que sí, pero definilo explícitamente.
12. **Barrido:** ¿cuántos puntos por eje y cuántas repeticiones Montecarlo por punto?
