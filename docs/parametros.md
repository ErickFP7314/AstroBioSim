# Parámetros del modelo — valores, procedencia y trazabilidad

> **Esta es la referencia oficial de todo número que entra al modelo.** Si vas a
> tocar un umbral, un factor de conversión o una constante física, se documenta
> acá y se cita. Un parámetro sin procedencia no entra.

Cada valor lleva una etiqueta de procedencia:

| Etiqueta | Significado |
|---|---|
| **[LIT]** | Valor publicado. Lleva referencia. |
| **[DER]** | Derivado de un **[LIT]** por una fórmula explícita que está en el código. |
| **[CONV]** | Convención del modelo, no dato. Es una decisión nuestra, y se justifica. |
| **[EST]** | Estimación sin respaldo directo. **Es deuda**: hay que cerrarla o documentarla como limitación. |

---

## 1. Especies (`core/microorganism.py` — dueña: Esmeralda)

### 1.1 Temperatura — puntos cardinales (°C)

| Especie | `t_min` | `t_opt` | `t_max` | Proc. | Nota |
|---|---|---|---|---|---|
| *E. coli* | 7.5 | 37.0 | 47.0 | **[LIT]** | mesófilo de referencia |
| *D. radiodurans* | 4.0 | 30.0 | 39.0 | **[LIT]** | **es mesófila**, pese a su fama |
| *M. burtonii* | −2.5 | 23.4 | 29.5 | **[LIT]** | óptimo 23.4 y máximo 29.5 publicados; mínimo teórico −2.5 |

Los tres puntos cardinales son exactamente lo que consume el modelo CTMI de
ADR-0013: no hay parámetros libres que ajustar.

### 1.2 Actividad de agua (0..1)

| Especie | `a_w_min` (crece) | `a_w_sup_min` (sobrevive) | Proc. | Nota |
|---|---|---|---|---|
| *E. coli* | 0.95 | 0.50 | **[LIT]** / **[EST]** | el 0.95 es dato duro y **no se toca**; el de supervivencia es estimación |
| *D. radiodurans* | 0.90 | 0.0 | **[LIT]** / **[LIT]** | 0.90 es su límite de metabolismo **activo**; el 0.0 es la anhidrobiosis |
| *M. burtonii* | 0.95 | 0.80 | **[LIT]** / **[EST]** | medio marino; **no** es anhidrobiótica |

> **Cota dura del modelo:** ningún `a_w_min` de **crecimiento** puede bajar de
> **0.605**, que es el límite inferior conocido de división celular para cualquier
> organismo terrestre. Hay un test que lo verifica y falla si alguien lo baja. Si
> una especie no crece, la respuesta correcta es que quede `LATENTE` — nunca
> bajarle el umbral.

### 1.3 Radiación UV (W/m²) — **derivados, no inventados**

La letalidad del UV es una **fluencia** (J/m²), pero el campo `R` es una
**irradiancia** (W/m²), que es lo que miden los datos. La conversión es explícita:

```
uv_letal = FLUENCIA_LETAL_J_M2 / SEGUNDOS_UV_POR_TICK
uv_max   = uv_letal / RAZON_INHIBICION_UV
```

| Constante | Valor | Proc. | Justificación |
|---|---|---|---|
| `SEGUNDOS_UV_POR_TICK` | 28 800 s (8 h) | **[CONV]** | sol útil en un tick diario, que es la resolución de los datasets |
| `RAZON_INHIBICION_UV` | 10 | **[CONV]** | el estrés subletal frena la división antes de matar |

| Especie | Fluencia letal (J/m²) | Proc. | `uv_letal` (W/m²) | `uv_max` (W/m²) |
|---|---|---|---|---|
| *E. coli* | 870 | **[LIT]** | 0.0302 | 0.0030 |
| *D. radiodurans* | 50 760 | **[LIT]** | 1.7625 | 0.1763 |
| *M. burtonii* | 870 | **[EST]** | 0.0302 | 0.0030 |

El cociente **58×** entre *D. radiodurans* y *E. coli* sale directo de las
fluencias publicadas — es de donde viene su fama de radiorresistente, y ya no es
un factor que hayamos elegido a ojo.

> ⚠️ **`SEGUNDOS_UV_POR_TICK` acopla dos módulos.** Si Erick cambia el Δt del
> autómata, esta constante **tiene que cambiar con él**, o los umbrales dejan de
> significar lo que dicen. Es el punto de acoplamiento más silencioso del modelo.

> ⚠️ **El UV de *M. burtonii* es [EST]**, el parámetro más débil que tenemos. No
> hay dato publicado; se asume el de *E. coli* como cota conservadora (arquea
> anaerobia estricta, sin la maquinaria de reparación de *Deinococcus*). En
> Encelado nunca se activa porque `R = 0`; **solo importa en Modo Sandbox**.

### 1.4 Tasa de crecimiento

| Especie | `mu_opt` (h⁻¹) | Proc. |
|---|---|---|
| *E. coli* | 2.1 | **[LIT]** |
| *D. radiodurans* | 0.26 | **[LIT]** |
| *M. burtonii* | 0.069 | **[LIT]** |

El orden relativo (mesófilo rápido › extremófilo › psicrótolerante) es lo que
importa para comparar dinámicas.

---

## 2. Entornos (`core/environment.py` — dueño: Jose)

| Constante | Valor | Proc. | Justificación |
|---|---|---|---|
| `FRACCION_UV` | 0.05 | **[CONV]** | fracción UV-A+UV-B de la irradiancia global |
| **Tierra** `T_SUBSUELO_C` | 19.8 | **[LIT]** | media anual del dataset: es el valor al que amortigua la onda térmica |
| **Tierra** `A_W_SUBSUELO` | 0.99 | **[LIT]** | suelo a capacidad de campo. **NO** la columna del dataset (ver §4) |
| **Tierra** `UV_SUBSUELO` | 0.0 | **[LIT]** | el suelo bloquea el UV por completo |
| **Marte** `T_SUPERFICIE_C` | 36.9 | **[LIT]** | media de máximos diarios de Atacama |
| **Marte** `T_PROFUNDO_C` | 7.8 | **[EST]** | media de **mínimos** diarios — **probablemente incorrecto**, ver §4 |
| **Marte** `RADIACION_GLOBAL_W_M2` | 844.2 | **[LIT]** | media de radiación solar máxima de Atacama |
| **Marte** `UV_SUPERFICIE` | 42.2 | **[DER]** | `844.2 × 0.05`. **Validación fuerte:** cae dentro del rango publicado de UV marciano (**42–55 W/m²**) |
| **Marte** `A_W_MEDIA` | 0.187 | **[EST]** | media del **mínimo diario** — cota pesimista, ver §4 |
| **Marte** `A_W_SIGMA` | 0.080 | **[LIT]** | dispersión real de esa serie |
| **Marte** `RAZON_ATENUACION_UV` | 10 | **[CONV]** | el UV se extingue en mm–cm, mucho más rápido que el calor |
| **Encelado** `T_OCEANO_C` | 2.4 | **[LIT]** | media de temperatura de ventila |
| **Encelado** `A_W_OCEANO` | 0.98 | **[LIT]** | media del dataset de ventilas |
| **Encelado** `UV_ENCELADO` | 0.0 | **[LIT]** | blindaje total del hielo; el IR del dataset es **calor**, no UV |
| **Encelado** `DELTA_T_FUMAROLA` | 25.0 | **[EST]** | pico sobre el fondo; ver §4 |
| **Encelado** `SIGMA_FRACCION` | 0.08 | **[CONV]** | radio de decaimiento como fracción de la grilla, para que la física no dependa de la resolución |

---

## 3. Qué produce el modelo con estos valores

| Especie / entorno | `ACTIVA` | `LATENTE` | `MUERTA` |
|---|---|---|---|
| *E. coli* / Tierra | 100 % | 0 % | 0 % |
| *D. radiodurans* / Marte | **0 %** | **94 %** | **6 %** |
| *M. burtonii* / Encelado | 100 % | 0 % | 0 % |

**La banda de profundidad marciana emerge sola de los datos**, sin ajustar nada:

| Filas | Estado | Causa |
|---|---|---|
| 0–2 | `MUERTA` | UV por encima de la fluencia letal: superficie estéril |
| 3–4 | `LATENTE` | el UV ya no mata pero inhibe; y falta agua |
| 5+ | `LATENTE` | el UV deja de limitar; sigue faltando agua |

Con un microrefugio húmedo (`a_w = 0.95`) **por debajo de la fila 5**, el
crecimiento se reactiva. Ese es exactamente el objeto de la pregunta de
investigación de ADR-0015: **cuánta agua transitoria, y cada cuánto, hace falta
para que la población persista.**

---

## 4. Deuda abierta — lo que hay que cerrar

Ordenado por impacto sobre la credibilidad del resultado.

| # | Qué | Dueño | Por qué importa |
|---|---|---|---|
| 1 | **`a_w` media de Atacama.** Hoy usamos el **mínimo diario** (0.187) como valor del campo. Es una cota pesimista, no el valor típico. | Fidel | Sesga toda corrida hacia la extinción. Es el parámetro que más mueve el resultado. |
| 2 | **`T_PROFUNDO_C` de Marte.** Es la media de los mínimos diarios, pero una onda térmica amortigua hacia la **media anual** (≈ 22.4 °C), no hacia el mínimo. | Jose | Cambia dónde queda la banda habitable. Creemos que está mal. |
| 3 | **`a_w` del control terrestre.** La columna del dataset es humedad del **aire** (media 0.55, rango 0.16–0.93, sd 0.23); un suelo no oscila así. Usamos 0.99 teórico. | Fidel | O se consigue `a_w` de suelo, o se documenta como limitación conocida. |
| 4 | **UV de *M. burtonii*.** **[EST]** sin dato publicado. | Esmeralda | Solo afecta al Modo Sandbox (en Encelado `R = 0`), pero es el único parámetro sin ninguna base. |
| 5 | **`a_w_sup_min` de *E. coli* y *M. burtonii*.** **[EST]**. | Esmeralda | Define cuánto aguantan antes de morir, no cuándo crecen. Impacto medio. |
| 6 | **`ΔT = 25` del evento hidrotermal.** Apilado sobre una fumarola existente lleva T a 59 °C y mata a *M. burtonii* en el 29 % de los disparos. Puede ser correcto (el núcleo de una ventila **es** letal), pero hay que decidirlo. | Jose | Afecta la dinámica de Encelado. |
| 7 | **`SEGUNDOS_UV_POR_TICK` y el Δt del autómata.** Tienen que ser coherentes. | Erick + Esmeralda | Si divergen, los umbrales UV dejan de significar lo que dicen, en silencio. |

---

## 5. Referencias

- **Límite de `a_w` para división celular (≈ 0.605):** Stevenson et al. (2015),
  *Multiplication of microbes below 0.690 water activity*, Environmental Microbiology.
- **Crecimiento en simulante de regolito marciano:** réplica marginal a `a_w = 0.34`,
  nula a `0.12`; *B. subtilis* cesa bajo `0.94`.
- **Crecimiento vs. supervivencia (precedente de ADR-0012):** estudio NanoSIMS en
  *S. liquefaciens* — "podría metabolizar y crecer sobre −5 °C y **sobrevivir pero
  no crecer** bajo −5 °C".
- **Puntos cardinales de *M. burtonii*:** óptimo 23.4 °C, máximo 29.5 °C, mínimo
  teórico −2.5 °C.
- **Fluencias UV₂₅₄:** *E. coli* 870 J/m²; *D. radiodurans* 50 760 J/m².
- **UV en superficie marciana:** 42–55 W/m² (200–400 nm) con poco polvo; dosis
  biológicamente efectiva hasta 3 órdenes de magnitud sobre la terrestre.
- **Radiación ionizante:** *D. radiodurans* tolera 5000 Gy sin pérdida de
  viabilidad (D37 ≈ 6000–7000 Gy); *E. coli* D10 ≈ 300 Gy; superficie marciana
  0.21 mGy/día ≈ 0.077 Gy/año (RAD, Curiosity) — de ahí que la dosis ionizante
  **no discrimine** en la escala de la simulación (ADR-0014).
