# ADR-0017: El Modo Analógico modula el campo espacial de Jose con la serie temporal

- **Estado:** Aceptado
- **Fecha:** 2026-07-24
- **Modifica:** contrato §3.1 (`PlanetaSubsuelo` gana `campo_modulado`).
  Relacionado: ADR-0005 (Modo Analógico), ADR-0014 (UV), ADR-0015 (banda de profundidad).

## Contexto

El Modo Analógico inyecta una **serie temporal de escalares** (un `temperature`,
`a_w`, `radiation` por día) al autómata. Había que decidir cómo se convierte cada
escalar diario en el campo `M×N`.

La opción trivial —campo **uniforme** por tick, cada celda igual al escalar del
día— es físicamente insostenible para un **subsuelo**: si cada celda toma el UV de
superficie, la grilla entera se esteriliza y desaparece la banda de profundidad
que es central a la pregunta de investigación (ADR-0014/0015). Un subsuelo tiene
estructura espacial (decaimiento de T y UV con la profundidad, fumarolas), y esa
estructura ya está modelada por Jose en `PlanetaSubsuelo` (Modo Sandbox).

## Decisión

**El Modo Analógico reusa el modelo espacial de Jose, modulado por el dato del
día**, en vez de reimplementar la física (DRY) o aplanar el campo.

**1. `PlanetaSubsuelo` gana `campo_modulado`** (extensión de §3.1):

```python
def campo_modulado(self, *, temperature: float, a_w: float,
                   radiation_global: float = 0.0,
                   rng=None) -> CampoAmbiental: ...
```

Cada entorno propaga los escalares con su propia física:
- **Marte:** `temperature` es la superficie del día y decae con la profundidad
  hacia la asíntota fría; `radiation_global × FRACCION_UV` es el UV de superficie,
  que se atenúa mucho más rápido (banda de profundidad).
- **Encelado:** `temperature` es el fondo oceánico del día; las fumarolas se suman
  encima con su kernel gaussiano. `R = 0`.
- **Tierra:** campo uniforme (el control no tiene estructura de profundidad);
  `R = 0` porque el suelo bloquea el UV.

**2. `campo_inicial` es el caso particular** de `campo_modulado` con los valores
medios por defecto de cada entorno. La física espacial vive en un solo lugar (DRY
también dentro de `environment.py`); los tests existentes de `campo_inicial` no
cambian.

**3. `data/resampling.secuencia_campos`** itera las filas temporales y delega en
`campo_modulado`. Itera sobre el tiempo (365 filas), no sobre celdas: cada campo
sigue siendo vectorizado.

**4. Interfaz de modo (`modes/base.ModoSimulacion`).** Un modo es un proveedor de
`CampoAmbiental` por tick (`campos() -> Iterator`). `ModoAnalogico` la cumple, y el
futuro Modo Sandbox también: el orquestador itera igual para ambos (DRY, no se
ramifica por modo).

## Alternativas consideradas

1. **Campo uniforme por tick.** Rechazado: el UV de superficie esteriliza toda la
   grilla; se pierde la banda de profundidad. Físicamente incorrecto para subsuelo.
2. **Reimplementar la física espacial en `resampling`.** Rechazado: duplica la
   lógica de Jose (viola DRY) y abre dos fuentes de verdad para el mismo modelo.
3. **Un ciclo diurno sintético** (usar `temperature_min/max` de Atacama para
   generar sub-pasos horarios). Aplazado: el paso es diario (365 ticks); los
   extremos diurnos quedan para el slider de la UI, no para la serie analógica.

## Consecuencias

- (+) El análogo conserva la banda de profundidad y las fumarolas, con la
  variación temporal real encima. Ej.: el control terrestre ahora muestra días
  fríos de invierno como `LATENTE` (T < 7.5 °C), textura que un campo uniforme
  también daría pero sin la estructura espacial de los otros dos entornos.
- (+) Sandbox y Analógico comparten el modelo espacial y la interfaz de modo.
- (−) **Extiende el contrato §3.1** (toca `environment.py`, de Jose). Es una
  adición retrocompatible (`campo_inicial` no cambia de firma), acordada con el
  coordinador, pero Jose debe revisarla al mergear.
- (−) El paso diario ignora el ciclo diurno; se documenta como decisión, no como
  omisión.
