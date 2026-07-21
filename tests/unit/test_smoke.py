"""Smoke test de Hito 0: los contratos de frontera (§3) importan correctamente.

No ejercita la lógica (todavía son stubs con NotImplementedError); solo garantiza
que `main` compila e importa, que es la condición de salida del Hito 0.
"""
from astrobiosim.core.environment import CampoAmbiental
from astrobiosim.core.microorganism import Microorganismo
from astrobiosim.data.loaders import cargar_atacama
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.stochastic import EventoEstocastico


def test_contratos_de_frontera_importables() -> None:
    assert CampoAmbiental is not None
    assert Microorganismo is not None
    assert EventoEstocastico is not None
    assert callable(paso)
    assert callable(cargar_atacama)
