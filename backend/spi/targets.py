"""Receptor objetivo del pase. El dataset no trae una columna de objetivo; se recupera del texto oficial
`playDescription` ("... pass short right to C.Godwin ..." / "... intended for X INTERCEPTED ...") y se cruza con
los jugadores con pff_role == "Pass Route" de esa misma jugada. Solo se acepta si el cruce es único.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

_SUFIJOS = {"jr", "sr", "ii", "iii", "iv", "v"}
_PATRON = re.compile(r"\bpass(?:ed)?\b(.*?)(?:\bintended for\b|\bto\b)\s+(.{2,40})", re.IGNORECASE)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def _apellido(nombre: str) -> str:
    partes = [p for p in nombre.replace(".", " ").split() if _norm(p) not in _SUFIJOS]
    return _norm(partes[-1]) if partes else ""


def texto_objetivo(desc: str) -> str | None:
    """Fragmento del texto que nombra al objetivo, o None si el pase no tiene destinatario."""
    if not isinstance(desc, str):
        return None
    m = _PATRON.search(desc)
    return m.group(2) if m else None


def emparejar(fragmento: str | None, candidatos: list[tuple[int, str]]) -> int | None:
    """Devuelve el nflId del candidato (Pass Route de la jugada) nombrado en el fragmento, si es único."""
    if not fragmento:
        return None
    # El nombre abreviado ("C.Godwin", "A.St. Brown") va al inicio del fragmento; se corta antes de la
    # continuación de la narración. El apellido debe aparecer en los primeros caracteres (tras las iniciales).
    corte = re.split(r"\s(?:to|for|ran|pushed|at|and)\s|\s\(|,|;", fragmento, maxsplit=1)[0]
    frag_n = _norm(corte)
    if not frag_n:
        return None
    inicial = frag_n[:1]
    hallados = []
    for pid, n in candidatos:
        ap = _apellido(n)
        i = frag_n.find(ap) if ap else -1
        if 0 <= i <= 8:
            hallados.append((i, pid, n))
    if not hallados:
        return None
    mejor = min(h[0] for h in hallados)
    hallados = [h for h in hallados if h[0] == mejor]
    if len(hallados) > 1:
        hallados = [h for h in hallados if _norm(h[2])[:1] == inicial]
    return int(hallados[0][1]) if len(hallados) == 1 else None


def objetivos(plays: pd.DataFrame, pff: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """Tabla (gameId, playId, targetId) para los pases C / I / IN con objetivo identificado de forma única."""
    nombres = players.set_index("nflId").displayName
    rutas = pff[pff.pff_role == "Pass Route"][["gameId", "playId", "nflId"]]
    cand = {k: [(int(i), nombres.get(i, "")) for i in g.nflId] for k, g in rutas.groupby(["gameId", "playId"])}
    filas = []
    for r in plays[plays.passResult.isin(["C", "I", "IN"])].itertuples(index=False):
        pid = emparejar(texto_objetivo(r.playDescription), cand.get((r.gameId, r.playId), []))
        if pid is not None:
            filas.append((r.gameId, r.playId, pid))
    return pd.DataFrame(filas, columns=["gameId", "playId", "targetId"])
