"""Tests del mapeo ambiental de `resampling.py` (base de Hito 0 para Fidel).

Solo se ejercita `mapear_radiacion`, que ya tiene lógica real (ADR-0014). El
resto (`limpiar_ventilas`, `secuencia_campos`) son stubs de Fidel.
"""
import numpy as np

from astrobiosim.core.environment import FRACCION_UV
from astrobiosim.data.resampling import Entorno, mapear_radiacion


def test_superficies_convierten_la_irradiancia_global_a_banda_uv() -> None:
    """ADR-0014: `R` es UV, no insolación total. El factor debe aplicarse."""
    rad = np.array([320.0, 850.0, 1150.0])
    for entorno in (Entorno.TIERRA, Entorno.MARTE):
        np.testing.assert_allclose(mapear_radiacion(rad, entorno), rad * FRACCION_UV)


def test_el_uv_es_una_fraccion_pequena_de_la_irradiancia_global() -> None:
    """Guardia contra volver a pasar el flujo total como si fuera UV."""
    rad = np.array([844.0])
    uv = mapear_radiacion(rad, Entorno.MARTE)
    assert np.all(uv < 0.1 * rad)
    assert np.all(uv > 0.0)


def test_encelado_mapea_radiacion_a_cero() -> None:
    rad = np.array([320.0, 320.5, 319.8])
    resultado = mapear_radiacion(rad, Entorno.ENCELADO)
    np.testing.assert_array_equal(resultado, np.zeros_like(rad))
    assert resultado.shape == rad.shape
