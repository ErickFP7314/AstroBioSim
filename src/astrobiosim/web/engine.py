"""Motor de simulación framework-free (dueño: Erick).

Orquesta el paquete `astrobiosim` para **dos** frentes sin acoplarse a ninguno:

- el **backend FastAPI** (`ui/api.py`), que lo envuelve en HTTP/WebSocket;
- **Pyodide** (el navegador), para el deploy 100% estático en Cloudflare Pages
  (el motor Python corre en el cliente, sin servidor).

No importa FastAPI ni matplotlib —solo el core + numpy/pandas—, y toda la config
llega como un ``dict`` JSON-able (no Pydantic, que no corre en Pyodide). Es la
**fuente única** de la lógica de orquestación: `api.py` y el worker de Pyodide
llaman a las mismas funciones (DRY, contrato §3).
"""
from __future__ import annotations

import base64
from collections.abc import Iterator
from itertools import islice
from pathlib import Path

import numpy as np

from astrobiosim.core.microorganism import (
    ACTIVA,
    LATENTE,
    MUERTA,
    DRadiodurans,
    EColi,
    MBurtonii,
    Microorganismo,
)
from astrobiosim.data.loaders import cargar_atacama, cargar_control_tierra, cargar_ventilas
from astrobiosim.data.resampling import Entorno
from astrobiosim.engine.cellular_automaton import paso
from astrobiosim.engine.stochastic import EventoEstocastico, SalmueraDelicuescente
from astrobiosim.engine.transition_rules import (
    PRESETS,
    REGLAS_DISPONIBLES,
    VOCABULARIO,
    ReglaTransicion,
    regla_desde_spec,
)
from astrobiosim.modes.analog import ModoAnalogico
from astrobiosim.modes.base import ModoSimulacion
from astrobiosim.modes.sandbox import ModoSandbox
from astrobiosim.simulation import sembrar_estado, simular_montecarlo

#: Carpeta con los CSV canónicos. El backend usa `data/processed` del repo;
#: Pyodide la reapunta (`engine.DATA_DIR = Path("/data")`) a donde monta los CSV
#: en su FS virtual. Es un atributo de módulo mutable a propósito.
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"

_ESPECIES: dict[str, type[Microorganismo]] = {
    "ecoli": EColi, "dradiodurans": DRadiodurans, "mburtonii": MBurtonii,
}
_ESPECIE_LABEL = {"ecoli": "E. coli", "dradiodurans": "D. radiodurans", "mburtonii": "M. burtonii"}
_ENTORNOS: dict[str, Entorno] = {
    "tierra": Entorno.TIERRA, "marte": Entorno.MARTE, "encelado": Entorno.ENCELADO,
}
_ENTORNO_LABEL = {"tierra": "Tierra", "marte": "Marte", "encelado": "Encelado"}
_LOADER = {
    "tierra": (cargar_control_tierra, "datos_tierra_control_2025.csv"),
    "marte": (cargar_atacama, "datos_atacama_2025_EXTREMOS_REALES.csv"),
    "encelado": (cargar_ventilas, "datos_ventilas_2025_procesados.csv"),
}

LADO_MIN, LADO_MAX = 10, 120
ITER_DEFECTO, ITER_MAX = 200, 800
MC_MAX = 60

#: Defaults de config, espejo del modelo Pydantic del backend. La UI manda la
#: config completa, pero se toleran claves faltantes con estos valores.
_DEF: dict = {
    "modo": "sandbox", "especie": "dradiodurans", "entorno": "marte",
    "T": 20.0, "R": 0.0, "A_w": 0.9, "m": 60, "n": 60,
    "fraccion_activa": 0.15, "patron": "uniforme", "semilla": 42,
    "n_iteraciones": None, "salmuera": False, "n_corridas": 30, "regla": None,
}


def _g(cfg: dict, clave: str):
    """Lee `clave` de la config, cayendo al default del modelo si falta o es None.
    (Para `n_iteraciones` y `regla` el default es None, así que su None se preserva.)"""
    valor = cfg.get(clave, _DEF[clave])
    return _DEF[clave] if valor is None else valor


# --------------------------------------------------------------------------
# Construcción de las piezas del motor a partir de la config (dict)
# --------------------------------------------------------------------------
def _shape(cfg: dict) -> tuple[int, int]:
    return (int(_g(cfg, "m")), int(_g(cfg, "n")))


def especie(cfg: dict) -> Microorganismo:
    return _ESPECIES[_g(cfg, "especie")]()


def n_iter(cfg: dict) -> int:
    it = _g(cfg, "n_iteraciones") or ITER_DEFECTO
    return min(int(it), ITER_MAX)


def construir_modo(cfg: dict, rng: np.random.Generator) -> ModoSimulacion:
    if _g(cfg, "modo") == "sandbox":
        return ModoSandbox(_shape(cfg), T=float(_g(cfg, "T")), R=float(_g(cfg, "R")),
                           A_w=float(_g(cfg, "A_w")))
    loader, archivo = _LOADER[_g(cfg, "entorno")]
    df = loader(str(DATA_DIR / archivo))
    # ciclico=True: si se piden más ticks que días tiene el dataset (~365), la
    # serie 2025 se recicla para respetar el nº de ticks pedido.
    return ModoAnalogico(df, _ENTORNOS[_g(cfg, "entorno")], _shape(cfg), rng=rng, ciclico=True)


def construir_eventos(cfg: dict) -> list[EventoEstocastico]:
    if _g(cfg, "salmuera") and _g(cfg, "entorno") == "marte":
        return [SalmueraDelicuescente(
            probabilidad_disparo=0.1, a_w_objetivo_min=0.95, a_w_objetivo_max=0.98)]
    return []


def estado_inicial(cfg: dict, rng: np.random.Generator) -> np.ndarray:
    return sembrar_estado(_shape(cfg), rng=rng,
                          fraccion_activa=float(_g(cfg, "fraccion_activa")),
                          patron=_g(cfg, "patron"))


def regla(cfg: dict) -> ReglaTransicion | None:
    """Resuelve `cfg['regla']` (id de preset, spec de bloques o None → logística)."""
    r = _g(cfg, "regla")
    if r is None:
        return None
    if isinstance(r, str):
        if r not in REGLAS_DISPONIBLES:
            raise ValueError(f"regla desconocida: {r!r} (usa {list(REGLAS_DISPONIBLES)})")
        return REGLAS_DISPONIBLES[r]
    return regla_desde_spec(r)


# --------------------------------------------------------------------------
# API pública del motor (la consumen api.py y el worker de Pyodide)
# --------------------------------------------------------------------------
def catalogo() -> dict:
    """Catálogos para poblar la UI (especies, entornos, reglas, límites, vocabulario)."""
    especies = []
    for eid, cls in _ESPECIES.items():
        e = cls()
        especies.append({
            "id": eid, "label": _ESPECIE_LABEL[eid],
            "t_min": e.t_min, "t_opt": e.t_opt, "t_max": e.t_max,
            "a_w_min": e.a_w_min, "uv_max": round(e.uv_max, 4), "mu_opt": e.mu_opt,
        })
    reglas = []
    for clave, spec in PRESETS.items():
        r = regla_desde_spec(spec)
        reglas.append({"id": clave, "nombre": r.nombre, "spec": spec, "notacion": r.notacion()})
    for clave in ("latencia_anhidro", "latencia_mortalidad"):
        r = REGLAS_DISPONIBLES[clave]
        reglas.append({"id": clave, "nombre": r.nombre, "spec": None, "notacion": r.notacion()})
    return {
        "especies": especies,
        "entornos": [{"id": k, "label": v} for k, v in _ENTORNO_LABEL.items()],
        "estados": {"MUERTA": MUERTA, "LATENTE": LATENTE, "ACTIVA": ACTIVA},
        "limites": {"lado": [LADO_MIN, LADO_MAX], "iter_max": ITER_MAX, "mc_max": MC_MAX},
        "reglas": reglas,
        "vocabulario": VOCABULARIO,
    }


def frame(tick: int, estado: np.ndarray) -> dict:
    """Un frame para el cliente: grilla (base64 int8) + conteos por estado."""
    e = np.ascontiguousarray(estado, dtype=np.int8)
    return {
        "type": "frame",
        "tick": tick,
        "shape": list(e.shape),
        "grid": base64.b64encode(e.tobytes()).decode("ascii"),
        "n": {"m": int((e == MUERTA).sum()), "l": int((e == LATENTE).sum()),
              "a": int((e == ACTIVA).sum())},
    }


def iter_frames(cfg: dict) -> Iterator[dict]:
    """Genera los frames de una corrida (uno por tick, incluido t=0). Lanza
    ValueError si la config/regla es inválida."""
    r = regla(cfg)
    ss = np.random.SeedSequence(_g(cfg, "semilla"))
    rng_modo, rng_estado, rng_din = (np.random.default_rng(h) for h in ss.spawn(3))
    modo = construir_modo(cfg, rng_modo)
    esp = especie(cfg)
    eventos = construir_eventos(cfg)
    estado = estado_inicial(cfg, rng_estado)
    # islice, no list(): el generador de campos es infinito (sandbox y analógico
    # cíclico), así que hay que cortarlo en `n_iter` sin materializarlo entero.
    campos = islice(modo.campos(), n_iter(cfg))

    yield frame(0, estado)
    for tick, campo_base in enumerate(campos, start=1):
        campo = campo_base
        for evento in eventos:
            campo = evento.aplicar(campo, rng_din)
        estado = paso(estado, campo, esp, rng_din, regla=r)
        yield frame(tick, estado)


def montecarlo(cfg: dict) -> dict:
    """Corre N réplicas y devuelve media ± σ por tick de las tres fracciones."""
    r = regla(cfg)  # valida (levanta ValueError si el spec/id es inválido)
    estado0 = estado_inicial(cfg, np.random.default_rng(_g(cfg, "semilla")))
    usa_eventos = bool(construir_eventos(cfg))
    res = simular_montecarlo(
        construir_modo=lambda rng: construir_modo(cfg, rng),
        especie=especie(cfg),
        estado_inicial=estado0,
        construir_eventos=(lambda rng: construir_eventos(cfg)) if usa_eventos else None,
        n_corridas=min(int(_g(cfg, "n_corridas")), MC_MAX),
        semilla=_g(cfg, "semilla"),
        n_iteraciones=n_iter(cfg),
        regla=r,
    )
    return {
        "n_corridas": res.n_corridas,
        "media": res.media.tolist(),
        "desviacion": res.desviacion.tolist(),
    }


def validar_regla(spec: dict) -> dict:
    """Valida un spec de bloques y devuelve su notación formal (para la UI)."""
    try:
        r = regla_desde_spec(spec)
    except ValueError as exc:
        return {"valida": False, "notacion": None, "error": str(exc)}
    return {"valida": True, "notacion": r.notacion(), "error": None}
