# ADR-0001: Arquitectura de dos motores desacoplados (biológico + ambiental)

- **Estado:** Aceptado
- **Fecha:** 2026-07-15

## Contexto
La especificación exige un sistema en Python con POO estricta y DRY, compuesto
por dos módulos principales interconectados: un motor físico/ambiental y un
motor biológico. El motor biológico decide vida/muerte/reproducción de células;
el ambiental provee, por celda y por iteración, el vector de condiciones
`E_{x,y} = {T, R, P, A_w}`. Ambos deben poder evolucionar de forma independiente
(añadir especies sin tocar entornos, y viceversa).

## Decisión
Separar el sistema en dos motores desacoplados con una frontera explícita:

- **Motor biológico** (`astrobiosim.core.microorganism`): jerarquía
  `Microorganismo` → especies. Conoce únicamente umbrales de tolerancia y tasa
  de reproducción. No sabe de grillas ni de datasets.
- **Motor ambiental** (`astrobiosim.core.environment`): jerarquía
  `PlanetaSubsuelo` → entornos. Produce el campo ambiental `E` sobre la grilla.
- Un **orquestador de simulación** (`astrobiosim.engine`) es el único que conoce
  ambos: pregunta al entorno el vector ambiental de cada celda y al organismo si
  sobrevive/reproduce bajo ese vector.

El contrato entre motores es una consulta pura:
`organismo.evalua(estado_celda, vector_ambiental, vecinos_vivos) -> nuevo_estado`.

## Alternativas consideradas
1. **Motor monolítico** con condiciones ambientales embebidas en la lógica
   biológica. Rechazado: viola DRY y acopla especies con entornos.
2. **Arquitectura por eventos/mensajería.** Sobredimensionada para una
   simulación de un solo proceso; añade complejidad sin beneficio.

## Consecuencias
- (+) Añadir una especie o un planeta es una subclase, sin tocar el otro motor.
- (+) Testeable en aislamiento (mock del vector ambiental).
- (+) Habilita repartir el trabajo del equipo por motor (biotec ↔ física).
- (−) Requiere disciplina en mantener la frontera: el orquestador no debe filtrar
  lógica biológica al motor ambiental.
