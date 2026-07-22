# ADR-0007: Estructura de paquetes y layout del repositorio

- **Estado:** Aceptado
- **Fecha:** 2026-07-15

## Contexto
El proyecto necesita un layout que refleje la separación de motores (ADR-0001),
soporte los dos modos de ejecución, aísle la capa de datos y mantenga el motor
agnóstico de la UI, además de ser navegable por un equipo de cuatro personas de
disciplinas distintas.

## Decisión
Adoptar layout `src/` con paquete `astrobiosim` organizado por responsabilidad:

```
AstroBioSim/
├── src/astrobiosim/
│   ├── core/            # Motores de dominio (POO)
│   │   ├── microorganism.py   # Microorganismo (base) + EColi, DRadiodurans, MBurtonii
│   │   └── environment.py     # PlanetaSubsuelo (base) + Tierra/Marte/Encelado, CampoAmbiental
│   ├── engine/          # Autómata Celular + estocasticidad
│   │   ├── cellular_automaton.py  # grilla, vecindad de Moore, bucle síncrono
│   │   ├── transition_rules.py    # reglas puras de transición
│   │   └── stochastic.py          # EventoEstocastico + eventos Montecarlo
│   ├── data/            # Modo Analógico
│   │   ├── loaders.py         # ingesta CRC1211DB (Atacama) + fallback sintético
│   │   └── resampling.py      # limpieza y remuestreo temporal
│   ├── modes/           # Estrategias de ejecución
│   │   ├── sandbox.py         # parámetros estáticos / sliders
│   │   └── analog.py          # inyección desde datasets
│   ├── ui/
│   │   └── api.py             # backend FastAPI (consume sólo la API del orquestador) — ADR-0009
│   ├── config.py        # constantes, semillas, parámetros por defecto
│   └── simulation.py    # orquestador que acopla los motores
├── frontend/            # dashboard React (Vite + TypeScript) — ADR-0009
├── tests/{unit,integration}/
├── notebooks/           # análisis retrospectivo (Jupyter)
├── data/{raw,processed}/
├── docs/adr/            # este registro
├── openspec/            # artefactos SDD (proposal, specs, design, tasks)
├── pyproject.toml
└── README.md
```

## Alternativas consideradas
1. **Layout plano** (módulos en la raíz). Rechazado: no escala ni aísla import
   accidentales; `src/` evita que los tests importen desde el árbol de trabajo.
2. **Organización por capas técnicas** (models/, services/, views/). Rechazado:
   la organización por dominio (core/engine/data/modes/ui) mapea directamente a
   los ADRs y a la división de trabajo del equipo.

## Consecuencias
- (+) Cada carpeta tiene un dueño natural en el equipo (ver división de trabajo).
- (+) La frontera UI/motor y motor/datos queda física, no sólo conceptual.
- (+) `src/` layout habilita `pip install -e .` y tests aislados con pytest.
- (−) Requiere `pyproject.toml` y configurar el paquete instalable desde el inicio.
