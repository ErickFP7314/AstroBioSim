# Fidel (Biotecnología) — Datos análogos + validación

**Carpeta:** `src/astrobiosim/data/` y `src/astrobiosim/modes/analog.py`
**Tests:** `tests/unit/test_data.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

> **Cambio de datos (ADR-0010):** ahora hay datos reales 2025 para los **tres**
> entornos, con esquemas crudos distintos y `A_w` ya calculada. Ver `data/README.md`.

1. `loaders.py`: **un adaptador por fuente** que aísla su esquema crudo y devuelve el
   DataFrame CANÓNICO nuevo (`t, temperature, a_w, radiation`; Atacama además
   `temperature_min/max`):
   - `cargar_control_tierra(ruta)` ← `datos_tierra_control_2025.csv` (Fresno).
   - `cargar_atacama(ruta)` ← `datos_atacama_2025_EXTREMOS_REALES.csv` (Marte).
   - `cargar_ventilas(ruta)` ← `datos_ventilas_2025_procesados.csv` (Encelado).
   Mantené el **fallback sintético** con la misma interfaz canónica. **Ojo:** `a_w`
   viene directa (0..1); ya NO se hace `humidity/100`.
2. `resampling.py`: limpieza y remuestreo a un paso común. **Imputá/enmascará el hueco
   de 8 días (17–24 ago) de ventilas** sin inventar valores. Producí la secuencia de
   `CampoAmbiental`: `A_w` tal cual; `R` = **irradiancia UV** desde `radiation` con
   **mapeo por entorno** (superficies: `radiation × FRACCION_UV`; **Encelado `R=0`**,
   su IR es calor, no UV — ADR-0014). Coordiná el gradiente térmico con Jose.
3. `modes/analog.py`: estrategia que entrega el `CampoAmbiental` de cada iteración
   al orquestador. Debe compartir el mismo bucle que Sandbox (DRY).
4. Tests: el mapeo a banda UV aplica el factor (no pasa el flujo global tal cual);
   el remuestreo no inventa valores fuera de rango físico; el fallback produce
   series en rango.

## Criterios de aceptación
- Una sola fuente real (Atacama); columnas canónicas **exactas**.
- `A_w` siempre en `[0, 1]`.
- El modo Analógico **no duplica** el bucle de Sandbox.
- El fallback sintético respeta la misma interfaz que el loader real.

## Qué reviso yo (validez de datos y resultados)
Con mi criterio de biotecnología verifico:
- **Radiación como UV (ADR-0014):** la pregunta de si el flujo total era un proxy
  defendible ya se respondió, y la respuesta fue **no**: la insolación global es
  visible e IR y no esteriliza. `R` es irradiancia UV. Lo que sí hay que documentar
  es la **banda** y el **factor de conversión** que usás.
- ¿El **remuestreo** no borra ciclos biológicamente relevantes (día/noche, estacional)?
- ¿El dataset de Atacama es un **análogo marciano** defendible? ¿El fallback hay
  que documentarlo como "solo para pruebas"?
- **Validación de salida:** ¿las poblaciones colapsan/crecen de forma
  biológicamente plausible, o hay artefactos (extinción instantánea, saturación irreal)?

## Mapa: tarea → historia de usuario (Trello)
Tablero: https://trello.com/b/cK8VP1aj — etiqueta 🟡 **Fidel**. Los criterios de
aceptación de cada historia están en el checklist de su tarjeta.

| Tarea de este archivo | Historia de usuario | Hito |
|---|---|---|
| Tarea 1 (`loaders.py` + fallback sintético) | **Capa de datos: loaders + DataFrame canónico** | Hito 1 |
| Tareas 2-3 (`resampling.py` + `modes/analog.py`) | **Remuestreo + Modo Analógico** | Hito 2 |
| Sección "Qué reviso yo" (validez de datos y salidas) | **Validación biológica de las salidas** | Hito 4 |

## Preguntas para configurar tu agente de IA
Respondé esto antes de que tu Claude implemente; si no, asumirá defaults que quizá no querés:
1. **Paso temporal:** los datasets son diarios (365 filas 2025). ¿Se remuestrea a diario o a otra resolución?
2. **Hueco de ventilas (8 días NaN):** ¿excluir esas iteraciones o interpolar linealmente de forma acotada?
3. **Mapeo escalar→grilla:** una fila temporal es un escalar por variable. ¿Campo uniforme por tick, o se le aplica el gradiente espacial de Jose?
4. **Atacama (`temperature_min/max`):** ¿se genera un ciclo diurno sintético entre min y max, o se usa solo la media?
5. **Fallback sintético:** ¿con qué distribución/rangos genera cada variable cuando no hay dataset?
6. **Duración de corrida analógica:** ¿365 iteraciones? Si la simulación es más larga, ¿se recicla la serie o se detiene?

---

# 🔄 Actualización 2026-07-23 — ADR-0012 a 0015

> 📐 **Todo valor numérico del modelo vive en `docs/parametros.md`** con su
> procedencia y su cita. Antes de fijar o cambiar un umbral, mirá ahí — y si lo
> cambiás, actualizá esa tabla en el mismo commit.


> Tu capa de datos no cambia de forma, pero **sí cambia el significado de dos
> columnas**. Esto salió de integrar los motores de Esmeralda y Jose.

## Lo que cambia en el contrato §3.5

| Columna | Antes | Ahora |
|---|---|---|
| `radiation` | flujo radiativo total (W/m²) | **irradiancia UV** (W/m²) — ADR-0014 |
| `a_w` | se usaba tal cual | sigue igual, **pero ojo con el origen** (ver abajo) |

## Tus tareas nuevas

1. **[Hito 1 — prioritaria] Convertir `radiation` a banda UV.** Los datasets dan
   irradiancia **global**, que es mayormente visible e infrarroja y no esteriliza.
   Multiplicá por la fracción UV y **dejá el factor documentado en el adaptador**,
   no escondido en una constante. Hoy hay un `FRACCION_UV = 0.05` en
   `core/environment.py` como valor de trabajo; si conseguís el dato real de la banda
   por fuente, mejor. Coordiná la **banda exacta** con Esmeralda: tiene que ser la
   misma con la que ella derive `uv_max` / `uv_letal`.
2. **[Hito 1] Re-extraer la `a_w` media de Atacama.** La columna disponible es
   `Actividad_Agua_Minima_aw`, o sea el **mínimo diario**: una cota inferior
   pesimista, no el valor típico. Usarla como valor del campo garantizaba la
   extinción. Necesitamos la media (y ojalá la dispersión) de la serie real.
3. **[Hito 1] Documentar el problema del control terrestre.** La columna
   `Actividad_Agua_aw` de Fresno (media 0.55, rango 0.16–0.93) es **humedad relativa
   del aire**, no actividad de agua del suelo — un suelo no oscila así de un día
   para otro. Para un modelo de **subsuelo** no sirve directa. Dos salidas: conseguir
   `a_w` de suelo, o documentar explícitamente que el control usa un valor teórico de
   capacidad de campo (0.99). Esto es exactamente el tipo de límite que tu sección
   "Qué reviso yo" existe para cazar.
4. **[Hito 2] `resampling.py`:** el mapeo por entorno ahora es UV. Superficies:
   `radiation × fracción UV`. **Encelado sigue en `R = 0`** — y ahora hay un motivo
   más fuerte: sus 320 W/m² de `Radiacion_Infrarroja_W_m2` son **calor**, no UV.

## Preguntas nuevas para tu agente

7. **Banda UV:** ¿UV-A+UV-B (~5 % del global), solo UV-B, o dosis DNA-ponderada? Debe
   coincidir con la banda de Esmeralda.
8. **`a_w` de Atacama:** ¿la fuente original permite extraer media y desviación, o solo
   tenemos el mínimo diario ya agregado?
9. **`a_w` de suelo vs. aire:** ¿hay alguna fuente de `a_w` de suelo para Fresno, o
   documentamos el valor teórico como limitación conocida del modelo?
