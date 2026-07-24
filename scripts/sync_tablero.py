#!/usr/bin/env python3
"""Regenera `docs/tablero.md` desde el tablero de Trello.

`docs/tablero.md` es el espejo en Markdown del tablero, para que cualquier agente
de IA o integrante sin acceso a Trello vea qué está hecho y con qué criterios.

Uso
---
    export TRELLO_KEY=...      # https://trello.com/power-ups/admin
    export TRELLO_TOKEN=...    # token generado desde la URL de autorización
    python scripts/sync_tablero.py

Las credenciales se leen del entorno a propósito: **nunca** se commitean.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BOARD = "cK8VP1aj"
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "tablero.md"

EMOJI = {"Esmeralda": "🟢", "Fidel": "🟡", "Jose": "🔵", "Erick": "🟣"}
AREA = {
    "Esmeralda": "Motor biológico + notebook",
    "Fidel": "Datos análogos + validación",
    "Jose": "Motor ambiental + eventos",
    "Erick": "Autómata Celular + UI",
}


def _get(path: str, **params: str) -> list[dict]:
    key, token = os.environ.get("TRELLO_KEY"), os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        sys.exit("Faltan TRELLO_KEY y/o TRELLO_TOKEN en el entorno.")
    params.update(key=key, token=token)
    url = f"https://api.trello.com/1/{path}?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def _duenio(card: dict) -> str:
    m = re.match(r"\[([^\]]+)\]", card["name"])
    if m and m.group(1) in EMOJI:
        return m.group(1)
    for etiqueta in card.get("labels", []):
        if etiqueta.get("name") in EMOJI:
            return etiqueta["name"]
    return "?"


def _titulo(card: dict) -> str:
    return re.sub(r"^\[[^\]]+\]\s*", "", card["name"])


def _items(card: dict) -> list[tuple[str, bool]]:
    return [
        (i["name"], i["state"] == "complete")
        for ch in card.get("checklists", [])
        for i in ch["checkItems"]
    ]


def main() -> None:
    listas = _get(f"boards/{BOARD}/lists")
    tarjetas = _get(
        f"boards/{BOARD}/cards", checklists="all", fields="name,idList,desc,labels"
    )

    total = hechos = 0
    por_persona = {k: [0, 0] for k in EMOJI}
    for c in tarjetas:
        items = _items(c)
        ok = sum(1 for _, s in items if s)
        total += len(items)
        hechos += ok
        d = _duenio(c)
        if d in por_persona:
            por_persona[d][0] += ok
            por_persona[d][1] += len(items)

    out: list[str] = [
        "# Tablero de tareas — AstroBioSim",
        "",
        "> **Espejo en Markdown del tablero de Trello** — <https://trello.com/b/cK8VP1aj>",
        ">",
        "> Existe para que cualquier agente de IA (o persona) **sin acceso a Trello** pueda",
        "> ver qué está hecho, qué falta y con qué criterios de aceptación se da por",
        "> terminada cada tarea.",
        ">",
        f"> **Última sincronización:** {datetime.date.today().isoformat()} · "
        "regenerar con `python scripts/sync_tablero.py`",
        "",
        "## Cómo leerlo",
        "",
        "- `- [x]` criterio de aceptación **cumplido** · `- [ ]` **pendiente**.",
        "- Una tarjeta pasa a **✅ Hecho** solo cuando **todos** sus criterios están marcados.",
        "- Los criterios son deliberadamente verificables: casi todos se comprueban",
        "  corriendo `pytest`. Si no se puede comprobar, no es un criterio.",
        "- Este documento dice **qué** falta; `docs/instrucciones/<nombre>.md` dice **cómo**",
        "  hacerlo, y `docs/adr/` dice **por qué** se decidió así.",
        "",
        f"**Progreso global:** {hechos}/{total} criterios ({hechos / total:.0%})",
        "",
        "| Integrante | Área | Criterios cumplidos |",
        "|---|---|---|",
    ]
    for k, (d, t) in por_persona.items():
        out.append(f"| {EMOJI[k]} **{k}** | {AREA[k]} | {d}/{t} ({d / t:.0%}) |" if t else "")
    out += ["", "---", ""]

    for lista in listas:
        cs = [c for c in tarjetas if c["idList"] == lista["id"]]
        if not cs:
            out += [f"## {lista['name']}", "", "_(vacío)_", "", "---", ""]
            continue
        t_items = sum(len(_items(c)) for c in cs)
        t_ok = sum(1 for c in cs for _, s in _items(c) if s)
        pct = f" — {t_ok}/{t_items} criterios" if t_items else ""
        out += [f"## {lista['name']}{pct}", ""]
        for c in cs:
            duenio = _duenio(c)
            items = _items(c)
            ok = sum(1 for _, s in items if s)
            estado = "✅" if items and ok == len(items) else ("🔸" if ok else "⬜")
            out += [
                f"### {estado} {EMOJI.get(duenio, '⚪')} {_titulo(c)}",
                "",
                f"**Dueño:** {duenio} · **Criterios:** {ok}/{len(items)}",
                "",
            ]
            if c.get("desc", "").strip():
                out += ["> " + ln if ln.strip() else ">" for ln in c["desc"].strip().splitlines()]
                out.append("")
            out += [f"- [{'x' if s else ' '}] {n}" for n, s in items]
            out.append("")
        out += ["---", ""]

    SALIDA.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{SALIDA.relative_to(RAIZ)} · {hechos}/{total} criterios · {len(tarjetas)} tarjetas")


if __name__ == "__main__":
    main()
