"""Casos controlados de las funciones cinemáticas (datos sintéticos, solo para pruebas)."""
import numpy as np
import pytest

from backend.spi import kinematics as K


def test_distancia_basica():
    d, _, _ = K.separacion_dinamica(*map(np.array, ([3.0], [4.0], [0.0], [0.0], [0.0], [0.0],
                                                    [0.0], [0.0], [0.0], [0.0], [0.0], [0.0])))
    assert d[0] == pytest.approx(5.0)


def test_velocidad_relativa_alejandose_y_persecucion():
    # Receptor en (5,0) corre +x a 2 yd/s; defensor quieto en el origen -> d' = +2
    _, dd, _ = K.separacion_dinamica(np.array([5.0]), np.array([0.0]), np.array([2.0]), np.array([0.0]),
                                     np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1),
                                     np.zeros(1), np.zeros(1))
    assert dd[0] == pytest.approx(2.0)
    # Defensor persigue a la misma velocidad -> d' = 0
    _, dd, _ = K.separacion_dinamica(np.array([5.0]), np.array([0.0]), np.array([2.0]), np.array([0.0]),
                                     np.zeros(1), np.zeros(1), np.zeros(1), np.zeros(1), np.array([2.0]), np.zeros(1),
                                     np.zeros(1), np.zeros(1))
    assert dd[0] == pytest.approx(0.0)


def test_derivadas_coinciden_con_diferencias_finitas():
    # Trayectorias suaves con aceleración: receptor (t², 5 + t), defensor (0.5 t, 0)
    t = np.linspace(0, 2, 2001)
    px, py = t ** 2, 5 + t
    qx, qy = 0.5 * t, 0 * t
    d, dd, ddd = K.separacion_dinamica(px, py, 2 * t, np.ones_like(t), 2 * np.ones_like(t), 0 * t,
                                       qx, qy, 0.5 * np.ones_like(t), 0 * t, 0 * t, 0 * t)
    h = t[1] - t[0]
    num_dd = np.gradient(d, h)
    num_ddd = np.gradient(num_dd, h)
    assert np.allclose(dd[5:-5], num_dd[5:-5], atol=1e-4)
    assert np.allclose(ddd[5:-5], num_ddd[5:-5], atol=1e-3)


def test_desalineacion():
    s = np.array([5.0, 5.0, 5.0, 0.5])
    assert K.desalineacion(s, np.array([90.0]), s, np.array([90.0]), 1.0)[0] == pytest.approx(0.0)
    m = K.desalineacion(s, np.array([90, 90, 90, 90.0]), s, np.array([90, 270, 0, 270.0]), 1.0)
    assert m[1] == pytest.approx(1.0)
    assert m[2] == pytest.approx(0.5)
    assert np.isnan(m[3])  # casi quieto -> dirección no confiable


def test_diferencia_angular_envuelve():
    assert K.diferencia_angular(350, 10) == pytest.approx(20)
    assert K.diferencia_angular(0, 180) == pytest.approx(180)


def test_vector_unitario_convencion_ngs():
    ux, uy = K.vector_unitario(np.array([0.0, 90.0]))
    assert (ux[0], uy[0]) == pytest.approx((0.0, 1.0))   # 0° = +y
    assert (ux[1], uy[1]) == pytest.approx((1.0, 0.0))   # 90° = +x


def test_media_ventana_es_causal():
    v = np.array([0, 0, 0, 0, 0, 10.0])
    m = K.media_ventana(v, 3)
    assert m[4] == 0          # no ve el 10 que ocurre después
    assert m[5] == pytest.approx(10 / 3)


def test_media_ventana_ignora_nan():
    m = K.media_ventana(np.array([1.0, np.nan, 3.0]), 3)
    assert m[2] == pytest.approx(2.0)


def test_racha_final():
    assert K.racha_final(np.array([1, 1, 0, 1, 1, 1], bool)).tolist() == [1, 2, 0, 1, 2, 3]
