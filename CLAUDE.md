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

> **¿Qué hay que hacer y qué falta?** → **`docs/tablero.md`**, espejo en Markdown
> del tablero de Trello con todas las tareas, su estado y sus criterios de
> aceptación. Consultalo antes de empezar cualquier tarea: te dice **qué** falta;
> `docs/instrucciones/<nombre>.md` te dice **cómo**, y `docs/adr/` **por qué**.
>
> **¿De dónde sale este número?** → **`docs/parametros.md`**, la referencia oficial
> de todo valor del modelo con su procedencia (**[LIT]** publicado · **[DER]**
> derivado · **[CONV]** convención nuestra · **[EST]** estimación pendiente) y su
> cita. **Un parámetro sin procedencia no entra al modelo.** Si vas a cambiar un
> umbral o una constante, actualizá esa tabla en el mismo commit.

> **La presión fue eliminada del modelo** (ADR-0008). Trabajamos con análogos
> terrestres donde la presión es casi constante y no discrimina. Si ves `P`,
> `p_min`, `p_max`, `presión` o el dataset IMAU Antarctic, es obsoleto: **no lo
> implementes**. Solo T, R, A_w.
>
> **`R` es irradiancia UV en W/m²** (ADR-0014), no flujo solar total ni dosis en
> Gy. La dosis ionizante no discrimina en la escala de la simulación (0.077 Gy/año
> en Marte frente a los ~5000 Gy que tolera *D. radiodurans*); el UV sí esteriliza.
> Si ves `r_letal`, es obsoleto: ahora son `uv_max` y `uv_letal`.
>
> **Pregunta de investigación** (ADR-0015): *¿con qué frecuencia y magnitud mínimas
> deben aparecer microrefugios húmedos transitorios para que una población persista
> en un subsuelo planetario, en vez de extinguirse?* Que Marte dé extinción en bulk
> es el resultado **correcto**, no un bug.

## 2. Reglas de oro (invariantes para TODOS los asistentes)

1. **Python 3.11+, POO estricta y DRY.** Las clases son las *especies* y los
   *entornos*, NO las celdas (las celdas son arrays NumPy). No dupliques la lógica
   de umbrales ni la de transición.
2. **Solo tres variables ambientales: `T`, `R`, `A_w`.** Nada de presión.
3. **Tres estados; la muerte es irreversible** (ADR-0012). Una célula está
   `ACTIVA` (crece), `LATENTE` (viva, no se reproduce) o `MUERTA` (terminal).
   `LATENTE → ACTIVA` sí es reversible; `MUERTA` es absorbente y **nadie
   resucita**. Sigue sin haber **esporulación**: la latencia es anhidrobiosis /
   quiescencia, no una espora con umbrales distintos.
   → Por eso cada especie declara **dos** juegos de umbrales: los de
   **crecimiento** y los de **supervivencia**. Nunca uses uno solo para las dos
   cosas.
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
    T: np.ndarray     # temperatura (°C),            shape (M, N)
    R: np.ndarray     # irradiancia UV (W/m²) — ADR-0014; shape (M, N)
    A_w: np.ndarray   # actividad de agua (0..1),    shape (M, N)

    def __post_init__(self) -> None: ...          # valida formas idénticas
    @property
    def shape(self) -> tuple[int, int]: ...

class PlanetaSubsuelo(ABC):
    def campo_inicial(self, rng: np.random.Generator | None = None) -> CampoAmbiental:
        """Campo en t=0. Con `rng`, los entornos que declaran dispersión la
        muestrean (ADR-0015); sin él, el campo es determinista."""
```

### 3.2 Especie — dueño: Esmeralda (`core/microorganism.py`)
```python
from abc import ABC
import numpy as np
from astrobiosim.core.environment import CampoAmbiental

MUERTA, LATENTE, ACTIVA = 0, 1, 2      # estados celulares (ADR-0012)

class Microorganismo(ABC):
    # --- umbrales de CRECIMIENTO (μ > 0) ---
    t_min: float; t_opt: float; t_max: float   # puntos cardinales (°C), para ADR-0013
    a_w_min: float                  # a_w mínima para crecer (0..1)
    uv_max: float                   # UV máxima bajo la cual crece (W/m²)
    # --- umbrales de SUPERVIVENCIA (viva, μ = 0) ---
    t_sup_min: float; t_sup_max: float
    a_w_sup_min: float              # ~0 en especies anhidrobióticas
    uv_letal: float                 # por encima: muerte irreversible
    # --- cinética ---
    mu_opt: float                   # tasa en el óptimo (h⁻¹)

    def condiciones_crecimiento(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M,N): True donde la especie SE REPRODUCE. Vectorizado:
            (campo.T >= t_min) & (campo.T <= t_max)
            & (campo.A_w >= a_w_min) & (campo.R <= uv_max)"""
    def condiciones_supervivencia(self, campo: CampoAmbiental) -> np.ndarray:
        """Máscara bool (M,N): True donde SIGUE VIVA. Superconjunto de la anterior."""
    def condiciones_habitables(self, campo: CampoAmbiental) -> np.ndarray:
        """Alias retrocompatible de condiciones_crecimiento()."""
```
> `a_w_min` **nunca** puede bajar de ~0.605: es el límite de división celular
> conocido para cualquier organismo terrestre. Si una especie no crece, la
> respuesta es que quede `LATENTE`, no bajarle el umbral.

### 3.3 Paso del autómata — dueño: Erick (`engine/cellular_automaton.py`)
```python
import numpy as np
from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import Microorganismo

def paso(estado: np.ndarray, campo: CampoAmbiental, especie: Microorganismo,
         rng: np.random.Generator) -> np.ndarray:
    """Un tick del AC (actualización síncrona). Devuelve el nuevo estado (M,N) int8
    con valores en {MUERTA, LATENTE, ACTIVA} (ADR-0012).

    - dentro de condiciones_crecimiento           -> ACTIVA
    - fuera de crecimiento, dentro de superviv.   -> LATENTE
    - fuera de condiciones_supervivencia          -> MUERTA (absorbente)
    El conteo de vecinos de Moore para reproducir cuenta SOLO celdas ACTIVA, y la
    probabilidad de reproducción sale de la cinética de ADR-0013 (transition_rules)."""
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
> **Los eventos no pueden ser todos degradantes** (ADR-0015). Hasta ahora todos
> empeoraban el ambiente (`MicroFisuraMarte` baja `A_w`), lo que sesgaba toda
> corrida hacia la extinción por construcción. Debe existir su contraparte que lo
> **mejore**: `SalmueraDelicuescente` sube `A_w` transitoriamente.

### 3.5 Datos análogos — dueño: Fidel (`data/`) · actualizado por ADR-0010
```python
import pandas as pd
# Datos reales 2025: una fuente por entorno, esquemas crudos distintos.
# Cada fuente tiene su ADAPTADOR que devuelve el DataFrame CANÓNICO con
# columnas EXACTAS:
#   "t"           (índice temporal)
#   "temperature" (°C)
#   "a_w"         (0..1, PROVISTA directamente — ya no se calcula humidity/100)
#   "radiation"   (W/m², irradiancia UV — ADR-0014. Si la fuente solo da
#                  irradiancia global, se multiplica por FRACCION_UV y el
#                  factor queda DOCUMENTADO en el adaptador, no escondido)
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
