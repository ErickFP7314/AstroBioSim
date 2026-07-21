# Nota para Esmeralda — Especie de Encelado: candidatas psicrófilas

> **Cuestión abierta (ADR-0010):** los datos de ventila 2025 dan **T ≈ 2.4 °C**
> (agua de fondo del océano subglacial), incompatibles con la termófila
> *Methanocaldococcus okinawensis* (50–80 °C) que teníamos asignada. Esta nota
> propone el reemplazo. **La decisión final es tuya (biología) + Jose (física del
> gradiente térmico).** Ver `docs/instrucciones/esmeralda.md`.

## Contexto físico del análogo

| Variable | Valor en los datos | Implicación para la especie |
|---|---|---|
| **T** | ~2.4 °C, casi constante | Necesita **psicrófila/psicrotolerante** |
| **A_w** | ~0.9817 (agua de mar, 34.5 psu) | Medio acuoso salino: `a_w_min` alto, ~0.94–0.96 |
| **R** | mapeada a ≈0 (subglacial, ver ADR-0010) | Radiación **no es limitante** → `r_letal` alto/no crítico |

## Dos caminos (elegí uno)

- **(A) Cambiar la especie por una psicrófila.** Recomendado: coherente con el
  dato real y con la narrativa astrobiológica de Encelado.
- **(B) Mantener una termófila viviendo solo en los picos calientes** que genere
  el evento hidrotermal estocástico de Jose (§3.4). Válido, pero depende de que
  el evento produzca celdas a 50–80 °C; hoy los datos no muestran ese gradiente,
  habría que inventarlo. Más frágil de defender.

## Candidatas psicrófilas (valores de partida, ajustá con literatura)

Todas son marinas/salinas y crecen en frío. Prioricé mantener el hilo
**metanógeno** (como la okinawensis), porque el penacho de Encelado tiene **CH₄ y
H₂** y la metanogénesis (H₂ + CO₂ → CH₄) es la metabolismo candidato principal —
argumento fuerte para el informe.

| Especie | T (°C) aprox. | `t_min` / `t_max` | `a_w_min` | Por qué |
|---|---|---|---|---|
| **Methanococcoides burtonii** ⭐ | -2 … 29, ópt. ~23 | -2 / 29 | ~0.94 | **Metanógena psicrotolerante** (Ace Lake, Antártida). Genoma secuenciado, organismo modelo de adaptación al frío. Mantiene el hilo metanógeno de Encelado. |
| Methanogenium frigidum | 0 … 18, ópt. ~15 | 0 / 18 | ~0.95 | Metanógena estrictamente psicrófila (Ace Lake). Más fría aún que burtonii; buen encaje con T≈2.4 °C. |
| Colwellia psychrerythraea 34H | -12 … 18, ópt. ~8 | -12 / 18 | ~0.94 | Psicrófila marina de referencia; crece en salmuera bajo cero. No metanógena, pero muy robusta como control frío. |
| Planococcus halocryophilus Or1 | -15 … 37, ópt. ~25 | -15 / 37 | ~0.90 | Extremófila **frío + sal**: se divide a -15 °C en alta salinidad. Ideal si querés enfatizar el estrés salino de la ventila. |

⭐ **Recomendación:** *Methanococcoides burtonii* como especie de Encelado.
Cubre T≈2.4 °C con margen, es metanógena (continuidad conceptual con la
okinawensis y relevancia astrobiológica directa), y está bien caracterizada. Si
preferís el ajuste más ceñido al dato frío, *Methanogenium frigidum* es la
alternativa estrictamente psicrófila.

## Valores de partida sugeridos para la clase

```python
# Encelado — reemplaza a MOkinawensis. Ajustá con literatura.
class MBurtonii(Microorganismo):
    t_min = -2.0      # °C
    t_max = 29.0      # °C  (cubre los ~2.4 °C del dato con holgura)
    a_w_min = 0.94    # medio marino, necesita agua líquida
    r_letal = 1_000.0 # W/m² — alto: R≈0 subglacial, radiación no limita (ADR-0010)
    mu_max = ...      # menor que E. coli: crecimiento lento en frío
```

> **Nota sobre `r_letal`:** como Encelado mapea `R≈0`, el valor concreto es casi
> irrelevante mientras sea positivo; ponelo alto para que la radiación nunca sea
> el factor que mata. El estrés real en Encelado es térmico/salino, no radiativo.

## Qué falta cerrar

1. Confirmar la especie (A vs. B) con Jose.
2. Fijar `mu_max` **relativo** entre las tres especies (biología tuya).
3. Documentar la fuente de literatura de cada umbral en el test de la especie.
