# División de trabajo — AstroBioSim (4 integrantes)

El reparto sigue la separación de motores del proyecto (ADR-0001, ADR-0007): cada
persona es **dueña de una carpeta**, alineada con su disciplina. Las fronteras
entre carpetas son interfaces acordadas, de modo que los cuatro pueden trabajar
en paralelo sin pisarse.

| Integrante | Disciplina | Carpeta / módulo dueño | Responsabilidad |
|-----------|-----------|------------------------|-----------------|
| **Esmeralda** | Biotecnología | `src/astrobiosim/core/microorganism.py` + `notebooks/` | Motor biológico: jerarquía de especies (`EColi`, `DRadiodurans`, `MOkinawensis`) y **calibración de los umbrales** T, R, A_w a partir de literatura; además el **notebook de análisis** retrospectivo de las corridas. |
| **Fidel** | Biotecnología | `src/astrobiosim/data/` + `src/astrobiosim/modes/analog.py` | Capa de datos análogos: loaders del dataset de Atacama, mapeo `HR → A_w` y gradiente de humedad, remuestreo temporal, y **validación biológica** de las corridas. |
| **Jose** | Física | `src/astrobiosim/core/environment.py` + `src/astrobiosim/engine/stochastic.py` | Motor ambiental/físico: entornos planetarios, **gradiente térmico** del regolito, campo de radiación, y física de los **eventos Montecarlo** (desecación marciana, emisiones hidrotermales con disipación). |
| **Erick** | Matemática | `src/astrobiosim/engine/cellular_automaton.py` + `transition_rules.py` + `ui/` + `frontend/` | Motor de Autómata Celular: formalización de la **función de transición**, vecindad de Moore, **vectorización NumPy**, estabilidad numérica y reproducibilidad; además el **dashboard React + API FastAPI** (ADR-0009) y la **validación estadística** de las corridas. |

## Piezas compartidas
- `simulation.py` (orquestador) — **lidera Erick** (acopla los motores); revisan todos.
- `ui/api.py` (FastAPI) + `frontend/` (React) — **lidera Erick** (ADR-0009); el
  motor queda agnóstico de la UI.
- `config.py` (constantes, semillas) — común; se edita con acuerdo previo.

## Orden de trabajo recomendado (para no bloquearse)
1. **Sprint 0 — contratos (los 4 juntos):** acordar las interfaces entre carpetas:
   - firma de `Microorganismo.evalua(...)` (Esmeralda ↔ Erick),
   - forma de `CampoAmbiental = {T, R, A_w}` (Jose ↔ Erick),
   - esquema canónico del DataFrame de datos (Fidel ↔ Jose).
   Con esos contratos fijos, los cuatro paralelizan.
2. **Fase 1 — motores en paralelo:** Esmeralda (especies), Jose (entornos +
   estocástico), Erick (AC sobre datos sintéticos), Fidel (loaders).
3. **Fase 2 — integración:** Erick une motores en `simulation.py`; Fidel conecta
   el Modo Analógico; Esmeralda arma el Modo Sandbox.
4. **Fase 3 — superficies:** Erick expone la API (FastAPI) y arma el dashboard
   React; Esmeralda construye el notebook de análisis.
5. **Fase 4 — validación:** Fidel valida biológicamente las salidas; Erick valida
   estadísticamente las corridas Montecarlo del notebook.

## Notas de coordinación
- Cada carpeta tiene **tests propios** en `tests/unit/` — el dueño escribe los suyos.
- Cambios que crucen una frontera de interfaz se acuerdan antes de tocar código
  (idealmente un ADR nuevo, como se hizo con la eliminación de la presión).
