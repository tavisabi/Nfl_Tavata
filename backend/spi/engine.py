"""Orquestador: extracción -> DSA -> SCS -> agregados -> hallazgos. Corre en un hilo al arrancar el servidor
(el servidor es efímero: todo se calcula en memoria, nada se escribe en disco). /health responde desde el inicio.
"""
from __future__ import annotations

import threading
import time
import traceback
import warnings

import numpy as np
import pandas as pd

from . import aggregates as AG
from . import dsa as DSA
from . import insights as INS
from . import scs as SCS
from . import stats as S
from .loader import tablas
from .pipeline import extraer


def _calidad_emparejamiento(R: pd.DataFrame) -> dict:
    """A5: qué tan estable es el defensor más cercano según el tipo de cobertura (justifica limitar a man)."""
    out = {}
    for tipo in ("Man", "Zone"):
        sub = R[(R.pff_passCoverageType == tipo) & (R.defId >= 0)]
        out[tipo] = {
            "rutas": int(len(sub)),
            "confianza_media": float(sub.def_conf.mean()),
            "cambios_def_media": float(sub.cambios_def.mean()),
            "pct_confianza_min": float((sub.def_conf >= AG.CONF_MIN).mean()),
        }
    return out


class Motor:
    def __init__(self) -> None:
        self.estado = "inactivo"
        self.progreso = 0.0
        self.mensaje = ""
        self.error: str | None = None
        self._lock = threading.Lock()
        self.rutas: pd.DataFrame | None = None
        self.series: dict = {}
        self.dsa: DSA.ModeloDSA | None = None
        self.scs: SCS.ModeloSCS | None = None
        self.receptores: pd.DataFrame | None = None
        self.defensores: pd.DataFrame | None = None
        self.emparejamientos: pd.DataFrame | None = None
        self.hallazgos: list[dict] = []
        self.resumen: dict = {}

    def _avance(self, p: float, m: str) -> None:
        self.progreso, self.mensaje = p, m

    def iniciar(self) -> None:
        with self._lock:
            if self.estado in ("cargando", "listo"):
                return
            self.estado = "cargando"
        threading.Thread(target=self._correr, daemon=True).start()

    def _correr(self) -> None:
        warnings.simplefilter("ignore")
        t0 = time.time()
        try:
            T = tablas()
            ext = extraer(lambda p, m: self._avance(0.85 * p, m))
            R = ext["rutas"]
            self._avance(0.87, "Ajustando la DSA")
            modelo, C = DSA.ajustar(R, ext["series"])
            R = R.join(C[["persist", "vsep", "asep", "desal", "dsa", "dsa_bruta"]])
            # DSA sobre lo esperado: compara cada ruta con rutas del mismo rol (alineación) y tipo de cobertura.
            # La DSA ya es neutral a la profundidad (A4), así que la DSA-OE también lo es.
            grp = R.groupby(["alineacion", "pff_passCoverageType"]).dsa
            R["dsa_esperada"] = grp.transform("mean")
            R["dsa_oe"] = R.dsa - R.dsa_esperada
            R["alta_rol"] = R.dsa >= grp.transform(lambda s: s.quantile(0.75))
            modelo.validacion["spearman_profundidad"]["dsa_oe"] = S.spearman(
                R.dsa_oe.to_numpy(), C.prof.reindex(R.index).to_numpy())
            self._avance(0.92, "Agrupando firmas de movimiento (SCS)")
            mscs, et = SCS.ajustar(R)
            R["scs"] = et
            pos = T["players"].set_index("nflId").officialPosition
            for g in mscs.grupos:
                sub = R[R.scs == g["id"]]
                g["posiciones"] = sub.nflId.map(pos).value_counts(normalize=True).round(3).head(4).to_dict()
                g["vs_man"] = float(sub[sub.pff_passCoverageType == "Man"].ganancia.mean())
                g["vs_zona"] = float(sub[sub.pff_passCoverageType == "Zone"].ganancia.mean())
                ob = sub[sub.objetivo]
                g["objetivos"] = int(len(ob))
                g["tasa_completo"] = float(ob.completo.mean()) if len(ob) else None
                g["dsa_pase_media"] = float(sub.dsa.mean())
            self._avance(0.96, "Calculando perfiles y hallazgos")
            rec = AG.receptores(R, T["players"], mscs.k)
            dfs = AG.defensores(R, T["players"])
            emp = AG.emparejamientos(R, T["players"])
            self.rutas, self.series, self.dsa, self.scs = R, ext["series"], modelo, mscs
            self.receptores, self.defensores, self.emparejamientos = rec, dfs, emp
            self.resumen = {
                "partidos": int(R.gameId.nunique()),
                "jugadas_analizadas": int(R.groupby(["gameId", "playId"]).ngroups),
                "jugadas_totales": int(len(T["plays"])),
                "rutas": int(len(R)),
                "receptores": int(R.nflId.nunique()),
                "defensores": int(R[R.defId >= 0].defId.nunique()),
                "equipos": int(R.possessionTeam.nunique()),
                "semanas": sorted(int(w) for w in R.week.unique()),
                "objetivos": int(R.objetivo.sum()),
                "emparejamiento": _calidad_emparejamiento(R),
                "motivos_exclusion": ext["motivos"],
                "segundos_carga": round(time.time() - t0, 1),
            }
            self.hallazgos = INS.generar(self)
            self.estado, self.progreso, self.mensaje = "listo", 1.0, "Listo"
        except Exception as e:  # el error se expone en /api/estado; la app no se cae
            self.error = f"{type(e).__name__}: {e}"
            self.estado = "error"
            traceback.print_exc()


motor = Motor()
