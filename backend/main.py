"""API de SPI (Situational Player Intelligence). Ejecuta: .venv\\Scripts\\uvicorn backend.main:app --reload

Contrato del hosting: GET /health -> {"status": "ok"}; toda la API bajo /api/...; el build de dashboard/dist se sirve
en la misma URL y puerto. El análisis se calcula en memoria al arrancar (en segundo plano).
"""
from __future__ import annotations

import math
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.spi import viewer
from backend.spi.dsa import NOMBRES
from backend.spi.engine import motor
from backend.spi.loader import tablas
from backend.spi.penalties import anulada
from backend.spi.scs import NOMBRE_RASGO


@asynccontextmanager
async def ciclo(app: FastAPI):
    motor.iniciar()
    yield


app = FastAPI(title="SPI · Situational Player Intelligence", lifespan=ciclo)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _limpio(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if math.isnan(v) or math.isinf(v) else round(float(v), 4)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, dict):
        return {str(k): _limpio(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpio(x) for x in v]
    return v


def _registros(df: pd.DataFrame) -> list[dict]:
    return [_limpio(r) for r in df.to_dict("records")]


def _listo():
    if motor.estado != "listo":
        raise HTTPException(503, detail={"estado": motor.estado, "progreso": motor.progreso, "mensaje": motor.mensaje})


@app.get("/api/estado")
def estado() -> dict:
    return {"estado": motor.estado, "progreso": round(motor.progreso, 3), "mensaje": motor.mensaje, "error": motor.error}


@app.get("/api/resumen")
def resumen() -> dict:
    _listo()
    m = motor.dsa
    return _limpio({
        **motor.resumen,
        "tau": m.tau,
        "componentes": [{"id": c, "nombre": NOMBRES[c], "peso": m.pesos[c], "error": m.error_std[c]} for c in m.componentes],
        "validacion": m.validacion,
        "seleccion": m.seleccion,
        "scs": {"k": motor.scs.k, "silhouettes": motor.scs.silhouettes, "grupos": motor.scs.grupos, "rasgos": NOMBRE_RASGO},
    })


@app.get("/api/equipos")
def equipos() -> list[str]:
    return sorted(tablas()["games"].homeTeamAbbr.unique().tolist())


@app.get("/api/receptores")
def receptores(equipo: str | None = None, min_rutas: int = Query(40, ge=1)) -> list[dict]:
    _listo()
    r = motor.receptores
    r = r[r.rutas >= min_rutas]
    if equipo:
        r = r[r.equipo == equipo]
    return _registros(r.sort_values("dsa_oe_ajustada", ascending=False))


@app.get("/api/receptores/{nfl_id}")
def receptor(nfl_id: int) -> dict:
    _listo()
    r = motor.receptores[motor.receptores.nflId == nfl_id]
    if r.empty:
        raise HTTPException(404, "Receptor sin rutas analizadas")
    R = motor.rutas[motor.rutas.nflId == nfl_id]
    cols = ["gameId", "playId", "week", "defensiveTeam", "pff_passCoverage", "pff_passCoverageType", "dsa", "dsa_oe", "sep_pase",
            "ganancia", "t_quiebre", "t_pase", "profundidad", "scs", "objetivo", "completo", "passResult", "defId", "def_conf"]
    jug = tablas()["players"].set_index("nflId").displayName
    top = R.sort_values("dsa", ascending=False).head(25)[cols].copy()
    top["defensor"] = top.defId.map(jug)
    por_cob = R.groupby("pff_passCoverage").agg(rutas=("dsa", "size"), dsa=("dsa", "mean"), sep=("sep_pase", "mean")).reset_index()
    return _limpio({
        "perfil": _registros(r)[0],
        "jugadas": _registros(top),
        "por_cobertura": _registros(por_cob[por_cob.rutas >= 5].sort_values("rutas", ascending=False)),
        "distribucion_dsa": np.histogram(R.dsa.dropna(), bins=10, range=(0, 100))[0].tolist(),
        "liga_scs": [g["n"] for g in motor.scs.grupos],
    })


@app.get("/api/defensores")
def defensores(equipo: str | None = None, min_rutas: int = Query(40, ge=1)) -> list[dict]:
    _listo()
    d = motor.defensores
    d = d[d.rutas >= min_rutas]
    if equipo:
        d = d[d.equipo == equipo]
    return _registros(d.sort_values("dsa_oe_permitida_ajustada"))


@app.get("/api/emparejamientos")
def emparejamientos(ofensiva: str | None = None, defensa: str | None = None, min_rutas: int = Query(3, ge=1)) -> list[dict]:
    _listo()
    e = motor.emparejamientos
    e = e[e.rutas >= min_rutas]
    if ofensiva:
        e = e[e.equipo_of == ofensiva]
    if defensa:
        e = e[e.equipo_def == defensa]
    return _registros(e.sort_values("dsa_oe", ascending=False).head(300))


@app.get("/api/hallazgos")
def hallazgos() -> list[dict]:
    _listo()
    return _limpio(motor.hallazgos)


@app.get("/api/partidos")
def partidos() -> list[dict]:
    g = tablas()["games"].sort_values(["week", "gameDate", "gameTimeEastern"])
    return _registros(g[["gameId", "week", "gameDate", "homeTeamAbbr", "visitorTeamAbbr"]])


@app.get("/api/partidos/{game_id}/jugadas")
def jugadas(game_id: int) -> list[dict]:
    _listo()
    p = tablas()["plays"]
    p = p[p.gameId == game_id][["playId", "quarter", "gameClock", "down", "yardsToGo", "possessionTeam", "passResult",
                                "pff_passCoverage", "playDescription", "foulName1"]].copy()
    p["castigo"] = p.foulName1.notna()
    p["anulada"] = p.playDescription.map(anulada)
    p = p.drop(columns=["foulName1"])
    R = motor.rutas[motor.rutas.gameId == game_id]
    mejor = R.groupby("playId").dsa.max().rename("dsa_max")
    p = p.merge(mejor, on="playId", how="left")
    p = p[p.dsa_max.notna()]          # solo jugadas analizadas (con snap, pase y rutas)
    return _registros(p.sort_values("playId"))


@app.get("/api/jugada/{game_id}/{play_id}")
def jugada(game_id: int, play_id: int) -> dict:
    _listo()
    try:
        return _limpio(viewer.jugada(motor, game_id, play_id))
    except (KeyError, FileNotFoundError) as e:
        raise HTTPException(404, str(e))


DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="dashboard")
