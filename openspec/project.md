# Contexto del Proyecto — AstroBioSim

## Qué es
Simulador interactivo en Python que modela la **viabilidad poblacional de
microorganismos representativos** en tres escenarios planetarios de subsuelo
(**Tierra, Marte y Encelado**), evaluando su supervivencia frente a tres
variables críticas: **temperatura (T), radiación (R) y actividad de agua (A_w)**.

> **Nota de alcance (ADR-0008, 2026-07-17):** el modelo original definía cuatro
> variables e incluía **presión (P)**. Al trabajar con análogos terrestres la
> presión resultó casi constante y sin poder discriminante, por lo que se
> eliminó del modelo. Ver `docs/adr/0008-reduccion-a-tres-variables-ambientales.md`.

Proyecto final para la *"1era Escuela de Invierno en Métodos Computacionales"*.

## Objetivo
Desarrollar un motor de **Autómatas Celulares (AC)** sobre una grilla 2D que
representa un corte transversal del subsuelo, acoplado a un **motor biológico**
(jerarquía de especies) y un **motor ambiental** (condiciones por celda),
visualizado mediante una **interfaz web** y analizado en **Jupyter Notebook**.

## Principios de diseño (obligatorios)
- **Lenguaje:** Python 3.11+.
- **Paradigma:** Programación Orientada a Objetos (POO) estricta.
- **DRY:** Don't Repeat Yourself — jerarquías de clases base/derivadas, sin
  duplicar lógica de umbrales ni de transición.
- **Separación de motores:** el motor físico/ambiental y el motor biológico se
  mantienen desacoplados e interconectados por interfaces claras.

## Modos de ejecución
1. **Sandbox:** parámetros ambientales estáticos o modificables en tiempo real
   con *sliders* en la UI web.
2. **Analógico:** los parámetros ambientales se inyectan iteración por iteración
   desde *datasets* externos de ambientes extremos terrestres análogos.

## Stack técnico
- **Núcleo numérico:** NumPy (grilla, vecindad de Moore, operaciones vectorizadas).
- **Datos / remuestreo:** pandas.
- **UI web:** frontend React (Vite + TypeScript) + backend FastAPI (ADR-0009).
- **Análisis:** Jupyter Notebook + matplotlib.
- **Aleatoriedad:** numpy.random con semilla fija para reproducibilidad.
- **Tests:** pytest.

## Datasets análogos (datos reales 2025 — ver ADR-0010 y `data/README.md`)
Una fuente por entorno; esquema canónico `t, temperature, a_w, radiation`:
- **Tierra (control):** Valles de Fresno, California (`datos_tierra_control_2025.csv`).
- **Marte (Regolito):** Desierto de Atacama / **CRC1211DB**
  (`datos_atacama_2025_EXTREMOS_REALES.csv`, con amplitud térmica diurna max/min).
- **Encelado:** ventilas hidrotermales, A_w derivada de salinidad
  (`datos_ventilas_2025_procesados.csv`); R≈0 subglacial (el IR es calor, no dosis).
- **Fuera de alcance:** exoplanetas (NASA Exoplanet Archive, PHL HWC) y el IMAU
  Antarctic (descartado en ADR-0008).

## Convenciones de código
- Paquete: `src/astrobiosim/` con layout `src/`.
- Nombres de clases en `PascalCase`, funciones/variables en `snake_case`.
- Cada clase de especie hereda de `Microorganismo`; cada entorno hereda de
  `PlanetaSubsuelo`.
- Type hints en toda API pública. Docstrings estilo NumPy.
- Un test por regla de transición y por clase de especie.

## Estado del repositorio
Greenfield. Ver `openspec/changes/bootstrap-simulator/` para el plan del MVP y
`docs/adr/` para las decisiones arquitectónicas.
