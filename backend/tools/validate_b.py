"""Fase B (validación breve): B1 objetivos, B2 sensibilidad, B3 estabilidad SCS, B5 memoria y tiempo.
Solo lectura. Uso: python -u -m backend.tools.validate_b
"""
from __future__ import annotations

import ctypes
import time
import warnings
from ctypes import wintypes

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
from backend.spi import dsa as DSA  # noqa: E402
from backend.spi import scs as SCS  # noqa: E402
from backend.spi import stats as S  # noqa: E402
from backend.spi.engine import motor  # noqa: E402
from backend.spi.loader import tablas  # noqa: E402


def memoria_pico_mb() -> float:
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("a", ctypes.c_size_t), ("b", ctypes.c_size_t),
                    ("c", ctypes.c_size_t), ("d", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    pmc = PMC()
    pmc.cb = ctypes.sizeof(PMC)
    h = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    return pmc.PeakWorkingSetSize / 2**20


def ari(a: np.ndarray, b: np.ndarray) -> float:
    """Índice de Rand ajustado."""
    tab = pd.crosstab(a, b).to_numpy()
    c2 = lambda x: x * (x - 1) / 2
    s_ij, s_a, s_b = c2(tab).sum(), c2(tab.sum(1)).sum(), c2(tab.sum(0)).sum()
    esp = s_a * s_b / c2(len(a))
    return float((s_ij - esp) / (0.5 * (s_a + s_b) - esp))


def ranking(R: pd.DataFrame, dsa: pd.Series) -> pd.Series:
    R = R.assign(dsa_v=dsa)
    R["oe"] = R.dsa_v - R.groupby(["alineacion", "pff_passCoverageType"]).dsa_v.transform("mean")
    g = R[R.alineacion.isin(["Abierto", "Slot", "TE"])].groupby("nflId")
    n, m = g.size(), g.oe.mean()
    return (m * n / (n + 30))[n >= 120]


def main() -> None:
    t0 = time.time()
    motor._correr()
    print(f"B5 carga completa: {time.time() - t0:.1f} s | memoria pico: {memoria_pico_mb():.0f} MB | estado: {motor.estado}")
    R, SE = motor.rutas, motor.series

    # B1: 50 objetivos aleatorios
    T = tablas()
    nom = T["players"].set_index("nflId").displayName
    obj = R[R.objetivo].sample(50, random_state=2021).merge(T["plays"][["gameId", "playId", "playDescription"]])
    print("\nB1 muestra de objetivos (nombre asignado | texto):")
    for r in obj.itertuples():
        frag = r.playDescription.split(" to ", 1)[-1][:28] if " to " in r.playDescription else r.playDescription[-40:]
        print(f"  {nom[r.nflId]:24s} | {frag}")

    # B2: sensibilidad
    base_rank = ranking(R, motor.rutas.dsa)
    variantes = {"base (20 bandas, p1-p99, tope 10 yd)": {}, "10 bandas": {"bandas": 10}, "40 bandas": {"bandas": 40},
                 "recorte p2.5-p97.5": {"pct": (0.025, 0.975)}, "recorte p0.5-p99.5": {"pct": (0.005, 0.995)},
                 "tope de separación 8 yd": {"tope": 8.0}}
    print("\nB2 sensibilidad (CV por partido; Spearman del ranking de receptores ≥120 rutas vs. base):")
    orig_def, orig_pct = DSA.neutralizador.__defaults__, DSA.RECORTE_PCT
    for nombre, v in variantes.items():
        DSA.neutralizador.__defaults__ = (v.get("bandas", 20),)
        DSA.RECORTE_PCT = v.get("pct", orig_pct)
        series = SE
        if "tope" in v:
            series = {k: (p, np.vstack([np.minimum(M[0], v["tope"]), M[1:]])) for k, (p, M) in SE.items()}
        m, C = DSA.ajustar(R.drop(columns=[c for c in ["persist", "vsep", "asep", "desal", "dsa", "dsa_bruta"] if c in R]), series)
        cv = m.validacion["dsa_neutral_profundidad"]
        rk = ranking(R, C.dsa)
        print(f"  {nombre:38s} AUC {cv['auc']:.4f} | log-loss {cv['log_loss']:.4f} | "
              f"ρ prof {m.validacion['spearman_profundidad']['dsa']:+.3f} | ρ ranking {S.spearman(base_rank.to_numpy(), rk.reindex(base_rank.index).to_numpy()):.3f} | componentes {m.componentes}")
    DSA.neutralizador.__defaults__, DSA.RECORTE_PCT = orig_def, orig_pct

    # B3: estabilidad SCS (bootstrap)
    cre = R[R.creada].dropna(subset=SCS.RASGOS)
    Z = (SCS._transformar(cre) - motor.scs.media) / motor.scs.desv
    base = motor.scs.asignar(cre)
    rng = np.random.default_rng(7)
    aris = []
    for _ in range(10):
        idx = rng.integers(0, len(Z), len(Z))
        _, Cb, _ = S.kmeans(Z[idx], motor.scs.k, n_init=3, semilla=int(rng.integers(1e6)))
        et = np.argmin(((Z[:, None, :] - Cb[None]) ** 2).sum(-1), axis=1)
        aris.append(ari(base, et))
    print(f"\nB3 SCS bootstrap (10 réplicas, k={motor.scs.k}): ARI media {np.mean(aris):.3f}, mín {np.min(aris):.3f}")
    print(f"\nTotal: {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
