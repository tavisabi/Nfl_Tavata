"""Separation Creation Signature (SCS): firma de movimiento del receptor alrededor del momento en que empieza a
crear separación (el "quiebre" = mínimo de separación en la fase de ruta, seguido de ≥ 1 yd de ganancia al pase).

Rasgos (solo del receptor, ventana [quiebre - 1.0 s, quiebre + 0.5 s], nunca después del pase):
  vel_quiebre  velocidad en el quiebre (yd/s)
  freno        máxima desaceleración en el segundo previo (yd/s²)          -> log1p (muchos ceros)
  acel_post    máxima aceleración en el medio segundo posterior (yd/s²)   -> log1p
  giro         cambio de dirección de movimiento entre -0.5 s y +0.5 s (°)
  div_orient   diferencia entre orientación del cuerpo y dirección de movimiento en el quiebre (°)

Los grupos salen de k-means sobre rasgos estandarizados; k se elige por silhouette (el mayor k a menos de 0.01 del
mejor valor, para ganar detalle sin perder separación entre grupos). Los nombres se derivan de los rasgos dominantes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import stats as S

RASGOS = ["vel_quiebre", "freno", "acel_post", "giro", "div_orient"]
LOG = {"freno", "acel_post"}
ETIQUETA = {
    ("vel_quiebre", 1): "a alta velocidad",
    ("vel_quiebre", -1): "desde baja velocidad",
    ("freno", 1): "freno marcado",
    ("freno", -1): "sin freno",
    ("acel_post", 1): "explosión posterior",
    ("acel_post", -1): "sin aceleración extra",
    ("giro", 1): "cambio de dirección fuerte",
    ("giro", -1): "trayectoria recta",
    ("div_orient", 1): "cuerpo girado respecto a la carrera",
    ("div_orient", -1): "cuerpo alineado con la carrera",
}
NOMBRE_RASGO = {
    "vel_quiebre": "Velocidad en el quiebre (yd/s)",
    "freno": "Freno previo (yd/s²)",
    "acel_post": "Aceleración posterior (yd/s²)",
    "giro": "Cambio de dirección (°)",
    "div_orient": "Cuerpo vs. carrera (°)",
}


@dataclass
class ModeloSCS:
    k: int
    media: np.ndarray
    desv: np.ndarray
    centroides: np.ndarray
    silhouettes: dict[int, float]
    grupos: list[dict]

    def asignar(self, F: pd.DataFrame) -> np.ndarray:
        Z = (_transformar(F) - self.media) / self.desv
        return np.argmin(((Z[:, None, :] - self.centroides[None]) ** 2).sum(-1), axis=1)


def _transformar(F: pd.DataFrame) -> np.ndarray:
    X = F[RASGOS].to_numpy(dtype=float).copy()
    for i, c in enumerate(RASGOS):
        if c in LOG:
            X[:, i] = np.log1p(np.maximum(X[:, i], 0))
    return X


def ajustar(rutas: pd.DataFrame, k_rango=range(2, 7)) -> tuple[ModeloSCS, pd.Series]:
    cre = rutas[rutas.creada].dropna(subset=RASGOS)
    X = _transformar(cre)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    sil, res = {}, {}
    for k in k_rango:
        et, C, _ = S.kmeans(Z, k, n_init=6)
        sil[k] = S.silhouette(Z, et)
        res[k] = (et, C)
    mejor = max(sil.values())
    k = max(kk for kk, v in sil.items() if v >= mejor - 0.01)
    et, C = res[k]
    # Ordenar grupos por ganancia media de separación (el primero es el que más separación crea).
    gan = [cre.ganancia.to_numpy()[et == j].mean() for j in range(k)]
    orden = np.argsort(gan)[::-1]
    C = C[orden]
    remap = {int(o): i for i, o in enumerate(orden)}
    et = np.array([remap[int(e)] for e in et])
    grupos = []
    for j in range(k):
        m = et == j
        sub = cre[m]
        z = C[j]
        top = np.argsort(-np.abs(z))[:2]
        partes = [ETIQUETA[(RASGOS[i], 1 if z[i] > 0 else -1)] for i in top]
        grupos.append({
            "id": j,
            "nombre": partes[0][0].upper() + partes[0][1:] + " y " + partes[1],
            "n": int(m.sum()),
            "z": {RASGOS[i]: float(z[i]) for i in range(len(RASGOS))},
            "mediana": {c: float(sub[c].median()) for c in RASGOS},
            "ganancia_media": float(sub.ganancia.mean()),
            "sep_pase_media": float(sub.sep_pase.mean()),
            "t_quiebre_mediana": float(sub.t_quiebre.median()),
            "profundidad_mediana": float(sub.profundidad.median()),
            "posiciones": {},
        })
    modelo = ModeloSCS(k, mu, sd, C, sil, grupos)
    etiquetas = pd.Series(-1, index=rutas.index, dtype=int)
    etiquetas.loc[cre.index] = et
    return modelo, etiquetas
