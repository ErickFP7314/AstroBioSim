# ADR-0005: Ingesta y remuestreo de datasets análogos (Modo Analógico)

- **Estado:** Aceptado
- **Fecha:** 2026-07-15
- **Modificado por:** [ADR-0008](0008-reduccion-a-tres-variables-ambientales.md) — se elimina la variable `P` y con ella el dataset IMAU Antarctic; el Modo Analógico depende ahora de una sola fuente (Atacama).

## Contexto
El Modo Analógico inyecta parámetros ambientales iteración por iteración desde
datasets de ambientes extremos terrestres:

- **Marte (Regolito):** dataset **CRC1211DB** (Desierto de Atacama) →
  `soil temperature` para el gradiente térmico del regolito; `relative humidity`
  para la actividad de agua vía `A_w = HR / 100`.
- Tras ADR-0008 esta es la **única** fuente del Modo Analógico. (El dataset
  IMAU Antarctic quedó descartado al eliminarse la presión.)

## Decisión
Definir una capa de datos con dos responsabilidades separadas:

- **Loaders** (`data/loaders.py`): una función/clase por fuente que devuelve un
  `DataFrame` normalizado con columnas canónicas (`t`, `temperature`,
  `humidity`), aislando el esquema crudo del dataset.
- **Remuestreo** (`data/resampling.py`): limpieza (huecos, outliers) y
  *downsampling*/interpolación a un paso temporal común, produciendo una
  secuencia de `CampoAmbiental` indexada por iteración.

El mapeo físico → variables de simulación se centraliza aquí:
`A_w = relative_humidity / 100` y gradiente térmico a partir de
`soil temperature`. Los tres entornos consumen `CampoAmbiental` idénticos al de
Sandbox, por lo que el bucle no distingue el origen (DRY).

**Fallback:** si un dataset no está disponible o su esquema difiere, un generador
sintético con la misma interfaz produce series plausibles, de modo que el
desarrollo del motor no se bloquea por dependencias de datos.

## Alternativas consideradas
1. **Leer los CSV crudos directamente en el bucle de simulación.** Rechazado:
   acopla el motor al esquema de cada dataset y rompe la reproducibilidad.
2. **Pre-materializar todo a un único archivo procesado.** Útil como caché
   (`data/processed/`), pero se mantiene la capa de loaders para trazabilidad.

## Consecuencias
- (+) Añadir una fuente nueva = un loader nuevo, sin tocar el motor.
- (+) El remuestreo reproducible (semilla + parámetros documentados) permite
  comparar corridas.
- (+) Con una sola fuente (Atacama) desaparece el problema de sincronizar dos
  series de resolución temporal distinta (ver ADR-0008).
- (−) Requiere acordar el esquema canónico temprano para no rehacer los mapeos.
- (−) Riesgo de acceso/formato del dataset real → mitigado por el fallback
  sintético.
