# Tablero de tareas — AstroBioSim

> **Espejo en Markdown del tablero de Trello** — <https://trello.com/b/cK8VP1aj>
>
> Existe para que cualquier agente de IA (o persona) **sin acceso a Trello** pueda
> ver qué está hecho, qué falta y con qué criterios de aceptación se da por
> terminada cada tarea.
>
> **Última sincronización:** 2026-07-25 · regenerar con `python scripts/sync_tablero.py`

## Cómo leerlo

- `- [x]` criterio de aceptación **cumplido** · `- [ ]` **pendiente**.
- Una tarjeta pasa a **✅ Hecho** solo cuando **todos** sus criterios están marcados.
- Los criterios son deliberadamente verificables: casi todos se comprueban
  corriendo `pytest`. Si no se puede comprobar, no es un criterio.
- Este documento dice **qué** falta; `docs/instrucciones/<nombre>.md` dice **cómo**
  hacerlo, y `docs/adr/` dice **por qué** se decidió así.

**Progreso global:** 61/103 criterios (59%)

| Integrante | Área | Criterios cumplidos |
|---|---|---|
| 🟢 **Esmeralda** | Motor biológico + notebook | 19/26 (73%) |
| 🟡 **Fidel** | Datos análogos + validación | 8/15 (53%) |
| 🔵 **Jose** | Motor ambiental + eventos | 19/24 (79%) |
| 🟣 **Erick** | Autómata Celular + UI | 15/38 (39%) |

---

## Hito 1 — Fundaciones

_(vacío)_

---

## Hito 2 — Dominio — 0/4 criterios

### ⬜ 🟡 Radiacion a banda UV + a_w media de Atacama

**Dueño:** Fidel · **Criterios:** 0/4

> ADR-0014 y ADR-0015. Dos correcciones de datos: la columna de radiacion cambia de significado, y la de a_w esta sesgada por usar el minimo diario.

- [ ] El adaptador convierte `radiation` a banda UV y el factor queda DOCUMENTADO en el codigo
- [ ] Se re-extrae la `a_w` MEDIA de Atacama (hoy el dataset solo trae el minimo diario)
- [ ] Queda documentado que la `a_w` del control terrestre es humedad del AIRE, no del suelo
- [ ] `pytest` en verde

---

## Hito 3 — Superficies — 0/21 criterios

### ⬜ 🟣 Integracion Montecarlo en el bucle

**Dueño:** Erick · **Criterios:** 0/4

> *Como orquestador, quiero repetir la simulacion N veces con semillas explicitas para obtener una distribucion, no una sola corrida.*
>
> Integracion final Montecarlo en `simulation.py`.
> Rama: `feat/simulation-orquestador`.

- [ ] N corridas con semillas distintas producen una distribucion de poblaciones
- [ ] Reproducible: el mismo conjunto de semillas da el mismo resultado agregado
- [ ] Devuelve media +- desviacion por iteracion de las TRES fracciones: activa / latente / muerta (ADR-0012)
- [ ] `pytest` en verde

### ⬜ 🟣 UI: backend FastAPI + dashboard React

**Dueño:** Erick · **Criterios:** 0/4

> *Como usuario, quiero un dashboard web para lanzar y visualizar la simulacion en tiempo real.*
>
> `ui/api.py` expone la API del orquestador; `frontend/` (React) consume SOLO esa API (ADR-0009).
> Rama: `feat/ui-dashboard`.

- [ ] El endpoint devuelve la grilla con sus TRES estados y las tres curvas de poblacion en JSON
- [ ] El dashboard React renderiza la grilla y el grafico consumiendo la API
- [ ] Los sliders T / UV / A_w y el selector de entorno cambian la simulacion mostrada
- [ ] La app corre localmente (uvicorn + npm) sin errores

### ⬜ 🟢 Notebook de analisis

**Dueño:** Esmeralda · **Criterios:** 0/4

> *Como analista, quiero un notebook que compare las dinamicas de los 3 entornos con estadistica Montecarlo.*
>
> Corridas Montecarlo, curvas de poblacion media ± σ, comparacion Tierra/Marte/Encelado.
> Rama: `feat/notebook-analisis`.

- [ ] El notebook corre de punta a punta sin errores usando `simulation.py`
- [ ] Grafica las TRES fracciones (ACTIVA/LATENTE/MUERTA) media +- sigma vs. tiempo para Tierra/Marte/Encelado
- [ ] Los resultados son reproducibles (semillas explicitas)
- [ ] La lectura biologica de cada entorno queda documentada en el notebook

### ⬜ 🟣 Barrido: umbral critico de microrefugios

**Dueño:** Erick · **Criterios:** 0/4

> ADR-0015. Es el entregable con mas peso academico del proyecto: responde la pregunta de investigacion.

- [ ] Barrido frecuencia x magnitud del evento de salmuera sobre ensambles Montecarlo con semillas explicitas
- [ ] La variable de respuesta es la persistencia (fraccion activa/latente/muerta al final de la corrida)
- [ ] El resultado identifica un UMBRAL CRITICO: debajo la poblacion se extingue, encima persiste
- [ ] El mapa de persistencia se regenera de forma reproducible desde el notebook

### ⬜ 🟣 Editor de reglas por bloques + panel de notacion

**Dueño:** Erick · **Criterios:** 0/5

> ADR-0016. La UI ofrece un menu con las reglas de fabrica (logistica/conway/hibrida) y una opcion 'personalizar' que arma reglas con bloques tipo Scratch (condicionales y procesos estandarizados). El motor ya esta preparado: cada regla es una ReglaTransicion y el editor es una fabrica de reglas, no toca engine/.

- [ ] Menu desplegable con las 3 reglas de fabrica (REGLAS_DISPONIBLES) intercambiables en vivo
- [ ] Opcion 'personalizar': bloques de condiciones/procesos que producen una ReglaTransicion valida
- [ ] El editor NO toca engine/: solo construye reglas contra la interfaz ReglaTransicion
- [ ] Panel que renderiza notacion() de la regla activa (LaTeX) en notacion formal de AC
- [ ] Una regla personalizada respeta los invariantes: sincrona, MUERTA absorbente, sin RNG global

---

## Hito 4 — Validacion — 0/17 criterios

### ⬜ 🟢 Calibracion de umbrales con literatura

**Dueño:** Esmeralda · **Criterios:** 0/3

> *Como biotecnologa, quiero umbrales de especie realistas para que los resultados sean defendibles.*
>
> Calibrar `t_min/t_opt/t_max/a_w_min/uv_max` y los umbrales de supervivencia de cada especie con literatura.
> Rama: `fix/bio-calibracion`.

- [ ] Los umbrales de cada especie citan fuente de literatura
- [ ] Ninguna especie queda con 0% de SUPERVIVENCIA en su entorno; tests/integration/test_especie_en_su_entorno.py en verde
- [ ] Los tests de especies siguen en verde tras la calibracion

### ⬜ 🟡 Validacion biologica de las salidas

**Dueño:** Fidel · **Criterios:** 0/3

> *Como biotecnologo, quiero comprobar que las poblaciones evolucionan de forma biologicamente plausible.*
>
> Validar las salidas de las 3 corridas y documentar limites del mapeo de datos.
> Rama: `chore/validacion-datos`.

- [ ] Las poblaciones no muestran artefactos (extincion instantanea / saturacion irreal) en las 3 corridas
- [ ] La banda UV y su factor de conversion quedan documentados en el adaptador (ADR-0014 reemplaza el proxy W/m2 vs Gy)
- [ ] Caso de prueba: el entorno mas hostil produce menor supervivencia que el control (Tierra)

### ⬜ 🔵 Sanidad fisica de gradientes y eventos

**Dueño:** Jose · **Criterios:** 0/5

> *Como fisico, quiero verificar que los campos y eventos son fisicamente coherentes.*
>
> Chequear gradiente termico, campo de radiacion y disipacion de eventos; confirmar diferenciacion de Encelado.
> Rama: `chore/sanidad-fisica`.

- [ ] El gradiente termico del regolito esta en rango fisico esperado por profundidad
- [ ] Los eventos estocasticos perturban/disipan sin generar valores no fisicos
- [ ] Encelado queda diferenciado de los otros entornos en el campo resultante
- [ ] Revisada la asintota termica de Marte: la onda amortigua hacia la media anual, no hacia el minimo diario
- [ ] Revisar ΔT=25 del evento hidrotermal: si cae sobre una fumarola existente lleva T a 59 °C y mata a M. burtonii en 29% de los disparos. Puede ser correcto (el nucleo de una ventila es letal), pero hay que decidirlo

### ⬜ 🟣 Validacion estadistica de Montecarlo

**Dueño:** Erick · **Criterios:** 0/3

> *Como responsable del motor, quiero asegurar que la estadistica de las corridas es solida.*
>
> Validar nº de repeticiones y reporte de dispersion de las corridas Montecarlo.
> Rama: `chore/validacion-estadistica`.

- [ ] El nº de repeticiones es suficiente (la media se estabiliza al aumentar N)
- [ ] No se confunde una corrida con la distribucion (se reporta media ± σ)
- [ ] Resultados reproducibles con semillas fijas

### ⬜ 🟣 Analisis de sensibilidad de parametros

**Dueño:** Erick · **Criterios:** 0/3

> ADR-0013. Blinda el resultado frente a la incertidumbre de los umbrales biologicos.

- [ ] Cada umbral se varia sobre su rango de incertidumbre en literatura
- [ ] Se reporta que parametro domina el desenlace
- [ ] Se documenta si las conclusiones se sostienen dentro de todo el rango de incertidumbre

---

## En revisión

_(vacío)_

---

## ✅ Hecho — 61/61 criterios

### ✅ 🔵 Motor ambiental: CampoAmbiental + 3 entornos

**Dueño:** Jose · **Criterios:** 8/8

> *Como motor ambiental, quiero exponer T, R y A_w por celda para que todos los modulos consuman el mismo campo.*
>
> Implementar `CampoAmbiental` (dataclass con validacion de formas) y `PlanetaSubsuelo` -> Tierra/Marte/Encelado con su campo inicial (contrato §3.1).
>
> **PRIORIDAD 1** — desbloquea a todo el equipo.
> Rama: `feat/env-campo-ambiental`.

- [x] `CampoAmbiental(T,R,A_w)` valida que las 3 capas tengan forma identica (levanta error si no)
- [x] `.shape` devuelve `(M,N)` correcto
- [x] Cada entorno (Tierra/Marte/Encelado) genera un CampoAmbiental con las 3 capas pobladas
- [x] `pytest tests/unit/test_environment.py` pasa en verde
- [x] `R` es irradiancia UV y el factor de conversion queda documentado (ADR-0014)
- [x] El campo de Tierra usa a_w de SUELO, no humedad del aire
- [x] El campo de Marte porta su dispersion con `rng` opcional, no el minimo colapsado (ADR-0015)
- [x] Fix: el radio de las fumarolas es fraccion de la grilla; la fisica ya no depende de la resolucion

### ✅ 🔵 Eventos estocasticos: micro-fisura + emision hidrotermal

**Dueño:** Jose · **Criterios:** 5/5

> *Como fisica del entorno, quiero perturbar el campo con eventos aleatorios reproducibles para modelar dinamica Montecarlo.*
>
> Implementar `EventoEstocastico.aplicar(campo, rng)` que perturba el campo sin tocar la biologia (contrato §3.4).
> Rama: `feat/engine-estocastico`.

- [x] `aplicar()` devuelve un CampoAmbiental nuevo perturbado, sin modificar el estado biologico
- [x] Usa el `rng` inyectado: misma semilla -> mismo resultado (reproducible)
- [x] Micro-fisura marciana y emision hidrotermal producen cambios dentro de rango fisico esperado
- [x] `pytest tests/unit/test_stochastic.py` pasa en verde
- [x] Los dos eventos siguen pasando sin cambios tras ADR-0012..0015 (`test_stochastic.py` en verde)

### ✅ 🟢 Motor biologico: especies y habitabilidad

**Dueño:** Esmeralda · **Criterios:** 8/8

> *Como motor biologico, quiero evaluar que celdas son habitables segun T, R y A_w para que el automata sepa donde puede vivir cada especie.*
>
> Implementar `Microorganismo` + `EColi`, `DRadiodurans`, `MOkinawensis` y `condiciones_habitables(campo)` (contrato §3.2).
> Rama: `feat/bio-especies`.

- [x] `condiciones_habitables(campo)` devuelve mascara `bool (M,N)` correcta para un campo de prueba
- [x] Test: cada especie muere si UNA sola variable sale de umbral (una prueba por variable y especie)
- [x] `pytest tests/unit/test_microorganism.py` pasa en verde
- [x] La mascara es vectorizada (sin bucles) y no hay logica de presion. La latencia SI existe ahora, pero como ESTADO (ADR-0012), no como umbral que resucite: MUERTA sigue siendo absorbente
- [x] Dos juegos de umbrales por especie: crecimiento y supervivencia (ADR-0012)
- [x] `condiciones_habitables()` sigue existiendo como alias: no rompe codigo previo
- [x] Ningun `a_w_min` de crecimiento baja de 0.605, verificado por test
- [x] `tests/integration/test_especie_en_su_entorno.py` en verde

### ✅ 🟡 Capa de datos: loaders + DataFrame canonico

**Dueño:** Fidel · **Criterios:** 4/4

> *Como capa de datos, quiero cargar los datasets reales 2025 en un esquema unico para alimentar el Modo Analogico.*
>
> Implementar `cargar_control_tierra` / `cargar_atacama` / `cargar_ventilas` + fallback sintetico (contrato §3.5, ADR-0010).
> Rama: `feat/data-loaders`.

- [x] Cada loader devuelve DataFrame con columnas EXACTAS `t, temperature, a_w, radiation` (Atacama ademas `temperature_min/max`)
- [x] `a_w` siempre en `[0,1]` y se usa directa (ya no `humidity/100`)
- [x] El fallback sintetico respeta la misma interfaz canonica
- [x] `pytest tests/unit/test_data.py` pasa en verde

### ✅ 🟣 Automata Celular: reglas de transicion + paso()

**Dueño:** Erick · **Criterios:** 5/5

> *Como motor de AC, quiero calcular S^{t+1} desde S^t de forma sincrona para simular la evolucion poblacional.*
>
> Implementar `transition_rules` + `paso(estado, campo, especie)` con vecindad de Moore, contra stubs de campo/especie (contrato §3.3).
> Rama: `feat/engine-transicion`.

- [x] `paso()` devuelve nuevo estado `(M,N) int8` SIN modificar el estado de entrada (doble buffer)
- [x] Conteo de vecinos de Moore correcto en casos de prueba (esquinas y bordes)
- [x] Estado int8 {MUERTA=0, LATENTE=1, ACTIVA=2}: fuera de crecimiento -> LATENTE; fuera de supervivencia -> MUERTA, absorbente (ADR-0012)
- [x] Vectorizado (sin bucles Python); pytest tests/unit/test_transition.py en verde (19 tests)
- [x] `paso()` recibe el `rng` inyectado; el conteo de vecinos de Moore cuenta SOLO celdas ACTIVA

### ✅ 🟡 Remuestreo + Modo Analogico

**Dueño:** Fidel · **Criterios:** 4/4

> *Como capa de datos, quiero convertir las series reales en una secuencia de CampoAmbiental para inyectarlas iteracion por iteracion.*
>
> `resampling.py` -> secuencia de CampoAmbiental; `modes/analog.py` la entrega al orquestador.
> Ramas: `feat/data-resampling` + `feat/modes-analogico`.

- [x] El remuestreo produce una secuencia de CampoAmbiental (uno por iteracion) en rango fisico
- [x] Imputa/enmascara el hueco de 8 dias de ventilas SIN inventar valores fuera de rango
- [x] `mapear_radiacion`: superficies convierten a banda UV con el factor DOCUMENTADO; Encelado mapea R=0 (ADR-0014)
- [x] El Modo Analogico no duplica el bucle de Sandbox (DRY); `pytest` en verde

### ✅ 🟣 Orquestador: simulation.py

**Dueño:** Erick · **Criterios:** 5/5

> *Como orquestador, quiero acoplar el motor biologico y el ambiental en el bucle del AC para correr una simulacion completa.*
>
> `simulation.py` une motores. Necesita el Hito 1 mergeado en `main`.
> Rama: `feat/simulation-orquestador`.

- [x] `simulation.py` corre N iteraciones acoplando campo + especie + `paso()` sin errores
- [x] Misma semilla -> misma corrida (reproducible)
- [x] Devuelve la serie de estados/poblaciones esperada para un caso de prueba
- [x] `pytest tests/integration/` pasa en verde
- [x] El orquestador propaga los tres estados y aplica los eventos (incluida la salmuera) antes de `paso()`

### ✅ 🟢 Modo Sandbox

**Dueño:** Esmeralda · **Criterios:** 4/4

> *Como usuario, quiero fijar T, R y A_w manualmente para explorar escenarios sin depender de un dataset.*
>
> `modes/sandbox.py`: parametros ambientales estaticos/ajustables.
> Rama: `feat/modes-sandbox`.

- [x] Sandbox construye un CampoAmbiental a partir de parametros T / UV / A_w dados (R es irradiancia UV, ADR-0014)
- [x] Cambiar un parametro cambia el resultado de la corrida de forma esperada
- [x] Comparte el mismo bucle que el Modo Analogico (DRY)
- [x] `pytest` en verde

### ✅ 🔵 Evento SalmueraDelicuescente (microrefugios)

**Dueño:** Jose · **Criterios:** 6/6

> ADR-0015. Contraparte de MicroFisuraMarte: hoy TODOS los eventos degradan el ambiente, lo que sesga cada corrida hacia la extincion por construccion. Este evento es el que le da a Marte algo que estudiar.

- [x] `SalmueraDelicuescente.aplicar()` SUBE `A_w` transitoriamente en un radio, con el `rng` inyectado
- [x] Misma semilla -> mismo campo (reproducible)
- [x] El refugio decae/expira: no es permanente y su duracion es un PARAMETRO (Erick lo va a barrer)
- [x] Test: aplicado al campo de Marte, `DRadiodurans.condiciones_crecimiento` pasa de 0% a >0%
- [x] `pytest tests/unit/test_stochastic.py` en verde
- [x] `aplicar()` devuelve SIEMPRE un CampoAmbiental nuevo, tambien cuando el evento no dispara (hoy devuelve el mismo objeto: aliasing intermitente segun la semilla)

### ✅ 🟣 Cinetica de crecimiento continua (CTMI + gamma)

**Dueño:** Erick · **Criterios:** 5/5

> ADR-0013. Reemplaza la mascara binaria por una tasa continua. Nace de la propuesta de Esmeralda de 'pesos que favorecen el crecimiento', con los pesos derivados de valores cardinales publicados.

- [x] `transition_rules.py` implementa mu = mu_opt * gamma_T * gamma_aw * gamma_UV, todos en [0,1]
- [x] gamma_T por CTMI vale 1.0 exactamente en t_opt y 0.0 en t_min / t_max
- [x] p_repro = clip(mu*dt, 0, 1) se muestrea con el `rng` inyectado (nunca np.random global)
- [x] Tests de bordes numericos (T = t_min, t_opt, t_max) sin division por cero
- [x] `pytest tests/unit/test_transition.py` en verde

### ✅ 🟢 Re-derivar umbrales UV y de supervivencia

**Dueño:** Esmeralda · **Criterios:** 7/7

> ADR-0012 y ADR-0014. PARCIALMENTE RESUELTO: los umbrales UV de E. coli y D. radiodurans ya se derivaron de fluencias publicadas (870 y 50.760 J/m2, factor 58x) dividiendo por SEGUNDOS_UV_POR_TICK. Ver docs/parametros.md. Queda el UV de M. burtonii (sin dato publicado) y los umbrales de supervivencia.

- [x] UV de E. coli y D. radiodurans derivados de fluencia publicada (870 / 50.760 J/m2) — ver docs/parametros.md §1.3
- [x] `t_sup_min`, `t_sup_max` y `a_w_sup_min` de las 3 especies citan fuente
- [x] Ningun `a_w_min` de crecimiento baja de 0.605 (limite de division celular conocido)
- [x] La banda usada (UV254) coincide con la que aplica Fidel en el adaptador
- [x] `pytest tests/unit/test_microorganism.py` en verde
- [x] UV de M. burtonii cerrado por analogia [ANA]: metanogenas adaptadas al frio resisten 2.5-13.8x mas que M. barkeri (~E. coli). Se toma 2.5x -> 2175 J/m2. Ver docs/parametros.md §1.3
- [x] Confirmar SEGUNDOS_UV_POR_TICK (28.800 s) con el dt que elija Erick: si divergen, los umbrales UV dejan de significar lo que dicen

---

