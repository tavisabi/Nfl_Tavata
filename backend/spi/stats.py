"""Estadística y aprendizaje en numpy puro (el stack no incluye scikit-learn ni scipy)."""
from __future__ import annotations

import numpy as np


def sigmoide(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def logit_ajustar(X: np.ndarray, y: np.ndarray, l2: float = 1e-3, iters: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Regresión logística por Newton-Raphson (IRLS) con penalización L2 leve (sin penalizar el intercepto).

    Devuelve (beta, error_estándar), con beta[0] = intercepto.
    """
    n, k = X.shape
    A = np.column_stack([np.ones(n), X])
    b = np.zeros(k + 1)
    P = np.eye(k + 1) * l2 * n
    P[0, 0] = 0.0
    for _ in range(iters):
        p = sigmoide(A @ b)
        g = A.T @ (y - p) - P @ b
        H = (A * (p * (1 - p))[:, None]).T @ A + P
        paso = np.linalg.solve(H, g)
        b += paso
        if np.max(np.abs(paso)) < 1e-8:
            break
    p = sigmoide(A @ b)
    H = (A * (p * (1 - p))[:, None]).T @ A + P
    se = np.sqrt(np.diag(np.linalg.inv(H)))
    return b, se


def logit_predecir(b: np.ndarray, X: np.ndarray) -> np.ndarray:
    return sigmoide(b[0] + X @ b[1:])


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def auc(y: np.ndarray, p: np.ndarray) -> float:
    """AUC por rangos (Mann-Whitney), con empates promediados."""
    orden = np.argsort(p, kind="mergesort")
    ps = p[orden]
    rangos = np.empty(len(p))
    i = 0
    while i < len(ps):
        j = i
        while j + 1 < len(ps) and ps[j + 1] == ps[i]:
            j += 1
        rangos[orden[i: j + 1]] = (i + j) / 2 + 1
        i = j + 1
    n1 = y.sum()
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((rangos[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def rangos(x: np.ndarray) -> np.ndarray:
    """Rangos promedio (empates promediados). Los NaN deben filtrarse antes."""
    orden = np.argsort(x, kind="mergesort")
    xs = x[orden]
    r = np.empty(len(x))
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[i]:
            j += 1
        r[orden[i: j + 1]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 3:
        return float("nan")
    return float(np.corrcoef(rangos(x[m]), rangos(y[m]))[0, 1])


def pliegues_por_grupo(grupos: np.ndarray, k: int, semilla: int = 7) -> list[np.ndarray]:
    """Asigna grupos completos (p. ej. partidos) a k pliegues: ningún partido aparece en train y test a la vez."""
    u = np.unique(grupos)
    rng = np.random.default_rng(semilla)
    rng.shuffle(u)
    asign = {g: i % k for i, g in enumerate(u)}
    f = np.array([asign[g] for g in grupos])
    return [np.where(f == i)[0] for i in range(k)]


def cv_logit(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, k: int = 5) -> dict:
    """Validación cruzada agrupada. X puede tener 0 columnas (modelo solo-intercepto = baseline)."""
    preds = np.zeros(len(y))
    for test in pliegues_por_grupo(grupos, k):
        train = np.setdiff1d(np.arange(len(y)), test)
        if X.shape[1] == 0:
            preds[test] = y[train].mean()
            continue
        mu, sd = X[train].mean(0), X[train].std(0) + 1e-9
        b, _ = logit_ajustar((X[train] - mu) / sd, y[train])
        preds[test] = logit_predecir(b, (X[test] - mu) / sd)
    return {"log_loss": log_loss(y, preds), "brier": brier(y, preds), "auc": auc(y, preds) if X.shape[1] else 0.5}


def kmeans(X: np.ndarray, k: int, n_init: int = 10, iters: int = 100, semilla: int = 11) -> tuple[np.ndarray, np.ndarray, float]:
    """k-means con inicialización k-means++. Devuelve (etiquetas, centroides, inercia)."""
    rng = np.random.default_rng(semilla)
    mejor = (None, None, np.inf)
    for _ in range(n_init):
        c = [X[rng.integers(len(X))]]
        for _ in range(1, k):
            d2 = np.min(((X[:, None, :] - np.array(c)[None]) ** 2).sum(-1), axis=1)
            c.append(X[rng.choice(len(X), p=d2 / d2.sum())])
        C = np.array(c)
        for _ in range(iters):
            et = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(-1), axis=1)
            nuevo = np.array([X[et == j].mean(0) if np.any(et == j) else C[j] for j in range(k)])
            if np.allclose(nuevo, C):
                break
            C = nuevo
        inercia = float(((X - C[et]) ** 2).sum())
        if inercia < mejor[2]:
            mejor = (et, C, inercia)
    return mejor


def silhouette(X: np.ndarray, et: np.ndarray, muestra: int = 2500, semilla: int = 3) -> float:
    rng = np.random.default_rng(semilla)
    idx = rng.choice(len(X), size=min(muestra, len(X)), replace=False)
    Xs, es = X[idx], et[idx]
    D = np.sqrt(((Xs[:, None, :] - Xs[None]) ** 2).sum(-1))
    s = []
    for i in range(len(Xs)):
        propio = es == es[i]
        if propio.sum() <= 1:
            continue
        a = D[i, propio].sum() / (propio.sum() - 1)
        b = min(D[i, es == j].mean() for j in np.unique(es) if j != es[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))
