# CLAUDE.md — Contexto compartido de AstroBioSim

> Claude Code lee este archivo en **cada** prompt, así que contiene **solo lo que
> todos los asistentes necesitan siempre**: contexto, reglas invariantes,
> contratos de frontera y flujo. Las instrucciones de cada integrante viven en su
> propio archivo (§4) para no saturar el contexto — cada uno se lo pasa a su Claude
> cuando trabaja.

## 1. Contexto del proyecto

AstroBioSim simula la **supervivencia poblacional de microorganismos** en
subsuelos de **Tierra, Marte y Encelado** mediante **Autómatas Celulares** sobre
una grilla 2D. Se evalúan **tres variables ambientales**: temperatura `T`,
radiación `R` y actividad de agua `A_w`.

Documentación: contexto completo en `openspec/project.md`; decisiones en
`docs/adr/`; reparto en `docs/division-trabajo.md`; plan del MVP en
`openspec/changes/bootstrap-simulator/proposal.md`.

> **La presión fue eliminada del modelo** (ADR-0008). Trabajamos con análogos
> terrestres donde la presión es casi constante y no discrimina. Si ves `P`,
> `p_min`, `p_max`, `presión` o el dataset IMAU Antarctic, es obsoleto: **no lo
> implementes**. Solo T, R, A_w.

## 2. Reglas de oro (invariantes para TODOS los asistentes)

1. **Python 3.11+, POO estricta y DRY.** Las clases son las *especies* y los
   *entornos*, NO las celdas (las celdas son arrays NumPy). No dupliques la lógica
   de umbrales ni la de transición.
2. **Solo tres variables ambientales: `T`, `R`, `A_w`.** Nada de presión.
3. **Sin latencia ni esporulación.** Si una célula sale de sus umbrales, muere de
   forma **irreversible**. No hay "dormancia".
4. **Autómata Celular síncrono.** `S^{t+1}` se calcula íntegro a partir de `S^t`
   (doble buffer). Nunca actualices la grilla in situ.
5. **Vectorizá con NumPy.** Prohibido recorrer la grilla celda por celda con
   bucles Python. Usá máscaras booleanas y desplazamientos/convolución.
6. **Reproducibilidad.** Toda aleatoriedad usa un único `numpy.random.Generator`
   con semilla explícita, inyectado como parámetro. Nunca `np.random` global.
7. **Respetá los contratos de frontera (§3).** No cambies una firma sin acordarlo
   con el grupo.
8. **Tests con pytest.** Cada quien escribe los tests de su carpeta en
   `tests/unit/`. Una regla o clase sin test no está terminada.
9. **Type hints y docstrings** (estilo NumPy) en toda función pública.

## 3. Contratos de frontera (Sprint 0 — NO cambiar sin acuerdo)

Firmas que permiten trabajar en paralelo. Impleméntalas tal cual; si algo no
encaja, se discute en grupo antes de tocarlas.

### 3.1 Campo ambiental — dueño: Jose (`core/environment.py`)
```python
from dataclasses import dataclass
import numpy as np

@dataclass
class CampoAmbiental:
    """Tres capas escalares alineadas a la grilla M×N. Todas la misma forma."""
    T: np.ndarray     # temperatura (°C),           shape (M, N)
    R: np.ndarray     # radiación: flujo (W/m²), proxy operativo — ver ADR-0010; shape (M, N)
    A_w: np.ndarray   # actividad de agua (0..1),   shape (M, N)

    def __post_init__(self) -> None: ...          # valida formas idénticas
    @property
    def shape(self) -> tuple[int, int]: ...
```

### 3.2 Especie — dueño: Esmeralda (`core/microorganism.py`)
```python
from abc import ABC
import numpy as np
from astrobiosim.core.environment import CampoAmbiental

class Microorganismo(ABC):
    t_min: float; t_max: float      # °C
    r_letal: float                  # umbral letal de radiación (W/m², ver ADR-0010; re-derivar)
    a_w_min: float                  # actividad de agua mínima (0..1)
    mu_max: float                   # tasa de reproducción óptima

    def condiciones_habitables(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M,N): True donde TODAS las variables están en umbral.
        Vectorizado:
            (campo.T >= t_min) & (campo.T <= t_max)
            & (campo.R <= r_letal) & (campo.A_w >= a_w_min)
        """
        ...
```

### 3.3 Paso del autómata — dueño: Erick (`engine/cellular_automaton.py`)
```python
import numpy as np
from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import Microorganismo

def paso(estado: np.ndarray, campo: CampoAmbiental,
         especie: Microorganismo) -> np.ndarray:
    """Un tick del AC (actualización síncrona). Devuelve el nuevo estado (M,N) int8.
    Usa especie.condiciones_habitables(campo) y el conteo de vecinos de Moore."""
    ...
```

### 3.4 Evento estocástico — dueño: Jose (`engine/stochastic.py`)
```python
from abc import ABC
import numpy as np
from astrobiosim.core.environment import CampoAmbiental

class EventoEstocastico(ABC):
    def aplicar(self, campo: CampoAmbiental,
                rng: np.random.Generator) -> CampoAmbiental:
        """Perturba y devuelve el campo (NO toca el estado biológico)."""
        ...
```

### 3.5 Datos análogos — dueño: Fidel (`data/`) · actualizado por ADR-0010
```python
import pandas as pd
# Datos reales 2025: una fuente por entorno, esquemas crudos distintos.
# Cada fuente tiene su ADAPTADOR que devuelve el DataFrame CANÓNICO con
# columnas EXACTAS:
#   "t"           (índice temporal)
#   "temperature" (°C)
#   "a_w"         (0..1, PROVISTA directamente — ya no se calcula humidity/100)
#   "radiation"   (W/m², flujo radiativo; proxy operativo de R, NO dosis en Gy)
# (Atacama expone además "temperature_min"/"temperature_max": amplitud diurna.)
def cargar_control_tierra(ruta: str) -> pd.DataFrame: ...
def cargar_atacama(ruta: str) -> pd.DataFrame: ...
def cargar_ventilas(ruta: str) -> pd.DataFrame: ...
# resampling.py -> secuencia de CampoAmbiental (uno por iteración):
#   A_w se usa tal cual (0..1); R se alimenta de "radiation" (W/m²).
#   Mapeo por entorno: superficies usan radiación solar como R;
#   Encelado subglacial mapea R≈0 (su IR es calor, no dosis). Ver ADR-0010.
```

## 4. Instrucciones por integrante (archivos separados)

Cada persona abre **su** archivo y le pasa esas instrucciones a su Claude. No están
aquí para no cargar en cada prompt lo que no te toca.

| Integrante | Carrera | Carpeta dueña | Su archivo |
|-----------|---------|---------------|-----------|
| Esmeralda | Biotecnología | `core/microorganism.py` + `notebooks/` | `docs/instrucciones/esmeralda.md` |
| Fidel | Biotecnología | `data/` + `modes/analog.py` | `docs/instrucciones/fidel.md` |
| Jose | Física | `core/environment.py` + `engine/stochastic.py` | `docs/instrucciones/jose.md` |
| Erick | Matemática | `engine/cellular_automaton.py` + `transition_rules.py` + `ui/` (dashboard React + API) | `docs/instrucciones/erick.md` |

## 5. Flujo de trabajo

- **Sprint 0 (los 4 juntos):** confirmar los contratos de §3. Hasta que no estén
  fijos, cada uno avanza contra *stubs* de los otros módulos.
- **Ramas:** una rama por persona/carpeta; PR pequeño con sus tests en verde.
- **`config.py` y `simulation.py`** se editan con acuerdo previo (son compartidos).
- **Tests:** `pytest` debe pasar antes de integrar.
- **Cambios de frontera:** si hay que cambiar una firma de §3, se discute y, si es
  una decisión de diseño, se escribe un **ADR nuevo** (como se hizo con ADR-0008).
