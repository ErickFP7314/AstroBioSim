# ADR-0002: Motor de simulación por Autómatas Celulares (vecindad de Moore)

- **Estado:** Aceptado
- **Fecha:** 2026-07-15
- **Modificado por:** [ADR-0008](0008-reduccion-a-tres-variables-ambientales.md) — la variable presión (`P`) fue eliminada de las reglas de transición.


> **Modificado por ADR-0012 y ADR-0013:** el estado deja de ser binario (pasa a
> `MUERTA`/`LATENTE`/`ACTIVA`) y la regla de transición deja de ser una máscara
> booleana (pasa a la tasa continua `μ = μ_opt·γ(T)·γ(a_w)·γ(UV)`). La muerte sigue
> siendo irreversible.

## Contexto
El espacio de simulación es una grilla 2D `G` de dimensiones `M×N` que
representa un corte transversal del subsuelo. El estado de cada celda
`S_{x,y}^t ∈ {0, 1}` (vacía/ocupada) evoluciona por una función de transición
que depende del estado propio, del vector ambiental y de la vecindad de Moore
`V(x,y)` (8 vecinos):

```
S_{x,y}^{t+1} = f( S_{x,y}^t, E_{x,y}^t, Σ_{i,j ∈ V} S_{i,j}^t )
```

## Decisión
Implementar un motor de Autómata Celular síncrono sobre arrays NumPy:

- La grilla de estado es un `ndarray` de enteros `M×N`.
- El conteo de vecinos vivos se calcula de forma **vectorizada** (convolución de
  la máscara de Moore o suma de 8 desplazamientos), no con bucles Python por
  celda.
- La actualización es **síncrona**: `S^{t+1}` se calcula íntegro a partir de
  `S^t` (doble buffer), nunca in situ.
- Las **reglas de transición** viven en un módulo dedicado
  (`engine/transition_rules.py`) y son funciones puras de
  `(estado, ambiente, vecinos_vivos, especie)`:
  1. **Muerte por estrés ambiental:** si alguna variable de `E` sale del rango
     tolerable de la especie (`T<T_min`, `T>T_max`, `R>R_letal`, `A_w<A_w_min`),
     la celda pasa a 0. Irreversible (sin latencia).
  2. **Muerte por sobrepoblación/aislamiento:** con condiciones óptimas, una
     célula viva muere si tiene <2 o >3 vecinas vivas.
  3. **Reproducción:** una celda vacía pasa a viva si tiene exactamente 3
     vecinas vivas **y** todas las variables de `E` están dentro de umbrales.

## Alternativas consideradas
1. **Bucle Python celda por celda.** Rechazado por rendimiento; NumPy
   vectorizado es 10–100× más rápido y mantiene el código DRY.
2. **Vecindad de Von Neumann (4 vecinos).** Rechazado: la especificación exige
   Moore (8 vecinos).
3. **Actualización asíncrona.** Rechazado: introduce artefactos dependientes del
   orden de barrido; la especificación define transición sincrónica.

## Consecuencias
- (+) Rendimiento adecuado para grillas grandes en tiempo real.
- (+) Reglas aisladas y testeables una por una.
- (−) Los bordes de la grilla requieren decisión explícita (toroidal vs.
  frontera muerta) — se documenta en el diseño; por defecto frontera muerta.
- (−) La vectorización de la regla 3 (AND de los umbrales por celda) exige cuidado
  para no romper la legibilidad; se encapsula en máscaras booleanas nombradas.
