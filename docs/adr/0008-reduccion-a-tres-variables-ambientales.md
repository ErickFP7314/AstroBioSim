# ADR-0008: Reducción del modelo a tres variables ambientales (T, R, A_w)

- **Estado:** Aceptado
- **Fecha:** 2026-07-17
- **Modifica:** ADR-0002, ADR-0003, ADR-0005, ADR-0006

## Contexto
El documento de especificación original define **cuatro** variables críticas:
temperatura (`T`), radiación (`R`), presión (`P`) y actividad de agua (`A_w`).

Al construir el Modo Analógico sobre datasets de ambientes extremos **terrestres**
(Atacama, Antártida), el equipo observó que la **presión** aporta poca o ninguna
capacidad discriminante: todos los análogos terrestres se encuentran en un rango
barométrico estrecho (~0.5–1 atm), por lo que `P` permanece esencialmente
constante a lo largo de la serie y nunca cruza los umbrales letales de las
especies. Una variable que no varía no separa escenarios: no produce muerte por
estrés, no diferencia entornos y sólo añade una dimensión muerta al vector
ambiental.

En contraste, la **actividad de agua** derivada de la humedad relativa del mismo
dataset (`A_w = HR / 100`) sí presenta variación amplia y es el factor limitante
dominante en subsuelo desértico — el análogo marciano más informativo.

## Decisión
Reducir el vector ambiental de cuatro a **tres** variables:

```
E_{x,y}^t = { T_{x,y}^t , R_{x,y}^t , A_{w; x,y}^t }
```

Consecuencias directas sobre el modelo:

1. **Motor biológico** — `Microorganismo` pierde los atributos `p_min` y `p_max`.
   Atributos restantes: `t_min`, `t_max`, `r_letal`, `a_w_min`, `mu_max`.
2. **Regla de muerte por estrés ambiental** — se elimina el término `P < P_min`.
   Queda: `T < T_min ∨ T > T_max ∨ R > R_letal ∨ A_w < A_w_min`.
3. **Regla de reproducción** — la conjunción de umbrales se evalúa sobre tres
   variables en lugar de cuatro.
4. **Capa de datos** — el dataset **IMAU Antarctic** deja de ser necesario (su
   único propósito era proveer `air pressure`). El Modo Analógico depende ahora
   de una sola fuente: **CRC1211DB (Atacama)**, de la que se extraen
   `soil temperature` → `T` y `relative humidity` → `A_w`.
5. **Eventos Montecarlo** — se reformulan sin el eje de presión:
   - *Marte — micro-fisuras:* pasa a ser un **evento de desecación**: caída
     abrupta de `A_w` en un radio de celdas. La causa física (micro-fisura y
     despresurización) se conserva como narrativa; su efecto modelado es la
     pérdida de agua interstitial, que es lo que mata la célula.
   - *Encelado — emisiones hidrotermales:* conserva el pico térmico
     `ΔT ~ N(μ, σ²)` con disipación radial; se elimina `ΔP`.
6. **Entornos** — `EnceladoSubglacial` deja de diferenciarse por presión
   barométrica y pasa a caracterizarse por `A_w ≈ 1` constante, gradiente
   térmico extremo cerca de fumarolas y `R ≈ 0` (protección total contra
   radiación estelar). Ver "Riesgos" abajo.

## Alternativas consideradas
1. **Conservar `P` como constante decorativa.** Rechazado: añade una dimensión
   al vector y ramas de código que nunca se activan — deuda muerta que
   contradice DRY.
2. **Conservar `P` sólo para Encelado** (donde sí variaría, por columna de
   agua/hielo). Rechazado por ahora: obligaría a un vector ambiental de forma
   variable según el entorno, rompiendo la uniformidad de `CampoAmbiental`
   (ADR-0003) y el bucle único de simulación. Reconsiderable si la
   diferenciación de Encelado resulta insuficiente.
3. **Reducir a `A_w` únicamente.** Rechazado: `T` y `R` son precisamente los ejes
   que definen a `M_Burtonii` (psicrotolerante, definida por su rango de T — ADR-0011)
   y `D_Radiodurans` (radiorresistente);
   sin ellos las tres especies serían indistinguibles y el estudio comparativo
   perdería su objeto.

## Consecuencias
- (+) **Menos superficie**: se elimina un loader completo (IMAU Antarctic), una
  capa del campo ambiental, dos atributos de especie y un término en cada regla.
- (+) El Modo Analógico depende de **un solo dataset**, lo que reduce el riesgo
  de acceso/formato y elimina el problema de sincronizar dos series con
  resoluciones temporales distintas (ADR-0005).
- (+) `A_w` queda como factor limitante dominante, coherente con la literatura de
  límites de habitabilidad en subsuelo desértico.
- (−) **Riesgo — diferenciación de Encelado:** la presión era uno de los rasgos
  que distinguían el océano subglacial. Encelado queda ahora definido por
  `T` (gradiente hidrotermal), `A_w ≈ 1` y `R ≈ 0`. Debe verificarse en la fase
  de validación que sigue produciendo dinámicas cualitativamente distintas de
  Tierra; si no, revisar la alternativa 2.
- (−) La justificación de "micro-fisura" como evento de desecación debe quedar
  explícita en el informe para que no se lea como una omisión del modelo.
