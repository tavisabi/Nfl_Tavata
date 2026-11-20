"""Dynamic Separation Advantage (DSA). Métrica experimental propia de SPI, no es una estadística oficial de la NFL.

1. Pesos: regresión logística completo ~ componentes + profundidad sobre pases con objetivo identificado. Un
   componente se conserva solo si mejora el log-loss en validación cruzada agrupada por partido. La profundidad es
   un control: no forma parte del puntaje.
2. Puntaje bruto: S = Σ_k w_k · z_k, con z_k estandarizado sobre todas las rutas en el momento del pase.
3. Neutralidad respecto de la profundidad (A4): S_n = S − g(prof), donde g(prof) es el puntaje medio de las rutas a esa
   profundidad (medias por bandas de cuantiles, interpoladas). Así una ruta corta no puntúa alto solo por ser corta.
4. Escala: DSA = 100 · F(S_n), con F la distribución empírica de S_n en el momento del pase de todas las rutas.
   DSA = 80 significa "más ventaja que el 80 % de las situaciones de receptores a la misma profundidad típica".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import stats as S
from .config import BANDAS_PROF, RECORTE_PCT, SEP_MAX
from .play_analysis import series_dsa

COMPONENTES = ["sep", "vsep", "asep", "desal", "persist"]
NOMBRES = {
    "sep": "Separación (yd)",
    "vsep": "Velocidad de separación (yd/s)",
    "asep": "Aceleración de separación (yd/s²)",
    "desal": "Desalineación de trayectorias (0-1)",
    "persist": "Persistencia de la ventaja (s)",
}
TOLERANCIA = 0.0005   # mejora mínima de log-loss en CV para conservar un componente


def neutralizador(prof: np.ndarray, puntaje: np.ndarray, bandas: int = BANDAS_PROF) -> tuple[np.ndarray, np.ndarray]:
    """Puntaje medio por banda de profundidad (bandas de igual tamaño por cuantiles).

    Devuelve (centros, medias) para interpolar g(prof). Fuera del rango se usa el valor del extremo.
    """
    m = ~(np.isnan(prof) | np.isnan(puntaje))
    p, s = prof[m], puntaje[m]
    cortes = np.unique(np.quantile(p, np.linspace(0, 1, bandas + 1)))
    banda = np.clip(np.searchsorted(cortes, p, side="right") - 1, 0, len(cortes) - 2)
    centros, medias = [], []
    for b in range(len(cortes) - 1):
        sel = banda == b
        if sel.any():
            centros.append(float(np.median(p[sel])))
            medias.append(float(s[sel].mean()))
    return np.array(centros), np.array(medias)


def neutralizar(puntaje: np.ndarray, prof: np.ndarray, centros: np.ndarray, medias: np.ndarray) -> np.ndarray:
    return puntaje - np.interp(prof, centros, medias)


@dataclass
class ModeloDSA:
    tau: float
    componentes: list[str]
    media: dict[str, float]
    desv: dict[str, float]
    pesos: dict[str, float]
    error_std: dict[str, float]
    imputacion_desal: float
    puntajes_ref: np.ndarray            # puntajes neutralizados ordenados (todas las rutas en el pase) para la CDF
    validacion: dict
    seleccion: list[dict]
    prof_centros: np.ndarray | None = None
    prof_medias: np.ndarray | None = None
    recortes: dict[str, tuple[float, float]] | None = None   # A3: límites p1-p99 por componente

    def puntaje(self, comp: dict[str, np.ndarray]) -> np.ndarray:
        """Puntaje bruto S (sin neutralizar)."""
        s = 0.0
        for c in self.componentes:
            v = np.asarray(comp[c], dtype=float)
            if c == "desal":
                v = np.where(np.isnan(v), self.imputacion_desal, v)
            if self.recortes and c in self.recortes:
                v = np.clip(v, *self.recortes[c])
            s = s + self.pesos[c] * (v - self.media[c]) / self.desv[c]
        return s

    def puntaje_neutral(self, comp: dict[str, np.ndarray]) -> np.ndarray:
        s = self.puntaje(comp)
        if self.prof_centros is None:
            return s
        return neutralizar(s, np.asarray(comp["prof"], dtype=float), self.prof_centros, self.prof_medias)

    def a_escala(self, puntaje: np.ndarray) -> np.ndarray:
        return 100.0 * np.searchsorted(self.puntajes_ref, puntaje, side="right") / len(self.puntajes_ref)

    def dsa_serie(self, d, vsep, asep, desal, prof) -> tuple[np.ndarray, dict[str, np.ndarray]]:
        comp = series_dsa(d, vsep, asep, desal, prof, self.tau)
        dsa = self.a_escala(self.puntaje_neutral(comp))
        dsa = np.where(np.isnan(d), np.nan, dsa)
        return dsa, comp


def componentes_en_pase(rutas: pd.DataFrame, series: dict, tau: float) -> pd.DataFrame:
    filas = []
    for k in zip(rutas.gameId, rutas.playId, rutas.nflId):
        p, M = series[k]
        f = series_dsa(*(M[i].astype(float) for i in range(5)), tau)
        filas.append([f[c][p] for c in COMPONENTES + ["prof"]])
    return pd.DataFrame(filas, columns=COMPONENTES + ["prof"], index=rutas.index)


def _pesos(Co: pd.DataFrame, C: pd.DataFrame, y: np.ndarray, activos: list[str]):
    """Ajusta la logística sobre objetivos y reexpresa los pesos en la escala de todas las rutas C."""
    X = Co[activos + ["prof"]].to_numpy()
    mu, sd = X.mean(0), X.std(0) + 1e-9
    b, se = S.logit_ajustar((X - mu) / sd, y)
    media = {c: float(C[c].mean()) for c in activos}
    desv = {c: float(C[c].std() + 1e-9) for c in activos}
    pesos = {c: float(b[i + 1] / sd[i] * desv[c]) for i, c in enumerate(activos)}
    error = {c: float(se[i + 1] / sd[i] * desv[c]) for i, c in enumerate(activos)}
    return media, desv, pesos, error, float(b[-1] / sd[-1])


def _puntaje(C: pd.DataFrame, activos, media, desv, pesos) -> np.ndarray:
    return sum(pesos[c] * (C[c].to_numpy() - media[c]) / desv[c] for c in activos)


def cv_dsa_neutral(C: pd.DataFrame, rutas: pd.DataFrame, obj_idx: pd.Index, y: np.ndarray, activos: list[str], k: int = 5) -> dict:
    """CV anidada por partido: en cada pliegue, pesos y neutralizador se estiman SOLO con partidos de entrenamiento;
    después se evalúa P(completo) ~ S_n + profundidad en los partidos de prueba."""
    g_obj = rutas.loc[obj_idx, "gameId"].to_numpy()
    preds = np.zeros(len(y))
    for test in S.pliegues_por_grupo(g_obj, k):
        juegos_test = set(g_obj[test])
        train = np.setdiff1d(np.arange(len(y)), test)
        Ctr = C[~rutas.gameId.isin(juegos_test)]
        Co_tr = C.loc[obj_idx[train]]
        media, desv, pesos, _, _ = _pesos(Co_tr, Ctr, y[train], activos)
        cen, med = neutralizador(Ctr.prof.to_numpy(), _puntaje(Ctr, activos, media, desv, pesos))
        Co = C.loc[obj_idx]
        sn = neutralizar(_puntaje(Co, activos, media, desv, pesos), Co.prof.to_numpy(), cen, med)
        X = np.column_stack([sn, Co.prof.to_numpy()])
        mu, sd = X[train].mean(0), X[train].std(0) + 1e-9
        b, _ = S.logit_ajustar((X[train] - mu) / sd, y[train])
        preds[test] = S.logit_predecir(b, (X[test] - mu) / sd)
    return {"log_loss": S.log_loss(y, preds), "brier": S.brier(y, preds), "auc": S.auc(y, preds)}


def ajustar(rutas: pd.DataFrame, series: dict) -> tuple[ModeloDSA, pd.DataFrame]:
    obj = rutas[rutas.objetivo & rutas.completo.notna()]
    tau = float(obj.sep_pase.median())
    C = componentes_en_pase(rutas, series, tau)
    imp = float(C.desal.median())
    C["desal"] = C.desal.fillna(imp)
    # A3: winsorización por percentiles en lugar de límites fijos a priori.
    recortes = {c: tuple(float(q) for q in np.nanquantile(C[c], RECORTE_PCT)) for c in ("vsep", "asep")}
    for c, (lo, hi) in recortes.items():
        C[c] = C[c].clip(lo, hi)
    Co = C.loc[obj.index]
    y = obj.completo.to_numpy()
    g = obj.gameId.to_numpy()

    def cv(cols):
        return S.cv_logit(Co[cols + ["prof"]].to_numpy(), y, g)

    # Eliminación hacia atrás: se quita el componente cuya ausencia menos empeora el log-loss, mientras empeore < TOLERANCIA.
    activos = list(COMPONENTES)
    seleccion = [{"paso": "todos", "componentes": list(activos), **cv(activos)}]
    while len(activos) > 1:
        base = cv(activos)["log_loss"]
        pruebas = {c: cv([x for x in activos if x != c])["log_loss"] - base for c in activos}
        c_min = min(pruebas, key=pruebas.get)
        if pruebas[c_min] >= TOLERANCIA:
            break
        activos.remove(c_min)
        seleccion.append({"paso": f"sin {c_min}", "componentes": list(activos), **cv(activos),
                          "delta_log_loss": pruebas[c_min]})

    media, desv, pesos, error, coef_prof = _pesos(Co, C, y, activos)
    bruto = _puntaje(C, activos, media, desv, pesos)
    cen, med = neutralizador(C.prof.to_numpy(), bruto)
    neutro = neutralizar(bruto, C.prof.to_numpy(), cen, med)
    modelo = ModeloDSA(tau, activos, media, desv, pesos, error, imp, np.sort(neutro), {}, seleccion, cen, med,
                       {c: recortes[c] for c in activos if c in recortes})
    C["dsa_bruta"] = 100.0 * np.searchsorted(np.sort(bruto), bruto, side="right") / len(bruto)
    C["dsa"] = modelo.a_escala(neutro)

    prof = C.prof.to_numpy()
    modelo.validacion = {
        "n_objetivos": int(len(obj)),
        "n_partidos": int(obj.gameId.nunique()),
        "tasa_completo": float(y.mean()),
        "pliegues": 5,
        "agrupado_por": "gameId",
        "baseline_intercepto": S.cv_logit(np.empty((len(y), 0)), y, g),
        "baseline_profundidad": S.cv_logit(Co[["prof"]].to_numpy(), y, g),
        "baseline_sep_profundidad": S.cv_logit(Co[["sep", "prof"]].to_numpy(), y, g),
        "dsa_profundidad": cv(activos),
        "dsa_neutral_profundidad": cv_dsa_neutral(C, rutas, obj.index, y, activos),
        "coef_profundidad": coef_prof,
        "spearman_profundidad": {
            "dsa_bruta": S.spearman(C.dsa_bruta.to_numpy(), prof),
            "dsa": S.spearman(C.dsa.to_numpy(), prof),
        },
        "recortes": recortes,
        "saturacion_pase": {
            **{c: float(np.mean((C[c].to_numpy() <= lo + 1e-9) | (C[c].to_numpy() >= hi - 1e-9)))
               for c, (lo, hi) in recortes.items()},
            "sep": float(np.mean(C.sep.to_numpy() >= SEP_MAX - 1e-6)),
        },
    }
    cal = pd.DataFrame({"dsa": C.loc[obj.index, "dsa"].to_numpy(), "y": y})
    cal["bin"] = np.minimum((cal.dsa // 10).astype(int), 9)
    modelo.validacion["calibracion"] = [
        {"rango": f"{int(b_) * 10}-{int(b_) * 10 + 10}", "n": int(len(gr)), "tasa_completo": float(gr.y.mean())}
        for b_, gr in cal.groupby("bin")
    ]
    return modelo, C
