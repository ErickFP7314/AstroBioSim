# Nota — Especie de Encelado: decisión y candidatas

> **✅ DECISIÓN (ADR-0011):** la especie de Encelado es **Methanococcoides
> burtonii** (metanógena psicrotolerante), en reemplazo de la termófila
> *Methanocaldococcus okinawensis*. Motivo: los datos de ventila 2025 dan
> **T ≈ 2.4 °C** (agua de fondo del océano subglacial), incompatible con una
> termófila de 50–80 °C. Solo falta que Esmeralda re-calibre los umbrales finales
> con literatura (Hito 4). Esta nota documenta el porqué y las alternativas.

## Contexto físico del análogo

| Variable | Valor en los datos | Implicación para la especie |
|---|---|---|
| **T** | ~2.4 °C, casi constante | Necesita **psicrófila/psicrotolerante** |
| **A_w** | ~0.9817 (agua de mar, 34.5 psu) | Medio acuoso salino: `a_w_min` alto, ~0.94–0.96 |
| **R** | mapeada a ≈0 (subglacial, ver ADR-0010) | Radiación **no es limitante** → `r_letal` alto/no crítico |

## Por qué Methanococcoides burtonii

Se priorizó mantener el hilo **metanógeno** (como la okinawensis), porque el penacho
de Encelado tiene **CH₄ y H₂** y la metanogénesis (H₂ + CO₂ → CH₄) es el metabolismo
candidato principal — argumento fuerte para el informe. *M. burtonii* cubre la
T≈2.4 °C con margen, es metanógena y está muy bien caracterizada (organismo modelo
de adaptación al frío).

## Candidatas evaluadas (valores de partida, ajustar con literatura)

| Especie | T (°C) aprox. | `t_min` / `t_max` | `a_w_min` | Estado |
|---|---|---|---|---|
| **Methanococcoides burtonii** ✅ | -2 … 29, ópt. ~23 | -2 / 29 | ~0.94 | **ELEGIDA** (ADR-0011). Metanógena psicrotolerante (Ace Lake). Genoma secuenciado, modelo de frío. |
| Methanogenium frigidum | 0 … 18, ópt. ~15 | 0 / 18 | ~0.95 | Alternativa. Metanógena estrictamente psicrófila; aún más ceñida al dato frío. |
| Colwellia psychrerythraea 34H | -12 … 18, ópt. ~8 | -12 / 18 | ~0.94 | Descartada como principal: no metanógena (se pierde el hilo astrobiológico). |
| Planococcus halocryophilus Or1 | -15 … 37, ópt. ~25 | -15 / 37 | ~0.90 | Descartada como principal: no metanógena; útil solo si se quisiera enfatizar el estrés salino. |

## Valores de partida para la clase

```python
# Encelado — reemplaza a MOkinawensis (ADR-0011). Ajustá con literatura.
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

## Qué falta cerrar (Hito 4)
1. Re-calibrar `t_min/t_max/a_w_min/r_letal` finales de `MBurtonii` con literatura.
2. Fijar `mu_max` **relativo** entre las tres especies.
3. Documentar la fuente de literatura de cada umbral en el test de la especie.
