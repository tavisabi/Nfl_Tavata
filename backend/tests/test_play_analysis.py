"""Jugadas sintéticas controladas para el análisis cuadro por cuadro, DSA y casos límite.
Los datos sintéticos solo existen en las pruebas; la aplicación usa exclusivamente el dataset oficial.
"""
import numpy as np
import pandas as pd
import pytest

from backend.spi.config import ASEP_MAX, DT
from backend.spi.dsa import ModeloDSA
from backend.spi.loader import estandarizar
from backend.spi.play_analysis import (calcular, defensor_principal, resumen_receptor, ultimo_minimo,
                                       velocidad_y_aceleracion)


def jugada_sintetica(n=31, pase=21, rec_v=6.0, def_v=6.0, cambio=None, sin_pase=False, faltan=None, eventos=None,
                     defensores=None):
    """Receptor 1 corre hacia +x desde x=20 (y=20). Por defecto el defensor 10 lo persigue 1 yd detrás.
    `cambio`: frame desde el cual el defensor frena a 3 yd/s. `eventos`: {frame: evento} que reemplaza los eventos
    por defecto del balón. `defensores`: lista de (nflId, x, y) de defensores quietos en lugar del perseguidor."""
    if eventos is None:
        eventos = {1: "ball_snap"} | ({} if sin_pase else {pase: "pass_forward"})
    filas = []
    for f in range(1, n + 1):
        t = (f - 1) * DT
        xr = 20 + rec_v * t
        if not (faltan and f in faltan):
            filas.append(dict(gameId=1, playId=1, nflId=1.0, frameId=f, jerseyNumber=11, team="OFF", playDirection="right",
                              x=xr, y=20.0, s=rec_v, a=0.0, o=90.0, dir=90.0, event=None))
        if defensores is None:
            if cambio and f > cambio:
                t0 = (cambio - 1) * DT
                xd, vd = 19 + def_v * t0 + 3.0 * (t - t0), 3.0
            else:
                xd, vd = 19 + def_v * t, def_v
            filas.append(dict(gameId=1, playId=1, nflId=10.0, frameId=f, jerseyNumber=24, team="DEF", playDirection="right",
                              x=xd, y=20.0, s=vd, a=0.0, o=90.0, dir=90.0, event=None))
        else:
            for pid, xd, yd in defensores:
                filas.append(dict(gameId=1, playId=1, nflId=float(pid), frameId=f, jerseyNumber=20, team="DEF",
                                  playDirection="right", x=xd, y=yd, s=0.0, a=0.0, o=270.0, dir=270.0, event=None))
        filas.append(dict(gameId=1, playId=1, nflId=np.nan, frameId=f, jerseyNumber=np.nan, team="football",
                          playDirection="right", x=18.0, y=20.0, s=0.0, a=0.0, o=np.nan, dir=np.nan, event=eventos.get(f)))
    return pd.DataFrame(filas)


def test_persecucion_mantiene_separacion_constante():
    jc = calcular(jugada_sintetica(), [1], [10])
    assert jc is not None and jc.pase == 20
    assert np.allclose(jc.d[0][: jc.pase + 1], 1.0)
    assert np.allclose(jc.vsep[0][: jc.pase + 1], 0.0, atol=1e-6)


def test_defensor_que_frena_genera_creacion():
    jc = calcular(jugada_sintetica(cambio=11), [1], [10])
    r = resumen_receptor(jc, 0)
    # tras el frame 11 el receptor se aleja a 3 yd/s durante 1.0 s -> ~3 yd de ganancia
    assert r["creada"] is True
    assert r["ganancia"] == pytest.approx(3.0, abs=0.35)
    assert r["t_quiebre"] == pytest.approx(1.0, abs=0.15)
    assert jc.vsep[0][jc.pase] == pytest.approx(3.0, abs=0.2)
    assert defensor_principal(jc, 0) == (0, 1.0)


# --- A1: último mínimo -------------------------------------------------------------------------------------------
def test_quiebre_en_meseta_es_el_ultimo_minimo():
    assert ultimo_minimo(np.array([3.0, 1.0, 1.0, 1.0, 2.0, 4.0])) == 3
    assert ultimo_minimo(np.array([2.0, 1.0, 3.0, 1.0, 5.0])) == 3      # dos mínimos separados: el último
    assert ultimo_minimo(np.array([np.nan, 2.0, 1.0, np.nan])) == 2     # ignora NaN


# --- A2: prioridad del evento manual -----------------------------------------------------------------------------
def test_evento_manual_tiene_prioridad_sobre_el_automatico():
    ev = {1: "autoevent_ballsnap", 2: "ball_snap", 19: "autoevent_passforward", 21: "pass_forward"}
    jc = calcular(jugada_sintetica(eventos=ev), [1], [10])
    assert jc.snap == 2 and jc.snap + jc.pase == 21


def test_evento_automatico_se_usa_si_falta_el_manual():
    jc = calcular(jugada_sintetica(eventos={1: "autoevent_ballsnap", 19: "autoevent_passforward"}), [1], [10])
    assert jc.snap == 1 and jc.snap + jc.pase == 19


# --- A3: aceleración de separación ---------------------------------------------------------------------------------
def test_aceleracion_igual_a_la_pendiente_de_la_velocidad_de_separacion():
    dd = (2.0 * np.arange(30) * DT)[None, None, :]       # d' crece 2 yd/s por segundo
    V, A = velocidad_y_aceleracion(dd, np.zeros((1, 30), dtype=int))
    assert A[0, 0] == 0.0
    assert np.allclose(A[0, 9:], 2.0)                     # con historia completa (≥ 2 ventanas)


def test_aceleracion_respeta_el_recorte():
    dd = np.concatenate([np.zeros(10), np.full(10, 8.0)])[None, None, :]
    _, A = velocidad_y_aceleracion(dd, np.zeros((1, 20), dtype=int))
    assert np.nanmax(np.abs(A)) <= ASEP_MAX


def test_aceleracion_usa_la_historia_del_defensor_actual():
    """Dos defensores con d' constante (+4 y -4): al cambiar el más cercano, V pasa a -4 sin rampa y A queda en 0."""
    dd = np.stack([np.full(20, 4.0), np.full(20, -4.0)])[None]
    cercano = np.array([[0] * 10 + [1] * 10])
    V, A = velocidad_y_aceleracion(dd, cercano)
    assert V[0, 9] == pytest.approx(4.0) and V[0, 10] == pytest.approx(-4.0)
    assert np.allclose(A[0, 1:], 0.0)


def test_cambio_de_defensor_cercano_sin_saltos():
    """El receptor pasa junto a dos defensores quietos: el más cercano cambia una vez. La separación debe ser
    continua y la aceleración no debe saturarse por el relevo."""
    jc = calcular(jugada_sintetica(n=41, pase=36, defensores=[(10, 26.0, 24.0), (11, 36.0, 24.0)]), [1], [10, 11])
    d = jc.d[0][: jc.pase + 1]
    assert np.max(np.abs(np.diff(d))) <= 6.0 * DT + 1e-6        # nunca más rápido que el propio receptor
    assert resumen_receptor(jc, 0)["cambios_def"] == 1
    A = jc.asep[0][: jc.pase + 1]
    assert np.all(np.isfinite(A))
    assert np.max(np.abs(A)) < ASEP_MAX


# --- Casos límite ------------------------------------------------------------------------------------------------
def test_jugada_sin_pase_se_descarta():
    assert calcular(jugada_sintetica(sin_pase=True), [1], [10]) is None


def test_receptor_sin_tracking_se_filtra():
    jc = calcular(jugada_sintetica(), [1, 999], [10, 888])
    assert jc.receptores == [1] and jc.defensores == [10]


def test_sin_receptores_o_defensores():
    assert calcular(jugada_sintetica(), [], [10]) is None
    assert calcular(jugada_sintetica(), [1], [999]) is None


def test_frames_faltantes_quedan_como_nan():
    jc = calcular(jugada_sintetica(faltan={5, 6}), [1], [10])
    assert np.isnan(jc.d[0][4]) and np.isnan(jc.d[0][5])
    assert not np.isnan(jc.d[0][10])
    assert resumen_receptor(jc, 0)["valida"]


def test_profundidad_relativa_a_la_linea():
    jc = calcular(jugada_sintetica(), [1], [10])
    assert jc.los_x == 18.0
    assert jc.prof[0][0] == pytest.approx(2.0) and jc.prof[0][10] == pytest.approx(8.0)


def test_estandarizacion_jugada_izquierda():
    df = pd.DataFrame(dict(playDirection=["left", "right"], x=[30.0, 30.0], y=[10.0, 10.0], o=[90.0, 90.0], dir=[270.0, 270.0]))
    s = estandarizar(df)
    assert s.x.tolist() == [90.0, 30.0]
    assert s.y.tolist() == pytest.approx([43.3, 10.0])
    assert s.dir.tolist() == [90.0, 270.0] and s.o.tolist() == [270.0, 90.0]


def test_dsa_monotona_en_separacion():
    m = ModeloDSA(tau=3.0, componentes=["sep", "vsep"], media={"sep": 3, "vsep": 0}, desv={"sep": 2, "vsep": 3},
                  pesos={"sep": 0.7, "vsep": 0.3}, error_std={}, imputacion_desal=0.4,
                  puntajes_ref=np.sort(np.random.default_rng(0).normal(size=1000)), validacion={}, seleccion=[])
    bajo = m.a_escala(m.puntaje({"sep": np.array([1.0]), "vsep": np.array([0.0])}))
    alto = m.a_escala(m.puntaje({"sep": np.array([6.0]), "vsep": np.array([0.0])}))
    assert 0 <= bajo[0] < alto[0] <= 100
