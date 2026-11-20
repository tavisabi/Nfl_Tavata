"""Fase de extracción: recorre el tracking partido por partido y produce una fila por ruta (receptor-jugada).

Se procesa en memoria al arrancar; no se escribe nada en disco.
"""
from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np
import pandas as pd

from .loader import archivos_tracking, estandarizar, tablas, COLS_TRACKING
from .play_analysis import arreglos_jugada, calcular, resumen_receptor
from .targets import objetivos


def grupo_alineacion(pos: str) -> str:
    """Agrupa pff_positionLinedUp en roles comparables: Abierto (LWR/RWR), Slot (S*WR), TE y Backfield."""
    if not isinstance(pos, str):
        return "Otro"
    if pos in ("LWR", "RWR"):
        return "Abierto"
    if pos.startswith("S") and "WR" in pos:
        return "Slot"
    if pos.startswith("TE"):
        return "TE"
    if pos.startswith(("HB", "FB", "QB")):
        return "Backfield"
    return "Otro"


def roles_por_jugada(pff: pd.DataFrame) -> dict[tuple[int, int], tuple[list[int], list[int]]]:
    out: dict = {}
    sub = pff[pff.pff_role.isin(["Pass Route", "Coverage"])]
    for (g, p), grp in sub.groupby(["gameId", "playId"]):
        out[(g, p)] = (grp.loc[grp.pff_role == "Pass Route", "nflId"].astype(int).tolist(),
                       grp.loc[grp.pff_role == "Coverage", "nflId"].astype(int).tolist())
    return out


def _procesar_archivo(ruta, roles) -> tuple[list[dict], dict, Counter]:
    t = estandarizar(pd.read_csv(ruta, usecols=COLS_TRACKING)).sort_values("playId", kind="stable")
    A = arreglos_jugada(t)
    plays_id = t["playId"].to_numpy()
    g = int(t["gameId"].iloc[0])
    cortes = np.flatnonzero(np.diff(plays_id)) + 1
    inicios = np.concatenate([[0], cortes])
    fines = np.concatenate([cortes, [len(plays_id)]])
    filas, series, motivos = [], {}, Counter()
    for a, b in zip(inicios, fines):
        p = int(plays_id[a])
        rec, dfs = roles.get((g, p), ([], []))
        jc = calcular({k: v[a:b] for k, v in A.items()}, rec, dfs)
        if jc is None:
            motivos["sin snap/pase o sin jugadores"] += 1
            continue
        motivos["analizada"] += 1
        for i, r in enumerate(jc.receptores):
            res = resumen_receptor(jc, i)
            if not res.get("valida"):
                motivos["ruta sin datos"] += 1
                continue
            j = res.pop("def_idx")
            res.update(gameId=int(g), playId=int(p), nflId=int(r),
                       defId=int(jc.defensores[j]) if j >= 0 else -1)
            filas.append(res)
            series[(int(g), int(p), int(r))] = (
                jc.pase,
                np.stack([jc.d[i], jc.vsep[i], jc.asep[i], jc.desal[i], jc.prof[i]]).astype(np.float32),
            )
    return filas, series, motivos


def extraer(progreso: Callable[[float, str], None] | None = None, limite: int | None = None, hilos: int = 4) -> dict:
    t0 = time.time()
    T = tablas()
    roles = roles_por_jugada(T["pff"])
    archivos = archivos_tracking()[:limite] if limite else archivos_tracking()
    filas, series, motivos = [], {}, Counter()
    with ThreadPoolExecutor(max_workers=hilos) as ex:
        futuros = [ex.submit(_procesar_archivo, a, roles) for a in archivos]
        for k, f in enumerate(futuros, 1):
            fl, se, mo = f.result()
            filas += fl
            series.update(se)
            motivos += mo
            if progreso:
                progreso(k / len(archivos), f"Procesando tracking {k}/{len(archivos)}")
    rutas = pd.DataFrame(filas)
    # Contexto de jugada y objetivo del pase
    plays = T["plays"][["gameId", "playId", "possessionTeam", "defensiveTeam", "passResult", "pff_passCoverage",
                        "pff_passCoverageType", "pff_playAction", "down", "yardsToGo", "quarter", "offenseFormation",
                        "dropBackType", "playResult"]]
    rutas = rutas.merge(plays, on=["gameId", "playId"], how="left")
    alin = T["pff"][T["pff"].pff_role == "Pass Route"][["gameId", "playId", "nflId", "pff_positionLinedUp"]]
    rutas = rutas.merge(alin, on=["gameId", "playId", "nflId"], how="left")
    rutas["alineacion"] = rutas.pff_positionLinedUp.map(grupo_alineacion)
    rutas = rutas.merge(T["games"][["gameId", "week"]], on="gameId", how="left")
    obj = objetivos(T["plays"], T["pff"], T["players"])
    rutas = rutas.merge(obj, on=["gameId", "playId"], how="left")
    rutas["objetivo"] = rutas.targetId == rutas.nflId
    rutas["completo"] = np.where(rutas.objetivo, (rutas.passResult == "C").astype(float), np.nan)
    rutas = rutas.drop(columns=["targetId"])
    return {"rutas": rutas, "series": series, "motivos": dict(motivos), "segundos": time.time() - t0}
