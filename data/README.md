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
  de mar a 34.5 psu). **T≈2.4 °C**: agua de fondo, coherente con la especie
  psicrotolerante `MBurtonii` (ADR-0011), no con la termófila previa.
- `tierra`, `atacama`: sin NaN. Rangos físicos correctos.
- **Radiación en W/m²**: la columna trae **irradiancia global**, y `R` es
  **irradiancia UV** (ADR-0014, reemplaza el proxy de flujo de ADR-0010). Solo
  **Marte** convierte multiplicando por la fracción UV (`resampling.mapear_radiacion`,
  factor documentado): es el único subsuelo parcialmente transparente al UV. No se
  usa dosis en Gy: a 0.077 Gy/año en Marte, la dosis ionizante no discrimina en la
  escala de la simulación. **Tierra y Encelado mapean `R = 0`**: el subsuelo
  terrestre bloquea el UV por completo (`TierraSubsuelo.UV_SUBSUELO`), y en
  Encelado el IR de la ventila es calor, no UV.
- **`Actividad_Agua_Minima_aw` (Atacama) es el MÍNIMO diario**, una cota inferior
  pesimista — no el valor típico. Se sigue usando tal cual fila a fila en el Modo
  Analógico (es el dato real disponible). **`MarteSubsuelo.A_W_MEDIA`/`A_W_SIGMA`
  (constante de Modo Sandbox) — CORREGIDA (2026-07-26).** Se re-derivó de la
  humedad relativa cruda (10 min) de la estación CRC1211DB 13 "Cerros de Calate":
  la media diaria real es **0.382** (antes 0.187, la media de los mínimos
  diarios) — el doble, como se esperaba. Metodología reproducible en
  `scripts/derivar_a_w_media_atacama.py`; detalle en `docs/parametros.md` §2/§4.
- **`Actividad_Agua_aw` (Tierra) — CORREGIDA (2026-07-24).** La columna original
  se había calculado con la humedad relativa del **aire** (`A_w = HR / 100`), no
  del suelo, y por eso oscilaba 0.16–0.93 (media 0.55, sd 0.23) — un suelo no hace
  eso. Esmeralda lo detectó. Al no haber medición de `a_w` de suelo, se reemplazó
  por **`a_w = 0.99` constante**, valor de un suelo a **capacidad de campo**
  (asunción física del control, no un dato medido). Con esto el control es un
  subsuelo húmedo estable, coherente con `TierraSubsuelo`.

## Fuera de alcance (no se usan)
- **NASA Exoplanet Archive**, **PHL Habitable Worlds Catalog**: exoplanetas — fuera del
  alcance del proyecto (subsuelos del Sistema Solar vía análogos terrestres).
- **PANGAEA IMAU Antarctic**: descartado en ADR-0008 (iba con la presión, ya eliminada).
