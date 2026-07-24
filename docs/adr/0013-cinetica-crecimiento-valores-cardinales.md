# ADR-0013: Cinética de crecimiento continua por valores cardinales (reemplaza la máscara binaria)

- **Estado:** Aceptado
- **Fecha:** 2026-07-23
- **Modifica:** ADR-0002 (regla de transición), contrato §3.3.
  Depende de: ADR-0012. Relacionado: ADR-0006.

## Contexto

`mu_max` está declarada en el contrato §3.2 desde el Sprint 0 pero **no se usa**: la
habitabilidad es una máscara booleana, así que una celda apenas viable y una celda en
condiciones óptimas se reproducen exactamente igual. Eso desperdicia el único
parámetro cinético del modelo y hace que el resultado sea "vive / muere" en vez de
"crece a tal tasa", que es lo que realmente se mide en el laboratorio.

Esmeralda propuso *"darle valores de prioridad como en las redes neuronales para
favorecer el crecimiento"*. La intuición estructural es correcta y coincide con el
estándar de la microbiología predictiva: el ***gamma concept***, en el que cada
variable ambiental aporta un factor multiplicativo en `[0, 1]` que modula la tasa
óptima. La única diferencia con la propuesta original es de dónde salen los pesos:
**se derivan de valores cardinales publicados**, no se ajustan a mano — y así el
modelo queda citable.

## Decisión

La tasa de crecimiento de una celda `ACTIVA` (ADR-0012) es el producto de factores
independientes:

```
μ(T, a_w, UV) = μ_opt · γ_T(T) · γ_aw(a_w) · γ_UV(UV),    γ_i ∈ [0, 1]
```

**`γ_T` — modelo cardinal con inflexión (CTMI, Rosso et al. 1993):**

```
              (T − T_max)(T − T_min)²
γ_T(T) = ───────────────────────────────────────────────────────────────────────
         (T_opt − T_min)·[ (T_opt − T_min)(T − T_opt)
                           − (T_opt − T_max)(T_opt + T_min − 2T) ]
```

para `T_min < T < T_max`, y `0` fuera. Usa exactamente los tres puntos cardinales que
la literatura reporta por especie (mínimo, óptimo, máximo), sin parámetros libres.

**`γ_aw`** — lineal normalizada entre el mínimo de crecimiento y la saturación:
`γ_aw = (a_w − a_w_min) / (1 − a_w_min)`, recortada a `[0, 1]`, y `0` bajo `a_w_min`.

**`γ_UV`** — decreciente con la irradiancia UV (ADR-0014):
`γ_UV = 1 − UV / uv_max`, recortada a `[0, 1]`, y `0` sobre `uv_max`.

**Uso en el autómata:** `μ` se convierte en la probabilidad de que una celda `ACTIVA`
coloque una hija en un vecino de Moore vacío durante un tick:

```
p_repro = clip(μ · Δt, 0, 1)
```

muestreada con el **`Generator` inyectado** (regla de oro nº6, sin `np.random` global).

## Alternativas consideradas

1. **Pesos ajustados a mano** (propuesta original). Rechazado como implementación
   final: no es citable y convierte cualquier resultado en un artefacto del tuning.
   Se conserva su estructura multiplicativa, que sí era acertada.
2. **Mantener la máscara binaria.** Rechazado: pierde todo el gradiente, no distingue
   "apenas viable" de "óptimo" y deja `mu_max` decorativa.
3. **Ratkowsky / Arrhenius para `γ_T`.** Viables, pero no exponen los tres cardinales
   de forma explícita, así que son menos interpretables y más difíciles de calibrar
   con los datos que Esmeralda ya tiene.

## Consecuencias

- (+) `mu_max` deja de ser decorativa y el resultado pasa de binario a **tasa**.
- (+) Habilita el **análisis de sensibilidad** cuantitativo (qué parámetro domina el
  desenlace), que es un entregable natural para Erick y sube mucho el nivel del
  informe.
- (+) Los tres puntos cardinales por especie están publicados, así que la calibración
  deja de ser una negociación interna y pasa a ser una cita.
- (−) Cada especie necesita un dato nuevo: `t_opt` (disponible en literatura;
  *M. burtonii* = 23.4 °C, *D. radiodurans* ≈ 30 °C, *E. coli* = 37 °C).
- (−) Erick debe implementarlo en `transition_rules.py` y testear los casos borde
  (`T = T_min`, `T = T_opt`, `T = T_max`) — el CTMI es numéricamente delicado cerca
  de los extremos.

## Referencias

- Rosso, Lobry & Flandrois (1993), modelo cardinal con inflexión (CTMI).
- *Gamma concept* (Zwietering / Wijtzes): factores ambientales multiplicativos.
