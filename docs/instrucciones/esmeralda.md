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
>   👉 Te dejé candidatas concretas (con umbrales de partida y recomendación:
>   *Methanococcoides burtonii*) en **`docs/notas/encelado-especie-psicrofila.md`**.

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

## Mapa: tarea → historia de usuario (Trello)
Tablero: https://trello.com/b/cK8VP1aj — etiqueta 🟢 **Esmeralda**. Los criterios de
aceptación de cada historia están en el checklist de su tarjeta.

| Tarea de este archivo | Historia de usuario | Hito |
|---|---|---|
| Tareas 1-3 (`Microorganismo` + 3 especies + tests) | **Motor biológico: especies y habitabilidad** | Hito 1 |
| (nueva) `modes/sandbox.py` | **Modo Sandbox** (detalle en el tablero) | Hito 2 |
| "Tarea de Hito 3 — Notebook de análisis" | **Notebook de análisis** | Hito 3 |
| Bloque ADR-0010 + supervisión de umbrales | **Calibración de umbrales con literatura** | Hito 4 |

## Preguntas para configurar tu agente de IA
Respondé esto antes de que tu Claude implemente; si no, asumirá defaults que quizá no querés:
1. **Encelado:** ¿qué especie final? Recomendación de la nota: *M. burtonii* psicrófila, o mantener la termófila solo en los picos calientes — ver `docs/notas/encelado-especie-psicrofila.md`.
2. **Umbrales:** ¿fijás vos los valores calibrados (`t_min`/`t_max`/`r_letal` en W/m²/`a_w_min`) o el agente propone y vos ajustás con literatura?
3. **mu_max relativo:** ¿qué especie se reproduce más rápido? ¿Qué orden relativo entre las tres?
4. **Estado inicial de la grilla:** ¿% de celdas vivas al arranque y cómo se distribuyen (aleatorio uniforme, cluster central)?
5. **Notebook:** ¿nº de repeticiones Montecarlo y semilla(s) por defecto?
6. **Curvas:** ¿qué métrica graficás (población absoluta viva, fracción viva, media ± σ)?
7. **Sandbox:** ¿qué rangos mín/máx para los sliders de T, R y A_w?
