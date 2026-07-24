# Architecture Decision Records (ADR) — AstroBioSim

Registro de decisiones arquitectónicas. Cada ADR captura una decisión con su
contexto, las alternativas consideradas y sus consecuencias. Formato basado en
Michael Nygard.

Estados posibles: `Propuesto` · `Aceptado` · `Rechazado` · `Sustituido por ADR-XXXX`.

| ADR | Título | Estado |
|-----|--------|--------|
| [0001](0001-arquitectura-dos-motores.md) | Arquitectura de dos motores desacoplados (biológico + ambiental) | Aceptado |
| [0002](0002-motor-automata-celular.md) | Motor de simulación por Autómatas Celulares (vecindad de Moore) | Aceptado |
| [0003](0003-representacion-estado-y-ambiente.md) | Representación del estado celular y del vector ambiental | Aceptado |
| [0004](0004-framework-ui-web.md) | Framework de interfaz web (Streamlit vs Gradio) | Reemplazado por ADR-0009 |
| [0005](0005-ingesta-datasets-analogicos.md) | Ingesta y remuestreo de datasets análogos (Modo Analógico) | Aceptado |
| [0006](0006-motor-estocastico-montecarlo.md) | Motor estocástico / Simulaciones Montecarlo | Aceptado |
| [0007](0007-estructura-paquetes-repositorio.md) | Estructura de paquetes y layout del repositorio | Aceptado |
| [0008](0008-reduccion-a-tres-variables-ambientales.md) | Reducción del modelo a tres variables ambientales (T, R, A_w) | Aceptado |
| [0009](0009-frontend-react-backend-fastapi.md) | Frontend React + backend FastAPI (reemplaza a ADR-0004) | Aceptado |
| [0010](0010-ingesta-datasets-reales-2025.md) | Ingesta de datasets reales 2025 (esquema canónico, A_w directa, R como flujo) | Aceptado |
| [0011](0011-especie-encelado-methanococcoides-burtonii.md) | Especie análoga de Encelado: Methanococcoides burtonii (reemplaza a M. okinawensis) | Aceptado |
| [0012](0012-tres-estados-celulares-y-separacion-de-umbrales.md) | Tres estados celulares (activa/latente/muerta) y separación de umbrales | Aceptado |
| [0013](0013-cinetica-crecimiento-valores-cardinales.md) | Cinética de crecimiento continua por valores cardinales (CTMI + gamma concept) | Aceptado |
| [0014](0014-radiacion-como-irradiancia-uv.md) | `R` reencuadrada como irradiancia UV (W/m²) con atenuación en el subsuelo | Aceptado |
| [0015](0015-microrefugios-salmueras-y-pregunta-de-investigacion.md) | Microrefugios por salmueras delicuescentes y pregunta de investigación | Aceptado |

> **Nota:** ADR-0008 modifica a ADR-0002, ADR-0003, ADR-0005 y ADR-0006 — la
> variable **presión (P)** fue eliminada del modelo. Los ADRs afectados llevan la
> anotación correspondiente.
>
> **Nota:** ADR-0011 resuelve la cuestión abierta #1 de ADR-0010 — la especie de
> Encelado pasa de *M. okinawensis* (termófila) a **M. burtonii** (psicrotolerante).
>
> **Nota:** ADR-0012 a ADR-0015 son un **bloque aceptado en conjunto** (2026-07-23).
> Surgen de la primera integración real entre el motor biológico y los entornos, que
> reveló que el modelo de **un solo umbral** (habitable / no habitable) no puede
> representar la biología de los extremófilos elegidos. ADR-0013, ADR-0014 y ADR-0015
> dependen de ADR-0012. Modifican la **regla de oro nº3** y los contratos de frontera
> **§3.2, §3.3, §3.4 y §3.5** de `CLAUDE.md`.
