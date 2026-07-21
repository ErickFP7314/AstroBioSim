"""Tests del mapeo ambiental de `resampling.py` (base de Hito 0 para Fidel).

Solo se ejercita `mapear_radiacion`, que ya tiene lógica real (ADR-0010). El
resto (`limpiar_ventilas`, `secuencia_campos`) son stubs de Fidel.
"""
import numpy as np

from astrobiosim.data.resampling import Entorno, mapear_radiacion


def test_superficies_usan_radiacion_tal_cual() -> None:
    rad = np.array([320.0, 850.0, 1150.0])
    for entorno in (Entorno.TIERRA, Entorno.MARTE):
        np.testing.assert_array_equal(mapear_radiacion(rad, entorno), rad)


def test_encelado_mapea_radiacion_a_cero() -> None:
    rad = np.array([320.0, 320.5, 319.8])
    resultado = mapear_radiacion(rad, Entorno.ENCELADO)
    np.testing.assert_array_equal(resultado, np.zeros_like(rad))
    assert resultado.shape == rad.shape
