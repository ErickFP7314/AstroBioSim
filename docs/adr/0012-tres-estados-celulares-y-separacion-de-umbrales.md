# ADR-0012: Tres estados celulares (activa / latente / muerta) y separación de umbrales

- **Estado:** Aceptado
- **Fecha:** 2026-07-23
- **Modifica:** regla de oro nº3 de `CLAUDE.md`, contratos de frontera §3.2 y §3.3.
  Relacionado: ADR-0001, ADR-0003, ADR-0008, ADR-0011.

## Contexto

Al integrar por primera vez el motor biológico (Esmeralda) con los entornos (Jose),
la habitabilidad dio **0 % en dos de los tres escenarios**:

| Especie / entorno | Celdas habitables | Causa |
|---|---|---|
| `EColi` / Tierra | 0.0 % | campo `A_w = 0.750` vs. `a_w_min = 0.95` |
| `DRadiodurans` / Marte | 0.0 % | campo `A_w = 0.187` vs. `a_w_min = 0.75` |
| `MBurtonii` / Encelado | 95.9 % | funciona |

La propuesta inicial fue **bajar `DRadiodurans.a_w_min` a 0.2** para que sobreviviera.
Se descarta: el límite inferior de actividad de agua para la **división celular** de
cualquier organismo terrestre conocido es **≈ 0.605** (Stevenson et al., 2015). En
simulante de regolito marciano (MMS-2) la réplica fue apenas detectable a `a_w = 0.34`
y nula a `0.12`; *B. subtilis* cesa el crecimiento bajo `0.94`. Declarar crecimiento a
0.2 sería afirmar actividad biológica por debajo del límite conocido de la vida.

La causa raíz **no es la calibración**. El modelo usa **un solo umbral** que significa
simultáneamente "puede crecer" y "sigue vivo", y la literatura los separa
explícitamente: el crecimiento cesa para la mayoría bajo `a_w ≈ 0.90`, mientras que la
**supervivencia** se extiende mucho más abajo vía anhidrobiosis. La resistencia
famosa de *D. radiodurans* a la desecación es exactamente eso — **vivo sin
metabolismo** — que es el estado que la regla de oro nº3 prohíbe representar.

## Decisión

**1. El estado celular pasa de binario a ternario** (`int8`, se conserva el dtype):

| Valor | Estado | Semántica |
|---|---|---|
| `0` | `MUERTA` | terminal, **irreversible** |
| `1` | `LATENTE` | viable, no se reproduce (μ = 0) |
| `2` | `ACTIVA` | se reproduce |

**2. Cada especie declara dos juegos de umbrales**, no uno:

- **Crecimiento** (`μ > 0`): `t_min`, `t_opt`, `t_max`, `a_w_min`, `uv_max`
- **Supervivencia** (sigue viva): `t_sup_min`, `t_sup_max`, `a_w_sup_min`, `uv_letal`

**3. Transición por celda** (síncrona, vectorizada, sin cambios en el doble buffer):

```
dentro de crecimiento                      -> ACTIVA
fuera de crecimiento, dentro de superviv.  -> LATENTE
fuera de supervivencia                     -> MUERTA
MUERTA                                     -> MUERTA  (absorbente)
```

**4. La regla de oro nº3 se reformula, no se elimina.** La muerte sigue siendo
irreversible y **sigue sin haber esporulación**; lo que se admite es
**quiescencia / anhidrobiosis** como estado viable no reproductivo. `LATENTE → ACTIVA`
es reversible; `MUERTA → *` nunca lo es.

**5. Contrato §3.2** gana dos métodos y conserva el existente como alias:

```python
def condiciones_crecimiento(self, campo: CampoAmbiental) -> np.ndarray: ...
def condiciones_supervivencia(self, campo: CampoAmbiental) -> np.ndarray: ...
# condiciones_habitables() se mantiene como alias de condiciones_crecimiento()
# para no romper los tests ya escritos.
```

**6. Contrato §3.3** — `paso()` devuelve `int8` con valores en `{0, 1, 2}`. El conteo
de vecinos de Moore para la reproducción cuenta **solo celdas `ACTIVA`**.

## Alternativas consideradas

1. **Bajar `a_w_min` de *D. radiodurans* a 0.2.** Rechazado: está por debajo del
   límite de división celular conocido (~0.605). Sería el primer punto que un revisor
   tumbaría.
2. **Pesos multiplicativos tipo red neuronal que favorezcan el crecimiento**
   (propuesta de Esmeralda). **No rechazado — promovido a ADR-0013.** La intuición
   estructural es correcta y coincide con el estándar de la microbiología predictiva
   (*gamma concept*); lo único que cambia es que los factores se derivan de **valores
   cardinales publicados** en vez de ajustarse a mano.
3. **Aceptar la extinción total en Tierra y Marte.** Biológicamente honesto para
   Marte, pero deja dos de tres corridas sin contenido comparativo; y para Tierra es
   directamente incorrecto (ver ADR-0014 y la nota de datos sobre `A_w` de suelo vs.
   humedad del aire).
4. **Modelar esporulación completa.** Rechazado: ninguna de las tres especies
   esporula (*E. coli* y *D. radiodurans* no forman esporas; *M. burtonii* es una
   arquea). El mecanismo correcto es anhidrobiosis/quiescencia, que es más simple.

## Consecuencias

- (+) **Todos los parámetros vuelven a ser citables** sin excepciones ni fudges.
- (+) *D. radiodurans* en Atacama queda **`LATENTE`** — que es la verdad biológica:
  sobrevive, no crece. Ni muerta, ni creciendo falsamente.
- (+) Aparece una **métrica nueva y más informativa**: fracción activa / latente /
  muerta a lo largo del tiempo, en vez de una sola curva de población.
- (+) Habilita la pregunta de investigación de ADR-0015 (¿cuánta agua transitoria
  hace falta para que una población latente vuelva a ser activa y persista?).
- (−) Cambia el estado, §3.2, §3.3 y los tests de Erick y Esmeralda. Es la
  modificación más invasiva del proyecto hasta ahora.
- (−) Hay que definir umbrales de **supervivencia** por especie, que están peor
  documentados en literatura que los de crecimiento.

## Referencias

- Stevenson et al. (2015), *Multiplication of microbes below 0.690 water activity*,
  Environmental Microbiology — límite ≈ 0.605 `a_w`.
- Crecimiento en simulante de regolito marciano MMS-2 (`a_w` 1.0 / 0.75 / 0.65 /
  0.34 / 0.12).
- Estudio NanoSIMS en *S. liquefaciens*: "podría metabolizar y crecer sobre −5 °C y
  **sobrevivir pero no crecer** bajo −5 °C" — precedente directo de la separación.
