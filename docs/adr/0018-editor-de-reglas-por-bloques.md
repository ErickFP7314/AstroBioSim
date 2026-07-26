# ADR-0018: Editor de reglas por bloques (spec JSON → `ReglaTransicion`)

- **Estado:** Aceptado
- **Fecha:** 2026-07-26
- **Relacionado:** ADR-0016 (reglas intercambiables), ADR-0012 (tres estados,
  MUERTA absorbente), ADR-0013 (cinética), ADR-0009 (UI React + FastAPI).

## Contexto

ADR-0016 dejó la regla del autómata como una `ReglaTransicion` intercambiable y
anticipó un **editor visual por bloques** (Hito 3) que produjera reglas nuevas
"sin tocar `engine/`", con la condición de que **validara los invariantes** del
motor (síncrona, vectorizada, `MUERTA` absorbente, sin RNG global). Faltaba
materializarlo. El equipo eligió un editor de **filas "SI condición → estado"**
(cascada, la primera fila que matchea gana) por sobre bloques encastrables tipo
Scratch: misma potencia, mucho menos trabajo de UI y calza con la `notacion()`
en cascada que ya tienen las reglas de fábrica.

Como el frontend **no** puede tener lógica de simulación (ADR-0009), la regla no
se puede ejecutar en el navegador: hay que representarla como **dato** que el
backend interprete.

## Decisión

**1. La regla se representa como un spec JSON declarativo.** Una regla es una
lista ordenada de **cláusulas** `{"cuando": [condición…], "entonces": ESTADO,
"prob": null|"contacto"|"mu"}`. Cada condición es una de tres familias, y todas
se reducen a máscaras booleanas sobre el `_Contexto` del tick:

- `estado` — la celda está `vacia` (MUERTA), `ocupada`, `activa` o `latente`.
- `ambiente` — el ambiente `crece` o `sobrevive` (o su negación).
- `vecinos` — conteo de vecinos de Moore (`activa` u `ocupada`) comparado con un
  umbral (`<`, `<=`, `==`, `>=`, `>`). Rangos como "∈{2,3}" se expresan con dos
  condiciones (`>=2` y `<=3`) en la misma fila (AND).

**2. `ReglaDesdeBloques` interpreta el spec, vectorizado.** Es una
`ReglaTransicion` más: evalúa las cláusulas en orden y la primera que matchea fija
el estado de cada celda (`np.full(MUERTA)` de base). Las condiciones de una fila
se combinan con AND; las filas actúan como cascada (OR con prioridad). `prob`
hace la transición estocástica con el único `rng` inyectado. Sigue siendo
síncrona y sin bucles por celda.

**3. `MUERTA` absorbente se fuerza en el motor, no en la validación.** Después de
armar el estado nuevo, se revierte a `MUERTA` toda celda que estaba vacía y
quedaría ocupada **sin ningún vecino ACTIVA**: reponer un sitio es *colonización*
por un vecino que se reproduce, nunca resurrección ni generación espontánea
(ADR-0012). Así el invariante se cumple **sea cual sea el spec** que arme el
usuario; no depende de que el editor lo prohíba.

**4. La frontera es la API, no el navegador.** `ConfigCorrida.regla` acepta un id
de preset (`"logistica"`/`"conway"`/`"hibrida"`), un spec de bloques inline, o
`null` (logística por defecto). `GET /api/config` expone el **vocabulario**
(familias, campos y opciones) para que el editor se arme genéricamente y las tres
reglas de fábrica **como plantilla editable**. `POST /api/regla/validar` valida un
spec en construcción y devuelve su `notacion()` (feedback en vivo). El spec
inválido lanza `ValueError` → la API responde error/422.

**5. El preset `logistica` en bloques es equivalente exacta a `ReglaLogistica`**
(mismo tick, un único sorteo de RNG), y hay un test que lo fija. Conway e híbrida
son puntos de partida: la guardia de MUERTA absorbente puede diferir del original
ante vecinos solo LATENTE (que no se reproducen), lo cual es más correcto.

## Alternativas consideradas

1. **Ejecutar la regla en el cliente (JS).** Rechazada: duplica el motor y rompe
   "el frontend no tiene lógica de simulación" (ADR-0009).
2. **Bloques encastrables tipo Scratch.** Rechazada por costo/beneficio: mucho más
   trabajo de UI (drag-drop anidado) para la misma expresividad que las filas.
3. **Notación B/S tipo Conway.** Rechazada como base: limitada a autómatas tipo
   Life; no expresa latencia ni el gradiente ambiental del modelo.
4. **Validar los invariantes con reglas estáticas sobre el spec.** Descartada a
   favor de forzar MUERTA absorbente en tiempo de ejecución: es imposible burlarla
   combinando cláusulas, y no restringe la experimentación del usuario.

## Consecuencias

- (+) El usuario arma reglas nuevas desde la UI sin tocar Python; el motor las
  corre igual que a las de fábrica.
- (+) Los invariantes (síncrona, vectorizada, MUERTA absorbente, RNG inyectado) se
  cumplen por construcción, no por confianza en el editor.
- (+) La notación formal y la validación salen del backend (única fuente de
  verdad); el editor solo edita datos.
- (−) La expresividad está acotada al vocabulario (tres familias de condición); un
  predicado fuera de eso necesita ampliar el vocabulario y el intérprete.
- (−) Presets no-logísticos no son bit-idénticos a sus clases por la guardia de
  colonización; se documenta y se testea la equivalencia solo donde aplica.
