# ADR-0006: Motor estocástico / Simulaciones Montecarlo

- **Estado:** Aceptado
- **Fecha:** 2026-07-15
- **Modificado por:** [ADR-0008](0008-reduccion-a-tres-variables-ambientales.md) — los eventos se reformulan sin el eje de presión.

## Contexto
La especificación exige Simulaciones Montecarlo que inyecten eventos estocásticos
geológicos/climáticos que perturben el subsuelo. Tras ADR-0008 (sin presión):

- **Marte — micro-fisuras / desecación:** con cierta probabilidad, en un radio de
  celdas, la actividad de agua `A_w` cae drásticamente, modelada por
  distribuciones de probabilidad. La causa física sigue siendo la micro-fisura y
  despresurización, pero su efecto modelado es la pérdida de agua interstitial.
- **Encelado — emisiones hidrotermales:** picos térmicos aleatorios
  `ΔT ~ N(μ, σ²)` por actividad geológica, que se propagan a celdas vecinas con
  disipación. (Se elimina la variación de presión `ΔP`.)

## Decisión
Modelar los eventos como **perturbaciones del campo ambiental**, no del estado
biológico: cada evento es un objeto que, al dispararse, modifica localmente las
capas de `CampoAmbiental` antes de que el AC evalúe la iteración.

- Interfaz común `EventoEstocastico.aplicar(campo, rng) -> campo`.
- Implementaciones: `MicroFisuraMarte` (caída de `A_w` en un radio con
  probabilidad de disparo) y `EmisionHidrotermalEncelado` (pico gaussiano de `T`
  con kernel de disipación radial hacia vecinos).
- **Reproducibilidad:** un único `numpy.random.Generator` con semilla explícita
  se inyecta en todos los eventos; ninguna llamada usa el RNG global.
- Los eventos se registran en el orquestador y se aplican en un *hook* previo a
  la transición del AC, de forma que la muerte por estrés (ADR-0002) reacciona
  naturalmente a la perturbación.

## Alternativas consideradas
1. **Perturbar directamente el estado de las celdas (matar células al azar).**
   Rechazado: rompe la causalidad física del modelo; la muerte debe emerger de
   condiciones ambientales fuera de umbral, no de un dado.
2. **RNG global de NumPy.** Rechazado: impide reproducibilidad y aislar tests.

## Consecuencias
- (+) Los eventos son componibles y testeables contra un `CampoAmbiental` fijo.
- (+) Reproducibilidad total con semilla → corridas Montecarlo comparables.
- (+) Añadir un evento nuevo no toca el AC ni el motor biológico.
- (−) El orden de aplicación de múltiples eventos en la misma iteración debe
  definirse (se documenta: eventos ordenados de forma determinista antes de
  transición).
