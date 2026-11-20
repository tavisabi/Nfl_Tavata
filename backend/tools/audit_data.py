"""Auditoría reproducible del dataset (Fase 1). Solo lee data/; no modifica nada.

Uso:  .venv\\Scripts\\python.exe -m backend.tools.audit_data > audit.txt
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"


def seccion(t: str) -> None:
    print(f"\n## {t}")


def resumen_tabla(nombre: str, df: pd.DataFrame, llaves: list[str]) -> None:
    seccion(f"{nombre}: {df.shape[0]:,} filas x {df.shape[1]} columnas")
    nulos = df.isna().sum()
    for c in df.columns:
        print(f"- {c} | {df[c].dtype} | nulos={nulos[c]:,} | únicos={df[c].nunique(dropna=True):,}")
    dup = df.duplicated(subset=llaves).sum()
    print(f"duplicados por llave {llaves}: {dup:,}; filas idénticas: {df.duplicated().sum():,}")


def main() -> None:
    t0 = time.time()
    seccion("Archivos")
    for f in sorted(DATA.rglob("*.csv"))[:6]:
        print(f"- {f.relative_to(RAIZ)}  {f.stat().st_size / 2**20:.1f} MB")
    trk = sorted((DATA / "tracking").glob("tracking_*.csv"))
    print(f"tracking: {len(trk)} archivos, {sum(f.stat().st_size for f in trk) / 2**20:.1f} MB")

    games = pd.read_csv(DATA / "games.csv")
    plays = pd.read_csv(DATA / "plays.csv")
    players = pd.read_csv(DATA / "players.csv")
    pff = pd.read_csv(DATA / "pffScoutingData.csv")

    resumen_tabla("games.csv", games, ["gameId"])
    resumen_tabla("plays.csv", plays, ["gameId", "playId"])
    resumen_tabla("players.csv", players, ["nflId"])
    resumen_tabla("pffScoutingData.csv", pff, ["gameId", "playId", "nflId"])

    seccion("Cobertura temporal y equipos")
    print("temporadas:", games.season.unique().tolist(), "| semanas:", sorted(games.week.unique().tolist()))
    print("partidos por semana:", games.week.value_counts().sort_index().to_dict())
    eq = pd.concat([games.homeTeamAbbr, games.visitorTeamAbbr]).value_counts()
    print(f"equipos: {eq.size} | partidos por equipo min={eq.min()} max={eq.max()}")
    print("fechas:", games.gameDate.min(), "->", games.gameDate.max())

    seccion("Relaciones entre tablas")
    g_ids = set(games.gameId)
    print("plays.gameId ⊆ games:", set(plays.gameId) <= g_ids, "| partidos con jugadas:", plays.gameId.nunique())
    kp = set(zip(plays.gameId, plays.playId))
    ks = set(zip(pff.gameId, pff.playId))
    print(f"jugadas en plays={len(kp):,} | en pff={len(ks):,} | pff⊆plays={ks <= kp} | plays sin pff={len(kp - ks):,}")
    print(f"pff.nflId en players: {pff.nflId.isin(players.nflId).mean():.4f}")
    print("pff_role:", pff.pff_role.value_counts().to_dict())
    pr = pff[pff.pff_role == "Pass Route"].merge(players[["nflId", "officialPosition"]], on="nflId", how="left")
    print("posición oficial de Pass Route:", pr.officialPosition.value_counts().to_dict())
    cv = pff[pff.pff_role == "Coverage"].merge(players[["nflId", "officialPosition"]], on="nflId", how="left")
    print("posición oficial de Coverage:", cv.officialPosition.value_counts().to_dict())
    print("Pass Route por jugada:", pff[pff.pff_role == "Pass Route"].groupby(["gameId", "playId"]).size().describe().round(2).to_dict())
    print("Coverage por jugada:", pff[pff.pff_role == "Coverage"].groupby(["gameId", "playId"]).size().describe().round(2).to_dict())
    print("pff_positionLinedUp (Pass Route):", pr.merge(pff[["gameId", "playId", "nflId", "pff_positionLinedUp"]], how="left").pff_positionLinedUp.value_counts().head(15).to_dict())

    seccion("Contexto de jugada")
    for c in ["passResult", "pff_passCoverage", "pff_passCoverageType", "dropBackType", "offenseFormation", "pff_playAction", "quarter", "down"]:
        print(f"{c}:", plays[c].value_counts(dropna=False).to_dict())
    print("columnas de objetivo/receptor objetivo presentes:", [c for c in plays.columns if "target" in c.lower()])

    seccion("Tracking (todos los archivos)")
    filas = 0
    jugadas_trk = set()
    eventos: dict[str, int] = {}
    dt_vals = []
    dup_total = 0
    nulos_nflid = 0
    rangos = {c: [np.inf, -np.inf] for c in ["x", "y", "s", "a", "dis", "o", "dir"]}
    nulos_cols: dict[str, int] = {}
    play_dirs: dict[str, int] = {}
    sin_snap = sin_pase = 0
    frames_snap_pase = []
    jugadas_por_archivo_ok = 0
    gid_ok = 0
    columnas = None
    for f in trk:
        t = pd.read_csv(f)
        columnas = list(t.columns)
        gid = int(f.stem.split("_")[1])
        gid_ok += int((t.gameId == gid).all())
        filas += len(t)
        nulos_nflid += int(t.nflId.isna().sum())
        for c, n in t.isna().sum().items():
            nulos_cols[c] = nulos_cols.get(c, 0) + int(n)
        for c in rangos:
            rangos[c][0] = min(rangos[c][0], float(t[c].min()))
            rangos[c][1] = max(rangos[c][1], float(t[c].max()))
        dup_total += int(t.duplicated(subset=["gameId", "playId", "nflId", "frameId"]).sum())
        for k, v in t.event.value_counts().items():
            eventos[k] = eventos.get(k, 0) + int(v)
        for k, v in t.drop_duplicates(["playId"]).playDirection.value_counts().items():
            play_dirs[k] = play_dirs.get(k, 0) + int(v)
        jugadas_trk |= set(zip(t.gameId, t.playId))
        balon = t[t.team == "football"]
        if len(dt_vals) < 20000:
            tt = pd.to_datetime(balon.time)
            d = balon.assign(tt=tt).sort_values(["playId", "frameId"]).groupby("playId").tt.diff().dt.total_seconds().dropna()
            dt_vals.extend(d.tolist())
        ev = balon[["playId", "frameId", "event"]].dropna()
        snap = ev[ev.event.isin(["ball_snap", "autoevent_ballsnap"])].groupby("playId").frameId.min()
        pase = ev[ev.event.isin(["pass_forward", "autoevent_passforward"])].groupby("playId").frameId.min()
        todas = balon.playId.unique()
        sin_snap += int(len(set(todas) - set(snap.index)))
        sin_pase += int(len(set(todas) - set(pase.index)))
        comun = snap.index.intersection(pase.index)
        frames_snap_pase.extend((pase[comun] - snap[comun]).tolist())
    print("columnas:", columnas)
    print(f"filas: {filas:,} | archivos con gameId consistente: {gid_ok}/{len(trk)} | duplicados (game,play,nflId,frame): {dup_total:,}")
    print(f"filas de balón (nflId NA): {nulos_nflid:,}")
    print("nulos por columna:", nulos_cols)
    print("rangos:", {k: (round(a, 2), round(b, 2)) for k, (a, b) in rangos.items()})
    print("playDirection por jugada:", play_dirs)
    dt = pd.Series(dt_vals)
    print("Δt entre frames (s):", dt.round(2).value_counts().head(5).to_dict())
    print(f"jugadas con tracking: {len(jugadas_trk):,} | plays sin tracking: {len(kp - jugadas_trk):,} | tracking sin plays: {len(jugadas_trk - kp):,}")
    print("eventos:", dict(sorted(eventos.items(), key=lambda x: -x[1])))
    print(f"jugadas sin snap: {sin_snap:,} | sin pase (pass_forward/autoevent): {sin_pase:,}")
    fs = pd.Series(frames_snap_pase) / 10
    print("segundos snap→pase:", fs.describe(percentiles=[.05, .25, .5, .75, .95]).round(2).to_dict())
    print(f"tiempo total: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
