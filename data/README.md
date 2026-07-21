# Datos — AstroBioSim

Convención de directorios:
- `raw/` — datos crudos de fuentes externas. **No se versionan** (ver `.gitignore`);
  cada quien los descarga de la fuente. Solo se versiona este README y los `.gitkeep`.
- `processed/` — series limpias listas para el simulador. Se versionan **solo** los
  tres CSV canónicos de abajo (pequeños y esenciales para reproducir las corridas).

## Datasets en uso (uno por entorno, sin redundancia)

| Archivo | Entorno | Fuente / análogo | Columnas |
|---|---|---|---|
| `processed/datos_tierra_control_2025.csv` | Tierra (control) | Valles de Fresno, California | `Fecha, Temperatura_C, Radiacion_Solar_W_m2, Actividad_Agua_aw` |
| `processed/datos_atacama_2025_EXTREMOS_REALES.csv` | Marte | Desierto de Atacama — CRC1211DB | `Fecha, Temp_Maxima_Superficie_C, Temp_Minima_Superficie_C, Radiacion_Solar_Maxima_W_m2, Actividad_Agua_Minima_aw` |
| `processed/datos_ventilas_2025_procesados.csv` | Encelado | Ventilas hidrotermales (A_w derivada de salinidad) | `Fecha, Temp_Ventila_C, Salinidad_psu, Actividad_Agua_aw, Radiacion_Infrarroja_W_m2` |

Todos: series diarias de 2025 (365 filas). Ver **ADR-0010** para el esquema canónico
(`t, temperature, a_w, radiation`) al que los adaptadores de `loaders.py` los mapean.

## Procedencia y licencias (COMPLETAR antes de entregar)
- **Atacama** ← CRC1211DB: *Hoffmeister, D. (2018), Meteorological and soil measurements
  of the permanent weather stations in the Atacama desert, Chile.* DOI
  `10.5880/CRC1211DB.1`. Licencia CC-BY (requiere atribución).
- **Tierra (Fresno)** y **Ventilas** ← procesados por Esmeralda; **falta documentar la
  fuente primaria y su licencia** (responsable: Esmeralda/Fidel).

## Avisos de calidad (verificado 2026-07-21)
- `ventilas`: **hueco de 8 días** (17–24 ago 2025) con NaN → `resampling.py` debe
  imputar/enmascarar sin inventar valores. `A_w≈0.9817` (constante, coherente con agua
  de mar a 34.5 psu). **T≈2.4 °C**: es agua de fondo, NO la termófila — ver riesgo #1 de ADR-0010.
- `tierra`, `atacama`: sin NaN. Rangos físicos correctos.
- **Radiación en W/m²** (flujo), no dosis en Gy: se usa como proxy operativo de `R`
  (ADR-0010). Encelado mapea `R≈0` (su IR es calor, no dosis ionizante).

## Fuera de alcance (no se usan)
- **NASA Exoplanet Archive**, **PHL Habitable Worlds Catalog**: exoplanetas — fuera del
  alcance del proyecto (subsuelos del Sistema Solar vía análogos terrestres).
- **PANGAEA IMAU Antarctic**: descartado en ADR-0008 (iba con la presión, ya eliminada).
