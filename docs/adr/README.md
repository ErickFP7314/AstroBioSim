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

> **Nota:** ADR-0008 modifica a ADR-0002, ADR-0003, ADR-0005 y ADR-0006 — la
> variable **presión (P)** fue eliminada del modelo. Los ADRs afectados llevan la
> anotación correspondiente.
