# ADR-0011: Especie análoga de Encelado — Methanococcoides burtonii (reemplaza a M. okinawensis)

- **Estado:** Aceptado
- **Fecha:** 2026-07-21
- **Modifica:** ADR-0010 (resuelve su cuestión abierta #1). Relacionado: ADR-0001, ADR-0003.

## Contexto
ADR-0010 dejó abierta una incompatibilidad biológica: los datos reales 2025 de las
ventilas hidrotermales dan **T ≈ 2.4 °C** (agua de fondo del océano subglacial),
mientras que la especie asignada a Encelado era *Methanocaldococcus okinawensis*, una
metanógena **termófila** (50–80 °C). Con la temperatura del análogo, la termófila
moriría en todas las celdas de forma trivial, dejando la corrida de Encelado sin
contenido comparativo.

## Decisión
Reemplazar la especie análoga de Encelado por **Methanococcoides burtonii**, una
**metanógena psicrotolerante** (lago Ace, Antártida; T ≈ -2…29 °C, óptimo ~23 °C,
genoma secuenciado y organismo modelo de adaptación al frío).

Valores de partida (Esmeralda re-calibra con literatura, Hito 4):
- `t_min = -2 °C`, `t_max = 29 °C` — cubre los ~2.4 °C del dato con holgura.
- `a_w_min ≈ 0.94` — medio marino, requiere agua líquida.
- `r_letal` alto (~1000 W/m²) — radiación **no limitante**, porque Encelado mapea
  `R ≈ 0` (ADR-0010: su IR es calor, no dosis ionizante).
- `mu_max` relativamente bajo (crecimiento lento en frío), a fijar por Esmeralda.

La clase pasa a llamarse **`MBurtonii`** y el roster de especies queda
`EColi` / `DRadiodurans` / `MBurtonii`.

## Alternativas consideradas
1. **Mantener la termófila viviendo solo en los picos calientes** del evento
   `EmisionHidrotermalEncelado` (§3.4). Rechazado: los datos no muestran ese
   gradiente caliente; habría que inventarlo, y el nicho habitable sería marginal y
   difícil de defender en el informe.
2. **Methanogenium frigidum** (metanógena estrictamente psicrófila, ópt. ~15 °C).
   Viable y aún más ceñida al dato frío; queda como alternativa. Se prefirió
   *burtonii* por estar mejor caracterizada (organismo modelo) manteniendo el hilo
   metanógeno.
3. **Psicrófila no metanógena** (*Colwellia psychrerythraea*, *Planococcus
   halocryophilus*). Rechazado como principal: se pierde la continuidad con la
   metanogénesis, que es el metabolismo candidato del penacho de Encelado
   (CH₄ + H₂) y un argumento astrobiológico central.

## Consecuencias
- (+) La corrida de Encelado vuelve a ser informativa: la especie es viable a la T
  del análogo.
- (+) Se conserva el hilo **metanógeno** (relevancia astrobiológica directa: el
  penacho de Encelado contiene CH₄ y H₂).
- (+) **Ninguna frontera cambia:** la clase sigue heredando de `Microorganismo`
  (§3.2); el motor biológico, el Autómata Celular y el orquestador no se tocan. Es
  un cambio de **parámetros y nombre**, no de arquitectura.
- (−) Hay que actualizar el nombre de la clase y sus umbrales en todo el plan (hecho
  en este cambio) y re-calibrar `mu_max` relativo (Esmeralda, Hito 4).
- (−) La documentación previa que citaba *M. okinawensis* (termófila) queda
  obsoleta; se anota como reemplazada.

## Referencias
- Nota de análisis y candidatas: `docs/notas/encelado-especie-psicrofila.md`.
- Cuestión abierta de origen: ADR-0010, riesgo #1.
