# ADR-0014: `R` reencuadrada como irradiancia UV (W/m²) con atenuación en el subsuelo

- **Estado:** Aceptado
- **Fecha:** 2026-07-23
- **Modifica:** ADR-0010 (definición de `R`), contrato §3.5 (adaptadores de datos).
  Depende de: ADR-0012. Relacionado: ADR-0008.

## Contexto

ADR-0010 definió `R` como **flujo radiativo total en W/m²** ("proxy operativo") y los
umbrales `r_letal` en las mismas unidades. Al calibrar aparece la incoherencia: la
insolación total medida en Atacama (≈ 844 W/m²) es mayoritariamente visible e
infrarroja — **no es dosis ionizante**. Comparar un `r_letal` contra ella no tiene
significado biológico; son magnitudes físicas distintas.

Los números de la literatura lo confirman:

- *D. radiodurans* soporta **5000 Gy sin pérdida de viabilidad** (D37 ≈ 6000–7000 Gy);
  *E. coli* tiene D10 ≈ 300 Gy.
- La superficie marciana recibe **0.21 mGy/día ≈ 0.077 Gy/año** (RAD, Curiosity).

Es decir: harían falta **~65 000 años** para acumular la dosis letal de
*D. radiodurans*. **La radiación ionizante no discrimina nada en la escala temporal
de nuestra simulación** — exactamente el mismo defecto por el que ADR-0008 eliminó la
presión.

Sin embargo, el equipo señala correctamente que la radiación **sí** es uno de los
mayores obstáculos para la vida en Marte. Lo es el **UV**, no la dosis ionizante
acumulada: el UV esteriliza la superficie de forma inmediata, es el motivo por el que
el nicho marciano candidato está en el **subsuelo**, y — clave para nosotros — se
mide en **W/m²**, las mismas unidades que ya usa el pipeline.

## Decisión

**1. `R` pasa a ser irradiancia UV biológicamente efectiva (W/m²).** Se conserva el
nombre del campo, la unidad y el tipo, así que `CampoAmbiental` (§3.1) **no cambia**.

**2. Atenuación exponencial rápida con la profundidad:**

```
R(z) = R_superficie · exp(−z / δ_UV),     δ_UV ≪ escala térmica
```

El regolito bloquea el UV en milímetros a centímetros, mucho más rápido que el calor.
`MarteSubsuelo` ya modela `escala_radiativa = escala_termica / 4`, que es
cualitativamente correcto: solo hay que **hacerlo más abrupto y renombrar** lo que
representa.

**3. Umbrales por especie**, consistentes con ADR-0012: `r_letal` se reemplaza por
`uv_max` (límite de crecimiento) y `uv_letal` (límite de supervivencia).

**4. Por entorno:** Encelado mantiene `R = 0` (blindaje total del hielo); el subsuelo
de Tierra mantiene `R = 0`; Marte conserva el gradiente.

**5. Capa de datos (Fidel):** el adaptador convierte la columna `radiation` a la banda
UV. Si la fuente solo entrega irradiancia global, se aplica la fracción UV estándar y
**el factor queda documentado en el adaptador**, no escondido en una constante.

## Alternativas consideradas

1. **Mantener `R` como flujo total.** Rechazado: incoherencia dimensional y
   biológica; es el punto más fácil de atacar de todo el modelo.
2. **Pasar a dosis ionizante acumulada (Gy).** Correcto en unidades, pero con
   0.077 Gy/año la variable nunca cruza un umbral en la escala de la corrida: se
   convertiría en una dimensión muerta, el mismo destino que la presión en ADR-0008.
3. **Eliminar `R` como se eliminó `P`.** Rechazado: dejaría a *D. radiodurans* sin el
   eje que la define, y se perdería el argumento central del subsuelo marciano
   (bajar para escapar del UV).

## Consecuencias

- (+) **El eje de profundidad adquiere significado biológico**: existe una
  profundidad mínima de seguridad UV, y por debajo de ella `R` deja de limitar.
  Combinado con ADR-0015, la ventana habitable marciana queda como una **banda de
  profundidad** — bastante profunda para escapar del UV, bastante activa para que se
  formen salmueras.
- (+) `CampoAmbiental`, las unidades y el pipeline de Fidel **no cambian**.
- (+) *D. radiodurans* recupera un eje donde realmente destaca (su resistencia al UV
  es ~20× la de *E. coli*).
- (−) Hay que re-derivar los umbrales UV de las tres especies (Esmeralda).
- (−) Modifica ADR-0010, que es reciente; hay que anotar la sustitución.
