"""Análisis cuadro por cuadro de una jugada: separación receptor-defensor y sus derivadas.

Fases (índices relativos al snap):
  - pre-pase: [snap, pase]       -> todas las variables que explican la ventaja
  - momento del pase: pase
  - post-pase: (pase, fin]       -> solo 0.5 s disponibles; se usan únicamente para Defensive Recovery
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import kinematics as K
from .config import (ASEP_MAX, DT, GANANCIA_MIN, INICIO_RUTA, PASE_AUTO, PASE_MANUAL, PROF_MAX, PROF_MIN, SEP_MAX,
                     SNAP_AUTO, SNAP_MANUAL, VEL_MIN, VENTANA, VSEP_MAX)

COLS = ["x", "y", "s", "o", "dir"]


@dataclass
class JugadaCalculada:
    """Resultado de una jugada. Las series [receptor, t] empiezan en el snap (t=0)."""
    snap: int                      # frameId del snap
    pase: int                      # índice t del pase (relativo al snap)
    los_x: float                   # línea de scrimmage (x estandarizada del balón en el snap)
    receptores: list[int]
    defensores: list[int]
    d: np.ndarray                  # separación al defensor más cercano (yd, recortada a SEP_MAX)
    vsep: np.ndarray               # V(t): media causal 0,5 s de d' respecto del defensor más cercano en t (yd/s)
    asep: np.ndarray               # A(t): cambio de V en 0,5 s respecto del mismo defensor (yd/s²)
    desal: np.ndarray              # desalineación de trayectorias [0, 1] (NaN si alguien está casi quieto)
    prof: np.ndarray               # profundidad del receptor: x - línea de scrimmage (yd)
    cercano: np.ndarray            # índice del defensor más cercano en cada t (-1 si no hay)
    dist_todos: np.ndarray         # [receptor, defensor, t] distancias crudas
    rx: np.ndarray
    ry: np.ndarray
    rs: np.ndarray
    rdir: np.ndarray
    ro: np.ndarray
    extra: dict = field(default_factory=dict)


def arreglos_jugada(g: pd.DataFrame) -> dict[str, np.ndarray]:
    """Convierte las filas (estandarizadas) de una jugada en arreglos numpy."""
    ev = g["event"].astype("object")
    return {
        "nflId": g["nflId"].to_numpy(dtype=float),
        "frameId": g["frameId"].to_numpy(dtype=int),
        **{c: g[c].to_numpy(dtype=float) for c in COLS},
        "snap_m": (ev == SNAP_MANUAL).to_numpy(), "snap_a": (ev == SNAP_AUTO).to_numpy(),
        "pase_m": (ev == PASE_MANUAL).to_numpy(), "pase_a": (ev == PASE_AUTO).to_numpy(),
    }


def frame_evento(frames: np.ndarray, manual: np.ndarray, auto: np.ndarray) -> int | None:
    """A2: primer frame del evento manual; si no existe, primer frame del automático; si no hay ninguno, None."""
    for marca in (manual, auto):
        f = frames[marca]
        if len(f):
            return int(f.min())
    return None


def _matriz(A: dict[str, np.ndarray], ids: list[int], n_frames: int) -> dict[str, np.ndarray]:
    pos = {pid: i for i, pid in enumerate(ids)}
    nid = A["nflId"]
    sel = np.isin(nid, ids)
    pi = np.array([pos[int(v)] for v in nid[sel]], dtype=int)
    fi = A["frameId"][sel] - 1
    out = {}
    for c in COLS:
        m = np.full((len(ids), n_frames), np.nan)
        m[pi, fi] = A[c][sel]
        out[c] = m
    return out


def calcular(g: pd.DataFrame | dict, receptores: list[int], defensores: list[int]) -> JugadaCalculada | None:
    """g: filas estandarizadas de una jugada (DataFrame o arreglos de `arreglos_jugada`).

    Devuelve None si la jugada no es analizable (sin snap, sin pase, o sin receptores/defensores con tracking).
    """
    A = arreglos_jugada(g) if isinstance(g, pd.DataFrame) else g
    es_balon = np.isnan(A["nflId"])
    fr_b = A["frameId"][es_balon]
    snap = frame_evento(fr_b, A["snap_m"][es_balon], A["snap_a"][es_balon])
    pase = frame_evento(fr_b, A["pase_m"][es_balon], A["pase_a"][es_balon])
    if snap is None or pase is None or pase <= snap or not receptores or not defensores:
        return None
    presentes = set(np.unique(A["nflId"][~es_balon]).astype(int).tolist())
    receptores = [r for r in receptores if r in presentes]
    defensores = [d for d in defensores if d in presentes]
    if not receptores or not defensores:
        return None
    n_frames = int(A["frameId"].max())
    R = _matriz(A, receptores, n_frames)
    D = _matriz(A, defensores, n_frames)
    i0 = snap - 1
    sl = slice(i0, n_frames)
    p = pase - 1 - i0

    def cin(M):
        x, y, s, dr, o = (M[c][:, sl] for c in COLS)
        vx, vy = K.velocidad(s, dr)
        return x, y, s, dr, o, vx, vy

    rx, ry, rs, rdir, ro, rvx, rvy = cin(R)
    dx, dy, ds, ddir, _do, dvx, dvy = cin(D)

    dist = np.hypot(rx[:, None, :] - dx[None, :, :], ry[:, None, :] - dy[None, :, :])
    dist_inf = np.where(np.isnan(dist), np.inf, dist)
    cercano = np.argmin(dist_inf, axis=1)
    sin_def = np.isinf(np.min(dist_inf, axis=1))
    cercano = np.where(sin_def, -1, cercano)
    idx = np.clip(cercano, 0, None)

    # Para cada receptor y t, variables del defensor más cercano en ese instante.
    def take(M: np.ndarray) -> np.ndarray:
        return M[idx, np.arange(M.shape[1])[None, :]]

    cero3 = np.zeros_like(dist)
    _, dd_todos, _ = K.separacion_dinamica(rx[:, None, :], ry[:, None, :], rvx[:, None, :], rvy[:, None, :], cero3, cero3,
                                           dx[None], dy[None], dvx[None], dvy[None], cero3, cero3)
    V, Aac = velocidad_y_aceleracion(np.clip(dd_todos, -VSEP_MAX, VSEP_MAX), cercano)
    d = np.where(sin_def, np.nan, np.min(dist_inf, axis=1))
    desal = K.desalineacion(rs, rdir, take(ds), take(ddir), VEL_MIN)

    bx = A["x"][es_balon][fr_b == snap]
    los_x = float(bx[0]) if len(bx) else float("nan")
    return JugadaCalculada(
        snap=snap, pase=p, los_x=los_x, receptores=receptores, defensores=defensores,
        d=np.minimum(d, SEP_MAX), vsep=V, asep=Aac, desal=desal, prof=rx - los_x,
        cercano=cercano, dist_todos=dist, rx=rx, ry=ry, rs=rs, rdir=rdir, ro=ro,
    )


def velocidad_y_aceleracion(vsep_todos: np.ndarray, cercano: np.ndarray, k: int = VENTANA) -> tuple[np.ndarray, np.ndarray]:
    """A3 / R-2. vsep_todos: d' de cada receptor respecto de CADA defensor [receptor, defensor, t].

    V(t) = media de d'_j en [t-k+1, t] y A(t) = (V_j(t) - V_j(t-k)) / (k·Δ), ambos con j = defensor más cercano en t.
    Usar la historia del mismo defensor evita los saltos falsos cuando cambia el más cercano (relevos en zona) y
    elimina el término geométrico de d''. Causal. Al inicio de la serie se usa el rezago disponible.
    """
    Vw = K.media_ventana(vsep_todos, k)
    n_r, _, n = Vw.shape
    t = np.arange(n)
    lag = np.minimum(t, k)
    j = np.clip(cercano, 0, None)
    ri = np.arange(n_r)[:, None]
    V = Vw[ri, j, t[None, :]]
    Vp = Vw[ri, j, (t - lag)[None, :]]
    with np.errstate(invalid="ignore", divide="ignore"):
        A = np.where(lag[None, :] > 0, (V - Vp) / (np.maximum(lag, 1)[None, :] * DT), 0.0)
    sin = cercano < 0
    return np.where(sin, np.nan, V), np.where(sin, np.nan, np.clip(A, -ASEP_MAX, ASEP_MAX))


def series_dsa(d: np.ndarray, V: np.ndarray, A: np.ndarray, desal: np.ndarray, prof: np.ndarray,
               tau: float) -> dict[str, np.ndarray]:
    """Componentes de la DSA en cada instante t. V y A ya vienen con ventana causal (ver velocidad_y_aceleracion)."""
    return {
        "sep": d,
        "vsep": V,
        "asep": A,
        "desal": K.media_ventana(desal, VENTANA),
        "persist": np.minimum(K.racha_final(np.nan_to_num(d, nan=0.0) >= tau) * DT, 3.0),
        "prof": np.clip(prof, PROF_MIN, PROF_MAX),
    }


def defensor_principal(jc: JugadaCalculada, r: int) -> tuple[int, float]:
    """Posible emparejamiento: el defensor que fue el más cercano en más frames de la fase de ruta.

    Devuelve (índice de defensor, confianza = fracción de frames). No es una asignación oficial.
    """
    a = min(INICIO_RUTA, jc.pase)
    c = jc.cercano[r, a: jc.pase + 1]
    c = c[c >= 0]
    if not len(c):
        return -1, 0.0
    cnt = np.bincount(c, minlength=len(jc.defensores))
    top = int(np.argmax(cnt))
    return top, float(cnt[top] / len(c))


def ultimo_minimo(w: np.ndarray) -> int:
    """A1: índice del ÚLTIMO mínimo de w (ignora NaN). En una meseta devuelve su final: el instante en que empieza la subida."""
    inv = w[::-1]
    return len(w) - 1 - int(np.nanargmin(inv))


def resumen_receptor(jc: JugadaCalculada, r: int) -> dict:
    """Métricas de una ruta (receptor r) que no dependen de parámetros ajustados."""
    p = jc.pase
    d = jc.d[r]
    a = min(INICIO_RUTA, p)
    w = d[a: p + 1]
    out: dict = {"t_pase": p * DT, "sep_pase": float(d[p]) if not np.isnan(d[p]) else np.nan}
    if np.all(np.isnan(w)):
        return out | {"valida": False}
    m = a + ultimo_minimo(w)
    ganancia = float(d[p] - d[m])
    creada = bool(ganancia >= GANANCIA_MIN and p - m >= 2)
    c = jc.cercano[r, a: p + 1]
    c = c[c >= 0]
    out |= {
        "valida": True,
        "sep_min": float(d[m]),
        "t_quiebre": m * DT,
        "ganancia": ganancia,
        "creada": creada,
        "profundidad": float(jc.prof[r, p]),
        "y_pase": float(jc.ry[r, p]),
        "cambios_def": int(np.sum(c[1:] != c[:-1])) if len(c) > 1 else 0,
    }
    # Firma de movimiento alrededor del quiebre (solo información del receptor, sin usar el futuro post-pase).
    s = jc.rs[r]
    dsdt = K.derivada(K.suavizar(s[None, :], 3))[0]
    a0, a1 = max(0, m - 10), min(p, m + 5)
    antes = dsdt[a0: m + 1]
    despues = dsdt[m: a1 + 1]
    out |= {
        "vel_quiebre": float(s[m]),
        "freno": float(max(0.0, -np.nanmin(antes))) if np.any(~np.isnan(antes)) else np.nan,
        "acel_post": float(max(0.0, np.nanmax(despues))) if np.any(~np.isnan(despues)) else np.nan,
        "giro": float(K.diferencia_angular(jc.rdir[r, min(p, m + 5)], jc.rdir[r, max(0, m - 5)])),
        "div_orient": float(K.diferencia_angular(jc.ro[r, m], jc.rdir[r, m])),
    }
    # Posible emparejamiento y recuperación defensiva tras el pase (única métrica post-pase).
    j, conf = defensor_principal(jc, r)
    out["def_idx"], out["def_conf"] = j, conf
    if j >= 0:
        dp = jc.dist_todos[r, j]
        out["def_sep_pase"] = float(min(dp[p], SEP_MAX))
        k = min(5, len(dp) - 1 - p)
        out["recuperacion"] = float((dp[p] - dp[p + k]) / (k * DT)) if k >= 2 and not np.isnan(dp[p + k]) else np.nan
    return out
