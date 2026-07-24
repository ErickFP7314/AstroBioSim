# ADR-0016: Reglas de transición intercambiables (Strategy) + notación formal

- **Estado:** Aceptado
- **Fecha:** 2026-07-24
- **Relacionado:** ADR-0002 (motor AC), ADR-0012 (tres estados), ADR-0013
  (cinética), ADR-0009 (UI React).

## Contexto

La regla de transición del autómata podía quedar "cableada" dentro de `paso()`.
Pero el equipo quiere, para la exposición y para la exploración, poder **cambiar
la regla desde la UI**: un menú con la regla logística (proceso de contacto), la
de Conway y una híbrida, más una opción **"personalizar"** que arme reglas con
bloques tipo Scratch. Y quiere un **panel que muestre la regla activa en notación
formal de autómatas celulares**, cualquiera sea (incluidas las de fábrica).

Una regla cableada haría imposible todo eso sin reescribir el motor.

## Decisión

**1. La regla es una estrategia intercambiable.** `paso()` acepta un objeto
`ReglaTransicion` (patrón Strategy) por parámetro opcional; por defecto usa
`ReglaLogistica`. La firma del contrato §3.3 no se rompe: `regla`, `dt` y `borde`
son *keyword-only* con valor por defecto.

```python
def paso(estado, campo, especie, rng, *,
         regla: ReglaTransicion | None = None,
         dt: float = 1.0, borde: str = "muerta") -> np.ndarray: ...
```

**2. `paso()` arma el contexto; la regla solo decide.** El motor calcula una vez
por tick las máscaras ambientales (`crece`, `sobrevive`), la cinética
(`p_repro`) y el conteo de vecinos, y se lo pasa a la regla en un `_Contexto`. La
regla no vuelve a tocar el campo ni la especie. Esto mantiene la separación de
responsabilidades y permite que reglas nuevas se escriban sin conocer el motor.

**3. Cada regla se autodescribe en notación formal.** `ReglaTransicion` obliga a
implementar `notacion() -> str`, que devuelve la función de transición en LaTeX.
El panel de la UI la renderiza directo, así que "ver la regla activa en notación
estándar" no requiere lógica aparte: la regla es su propia documentación.

**4. Tres reglas de fábrica** (`REGLAS_DISPONIBLES`): `logistica` (default, la más
defendible), `conway` (B3/S23, familiar y visual) e `hibrida` (contacto + tope de
hacinamiento). El **editor por bloques (Hito 3, UI)** produce nuevas
`ReglaTransicion` sin tocar `engine/`.

## Alternativas consideradas

1. **Regla cableada en `paso()`.** Rechazada: imposibilita el menú y el editor sin
   reescribir el motor.
2. **Pasar la regla como un *flag* string** (`regla="conway"`) y ramificar dentro.
   Rechazada: no escala al editor por bloques ni a la autodescripción en notación.
3. **Un DSL de reglas propio desde ya.** Aplazado: el editor por bloques (Hito 3)
   materializará esto sobre la interfaz `ReglaTransicion`; no hace falta el DSL
   para cerrar el motor de Hito 1.

## Consecuencias

- (+) La UI puede ofrecer el menú de reglas y el panel de notación sin tocar el
  motor; el editor por bloques es una fábrica de `ReglaTransicion`.
- (+) Cada regla es testeable en aislamiento; el motor se testea una vez.
- (+) La notación formal para la defensa sale del propio código, no de un doc que
  se desincroniza.
- (−) Una indirección más (Strategy) frente a una función monolítica.
- (−) El editor por bloques (Hito 3) debe validar que las reglas que produce
  respeten los invariantes (síncrona, `MUERTA` absorbente, sin RNG global).
