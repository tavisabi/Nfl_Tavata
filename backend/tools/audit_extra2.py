"""Auditoría complementaria 2 (solo lectura): ventanas temporales, eventos duplicados, cobertura de roles en el
tracking y significado de la columna `a`. Uso: python -m backend.tools.audit_extra2
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backend.spi.config import EVENTOS_PASE, EVENTOS_SNAP
from backend.spi.loader import archivos_tracking, tablas


def main() -> None:
    T = tablas()
    pff, plays = T["pff"], T["plays"]
    pre, post_ev, ambos_snap, ambos_pase, dif_pase, dif_snap = [], [], 0, 0, [], []
    rol_sin_trk, rol_total = 0, 0
    a_vs_ds, a_neg = [], 0
    sin_pase_resultado = []
    for f in archivos_tracking():
        t = pd.read_csv(f, usecols=["gameId", "playId", "nflId", "frameId", "s", "a", "event"])
        gid = int(t.gameId.iloc[0])
        b = t[t.nflId.isna()]
        ev = b.dropna(subset=["event"])
        for pid, e in ev.groupby("playId"):
            sm = e[e.event == "ball_snap"].frameId
            sa = e[e.event == "autoevent_ballsnap"].frameId
            pm = e[e.event == "pass_forward"].frameId
            pa = e[e.event == "autoevent_passforward"].frameId
            if len(sm) and len(sa):
                ambos_snap += 1
                dif_snap.append(int(sa.min() - sm.min()))
            if len(pm) and len(pa):
                ambos_pase += 1
                dif_pase.append(int(pa.min() - pm.min()))
            snap = e[e.event.isin(EVENTOS_SNAP)].frameId
            if len(snap):
                pre.append(int(snap.min()) - 1)
            if not len(e[e.event.isin(EVENTOS_PASE)]):
                sin_pase_resultado.append((gid, pid))
        presentes = set(zip(t.playId, t.nflId.dropna().astype(int))) if False else None
        ids = t.dropna(subset=["nflId"]).groupby("playId").nflId.apply(lambda s: set(s.astype(int)))
        sub = pff[(pff.gameId == gid) & pff.pff_role.isin(["Pass Route", "Coverage"])]
        for r in sub.itertuples():
            rol_total += 1
            rol_sin_trk += int(r.nflId not in ids.get(r.playId, set()))
        j = t.dropna(subset=["nflId"]).sort_values(["playId", "nflId", "frameId"])
        ds = j.groupby(["playId", "nflId"]).s.diff() / 0.1
        m = ds.notna() & (j.s > 1)
        a_vs_ds.append(np.corrcoef(j.a[m], ds[m].abs())[0, 1])
        a_neg += int((j.a < 0).sum())
    print("frames antes del snap:", pd.Series(pre).describe(percentiles=[.05, .5, .95]).round(1).to_dict())
    print(f"jugadas con ball_snap y autoevent_ballsnap: {ambos_snap} | diferencia auto-manual (frames):",
          pd.Series(dif_snap).value_counts().head(6).to_dict())
    print(f"jugadas con pass_forward y autoevent_passforward: {ambos_pase} | diferencia auto-manual (frames):",
          pd.Series(dif_pase).value_counts().head(6).to_dict())
    # A2: con "manual primero", el frame cambia respecto de "el primero de los dos" cuando el automático va antes.
    print(f"A2 - jugadas cuyo snap cambia: {int((pd.Series(dif_snap) < 0).sum())} | cuyo pase cambia: {int((pd.Series(dif_pase) < 0).sum())}")
    sp = pd.DataFrame(sin_pase_resultado, columns=["gameId", "playId"]).merge(plays, on=["gameId", "playId"])
    print("resultado de las jugadas sin evento de pase:", sp.passResult.value_counts().to_dict())
    print(f"roles Pass Route/Coverage sin tracking en su jugada: {rol_sin_trk} de {rol_total}")
    print(f"corr(a, |ds/dt|) mediana por partido: {np.median(a_vs_ds):.3f} | valores a<0: {a_neg}")


if __name__ == "__main__":
    main()
