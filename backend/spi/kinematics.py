"""Funciones cinemáticas puras (numpy). Sin dependencias de pandas para poder probarlas con casos controlados.

Convención (verificada en tests con datos reales): `dir` y `o` están en grados, 0° apunta a +y y crecen en
sentido horario, así que el vector unitario es (sin θ, cos θ). Tras estandarizar, la ofensiva ataca hacia +x.
"""
from __future__ import annotations

import numpy as np

from .config import DT


def vector_unitario(grados: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r = np.deg2rad(grados)
    return np.sin(r), np.cos(r)


def velocidad(s: np.ndarray, dir_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ux, uy = vector_unitario(dir_deg)
    return s * ux, s * uy


def derivada(v: np.ndarray, eje: int = -1) -> np.ndarray:
    """Derivada temporal centrada (diferencias finitas) a 10 Hz. Respeta NaN."""
    if v.shape[eje] < 2:
        return np.zeros_like(v)
    return np.gradient(v, DT, axis=eje)


def suavizar(v: np.ndarray, k: int = 3) -> np.ndarray:
    """Media móvil centrada de k frames sobre el último eje, ignorando NaN."""
    if k <= 1 or v.shape[-1] < k:
        return v
    pad = k // 2
    vp = np.pad(v, [(0, 0)] * (v.ndim - 1) + [(pad, pad)], mode="edge")
    validos = ~np.isnan(vp)
    vp0 = np.where(validos, vp, 0.0)
    c = np.cumsum(vp0, axis=-1)
    n = np.cumsum(validos, axis=-1)
    c = np.concatenate([np.zeros(c.shape[:-1] + (1,)), c], axis=-1)
    n = np.concatenate([np.zeros(n.shape[:-1] + (1,)), n], axis=-1)
    suma = c[..., k:] - c[..., :-k]
    cnt = n[..., k:] - n[..., :-k]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, suma / cnt, np.nan)


def diferencia_angular(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """|a - b| en grados, en [0, 180]."""
    d = np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0)
    return d


def separacion_dinamica(px, py, vx, vy, ax, ay, qx, qy, wx, wy, bx, by):
    """Distancia d entre receptor (p, v, a) y defensor (q, w, b) y sus derivadas exactas.

    d'  = (r · u) / d                    con r = p - q, u = v - w (velocidad relativa)
    d'' = (|u|² + r · α - d'²) / d       con α = a - b (aceleración relativa)
    Devuelve (d, d', d''). Positivo = la separación crece.
    """
    rx, ry = px - qx, py - qy
    ux, uy = vx - wx, vy - wy
    alx, aly = ax - bx, ay - by
    d = np.hypot(rx, ry)
    with np.errstate(invalid="ignore", divide="ignore"):
        dd = (rx * ux + ry * uy) / d
        ddd = (ux * ux + uy * uy + rx * alx + ry * aly - dd * dd) / d
    d_seg = np.where(d > 1e-6, d, np.nan)
    dd = np.where(np.isnan(d_seg), 0.0, dd)
    ddd = np.where(np.isnan(d_seg), 0.0, ddd)
    return d, dd, ddd


def desalineacion(s1, dir1, s2, dir2, vel_min: float) -> np.ndarray:
    """(1 - cos Δdir) / 2 entre dos trayectorias: 0 = misma dirección, 1 = direcciones opuestas.

    NaN si alguno se mueve a menos de `vel_min` (su dirección no es confiable).
    """
    d = np.deg2rad(diferencia_angular(dir1, dir2))
    m = (1.0 - np.cos(d)) / 2.0
    return np.where((s1 >= vel_min) & (s2 >= vel_min), m, np.nan)


def racha_final(cond: np.ndarray) -> np.ndarray:
    """Para cada t, número de frames consecutivos (terminando en t) donde cond es verdadera."""
    out = np.zeros(cond.shape[-1], dtype=float)
    c = 0
    for i, v in enumerate(cond):
        c = c + 1 if v else 0
        out[i] = c
    return out


def media_ventana(v: np.ndarray, k: int) -> np.ndarray:
    """Para cada t (último eje), media de v[..., t-k+1 .. t] ignorando NaN (ventana causal: no usa el futuro)."""
    v = np.asarray(v, dtype=float)
    n = v.shape[-1]
    validos = ~np.isnan(v)
    cero = np.zeros(v.shape[:-1] + (1,))
    c = np.concatenate([cero, np.cumsum(np.where(validos, v, 0.0), axis=-1)], axis=-1)
    cn = np.concatenate([cero, np.cumsum(validos, axis=-1)], axis=-1)
    t = np.arange(n)
    a = np.maximum(0, t - k + 1)
    cnt = cn[..., t + 1] - cn[..., a]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(cnt > 0, (c[..., t + 1] - c[..., a]) / np.maximum(cnt, 1), np.nan)
