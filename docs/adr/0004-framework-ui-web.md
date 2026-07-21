# ADR-0004: Framework de interfaz web (Streamlit vs Gradio)

- **Estado:** Reemplazado por [ADR-0009](0009-frontend-react-backend-fastapi.md)
- **Fecha:** 2026-07-15

> **Obsoleto (2026-07-21).** El equipo optó por una SPA de React con backend
> FastAPI en lugar de Streamlit. Ver ADR-0009. Este documento se conserva por
> trazabilidad histórica; **no lo implementes**.

## Contexto
La especificación pide una interfaz web para interacción en tiempo real (sliders
en Modo Sandbox, arranque/pausa, render de la matriz de supervivencia) y admite
**Streamlit o Gradio**. Debe complementarse con un entorno Jupyter para análisis
retrospectivo.

## Decisión (propuesta)
Adoptar **Streamlit** como framework del dashboard, tras la primera
demostración funcional del motor.

Razones:
- Modelo de estado de sesión (`st.session_state`) adecuado para mantener la
  grilla entre reruns y controlar el bucle de simulación paso a paso.
- Sliders, botones y `st.pyplot`/`st.image` cubren el render de la matriz sin
  dependencias extra.
- Amplia documentación y curva de entrada baja para un equipo académico.

Gradio queda como alternativa si se prioriza exponer la simulación como demo
compartible con interfaz mínima. La frontera de UI (ADR-0001) mantiene el motor
agnóstico del framework, por lo que el cambio es de bajo costo.

## Alternativas consideradas
1. **Gradio.** Más simple para demos y `share=True`, pero su modelo de estado es
   menos natural para una animación iterativa con control de bucle.
2. **Dash / Panel.** Más potentes pero con mayor sobrecarga; innecesario para el
   alcance del MVP.

## Consecuencias
- (+) Prototipado rápido del dashboard.
- (+) El motor permanece desacoplado de la UI: `ui/dashboard.py` sólo consume la
  API pública del orquestador.
- (−) Streamlit re-ejecuta el script en cada interacción; el bucle de simulación
  debe diseñarse para avanzar por pasos guardados en `session_state`, no como
  `while` bloqueante.
- Decisión a **confirmar** tras el primer spike de UI (por eso queda en estado
  Propuesto).
