# ADR-0003: Representación del estado celular y del vector ambiental

- **Estado:** Aceptado
- **Fecha:** 2026-07-15
- **Modificado por:** [ADR-0008](0008-reduccion-a-tres-variables-ambientales.md) — el vector ambiental pasa de cuatro a tres capas (se elimina `P`).

## Contexto
Cada celda tiene un estado biológico escalar `S_{x,y} ∈ {0,1}` y un vector
ambiental multidimensional `E_{x,y} = {T, R, A_w}` (tres variables tras ADR-0008;
originalmente cuatro, incluía `P`). El motor debe leer estos
cuatro campos por celda en cada iteración de forma eficiente y clara.

## Decisión
Separar **estado** y **ambiente** en estructuras paralelas alineadas a la grilla:

- **Estado biológico:** un único `ndarray` entero `M×N` (`0`/`1`). Opcionalmente
  una segunda capa `M×N` con el *id de especie* que ocupa cada celda, para
  soportar poblaciones mixtas.
- **Ambiente:** un conjunto de **capas escalares paralelas** — un `ndarray`
  `M×N` por variable (`T`, `R`, `A_w`) — agrupadas en una dataclass
  `CampoAmbiental`. Esto permite operaciones vectorizadas por variable y
  máscaras booleanas de tolerancia sin desempaquetar structs por celda.

En Modo Sandbox las capas son homogéneas (o editadas por sliders); en Modo
Analógico se refrescan por iteración desde el dataset. La forma de las capas es
idéntica en ambos modos, por lo que el bucle de simulación no se ramifica (DRY).

## Alternativas consideradas
1. **Grilla de objetos `Celda`** (un objeto Python por celda con atributos
   T/R/P/A_w). Rechazado: mata el rendimiento y la vectorización; POO no obliga
   a modelar cada celda como objeto — los objetos son las *especies* y los
   *entornos*, no las celdas.
2. **Un solo `ndarray` `M×N×4`.** Viable, pero el acceso por nombre de variable
   es menos legible y mezcla escalas físicas dispares en un mismo tensor. Se
   prefieren capas nombradas.

## Consecuencias
- (+) Vectorización natural: `mask = campo.T < especie.t_min` opera sobre toda la
  grilla de golpe.
- (+) La capa de *id de especie* deja la puerta abierta a co-cultivos sin
  rediseñar el estado.
- (−) Mantener cuatro capas sincronizadas exige que `CampoAmbiental` valide
  formas coincidentes al construirse.
