"""Agregaciones por receptor, defensor y emparejamiento. Todas incluyen el tamaño de muestra.

Para comparar jugadores con roles distintos se usa la DSA sobre lo esperado (DSA-OE): DSA de la ruta menos la DSA
media de las rutas con la misma alineación (Abierto / Slot / TE / Backfield) y el mismo tipo de cobertura.
Los promedios se encogen hacia la media de la liga con PRIOR rutas virtuales para no premiar muestras pequeñas.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PRIOR = 30            # rutas "virtuales" de la media de la liga para encoger promedios con poca muestra
CONF_MIN = 0.5        # confianza mínima del posible emparejamiento


def _encoger(media: pd.Series, n: pd.Series, liga: float, k: int = PRIOR) -> pd.Series:
    return (media * n + liga * k) / (n + k)


def _moda(s: pd.Series):
    m = s.dropna().mode()
    return m.iloc[0] if len(m) else None


def receptores(R: pd.DataFrame, jugadores: pd.DataFrame, n_grupos: int) -> pd.DataFrame:
    g = R.groupby("nflId")
    man = R[R.pff_passCoverageType == "Man"].groupby("nflId")
    zona = R[R.pff_passCoverageType == "Zone"].groupby("nflId")
    cre = R[R.creada].groupby("nflId")
    a = pd.DataFrame({
        "equipo": g.possessionTeam.agg(_moda),
        "alineacion": g.alineacion.agg(_moda),
        "rutas": g.size(),
        "objetivos": g.objetivo.sum(),
        "completos": g.completo.sum(),
        "dsa_media": g.dsa.mean(),
        "dsa_oe": g.dsa_oe.mean(),
        "consistencia": g.alta_rol.mean(),
        "sep_pase": g.sep_pase.mean(),
        "persistencia": g.persist.mean(),
        "tasa_creacion": g.creada.mean(),
        "t_creacion": cre.t_quiebre.median(),
        "ganancia": cre.ganancia.mean(),
        "dsa_oe_man": man.dsa_oe.mean(),
        "rutas_man": man.size(),
        "dsa_oe_zona": zona.dsa_oe.mean(),
        "rutas_zona": zona.size(),
    })
    a["dsa_oe_ajustada"] = _encoger(a.dsa_oe, a.rutas, 0.0)
    a["consistencia_ajustada"] = _encoger(a.consistencia, a.rutas, 0.25)
    for c in ("rutas_man", "rutas_zona"):
        a[c] = a[c].fillna(0).astype(int)
    firma = R[R.scs >= 0].groupby(["nflId", "scs"]).size().unstack(fill_value=0)
    firma = firma.reindex(columns=range(n_grupos), fill_value=0)
    tot = firma.sum(1)
    for j in range(n_grupos):
        a[f"scs_{j}"] = (firma[j] / tot).reindex(a.index)
    a["n_creaciones"] = tot.reindex(a.index).fillna(0).astype(int)
    a = a.join(jugadores.set_index("nflId")[["displayName", "officialPosition"]])
    return a.reset_index()


def defensores(R: pd.DataFrame, jugadores: pd.DataFrame) -> pd.DataFrame:
    M = R[(R.defId >= 0) & (R.def_conf >= CONF_MIN)]
    g = M.groupby("defId")
    obj = M[M.objetivo]
    a = pd.DataFrame({
        "equipo": g.defensiveTeam.agg(_moda),
        "rutas": g.size(),
        "dsa_permitida": g.dsa.mean(),
        "dsa_oe_permitida": g.dsa_oe.mean(),
        "sep_permitida": g.def_sep_pase.mean(),
        "objetivos": obj.groupby("defId").size(),
        "completos_permitidos": obj.groupby("defId").completo.sum(),
        "recuperacion": obj.groupby("defId").recuperacion.mean(),
        "conf_media": g.def_conf.mean(),
        "rutas_man": M[M.pff_passCoverageType == "Man"].groupby("defId").size(),
        "dsa_oe_permitida_man": M[M.pff_passCoverageType == "Man"].groupby("defId").dsa_oe.mean(),
        "alineacion_rival": g.alineacion.agg(_moda),
    })
    a["objetivos"] = a.objetivos.fillna(0).astype(int)
    a["rutas_man"] = a.rutas_man.fillna(0).astype(int)
    a["dsa_oe_permitida_ajustada"] = _encoger(a.dsa_oe_permitida, a.rutas, 0.0)
    a = a.join(jugadores.set_index("nflId")[["displayName", "officialPosition"]])
    return a.reset_index().rename(columns={"defId": "nflId"})


def emparejamientos(R: pd.DataFrame, jugadores: pd.DataFrame) -> pd.DataFrame:
    """A5: solo rutas contra cobertura man (pff_passCoverageType == "Man"). En zona el defensor más cercano refleja
    el área que cubre el esquema, no un duelo; por eso esas rutas no forman parejas."""
    M = R[(R.defId >= 0) & (R.def_conf >= CONF_MIN) & (R.pff_passCoverageType == "Man")]
    g = M.groupby(["nflId", "defId"])
    a = pd.DataFrame({
        "rutas": g.size(),
        "dsa_media": g.dsa.mean(),
        "dsa_oe": g.dsa_oe.mean(),
        "sep_pase": g.def_sep_pase.mean(),
        "conf_media": g.def_conf.mean(),
        "objetivos": g.objetivo.sum(),
        "completos": g.completo.sum(),
        "equipo_of": g.possessionTeam.agg(_moda),
        "equipo_def": g.defensiveTeam.agg(_moda),
        "alineacion": g.alineacion.agg(_moda),
    }).reset_index()
    a["cobertura"] = "Man"
    nom = jugadores.set_index("nflId")
    a["receptor"] = a.nflId.map(nom.displayName)
    a["pos_receptor"] = a.nflId.map(nom.officialPosition)
    a["defensor"] = a.defId.map(nom.displayName)
    a["pos_defensor"] = a.defId.map(nom.officialPosition)
    return a
