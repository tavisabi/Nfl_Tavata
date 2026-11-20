"""Verificaciones sobre el dataset oficial (se omiten si data/ no está disponible)."""
import numpy as np
import pytest

from backend.spi import kinematics as K
from backend.spi.config import TRACKING
from backend.spi.loader import archivos_tracking, leer_tracking, tablas
from backend.spi.play_analysis import calcular
from backend.spi.pipeline import roles_por_jugada

pytestmark = pytest.mark.skipif(not TRACKING.exists(), reason="sin data/tracking")


@pytest.fixture(scope="module")
def partido():
    gid = int(archivos_tracking()[0].stem.split("_")[1])
    return gid, leer_tracking(gid)


def test_convencion_de_angulos_contra_desplazamiento_real(partido):
    """La velocidad (s, dir) debe apuntar en la misma dirección que el desplazamiento observado de (x, y)."""
    _, t = partido
    j = t[t.nflId.notna()].sort_values(["playId", "nflId", "frameId"])
    dx = j.groupby(["playId", "nflId"]).x.diff().shift(-1)
    dy = j.groupby(["playId", "nflId"]).y.diff().shift(-1)
    vx, vy = K.velocidad(j.s.to_numpy(), j["dir"].to_numpy())
    m = (j.s > 2).to_numpy() & dx.notna().to_numpy()
    cos = (vx[m] * dx[m] + vy[m] * dy[m]) / (np.hypot(vx[m], vy[m]) * np.hypot(dx[m], dy[m]) + 1e-9)
    assert np.median(cos) > 0.95


def test_ofensiva_ataca_hacia_x_positivo_tras_estandarizar(partido):
    """Tras estandarizar, el balón avanza hacia +x entre el snap y el pase en la gran mayoría de jugadas."""
    _, t = partido
    b = t[t.nflId.isna()]
    snap = b[b.event.isin(["ball_snap", "autoevent_ballsnap"])].groupby("playId").x.first()
    qb_atras = 0
    for pid, xs in snap.items():
        bb = b[b.playId == pid]
        pase = bb[bb.event.isin(["pass_forward", "autoevent_passforward"])]
        if len(pase):
            qb_atras += int(pase.x.iloc[0] < xs)  # el QB retrocede (dropback) -> balón detrás de la línea
    assert qb_atras / len(snap) > 0.8


def test_sin_duplicados_por_llave(partido):
    _, t = partido
    assert not t.duplicated(["gameId", "playId", "nflId", "frameId"]).any()


def test_jugada_real_produce_series_coherentes(partido):
    gid, t = partido
    roles = roles_por_jugada(tablas()["pff"])
    hechas = 0
    for pid, g in t.groupby("playId"):
        rec, dfs = roles.get((gid, pid), ([], []))
        jc = calcular(g, rec, dfs)
        if jc is None:
            continue
        assert jc.d.shape[0] == len(jc.receptores)
        assert np.nanmin(jc.d) >= 0 and np.nanmax(jc.d) <= 10
        # la separación al defensor más cercano nunca supera la distancia a cualquier defensor
        assert np.all(np.nan_to_num(jc.d) <= np.nan_to_num(np.nanmin(jc.dist_todos, axis=1), nan=10) + 1e-6)
        hechas += 1
        if hechas >= 20:
            break
    assert hechas >= 10
