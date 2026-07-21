# Jose (Física) — Motor ambiental + eventos estocásticos

**Carpeta:** `src/astrobiosim/core/environment.py` y `src/astrobiosim/engine/stochastic.py`
**Tests:** `tests/unit/test_environment.py`, `tests/unit/test_stochastic.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

1. `environment.py`: implementá `CampoAmbiental` (contrato §3.1) y la jerarquía
   `PlanetaSubsuelo` → `TierraSubsuelo`, `MarteSubsuelo`, `EnceladoSubglacial`.
   Cada entorno construye su campo inicial:
   - Tierra: `T` estable, `A_w` alta, `R≈0`.
   - Marte: **gradiente térmico** del regolito con la profundidad, `A_w` baja, `R` presente.
   - Encelado: `T` con **gradiente hidrotermal** (picos cerca de fumarolas),
     `A_w≈1`, `R≈0` (protección total).
2. `stochastic.py`: implementá `EventoEstocastico` (contrato §3.4) y dos eventos:
   - `MicroFisuraMarte`: con probabilidad de disparo, **caída de `A_w`** en un radio
     de celdas (desecación). Modelado por distribución de probabilidad.
   - `EmisionHidrotermalEncelado`: pico `ΔT ~ N(μ, σ²)` que **se disipa radialmente**
     hacia las celdas vecinas (kernel de difusión de calor).
   Ambos reciben el `rng` inyectado; nada de aleatoriedad global.
3. Tests: los gradientes tienen el signo/monotonía física correcta; un evento
   aplicado dos veces con la misma semilla da el mismo campo (reproducibilidad).

## Criterios de aceptación
- `CampoAmbiental` valida que las tres capas tengan la misma forma.
- Los tres entornos son **cualitativamente distintos**.
- Los eventos solo tocan el **campo** (no el estado biológico).
- Todo evento usa el `rng` **inyectado** (reproducible).

## Qué reviso yo (coherencia física)
Con mi criterio de física verifico:
- ¿El **gradiente térmico** del regolito/hidrotermal tiene el signo y magnitud
  correctos (más frío/caliente con la profundidad según el caso)?
- ¿La **disipación** de la emisión hidrotermal se comporta como difusión de calor
  (decae con la distancia de forma razonable)?
- ¿Las **unidades** son consistentes (°C, W/m² para R según ADR-0010, adimensional)?
  ¿Los rangos son físicos?
- **Riesgo de ADR-0008:** sin presión, ¿Encelado sigue siendo físicamente
  distinguible de Tierra solo por T, A_w y R? Si no, aviso al grupo.

## Mapa: tarea → historia de usuario (Trello)
Tablero: https://trello.com/b/cK8VP1aj — etiqueta 🔵 **Jose**. Los criterios de
aceptación de cada historia están en el checklist de su tarjeta.

| Tarea de este archivo | Historia de usuario | Hito |
|---|---|---|
| Tarea 1 (`environment.py`: `CampoAmbiental` + 3 entornos) | **Motor ambiental: CampoAmbiental + 3 entornos** (Prioridad 1) | Hito 1 |
| Tarea 2 (`stochastic.py`: micro-fisura + emisión hidrotermal) | **Eventos estocásticos: micro-fisura + emisión hidrotermal** | Hito 2 |
| Sección "Qué reviso yo" (sanidad física) | **Sanidad física de gradientes y eventos** | Hito 4 |

## Preguntas para configurar tu agente de IA
Respondé esto antes de que tu Claude implemente; si no, asumirá defaults que quizá no querés:
1. **Grilla:** ¿qué dimensiones M×N por defecto? ¿La profundidad va en el eje vertical (fila 0 = superficie)?
2. **Gradiente marciano:** ¿lineal o exponencial con la profundidad? ¿Rango de T entre superficie y fondo del regolito?
3. **Encelado:** ¿dónde se ubican las fumarolas en la grilla y cuál es el pico hidrotermal `ΔT ~ N(μ, σ²)` (valores de μ y σ)?
4. **Micro-fisura marciana:** ¿probabilidad de disparo por tick, radio de celdas afectadas y magnitud de la caída de A_w?
5. **Disipación hidrotermal:** ¿qué kernel de difusión (gaussiano, radio de alcance) y cuánto decae por celda?
6. **Radiación (ADR-0010, W/m²):** ¿qué valor de R por entorno en superficie? ¿Encelado `R=0` confirmado?
7. **Valores iniciales:** los campos T/R/A_w de cada entorno, ¿salen del dataset real (Fidel) o de valores teóricos tuyos?
