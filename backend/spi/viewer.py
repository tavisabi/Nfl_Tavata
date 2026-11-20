"""Datos para el visor de jugadas: posiciones cuadro por cuadro de los 22 jugadores + balón, y las series de
separación/DSA de cada receptor (las mismas funciones que usa el pipeline, para que los números coincidan).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DT
from .loader import tablas, tracking_cacheado
from .penalties import anulada, castigos
from .play_analysis import calcular, defensor_principal, resumen_receptor


def _r(a, d=2):
    return [None if (v is None or np.isnan(v)) else round(float(v), d) for v in a]


def jugada(motor, game_id: int, play_id: int) -> dict:
    T = tablas()
    plays = T["plays"]
    meta = plays[(plays.gameId == game_id) & (plays.playId == play_id)]
    if meta.empty:
        raise KeyError("Jugada no encontrada")
    meta = meta.iloc[0]
    t = tracking_cacheado(int(game_id))
    g = t[t.playId == play_id].sort_values(["frameId"])
    pff = T["pff"]
    roles = pff[(pff.gameId == game_id) & (pff.playId == play_id)].set_index("nflId")
    rec = roles.index[roles.pff_role == "Pass Route"].astype(int).tolist()
    dfs = roles.index[roles.pff_role == "Coverage"].astype(int).tolist()
    jug = T["players"].set_index("nflId")

    n_frames = int(g.frameId.max())
    jugadores = []
    for pid, gp in g[g.nflId.notna()].groupby("nflId"):
        pid = int(pid)
        x = np.full(n_frames, np.nan); y = x.copy(); s = x.copy(); o = x.copy()
        fi = gp.frameId.to_numpy(int) - 1
        x[fi], y[fi], s[fi], o[fi] = gp.x, gp.y, gp.s, gp.o
        lado = "ofensiva" if gp.team.iloc[0] == meta.possessionTeam else "defensa"
        jugadores.append({
            "nflId": pid, "nombre": jug.displayName.get(pid, str(pid)), "posicion": jug.officialPosition.get(pid, ""),
            "dorsal": int(gp.jerseyNumber.iloc[0]) if pd.notna(gp.jerseyNumber.iloc[0]) else None,
            "lado": lado, "rol": roles.pff_role.get(pid, ""), "x": _r(x), "y": _r(y), "s": _r(s, 1), "o": _r(o, 0),
        })
    b = g[g.nflId.isna()]
    bx = np.full(n_frames, np.nan); by = bx.copy()
    fi = b.frameId.to_numpy(int) - 1
    bx[fi], by[fi] = b.x, b.y
    eventos = [{"frame": int(f), "evento": e} for f, e in b.dropna(subset=["event"])[["frameId", "event"]].itertuples(index=False)]

    jc = calcular(g, rec, dfs)
    receptores = []
    if jc is not None and motor.dsa is not None:
        for i, r in enumerate(jc.receptores):
            dsa, comp = motor.dsa.dsa_serie(jc.d[i], jc.vsep[i], jc.asep[i], jc.desal[i], jc.prof[i])
            res = resumen_receptor(jc, i)
            j, conf = defensor_principal(jc, i)
            cerc = [int(jc.defensores[c]) if c >= 0 else None for c in jc.cercano[i]]
            fila = None
            if motor.rutas is not None:
                f = motor.rutas[(motor.rutas.gameId == game_id) & (motor.rutas.playId == play_id) & (motor.rutas.nflId == r)]
                fila = f.iloc[0] if len(f) else None
            receptores.append({
                "nflId": int(r), "nombre": jug.displayName.get(r, str(r)), "posicion": jug.officialPosition.get(r, ""),
                "defensorPrincipal": int(jc.defensores[j]) if j >= 0 else None, "confianza": round(conf, 2),
                "objetivo": bool(fila.objetivo) if fila is not None else False,
                "scs": int(fila.scs) if fila is not None else -1,
                "resumen": {k: (None if isinstance(v, float) and np.isnan(v) else (round(v, 2) if isinstance(v, float) else v))
                            for k, v in res.items() if k not in ("def_idx", "valida")},
                "serie": {
                    "t": _r(np.arange(len(jc.d[i])) * DT, 1),
                    "sep": _r(jc.d[i]), "vsep": _r(comp["vsep"]), "asep": _r(comp["asep"]),
                    "desal": _r(comp["desal"]), "persist": _r(comp["persist"], 1), "prof": _r(comp["prof"], 1),
                    "dsa": _r(dsa, 1),
                    "cercano": cerc,
                },
            })
        receptores.sort(key=lambda r: -(r["serie"]["dsa"][jc.pase] or 0))
    return {
        "gameId": int(game_id), "playId": int(play_id), "frames": n_frames,
        "snap": jc.snap if jc else None, "pase": (jc.snap + jc.pase) if jc else None,
        "losX": jc.los_x if jc else None,
        "meta": {
            "descripcion": meta.playDescription, "ofensiva": meta.possessionTeam, "defensa": meta.defensiveTeam,
            "cuarto": int(meta.quarter), "down": int(meta.down), "distancia": int(meta.yardsToGo),
            "cobertura": meta.pff_passCoverage, "tipoCobertura": meta.pff_passCoverageType,
            "formacion": meta.offenseFormation if pd.notna(meta.offenseFormation) else None,
            "resultado": meta.passResult, "yardas": int(meta.playResult), "playAction": bool(meta.pff_playAction),
            "anulada": anulada(meta.playDescription),
            "castigos": castigos(meta, T["players"], {j["nflId"]: (meta.possessionTeam if j["lado"] == "ofensiva" else meta.defensiveTeam)
                                                       for j in jugadores}),
        },
        "jugadores": jugadores, "balon": {"x": _r(bx), "y": _r(by)}, "eventos": eventos, "receptores": receptores,
    }
