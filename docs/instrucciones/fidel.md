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
   **mapeo por entorno** (Marte: `radiation × FRACCION_UV`; **Tierra y Encelado
   `R=0`**, el subsuelo terrestre bloquea el UV por completo y el IR de Encelado es
   calor, no UV — ADR-0014). Coordiná el gradiente térmico con Jose.
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

1. ~~**[Hito 1 — prioritaria] Convertir `radiation` a banda UV.**~~ ✅ **REVISADO
   (2026-07-25).** El factor `FRACCION_UV = 0.05` ya estaba documentado y
   coordinado con Esmeralda (ver `docs/parametros.md` §1.3 y §2: `uv_max`/`uv_letal`
   y `UV_SUPERFICIE ≈ 42.2 W/m²` se derivan de la misma constante, y ese valor cae
   dentro del rango publicado de UV marciano, 42–55 W/m²). No hay dato real de banda
   por fuente disponible, así que `FRACCION_UV` sigue como **[CONV]** documentada.
   Se corrigió un bug real en `resampling.mapear_radiacion`: mapeaba **Tierra**
   como si convirtiera `radiation × FRACCION_UV` (UV no nulo), pero el modelo real
   (`TierraSubsuelo.campo_modulado`, `UV_SUBSUELO = 0.0`) siempre da `R = 0` ahí —
   el subsuelo terrestre bloquea el UV por completo, igual que Encelado lo bloquea
   por hielo. Ahora `mapear_radiacion` solo convierte para **Marte** (el único
   subsuelo parcialmente transparente al UV); Tierra y Encelado mapean a `0`. Tests
   actualizados en `tests/unit/test_resampling.py`.
2. ~~**[Hito 1] Re-extraer la `a_w` media de Atacama.**~~ ✅ **RESUELTO
   (2026-07-26).** La columna procesada (`Actividad_Agua_Minima_aw`) solo trae el
   **mínimo diario**; para la media real había que ir a la fuente. Se descargó la
   humedad relativa cruda (10 min) de la estación CRC1211DB 13 ("Cerros de
   Calate", `https://www.crc1211db.uni-koeln.de/wd/index.php?station=13`, sin
   necesidad de solicitud formal pese a lo que decía ADR-0010) y se recalculó
   `a_w = RH/100` por lectura, promedio diario, media/sd de esos promedios.
   Resultado: `MarteSubsuelo.A_W_MEDIA` pasa de 0.187 a **0.382** (el doble) y
   `A_W_SIGMA` de 0.080 a **0.256**. Validación: la media de los MÍNIMOS diarios
   de esta misma serie cruda (0.185) coincide con el 0.187 ya documentado, lo que
   confirma que es la estación correcta. Caveat honesto: la estación solo tiene
   datos 2025-03-27..12-06 (146 días, falta el verano austral); no cambia la
   tabla de resultados de §3 en `parametros.md` porque 0.382 sigue muy por debajo
   del `a_w_min = 0.90` de *D. radiodurans* (verificado corriendo `campo_inicial()`
   con ambos valores). Metodología reproducible en
   `scripts/derivar_a_w_media_atacama.py` (el .txt crudo no se versiona, como el
   resto de `data/raw/`).
3. ~~**[Hito 1] Documentar el problema del control terrestre.**~~ ✅ **RESUELTO
   (2026-07-24).** Esmeralda confirmó que la `a_w` de Fresno se calculó con humedad
   del **aire** (por eso oscilaba 0.16–0.93). Como no hay medición de `a_w` de
   suelo, el dataset `datos_tierra_control_2025.csv` se corrigió a **`a_w = 0.99`
   constante** (suelo a capacidad de campo, asunción física documentada en
   `data/README.md`). Coincide con `TierraSubsuelo.A_W_SUBSUELO`.
4. ~~**[Hito 2] `resampling.py`**~~ ✅ **IMPLEMENTADO (2026-07-24)** en la rama
   `feat/data-resampling`: `limpiar_ventilas` (interpolación lineal acotada del
   hueco de 8 días), `secuencia_campos` (un `CampoAmbiental` por día) y
   `modes/analog.py` (`ModoAnalogico`, cumple la interfaz `ModoSimulacion` de
   `modes/base.py`). **Decisión clave (ADR-0017):** el escalar diario se propaga
   con el modelo espacial de Jose (`campo_modulado`), no aplanando el campo —así
   Marte conserva su banda de profundidad. Revisión de la banda UV completada
   (tarea 1, ✅ 2026-07-25); queda pendiente la `a_w` media de Atacama (tarea 2 /
   deuda #1).

## Preguntas nuevas para tu agente

7. **Banda UV:** ¿UV-A+UV-B (~5 % del global), solo UV-B, o dosis DNA-ponderada? Debe
   coincidir con la banda de Esmeralda.
8. **`a_w` de Atacama:** ¿la fuente original permite extraer media y desviación, o solo
   tenemos el mínimo diario ya agregado?
9. **`a_w` de suelo vs. aire:** ¿hay alguna fuente de `a_w` de suelo para Fresno, o
   documentamos el valor teórico como limitación conocida del modelo?

## Estado (2026-07-27)

- ✅ **Validación biológica de las salidas IMPLEMENTADA** en la rama
  `chore/validacion-datos`. Los 3 criterios de la tarjeta, cubiertos por
  `tests/integration/test_validacion_biologica.py` (10 tests, integración con los
  datasets reales):
  1. **Sin artefactos** — ninguna de las 3 corridas análogas se extingue de golpe
     (`viva > 0` en todo tick) ni satura de forma irreal (`max|Δactiva|` por tick
     < 0.5); Marte da **supervivencia latente sin crecimiento** (ADR-0015), no
     extinción total.
  2. **Banda UV en el adaptador** — `mapear_radiacion` aplica `FRACCION_UV` en Marte
     (UV ∈ 42–55 W/m², rango publicado) y la anula en Tierra/Encelado; el factor es
     una constante nombrada y documentada, no un número mágico (ADR-0014 reemplaza
     el proxy W/m² vs Gy).
  3. **Hostil < control** — aislando el entorno con la MISMA especie (*E. coli*):
     prospera en Tierra y se extingue en Marte (regolito seco).
  Figura para la defensa: `docs/toBePresented/validacion_biologica_3entornos.png`
  (composición \MUERTA/\LATENTE/\ACTIVA en el tiempo, media ± σ, las 3 corridas),
  reproducible con `scripts/validacion_biologica.py`.
- ⚠️ **Límite del mapeo de datos documentado (criterio 3 de tu revisión):** el modo
  Analógico alimenta la **temperatura diaria de superficie** tal cual (Tierra oscila
  4.9–36.5 °C, media 19.85), **sin amortiguarla al subsuelo tick a tick**. El
  amortiguamiento a la media anual estable (19.8 °C de `fisica.tex`) vive en el campo
  medio/estático, no en cada tick del análogo. Por eso *E. coli* en Tierra cae a
  `LATENTE` en los días fríos (T < `t_min` = 7.5 °C) antes de colonizar la grilla —
  **no es un artefacto numérico, es la respuesta correcta al dato real**, pero
  conviene declararlo como límite del análogo (mismo espíritu que la corrección de
  `a_w` de aire → suelo). Ver deuda §4 candidata: amortiguar la serie diaria al
  subsuelo en el modo Analógico, o documentar que el control análogo es "superficie",
  no "subsuelo estable".
