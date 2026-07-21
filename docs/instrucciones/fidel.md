# Fidel (Biotecnología) — Datos análogos + validación

**Carpeta:** `src/astrobiosim/data/` y `src/astrobiosim/modes/analog.py`
**Tests:** `tests/unit/test_data.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

1. `loaders.py`: `cargar_atacama(ruta)` lee el dataset CRC1211DB y devuelve el
   DataFrame canónico del contrato §3.5 (`t, temperature, humidity`), aislando el
   esquema crudo. Incluí un **fallback sintético** (`generar_serie_sintetica(...)`)
   con la misma interfaz por si el dataset no está disponible.
2. `resampling.py`: limpieza (huecos/outliers) y remuestreo a un paso temporal
   común; producí la secuencia de `CampoAmbiental` aplicando `A_w = humidity/100`
   y el gradiente térmico del regolito (coordino el gradiente con Jose).
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
- ¿El mapeo **`A_w = HR/100`** es una aproximación aceptable para el informe? ¿Hay
  que aclarar sus límites?
- ¿El **remuestreo** no borra ciclos biológicamente relevantes (día/noche, estacional)?
- ¿El dataset de Atacama es un **análogo marciano** defendible? ¿El fallback hay
  que documentarlo como "solo para pruebas"?
- **Validación de salida:** ¿las poblaciones colapsan/crecen de forma
  biológicamente plausible, o hay artefactos (extinción instantánea, saturación irreal)?
