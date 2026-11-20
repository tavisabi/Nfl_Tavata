"""Acceso a datos. Solo lectura de data/: nunca escribe ni modifica los archivos originales."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CAMPO_ANCHO, CAMPO_LARGO, DATA, TRACKING

COLS_TRACKING = ["gameId", "playId", "nflId", "frameId", "jerseyNumber", "team", "playDirection",
                 "x", "y", "s", "a", "o", "dir", "event"]


@lru_cache(maxsize=1)
def tablas() -> dict[str, pd.DataFrame]:
    """games, plays, players y pff, cargados una vez."""
    return {
        "games": pd.read_csv(DATA / "games.csv"),
        "plays": pd.read_csv(DATA / "plays.csv"),
        "players": pd.read_csv(DATA / "players.csv"),
        "pff": pd.read_csv(DATA / "pffScoutingData.csv"),
    }


def archivos_tracking() -> list[Path]:
    return sorted(TRACKING.glob("tracking_*.csv"))


def ruta_tracking(game_id: int) -> Path:
    p = TRACKING / f"tracking_{int(game_id)}.csv"
    if not p.exists():
        raise FileNotFoundError(f"No existe tracking para gameId={game_id}")
    return p


def estandarizar(t: pd.DataFrame) -> pd.DataFrame:
    """Gira las jugadas hacia la izquierda para que la ofensiva siempre ataque hacia +x.

    x' = 120 - x, y' = 53.3 - y, ángulos + 180°. Así todas las rutas son comparables.
    """
    t = t.copy()
    izq = (t["playDirection"] == "left").to_numpy()
    t.loc[izq, "x"] = CAMPO_LARGO - t.loc[izq, "x"]
    t.loc[izq, "y"] = CAMPO_ANCHO - t.loc[izq, "y"]
    for c in ("o", "dir"):
        t.loc[izq, c] = (t.loc[izq, c] + 180.0) % 360.0
    return t


def leer_tracking(game_id: int) -> pd.DataFrame:
    t = pd.read_csv(ruta_tracking(game_id), usecols=COLS_TRACKING)
    return estandarizar(t)


@lru_cache(maxsize=6)
def tracking_cacheado(game_id: int) -> pd.DataFrame:
    """Para el visor: mantiene en memoria los últimos partidos consultados."""
    return leer_tracking(game_id)


def matriz_jugadores(g: pd.DataFrame, ids: list[int], n_frames: int, cols: list[str]) -> dict[str, np.ndarray]:
    """Convierte las filas de una jugada en matrices [jugador, frame] por columna (NaN si falta el frame)."""
    pos = {pid: i for i, pid in enumerate(ids)}
    sub = g[g.nflId.isin(pos)]
    fi = sub.frameId.to_numpy(dtype=int) - 1
    pi = sub.nflId.map(pos).to_numpy(dtype=int)
    out = {}
    for c in cols:
        m = np.full((len(ids), n_frames), np.nan)
        m[pi, fi] = sub[c].to_numpy(dtype=float)
        out[c] = m
    return out
