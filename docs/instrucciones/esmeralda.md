# Esmeralda (Biotecnología) — Motor biológico + notebook de análisis

**Carpeta:** `src/astrobiosim/core/microorganism.py` + `notebooks/`
**Tests:** `tests/unit/test_microorganism.py`

> Antes de empezar, tu Claude ya tiene el contexto y los contratos por el
> `CLAUDE.md` de la raíz. Pasale las instrucciones de abajo tarea por tarea.

## Instrucciones para tu Claude

1. Implementá la clase base abstracta `Microorganismo` según el contrato §3.2 del
   `CLAUDE.md`: atributos `t_min, t_max, r_letal, a_w_min, mu_max` y el método
   vectorizado `condiciones_habitables(campo)`.
2. Implementá las tres especies derivadas con estos **valores de partida** (los
   ajusto yo con literatura, ver abajo):
   - `EColi` (control terrestre): `t_min=15, t_max=45, r_letal=50, a_w_min=0.95`.
   - `DRadiodurans` (análogo Marte): radiorresistente `r_letal=5000`, resistente a
     desecación `a_w_min≈0.5`, tolera frío `t_min≈-20, t_max≈45`.
   - `MOkinawensis` (análogo Encelado): termófila `t_min≈50, t_max≈80`, medio
     acuoso `a_w_min≈0.9`, radiación no crítica `r_letal` alto.
3. Escribí tests: cada especie devuelve la máscara correcta cuando **una sola**
   variable está fuera de umbral (una prueba por variable y por especie).

> **Cambios por los datos reales 2025 (ADR-0010) — a resolver con Jose/Fidel:**
> - **`r_letal` ahora en W/m²**, no en Gy (los datos dan flujo radiativo, no dosis).
>   Los valores 50/5000 "Gy" quedan obsoletos como magnitud: **re-derivá los umbrales
>   de radiación en W/m²** con literatura.
> - **Encelado vs. termófila:** los datos de ventila dan **T≈2.4 °C** (océano de fondo),
>   incompatible con *M. okinawensis* (50–80 °C). Decidí: (a) cambiar la especie de
>   Encelado por una **psicrófila**, o (b) que la termófila solo viva en los **picos
>   calientes** del evento hidrotermal (§3.4). Es una decisión biológica tuya + Jose.

## Criterios de aceptación
- Las tres especies instancian y heredan de `Microorganismo`.
- `condiciones_habitables` es **vectorizada** (sin bucles) y devuelve `bool (M,N)`.
- No existe ningún atributo ni lógica de **presión**.
- No hay estados de **latencia** (la muerte es definitiva).

## Tarea de Hito 3 — Notebook de análisis (`notebooks/analisis.ipynb`)
Después del motor biológico (Hito 1), construís el notebook de análisis
retrospectivo (esta tarea era de Erick; la asumís vos):
1. **Corridas Montecarlo:** N repeticiones con semillas explícitas (usá el
   orquestador `simulation.py` de Erick; no reimplementes la simulación).
2. **Curvas poblacionales:** población viva media ± desviación estándar vs. tiempo,
   con matplotlib. Comparación de las **tres dinámicas** (Tierra / Marte / Encelado).
3. **Lectura biológica:** interpretá los colapsos/crecimientos con tu criterio de
   biotecnología (¿son plausibles? ¿qué especie sobrevive en qué entorno y por qué?).
4. Coordinás con Erick: él **valida la estadística** (nº de repeticiones suficiente,
   no confundir una corrida con la distribución); vos aportás la lectura biológica.

## Qué reviso yo (supervisión biológica)
Tu Claude puede escribir el código correcto pero con **parámetros irreales**. Yo
verifico, con mi criterio de biotecnología:
- ¿Los **umbrales** de cada especie son coherentes con la literatura? (E. coli
  mesófila; *D. radiodurans* radiorresistente y anhidrobiótica; *M. okinawensis*
  metanógena termófila que necesita agua). Ajusto los valores de partida.
- ¿La `mu_max` (tasa de reproducción) tiene sentido **relativo** entre especies?
- ¿Se respeta que **no hay latencia**? Ninguna célula debería "revivir".
- ¿La asignación especie↔entorno es defendible (*D. radiodurans* para Marte, etc.)?
