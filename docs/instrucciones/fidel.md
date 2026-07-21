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
   `CampoAmbiental`: `A_w` tal cual; `R` desde `radiation` (W/m²) con **mapeo por
   entorno** (superficies = radiación solar; **Encelado `R≈0`**, su IR es calor, no
   dosis). Coordiná el gradiente térmico con Jose.
3. `modes/analog.py`: estrategia que entrega el `CampoAmbiental` de cada iteración
   al orquestador. Debe compartir el mismo bucle que Sandbox (DRY).
4. Tests: el mapeo `A_w = HR/100` es correcto; el remuestreo no inventa valores
   fuera de rango físico; el fallback produce series en rango.

## Criterios de aceptación
- Una sola fuente real (Atacama); columnas canónicas **exactas**.
- `A_w` siempre en `[0, 1]`.
- El modo Analógico **no duplica** el bucle de Sandbox.
- El fallback sintético respeta la misma interfaz que el loader real.

## Qué reviso yo (validez de datos y resultados)
Con mi criterio de biotecnología verifico:
- **Radiación como W/m² (no Gy):** los datos dan flujo radiativo, no dosis ionizante.
  ¿Es defendible usarlo como proxy de `R` en el informe? Documentá el límite (ADR-0010).
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
