# ADR-0015: Microrefugios por salmueras delicuescentes y pregunta de investigación

- **Estado:** Aceptado
- **Fecha:** 2026-07-23
- **Modifica:** contrato §3.4 (eventos estocásticos), `openspec/project.md` (objetivo).
  Depende de: ADR-0012, ADR-0014. Relacionado: ADR-0006, ADR-0008.

## Contexto

Con los umbrales corregidos (ADR-0012), el regolito marciano **en bulk** (`a_w ≈ 0.19`)
queda muy por debajo del límite de división celular (~0.605): **es inhabitable**. Eso
no es un error del modelo — es el resultado correcto, y coincide con la literatura.

Lo que la literatura muestra además es que la vida **sí persiste** en esos ambientes,
pero en **microrefugios**: en Atacama, dentro de nódulos de halita que por
delicuescencia elevan localmente la actividad de agua; en Marte, el nicho candidato
son las **salmueras de percloratos** del subsuelo, donde la disponibilidad de agua es
teóricamente más favorable. El equipo lo confirma de forma independiente.

Hay además un **sesgo estructural** en el modelo actual: todos los eventos
estocásticos implementados **degradan** el ambiente (`MicroFisuraMarte` baja `A_w`).
No existe ningún evento que lo mejore, así que toda corrida está sesgada hacia la
extinción por construcción.

Y un **sesgo de muestreo** en la capa de datos: el campo de Marte usa la **media de
los mínimos** de `a_w` (0.187) como valor constante. Colapsar una distribución a su
peor caso garantiza la extinción y desperdicia justamente aquello que un modelo
espacial estocástico existe para representar.

## Decisión

**1. Nuevo evento `SalmueraDelicuescente`** (`engine/stochastic.py`, dueño: Jose),
contraparte simétrica de `MicroFisuraMarte`: con probabilidad `p` por tick **eleva
`A_w` de forma transitoria** en un radio de celdas, con magnitud y duración
muestreadas del `Generator` inyectado. Respeta §3.4: perturba **solo** el campo.

**2. Corregir el sesgo de muestreo:** el campo deja de usar el mínimo de la
distribución como constante. Se parametriza con **media y dispersión**, y la
heterogeneidad espacial la genera el modelo, no un recorte del dato.

**3. Se formaliza la pregunta de investigación del proyecto:**

> **¿Con qué frecuencia y magnitud mínimas deben aparecer microrefugios húmedos
> transitorios para que una población microbiana persista en un subsuelo planetario,
> en lugar de extinguirse?**

Con el corolario espacial de ADR-0014: en Marte la ventana habitable es una **banda de
profundidad**, acotada arriba por el UV y abajo por la disponibilidad de salmueras.

**4. Entregable asociado:** barrido de parámetros `frecuencia × magnitud → persistencia`
sobre ensambles Montecarlo con semillas explícitas (dueño: Erick), con la fracción
activa / latente / muerta (ADR-0012) como variable de respuesta.

## Alternativas consideradas

1. **Bajar los umbrales de las especies hasta que algo sobreviva.** Rechazado en
   ADR-0012: indefendible ante literatura.
2. **Aceptar la extinción trivial en Marte.** Correcto pero estéril: desperdicia el
   modelo espacial y estocástico, que es justamente lo que tenemos de distinto.
3. **Modelar la química de la salmuera explícitamente** (percloratos, actividad
   iónica). Rechazado por alcance: agregaría una capa físico-química completa. El
   evento estocástico captura el efecto observable (`A_w` sube transitoriamente) sin
   comprometerse con el mecanismo.

## Consecuencias

- (+) **Le da al proyecto una pregunta cuantitativa y un aporte real.** La mayoría de
  las evaluaciones de habitabilidad publicadas son puntuales (0-D); acá hay
  espacialidad + estocasticidad + latencia, que es una combinación poco cubierta.
- (+) **Marte pasa de ser el caso roto a ser el caso central** del estudio.
- (+) El resultado deja de depender de si una especie "sobrevive o no" y pasa a ser un
  umbral crítico medible — mucho más robusto frente a la incertidumbre de parámetros.
- (−) Un evento más que implementar y testear (Jose).
- (−) Hay que definir la **duración y el decaimiento** del refugio, para lo que hay
  menos dato directo que para el resto; conviene tratarlo como parámetro del barrido
  en vez de fijarlo.
