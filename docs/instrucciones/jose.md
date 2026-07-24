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

---

# 🔄 Actualización 2026-07-23 — ADR-0012 a 0015

> Tus Hitos 1 y 2 quedaron **aprobados**. Abajo está lo que se corrigió en tu código
> y lo que viene.

## Lo que ya se corrigió en `environment.py` (no lo rehagas)

| Antes | Ahora | Por qué |
|---|---|---|
| `A_W_ALTA = 0.75` (Tierra) | `A_W_SUBSUELO = 0.99` | **La columna `Actividad_Agua_aw` del dataset es humedad del AIRE, no del suelo.** Media 0.55, rango 0.16–0.93, sd 0.23 — un suelo no oscila así. Viene del `A_w = HR/100` de ADR-0008. Un suelo a capacidad de campo está en ~0.99. Con 0.75, *E. coli* no crecía en su propio control. |
| `T_SUBSUELO_C = 15.0` | `19.8` | media anual real del dataset: es el valor al que amortigua la onda térmica |
| `R_SUPERFICIE = 844` (total) | `UV_SUPERFICIE ≈ 42.2` | ADR-0014: `R` es UV, = global × `FRACCION_UV` (0.05), documentado |
| `escala_radiativa = térmica/4` | `térmica/10` | el UV se extingue en mm–cm, mucho más rápido que el calor |
| `A_W_BAJA = 0.187` constante | `A_W_MEDIA` + `A_W_SIGMA = 0.080` | ADR-0015: usar el **mínimo** de la serie como constante garantizaba la extinción |
| `campo_inicial()` | `campo_inicial(rng=None)` | permite muestrear la dispersión de forma reproducible |
| `SIGMA_ESPACIAL = 4.0` celdas | `SIGMA_FRACCION = 0.08` | **bug encontrado:** en grillas chicas las 3 fumarolas se solapaban y el pico llegaba a 43 °C. La física no puede depender de la resolución. A 50×50 da los mismos 4.0 de antes. |

## Tus tareas nuevas

1. **[Hito 2 — prioritaria] `SalmueraDelicuescente`** en `stochastic.py`. Es la
   contraparte de `MicroFisuraMarte`: con probabilidad `p` por tick **sube** `A_w`
   transitoriamente en un radio, con magnitud y duración muestreadas del `rng`.
   Hoy **todos** tus eventos degradan el ambiente, así que toda corrida está sesgada
   a la extinción por construcción. Este evento es el que hace que Marte tenga algo
   que estudiar (ADR-0015).
2. **[Hito 2] Decaimiento del refugio.** El refugio no puede ser permanente: definí
   cómo se disipa (exponencial en el tiempo, o duración fija). Tratalo como
   **parámetro**, no como constante — Erick va a barrerlo.
3. **[Hito 4] Revisar la asíntota térmica de Marte.** `T_PROFUNDO_C = 7.8` es la
   media de los **mínimos** diarios, pero una onda térmica amortigua hacia la **media
   anual** (≈ 22.4 °C), no hacia el mínimo. No lo toqué porque es tu dominio, pero
   creo que está mal y cambia dónde queda la banda habitable. Decidilo vos.

## Preguntas nuevas para tu agente

8. **Salmuera:** ¿probabilidad de disparo, radio, y hasta qué `a_w` sube? (Para
   reactivar a *D. radiodurans* tiene que superar 0.90.)
9. **Duración:** ¿el refugio dura un tick o varios? Si dura, ¿el evento necesita
   estado interno, o se modela como un decaimiento del campo?
10. **Profundidad:** ¿a qué profundidad física (cm) corresponde una celda? Hace falta
    para justificar la atenuación UV y la asíntota térmica.
