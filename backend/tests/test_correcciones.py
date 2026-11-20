"""Pruebas de las correcciones A4 (neutralidad de profundidad), A5 (emparejamientos solo man) y A6 (hallazgos).
Usan datos sintéticos generados aquí; nunca se presentan como datos oficiales.
"""
import re
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from backend.spi import aggregates as AG
from backend.spi import insights as INS
from backend.spi import stats as S
from backend.spi.dsa import ModeloDSA, neutralizador, neutralizar


# --- A4 --------------------------------------------------------------------------------------------------------------
def test_neutralizador_elimina_la_dependencia_de_la_profundidad():
    rng = np.random.default_rng(0)
    prof = rng.uniform(-3, 35, 20000)
    puntaje = -0.12 * prof + 0.002 * prof ** 2 + rng.normal(0, 0.5, prof.size)   # relación no lineal con la profundidad
    assert abs(S.spearman(puntaje, prof)) > 0.3
    cen, med = neutralizador(prof, puntaje, bandas=20)
    neutro = neutralizar(puntaje, prof, cen, med)
    assert abs(S.spearman(neutro, prof)) < 0.05


def test_neutralizador_conserva_el_orden_a_igual_profundidad():
    prof = np.repeat([0.0, 10.0, 20.0], 100)
    puntaje = np.tile(np.linspace(-1, 1, 100), 3) + prof * 0.1
    cen, med = neutralizador(prof, puntaje, bandas=3)
    neutro = neutralizar(puntaje, prof, cen, med)
    assert np.all(np.diff(neutro[:100]) > 0)
    assert np.allclose(neutro[:100], neutro[100:200])     # misma posición relativa = mismo puntaje neutral


def test_dsa_serie_usa_el_puntaje_neutral():
    cen, med = np.array([0.0, 20.0]), np.array([1.0, -1.0])
    m = ModeloDSA(tau=3.0, componentes=["sep"], media={"sep": 0.0}, desv={"sep": 1.0}, pesos={"sep": 1.0},
                  error_std={}, imputacion_desal=0.4, puntajes_ref=np.linspace(-3, 3, 601), validacion={},
                  seleccion=[], prof_centros=cen, prof_medias=med)
    corto = m.a_escala(m.puntaje_neutral({"sep": np.array([2.0]), "prof": np.array([0.0])}))
    largo = m.a_escala(m.puntaje_neutral({"sep": np.array([2.0]), "prof": np.array([20.0])}))
    assert largo[0] > corto[0]     # la misma separación vale más donde lo típico es menos separación


# --- A3: recorte por percentiles ---------------------------------------------------------------------------------
def test_puntaje_aplica_los_recortes_del_modelo():
    m = ModeloDSA(tau=3.0, componentes=["vsep"], media={"vsep": 0.0}, desv={"vsep": 1.0}, pesos={"vsep": 1.0},
                  error_std={}, imputacion_desal=0.4, puntajes_ref=np.array([0.0]), validacion={}, seleccion=[],
                  recortes={"vsep": (-2.0, 2.0)})
    assert m.puntaje({"vsep": np.array([9.0])})[0] == m.puntaje({"vsep": np.array([2.0])})[0] == 2.0
    assert m.puntaje({"vsep": np.array([-9.0])})[0] == -2.0


# --- Datos sintéticos para A5/A6 ----------------------------------------------------------------------------------
def rutas_sinteticas(semilla=1, escala_ganancia=1.0):
    rng = np.random.default_rng(semilla)
    n_rec, por_rec = 8, 200
    filas = []
    for r in range(n_rec):
        for k in range(por_rec):
            obj = rng.random() < 0.3
            filas.append(dict(
                gameId=1000 + k % 10, playId=k, nflId=r + 1, defId=101 + (r + k) % 4, def_conf=0.8,
                possessionTeam=f"O{r % 2}", defensiveTeam=f"D{(r + k) % 3}", alineacion=["Abierto", "Slot"][r % 2],
                pff_passCoverageType=["Man", "Zone"][k % 2], objetivo=obj,
                completo=float(rng.random() < 0.6) if obj else np.nan,
                dsa=rng.uniform(0, 100), dsa_oe=rng.normal(r - 3.5, 10), alta_rol=rng.random() < 0.25,
                sep_pase=rng.uniform(1, 5), persist=rng.uniform(0, 2), vsep=rng.normal(0, 2),
                creada=rng.random() < 0.4, t_pase=2.8, t_quiebre=rng.uniform(0.5, 2.5),
                ganancia=escala_ganancia * rng.uniform(1, 4), scs=int(rng.integers(-1, 3)),
                def_sep_pase=rng.uniform(1, 6), recuperacion=rng.normal(0, 1),
            ))
    return pd.DataFrame(filas)


def jugadores_sinteticos():
    ids = list(range(1, 9)) + [101, 102, 103, 104]
    return pd.DataFrame({"nflId": ids, "displayName": [f"Jugador {i}" for i in ids],
                         "officialPosition": ["WR"] * 8 + ["CB"] * 4})


def motor_sintetico(R):
    J = jugadores_sinteticos()
    grupos = [{"id": j, "nombre": n, "n": int((R.scs == j).sum()), "profundidad_mediana": p, "t_quiebre_mediana": 1.5,
               "mediana": {"vel_quiebre": 5, "freno": 1, "acel_post": 1, "giro": 30, "div_orient": 20},
               "ganancia_media": float(R[R.scs == j].ganancia.mean())}
              for j, (n, p) in enumerate([("Grupo uno", 8.0), ("Grupo dos", 1.0), ("Grupo tres", 6.0)])]
    return SimpleNamespace(
        rutas=R, receptores=AG.receptores(R, J, 3), defensores=AG.defensores(R, J), emparejamientos=AG.emparejamientos(R, J),
        scs=SimpleNamespace(k=3, silhouettes={3: 0.34}, grupos=grupos),
        dsa=SimpleNamespace(pesos={"sep": 0.6, "vsep": 0.3}, componentes=["sep", "vsep"], tau=3.4),
        resumen={"emparejamiento": {"Man": {"confianza_media": 0.9}, "Zone": {"confianza_media": 0.7}}},
    )


# --- A5 --------------------------------------------------------------------------------------------------------------
def test_emparejamientos_solo_usan_cobertura_man():
    R = rutas_sinteticas()
    emp = AG.emparejamientos(R, jugadores_sinteticos())
    esperado = R[(R.pff_passCoverageType == "Man") & (R.def_conf >= AG.CONF_MIN)].groupby(["nflId", "defId"]).size()
    assert emp.set_index(["nflId", "defId"]).rutas.sort_index().tolist() == esperado.sort_index().tolist()
    assert set(emp.cobertura) == {"Man"}


# --- A6 --------------------------------------------------------------------------------------------------------------
CAMPOS = ["que_ocurrio", "jugadores", "cuando", "movimiento", "metricas", "repeticion", "aprendizaje", "limitaciones"]
CAUSALES = re.compile(r"\b(causa|causan|provoca|provocan|garantiza|garantizan|asegura|aseguran)\b", re.IGNORECASE)


@pytest.fixture(scope="module")
def hallazgos():
    return INS.generar(motor_sintetico(rutas_sinteticas()))


def test_hallazgos_tienen_los_ocho_campos(hallazgos):
    assert len(hallazgos) == 7
    for h in hallazgos:
        for c in CAMPOS + ["titulo", "pregunta"]:
            assert c in h, (h["id"], c)
        for c in ["que_ocurrio", "cuando", "movimiento", "repeticion", "aprendizaje", "limitaciones", "titulo"]:
            assert isinstance(h[c], str) and h[c].strip(), (h["id"], c)
        assert h["metricas"], h["id"]


def test_recomendaciones_condicionales_y_sin_lenguaje_causal(hallazgos):
    for h in hallazgos:
        assert h["aprendizaje"].startswith("Si "), h["id"]
        for c in ["titulo", "que_ocurrio", "aprendizaje"]:
            assert not CAUSALES.search(h[c]), (h["id"], c, h[c])


def test_cifras_salen_de_los_datos(hallazgos):
    R = rutas_sinteticas()
    ob = R[R.objetivo & R.completo.notna()]
    banda = ob[(ob.sep_pase >= 2) & (ob.sep_pase <= 4)]
    tasa = INS._pct(banda[banda.vsep > 0].completo.mean())
    h = next(x for x in hallazgos if x["id"] == "tendencia")
    assert tasa in h["titulo"]
    # Si cambian los datos, cambian las cifras
    otros = INS.generar(motor_sintetico(rutas_sinteticas(escala_ganancia=2.0)))
    f1 = next(x for x in hallazgos if x["id"] == "firmas")["titulo"]
    f2 = next(x for x in otros if x["id"] == "firmas")["titulo"]
    assert f1 != f2


def test_hallazgo_de_emparejamientos_declara_cobertura_man(hallazgos):
    h = next(x for x in hallazgos if x["id"] == "emparejamientos")
    assert "man" in h["titulo"].lower() and "solo cobertura man" in h["limitaciones"].lower()
