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
   - `MBurtonii` (análogo Encelado, ADR-0011): metanógena **psicrotolerante**
     `t_min≈-2, t_max≈29`, medio acuoso `a_w_min≈0.94`, radiación no crítica
     `r_letal` alto (R≈0 subglacial). Reemplaza a la termófila *M. okinawensis*.
3. Escribí tests: cada especie devuelve la máscara correcta cuando **una sola**
   variable está fuera de umbral (una prueba por variable y por especie).

> **Cambios por los datos reales 2025 (ADR-0010) — a resolver con Jose/Fidel:**
> - **`r_letal` ahora en W/m²**, no en Gy (los datos dan flujo radiativo, no dosis).
>   Los valores 50/5000 "Gy" quedan obsoletos como magnitud: **re-derivá los umbrales
>   de radiación en W/m²** con literatura.
> - **Encelado — especie decidida (ADR-0011):** la termófila *M. okinawensis* se
>   reemplaza por **`MBurtonii`** (metanógena psicrotolerante, T≈-2…29 °C), porque
>   los datos de ventila dan **T≈2.4 °C**. Umbrales de partida y justificación en
>   **`docs/notas/encelado-especie-psicrofila.md`**. Solo falta que re-calibres los
>   valores finales con literatura.

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
  mesófila; *D. radiodurans* radiorresistente y anhidrobiótica; *M. burtonii*
  metanógena psicrotolerante que necesita agua líquida — ADR-0011). Ajusto los valores de partida.
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
1. **Encelado (especie ya decidida — `MBurtonii`, ADR-0011):** ¿confirmás los umbrales de partida (`t_min≈-2`, `t_max≈29`, `a_w_min≈0.94`, `r_letal` alto) o los ajustás con literatura antes de implementar?
2. **Umbrales:** ¿fijás vos los valores calibrados (`t_min`/`t_max`/`r_letal` en W/m²/`a_w_min`) o el agente propone y vos ajustás con literatura?
3. **mu_max relativo:** ¿qué especie se reproduce más rápido? ¿Qué orden relativo entre las tres?
4. **Estado inicial de la grilla:** ¿% de celdas vivas al arranque y cómo se distribuyen (aleatorio uniforme, cluster central)?
5. **Notebook:** ¿nº de repeticiones Montecarlo y semilla(s) por defecto?
6. **Curvas:** ¿qué métrica graficás (población absoluta viva, fracción viva, media ± σ)?
7. **Sandbox:** ¿qué rangos mín/máx para los sliders de T, R y A_w?

---

# 🔄 Actualización 2026-07-23 — ADR-0012 a 0015

> Tu Hito 1 quedó **aprobado y mergeado**. Lo que sigue son los cambios que trajo el
> bloque ADR-0012…0015, que nació justamente de integrar tu motor con el de Jose.

## Lo que ya se corrigió en tu archivo (no lo rehagas)

| Antes | Ahora | Por qué |
|---|---|---|
| Un umbral por variable | **Dos**: crecimiento y supervivencia | ADR-0012 |
| `DRadiodurans.a_w_min = 0.75` | `a_w_min = 0.90` + `a_w_sup_min = 0.0` | 0.90 es su límite metabólico real; la anhidrobiosis va al umbral de supervivencia |
| `MBurtonii.t_max = 20` | `t_min=-2.5, t_opt=23.4, t_max=29.5` | valores publicados; ahora los núcleos de fumarola son habitables |
| `MBurtonii.a_w_min = 0.98` | `0.95` | 0.98 quedaba exactamente al filo del campo |
| `r_letal` | `uv_max` / `uv_letal` | ADR-0014: `R` es UV, no radiación total |
| `mu_max` | `mu_opt` + nuevo `t_opt` | ADR-0013 necesita los tres puntos cardinales |

Tenías razón en todo lo que dijiste: *E. coli* no se tocó (0.95 sigue siendo dato
duro), y tu intuición de los "pesos que favorecen el crecimiento" se convirtió en el
ADR-0013 tal cual, solo que con los pesos sacados de literatura.

## Tus tareas nuevas

1. **[Hito 4] Re-derivar los umbrales UV.** `uv_max` y `uv_letal` de las tres
   especies están marcados `# PROVISIONAL` en el código: los puse por orden de
   magnitud (*D. radiodurans* ≈ 20× *E. coli*) para desbloquear al resto, pero el
   valor con literatura lo ponés vos. Es el único parámetro del modelo que hoy no
   está citado.
2. **[Hito 4] Validar los umbrales de supervivencia.** `t_sup_min/max` y
   `a_w_sup_min` son mi mejor estimación, no literatura. El de *D. radiodurans*
   (`a_w_sup_min = 0.0`, anhidrobiosis) es el más defendible; los otros dos
   revisalos.
3. **[Hito 3] El notebook cambia de métrica.** Ya no es una curva de población viva:
   son **tres** — fracción `ACTIVA`, `LATENTE` y `MUERTA` en el tiempo. La lectura
   biológica interesante pasa a ser la transición latente↔activa en Marte cuando
   aparece un microrefugio.

## Preguntas nuevas para tu agente

8. **UV:** ¿en qué banda derivás los umbrales (UV-B, UV-C, dosis DNA-ponderada)? Debe
   ser la misma banda que use Fidel al convertir la columna `radiation`.
9. **Supervivencia:** ¿cuánto tiempo puede una célula quedar `LATENTE` antes de morir,
   o la latencia es indefinida mientras esté dentro del rango de supervivencia?
10. **Reactivación:** ¿una célula latente vuelve a `ACTIVA` de inmediato al mejorar las
    condiciones, o hay un retardo (lag de recuperación)?
