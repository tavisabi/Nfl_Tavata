"""B4: contrato HTTP. Sin entrar al contexto de TestClient no se ejecuta el arranque, así que el motor queda
'inactivo' y se puede probar el comportamiento durante la carga sin procesar el dataset."""
from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)


def test_health_responde_aunque_el_analisis_no_este_listo():
    r = cliente.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_estado_expone_progreso():
    r = cliente.get("/api/estado")
    assert r.status_code == 200 and {"estado", "progreso", "mensaje", "error"} <= set(r.json())


def test_endpoints_de_datos_responden_503_mientras_carga():
    for ruta in ["/api/resumen", "/api/receptores", "/api/defensores", "/api/emparejamientos", "/api/hallazgos",
                 "/api/jugada/2021090900/97", "/api/receptores/1"]:
        assert cliente.get(ruta).status_code == 503, ruta


def test_endpoints_estaticos_de_catalogo():
    assert len(cliente.get("/api/equipos").json()) == 32
    assert len(cliente.get("/api/partidos").json()) == 122


def test_ruta_inexistente_404():
    assert cliente.get("/api/no-existe").status_code == 404
