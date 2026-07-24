# ADR-0010: Ingesta de datasets reales 2025 — esquema canónico multi-fuente, A_w directa y semántica operativa de R

- **Estado:** Aceptado
- **Fecha:** 2026-07-21
- **Modifica a:** [ADR-0005](0005-ingesta-datasets-analogicos.md) (esquema de ingesta) y
  matiza la definición de `R` de [ADR-0003](0003-representacion-estado-y-ambiente.md) /
  [ADR-0008](0008-reduccion-a-tres-variables-ambientales.md).


> **Modificado por ADR-0014:** `R` deja de ser un "proxy operativo" de flujo
> radiativo total y pasa a ser **irradiancia UV** (W/m²). La cuestión abierta sobre
> si el flujo total era defendible como proxy queda resuelta: no lo era. Los
> umbrales `r_letal` se reemplazan por `uv_max` / `uv_letal`.

## Contexto
El equipo consiguió datos reales 2025 (procesados por Esmeralda) para los **tres**
entornos, no solo Atacama. Al inspeccionar su estructura aparecen tres diferencias
respecto de lo que asumían ADR-0005 y el contrato §3.5:

1. **Esquemas heterogéneos** (una fuente por entorno, columnas distintas):
   - `datos_tierra_control_2025.csv` (control, Valles de Fresno): `Temperatura_C`,
     `Radiacion_Solar_W_m2`, `Actividad_Agua_aw`.
   - `datos_atacama_2025_EXTREMOS_REALES.csv` (Marte): `Temp_Maxima_Superficie_C`,
     `Temp_Minima_Superficie_C`, `Radiacion_Solar_Maxima_W_m2`, `Actividad_Agua_Minima_aw`.
   - `datos_ventilas_2025_procesados.csv` (Encelado): `Temp_Ventila_C`, `Salinidad_psu`,
     `Actividad_Agua_aw`, `Radiacion_Infrarroja_W_m2`.
2. **`A_w` viene ya calculada** (0..1) en las tres fuentes → el mapeo
   `A_w = humidity/100` de §3.5 deja de aplicar. (Validación: en ventilas
   `a_w≈0.9817` coincide con el agua de mar a 34.5 psu ≈ 0.9814. Correcto.)
3. **La radiación viene en W/m²** (flujo solar o IR), **no** como dosis ionizante
   acumulada en Gy, que es lo que asumía el modelo (`r_letal` en Gy).

## Decisión

### 1. Esquema canónico nuevo (reemplaza `t, temperature, humidity`)
Cada fuente tiene su **adaptador** en `loaders.py` que devuelve un DataFrame canónico
con columnas EXACTAS:

    "t"            índice temporal
    "temperature" (°C)
    "a_w"         (0..1, provista directamente — sin /100)
    "radiation"   (W/m², flujo radiativo)

Atacama expone además `temperature_min` / `temperature_max` (amplitud térmica diurna).

### 2. `A_w` directa
`resampling.py` usa la columna `a_w` tal cual; se elimina la conversión desde humedad
relativa. Se conserva `A_w = humidity/100` solo como fallback documentado para fuentes
que entreguen humedad en vez de A_w.

### 3. Semántica operativa de `R` (proxy de irradiancia, no dosis en Gy)
Para el MVP, la capa `R` del `CampoAmbiental` se alimenta de la columna `radiation`
(W/m²) como **proxy de carga radiativa**, NO como dosis acumulada en Gy. Consecuencias:
- `r_letal` de cada especie debe re-expresarse en **W/m²** (lo re-deriva Esmeralda).
  Los valores 50/5000 "Gy" quedan obsoletos como magnitud absoluta.
- **Mapeo por entorno** (en `resampling.py`, coordinado con Jose): superficies
  (Tierra, Atacama) usan la radiación solar como `R`; **Encelado subglacial mapea
  `R ≈ 0`** — su columna IR (~320 W/m²) es calor, no dosis que dañe ADN, así que NO
  se usa como estrés radiativo (la protección total del hielo se mantiene, ADR-0008).

## Consecuencias
- (+) **La arquitectura de dos motores NO cambia.** El `CampoAmbiental`, el Autómata
  Celular (§3.3) y el orquestador siguen igual: absorben los datos por la misma
  frontera. Esto valida ADR-0001/0003.
- (+) Un solo formato canónico downstream pese a tres esquemas crudos distintos.
- (+) Atacama habilita un análisis extra **sin redundancia**: amplitud térmica diurna
  (max/min) como estresor marciano.
- (−) Cambia el contrato §3.5 (loaders por fuente + columnas nuevas) y la unidad de
  `r_letal`. Requiere re-calibrar umbrales de radiación (Esmeralda).
- (−) `resampling.py` debe **imputar/enmascarar** el hueco de 8 días (17–24 ago) de
  ventilas sin inventar valores (Fidel).

## Riesgos / cuestiones abiertas (a resolver por sus dueños, no aquí)
1. **Encelado vs. termófila.** ✅ **RESUELTO por ADR-0011:** los datos de ventila dan
   T≈2.4 °C (océano de fondo), incompatible con *M. okinawensis* (50–80 °C). Se
   reemplaza la especie de Encelado por **Methanococcoides burtonii** (metanógena
   psicrotolerante, T≈-2…29 °C), compatible con la T del análogo.
2. **Defensa del proxy de R.** Documentar en el informe que W/m² ≠ dosis ionizante;
   es una aproximación de estrés radiativo para análogos terrestres (Fidel valida).

## Datasets evaluados y descartados (trazabilidad)
- **NASA Exoplanet Archive** (template de parámetros) y **PHL Habitable Worlds
  Catalog**: fuera de alcance. El proyecto simula subsuelos de Tierra/Marte/Encelado
  con análogos terrestres; **nunca** incluyó exoplanetas (no hay ADR que los descarte
  porque nunca estuvieron en el alcance — ver `openspec/project.md`). Sus columnas
  (periodo orbital, masa/radio planetario, ESI) no aportan series de T/R/A_w de subsuelo.
- **PANGAEA IMAU Antarctic** (19 estaciones): es el dataset que **ADR-0008 ya
  descartó** al eliminar la presión. Reintroducirlo sería redundante con los tres
  análogos actuales y reabriría el problema de unidades de radiación. No se usa.
- **CRC1211DB (Atacama)**: fuente **autoritativa** del Atacama procesado (descarga
  bajo solicitud). Se cita como origen (ADR-0005); no se re-ingiere si el procesado
  de Esmeralda es suficiente.
