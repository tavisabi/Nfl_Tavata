import pandas as pd
import pytest

from backend.spi.config import DATA
from backend.spi.penalties import FALTAS, anulada, castigos

JUG = pd.DataFrame({"nflId": [40011, 52624], "displayName": ["Travis Kelce", "Kamren Curl"], "officialPosition": ["TE", "FS"]})


def test_jugada_con_castigos_compensados():
    fila = pd.Series({
        "playDescription": "(6:40) P.Mahomes pass short middle to T.Hill ran ob at WAS 30 for 19 yards (W.Jackson). Penalty on "
                           "KC-T.Kelce, Low Block, offsetting, enforced at WAS 49 - No Play. Penalty on WAS-K.Curl, Defensive Holding, offsetting.",
        "foulName1": "Low Block", "foulNFLId1": 40011.0, "foulName2": "Defensive Holding", "foulNFLId2": 52624.0,
        "foulName3": float("nan"), "foulNFLId3": float("nan"),
    })
    c = castigos(fila, JUG, {40011: "KC", 52624: "WAS"})
    assert [x["jugador"] for x in c] == ["Travis Kelce", "Kamren Curl"]
    assert [x["equipo"] for x in c] == ["KC", "WAS"]
    assert [x["estado"] for x in c] == ["compensada", "compensada"]
    assert c[0]["falta_es"] == "Bloqueo bajo" and c[0]["motivo"]
    assert anulada(fila.playDescription)


def test_falta_rechazada_y_jugada_sin_castigo():
    fila = pd.Series({"playDescription": "T.Brady pass to A.Brown for 27 yards. Penalty on DAL-T.Diggs, Illegal Use of Hands, declined.",
                      "foulName1": "Illegal Use of Hands", "foulNFLId1": float("nan")})
    c = castigos(fila, JUG)
    assert c[0]["estado"] == "rechazada" and c[0]["jugador"] is None
    assert not anulada(fila.playDescription)
    assert castigos(pd.Series({"playDescription": "x", "foulName1": float("nan")}), JUG) == []


@pytest.mark.skipif(not (DATA / "plays.csv").exists(), reason="sin datos")
def test_todas_las_faltas_del_dataset_tienen_traduccion():
    p = pd.read_csv(DATA / "plays.csv")
    faltas = set(pd.concat([p[f"foulName{i}"] for i in (1, 2, 3)]).dropna())
    assert faltas <= set(FALTAS), faltas - set(FALTAS)
