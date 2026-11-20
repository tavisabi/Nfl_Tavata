"""Auditoría complementaria: frecuencia, frames post-pase y viabilidad de identificar el receptor objetivo."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"


def main() -> None:
    plays = pd.read_csv(DATA / "plays.csv")
    players = pd.read_csv(DATA / "players.csv")
    pff = pd.read_csv(DATA / "pffScoutingData.csv")
    trk = sorted((DATA / "tracking").glob("tracking_*.csv"))

    print("## Frecuencia (dis / s) y frames posteriores al pase (muestra de 15 partidos)")
    ratios, post, total = [], [], []
    for f in trk[::8]:
        t = pd.read_csv(f)
        j = t[(t.s > 1) & t.nflId.notna()]
        ratios.extend((j.dis / j.s).sample(min(5000, len(j)), random_state=0).tolist())
        b = t[t.team == "football"]
        last = b.groupby("playId").frameId.max()
        pf = b[b.event.isin(["pass_forward", "autoevent_passforward"])].groupby("playId").frameId.min()
        post.extend((last[pf.index] - pf).tolist())
        total.extend(last.tolist())
    r = pd.Series(ratios)
    print("dis/s mediana:", round(r.median(), 4), "| p10-p90:", r.quantile([.1, .9]).round(4).tolist())
    print("frames tras el pase:", pd.Series(post).describe(percentiles=[.1, .5, .9]).round(1).to_dict())
    print("frames por jugada:", pd.Series(total).describe(percentiles=[.1, .5, .9]).round(1).to_dict())

    print("\n## Objetivo del pase desde playDescription")
    pat = re.compile(r"(?:pass|passed)\s.*?(?:\bto\b|intended for)\s+([A-Z][A-Za-z'\.\-]*\.?\s?[A-Z][A-Za-z'\-\.]+(?:\s(?:Jr|Sr|II|III|IV)\.?)?)")
    pases = plays[plays.passResult.isin(["C", "I", "IN"])].copy()
    pases["nombre"] = pases.playDescription.str.extract(pat, expand=False)
    print(f"pases C/I/IN: {len(pases):,} | con nombre extraído: {pases.nombre.notna().sum():,}")
    print("ejemplos:", pases.playDescription.head(4).tolist())

    def abrev(n: str) -> str:
        p = n.replace(".", ". ").split()
        return (p[0][0] + "." + "".join(p[1:])).lower().replace(" ", "") if len(p) > 1 else n.lower()

    players["abrev"] = players.displayName.map(lambda n: (n.split()[0][0] + "." + n.split()[-1] if len(n.split()) > 1 else n).lower())
    players["abrev2"] = players.displayName.map(lambda n: (n.split()[0][0] + "." + n.split()[1] if len(n.split()) > 1 else n).lower())
    rutas = pff[pff.pff_role == "Pass Route"].merge(players[["nflId", "abrev", "abrev2"]], on="nflId")
    pases["clave"] = pases.nombre.fillna("").str.replace(r"\s(Jr|Sr|II|III|IV)\.?$", "", regex=True).str.replace(" ", "").str.lower()
    m = pases.merge(rutas, on=["gameId", "playId"])
    m = m[(m.clave == m.abrev) | (m.clave == m.abrev2) | m.apply(lambda r: r.clave != "" and r.clave.split(".")[-1] == r.abrev.split(".")[-1] and r.clave[:1] == r.abrev[:1], axis=1)]
    unico = m.groupby(["gameId", "playId"]).nflId.nunique()
    print(f"pases con objetivo identificado de forma única entre los Pass Route: {(unico == 1).sum():,} ({(unico == 1).sum() / len(pases):.1%}) | ambiguos: {(unico > 1).sum():,}")
    print("tasa de completo entre identificados:", pases.set_index(["gameId", "playId"]).loc[unico[unico == 1].index].passResult.value_counts(normalize=True).round(3).to_dict())


if __name__ == "__main__":
    main()
