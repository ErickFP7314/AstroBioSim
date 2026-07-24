# Propuesta: bootstrap-simulator (MVP de AstroBioSim)

## Intención
Construir el MVP funcional de AstroBioSim: un simulador de Autómatas Celulares
que modele la supervivencia poblacional de microorganismos en subsuelos de
Tierra, Marte y Encelado, con los dos modos de ejecución (Sandbox y Analógico),
eventos estocásticos Montecarlo y un dashboard web.

> **Alcance revisado (ADR-0008):** el modelo trabaja con **tres** variables
> ambientales — **T, R, A_w**. La presión (`P`) fue eliminada por falta de poder
> discriminante en análogos terrestres.

## Motivación
Entregable final de la Escuela de Invierno. El documento de especificación
define el modelo físico-biológico completo; esta propuesta lo traduce a una
arquitectura de software implementable, dividida en incrementos verificables.

## Alcance

### Incluye
1. **Motor biológico** — jerarquía POO:
   - `Microorganismo` (clase base abstracta) con **dos** juegos de umbrales
     (ADR-0012): crecimiento (`t_min`, `t_opt`, `t_max`, `a_w_min`, `uv_max`) y
     supervivencia (`t_sup_min`, `t_sup_max`, `a_w_sup_min`, `uv_letal`), más
     `mu_opt`. `R` es irradiancia UV en W/m² (ADR-0014).
   - Especies derivadas: `EColi` (control terrestre), `DRadiodurans` (Marte),
     `MBurtonii` (Encelado, ADR-0011).
2. **Motor ambiental** — jerarquía POO:
   - `PlanetaSubsuelo` (base) → `TierraSubsuelo`, `MarteSubsuelo`, `EnceladoSubglacial`.
   - Vector ambiental por celda `E_{x,y} = {T, R, A_w}`.
3. **Motor de Autómata Celular**:
   - Grilla 2D `M×N`, estado de celda ∈ {0 `MUERTA`, 1 `LATENTE`, 2 `ACTIVA`}
     (ADR-0012).
   - Vecindad de Moore (8 vecinos); para reproducir se cuentan **solo** las
     celdas `ACTIVA`.
   - Reglas de transición: dentro de `condiciones_crecimiento` → `ACTIVA`; fuera
     de crecimiento pero dentro de `condiciones_supervivencia` → `LATENTE`; fuera
     de supervivencia → `MUERTA`. La reproducción usa la tasa continua
     `μ = μ_opt·γ(T)·γ(a_w)·γ(UV)` de ADR-0013, no una máscara binaria.
   - **Restricción estricta:** la muerte es **irreversible** (`MUERTA` es
     absorbente) y **no hay esporulación**. `LATENTE → ACTIVA` sí es reversible:
     es quiescencia/anhidrobiosis, no una resurrección.
4. **Modo Sandbox**: parámetros ambientales estáticos o vía sliders.
5. **Modo Analógico**: ingesta del dataset de Atacama (CRC1211DB) con limpieza y
   remuestreo al marco temporal de la simulación.
6. **Motor estocástico (Montecarlo)**:
   - Marte: micro-fisuras / desecación (caída de A_w en un radio).
   - Encelado: emisiones hidrotermales (picos ΔT ~ N(μ, σ²)) con disipación a
     celdas vecinas.
7. **Dashboard web** (React + backend FastAPI, ADR-0009): render de la matriz de
   supervivencia poblacional en tiempo real.
8. **Notebook de análisis**: dinámicas poblacionales retrospectivas.

### Excluye (fuera de alcance del MVP)
- Grillas 3D (el corte es 2D).
- Mecanismos de latencia/esporulación (prohibidos por la especificación).
- Especies adicionales más allá de las tres definidas.
- Optimización GPU / paralelización distribuida.

## Enfoque
Arquitectura de dos motores desacoplados coordinados por un orquestador de
simulación. El AC opera sobre arrays NumPy; el vector ambiental se mantiene en
capas paralelas a la grilla de estado. Los modos y las fuentes de datos se
inyectan por interfaz (Strategy), de modo que Sandbox y Analógico comparten el
mismo bucle de simulación. Ver `docs/adr/` para las decisiones clave.

## Capacidades afectadas (delta specs)
- `biological-engine`
- `environmental-engine`
- `cellular-automaton`
- `execution-modes`
- `stochastic-events`
- `web-dashboard`

## Riesgos
- **Disponibilidad y formato del dataset** (Atacama CRC1211DB): puede requerir
  fallback sintético si el acceso o el esquema difiere. → ADR-0005.
- **Diferenciación de Encelado sin presión:** al eliminar `P`, Encelado se
  distingue sólo por `T`, `A_w ≈ 1` y `R ≈ 0`; debe verificarse en validación que
  sigue produciendo dinámicas distintas de Tierra. → ADR-0008.
- **Estabilidad numérica** del AC (poblaciones que colapsan o saturan la grilla)
  → requiere calibración de umbrales y del paso temporal.

## Criterios de aceptación
- Las tres especies se instancian y responden correctamente a sus umbrales.
- Los tres entornos producen dinámicas poblacionales cualitativamente distintas.
- Ambos modos ejecutan el mismo bucle sin ramas duplicadas (DRY verificable).
- Los eventos Montecarlo perturban la grilla de forma reproducible con semilla.
- El dashboard renderiza la evolución de la matriz sin bloquear la simulación.
