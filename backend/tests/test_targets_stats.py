import numpy as np
import pytest

from backend.spi import stats as S
from backend.spi.targets import emparejar, texto_objetivo

CANDIDATOS = [(1, "Chris Godwin"), (2, "Mike Evans"), (3, "Amon-Ra St. Brown"), (4, "Odell Beckham Jr."),
              (5, "Tyler Johnson"), (6, "Diontae Johnson")]


@pytest.mark.parametrize("desc,esperado", [
    ("(13:33) (Shotgun) T.Brady pass incomplete deep right to C.Godwin.", 1),
    ("(13:18) T.Brady pass deep left to M.Evans pushed ob at DAL 30 for 28 yards (A.Winfield).", 2),
    ("J.Goff pass short middle to A.St. Brown to DET 40 for 6 yards (X.Y).", 3),
    ("M.Stafford pass short right to O.Beckham Jr. to LA 20 for 5 yards.", 4),
    ("B.Roethlisberger pass short left to D.Johnson to PIT 30 for 4 yards.", 6),
    ("T.Brady pass short middle intended for M.Evans INTERCEPTED by J.Lewis at TB 40. J.Lewis to TB 20.", 2),
    ("(1:16) (Shotgun) D.Prescott pass incomplete short right.", None),
    ("(:39) (Shotgun) J.Allen pass incomplete short right. Thrown away.", None),
])
def test_objetivo_desde_descripcion(desc, esperado):
    assert emparejar(texto_objetivo(desc), CANDIDATOS) == esperado


def test_objetivo_no_es_otro_jugador_de_la_narracion():
    # El tackleador (no es Pass Route) no debe confundirse con el objetivo
    assert emparejar(texto_objetivo("X.Y pass short left to C.Godwin to TB 30 for 3 yards (M.Evans)."), CANDIDATOS) == 1


def test_logit_recupera_coeficientes():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(20000, 2))
    y = (rng.random(20000) < S.sigmoide(0.5 + 1.2 * X[:, 0] - 0.8 * X[:, 1])).astype(float)
    b, se = S.logit_ajustar(X, y, l2=0)
    assert b == pytest.approx([0.5, 1.2, -0.8], abs=0.06)
    assert np.all(se > 0)


def test_auc_casos_extremos():
    y = np.array([0, 0, 1, 1.0])
    assert S.auc(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert S.auc(y, np.array([0.9, 0.8, 0.2, 0.1])) == 0.0
    assert S.auc(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.5


def test_pliegues_no_mezclan_partidos():
    g = np.repeat(np.arange(20), 5)
    pl = S.pliegues_por_grupo(g, 5)
    vistos = [set(g[i]) for i in pl]
    for i in range(5):
        for j in range(i + 1, 5):
            assert not (vistos[i] & vistos[j])
    assert sum(len(i) for i in pl) == len(g)


def test_kmeans_separa_grupos_evidentes():
    rng = np.random.default_rng(1)
    X = np.vstack([rng.normal(0, 0.2, (100, 2)), rng.normal(5, 0.2, (100, 2))])
    et, C, _ = S.kmeans(X, 2, n_init=3)
    assert len(set(et[:100])) == 1 and len(set(et[100:])) == 1 and et[0] != et[150]
    assert S.silhouette(X, et) > 0.8
