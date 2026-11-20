"""Exploración para fijar la fórmula de la DSA (Fase 2). Herramienta de desarrollo: guarda un caché en %TEMP%,
nunca dentro del proyecto, y la aplicación no lo usa.
"""
from __future__ import annotations

import os
import pickle
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
from backend.spi import stats as S  # noqa: E402
from backend.spi.pipeline import extraer  # noqa: E402
from backend.spi.play_analysis import series_dsa  # noqa: E402

CACHE = Path(tempfile.gettempdir()) / "spi_extraccion_v3.pkl"   # v3: series = [d, V, A, desal, prof]


def cargar() -> dict:
    if CACHE.exists() and "--fresco" not in sys.argv:
        return pickle.loads(CACHE.read_bytes())
    r = extraer()
    CACHE.write_bytes(pickle.dumps(r))
    return r


def main() -> None:
    r = cargar()
    R, SE = r["rutas"], r["series"]
    print("extracción s:", round(r["segundos"], 1), "| motivos:", r["motivos"], "| rutas:", len(R))
    obj = R[R.objetivo]
    tau = float(obj.sep_pase.median())
    print(f"objetivos: {len(obj):,} | tau (mediana sep al pase de objetivos) = {tau:.2f} yd | todas las rutas mediana = {R.sep_pase.median():.2f}")

    comp = []
    for k in zip(R.gameId, R.playId, R.nflId):
        p, M = SE[k]
        f = series_dsa(*(M[i].astype(float) for i in range(5)), tau)
        comp.append([f[c][p] for c in ("sep", "vsep", "asep", "desal", "persist")])
    C = pd.DataFrame(comp, columns=["sep", "vsep", "asep", "desal", "persist"], index=R.index)
    print("componentes:\n", C.describe().round(2).to_string())
    print("faltantes:", C.isna().sum().to_dict())
    print("correlación (Spearman):\n", C.rank().corr().round(2).to_string())

    Y = obj.completo.to_numpy()
    G = obj.gameId.to_numpy()
    Co = C.loc[obj.index].copy()
    Co["desal"] = Co.desal.fillna(C.desal.median())
    Co["prof"] = obj.profundidad.clip(-5, 40)
    print("\ncompletos por cuartil de separación:", obj.groupby(pd.qcut(obj.sep_pase, 4)).completo.mean().round(3).to_dict())
    modelos = {
        "solo intercepto": [],
        "profundidad": ["prof"],
        "sep + prof": ["sep", "prof"],
        "sep + vsep + prof": ["sep", "vsep", "prof"],
        "todo": ["sep", "vsep", "asep", "desal", "persist", "prof"],
    }
    for n, cols in modelos.items():
        print(f"CV {n:22s}", {k: round(v, 4) for k, v in S.cv_logit(Co[cols].to_numpy(), Y, G).items()})
    todo = ["sep", "vsep", "asep", "desal", "persist", "prof"]
    base = S.cv_logit(Co[todo].to_numpy(), Y, G)["log_loss"]
    for c in todo:
        cols = [x for x in todo if x != c]
        print(f"  sin {c:8s} Δlogloss = {S.cv_logit(Co[cols].to_numpy(), Y, G)['log_loss'] - base:+.4f}")
    X = Co[todo].to_numpy()
    mu, sd = X.mean(0), X.std(0)
    b, se = S.logit_ajustar((X - mu) / sd, Y)
    print("coeficientes estandarizados:", {c: (round(b[i + 1], 3), round(se[i + 1], 3)) for i, c in enumerate(todo)})

    cre = R[R.creada]
    print(f"\nrutas con creación: {len(cre):,} ({len(cre) / len(R):.1%})")
    F = cre[["vel_quiebre", "freno", "acel_post", "giro", "div_orient"]].dropna()
    print("SCS rasgos:\n", F.describe().round(2).to_string())
    print("correlación SCS:\n", F.rank().corr().round(2).to_string())
    Z = ((F - F.mean()) / F.std()).to_numpy()
    for k in range(2, 8):
        et, Cc, inercia = S.kmeans(Z, k, n_init=4)
        print(f"k={k} silhouette={S.silhouette(Z, et):.3f} inercia={inercia:.0f} tamaños={np.bincount(et).tolist()}")


if __name__ == "__main__":
    main()
