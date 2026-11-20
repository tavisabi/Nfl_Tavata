"""Prueba de punta a punta contra el servidor real (uvicorn en http://localhost:8000).
Uso: arrancar `uvicorn backend.main:app --port 8000` y luego `python -m backend.tools.e2e`."""
import re
import sys
import time

import httpx

B = "http://localhost:8000"
fallos = []


def ok(cond, msg):
    print(("OK   " if cond else "FALLA") + " " + msg)
    if not cond:
        fallos.append(msg)


t0 = time.time()
while True:
    try:
        r = httpx.get(f"{B}/health", timeout=5)
        break
    except httpx.HTTPError:
        time.sleep(1)
ok(r.json() == {"status": "ok"}, f"/health responde durante la carga ({time.time() - t0:.0f} s tras arrancar)")
e = httpx.get(f"{B}/api/estado").json()
ok(e["estado"] in ("cargando", "listo"), f"/api/estado = {e['estado']} ({e['mensaje']})")
if e["estado"] == "cargando":
    ok(httpx.get(f"{B}/api/resumen").status_code == 503, "/api/resumen responde 503 mientras carga")
while httpx.get(f"{B}/api/estado").json()["estado"] == "cargando":
    time.sleep(3)
e = httpx.get(f"{B}/api/estado").json()
ok(e["estado"] == "listo", f"análisis listo en {time.time() - t0:.0f} s")

idx = httpx.get(f"{B}/")
ok(idx.status_code == 200 and "<div id=\"root\">" in idx.text, "el build del dashboard se sirve en la misma URL")
assets = re.findall(r'(?:src|href)="([^"]+)"', idx.text)
ok(all(not a.startswith("/") for a in assets), f"rutas del build relativas: {assets}")
for a in assets:
    ok(httpx.get(f"{B}/{a.lstrip('./')}").status_code == 200, f"asset {a} disponible")

res = httpx.get(f"{B}/api/resumen").json()
ok(res["partidos"] == 122 and res["rutas"] > 30000, f"resumen: {res['partidos']} partidos, {res['rutas']} rutas")
h = httpx.get(f"{B}/api/hallazgos").json()
ok(len(h) == 7 and all(x["ejemplo"] for x in h), f"{len(h)} hallazgos con jugada de ejemplo")
ok(len(httpx.get(f"{B}/api/receptores?min_rutas=80").json()) > 50, "lista de receptores")
ok(len(httpx.get(f"{B}/api/defensores?min_rutas=80").json()) > 50, "lista de defensores")
emp = httpx.get(f"{B}/api/emparejamientos?min_rutas=4").json()
ok(len(emp) > 100 and all(x["cobertura"] == "Man" for x in emp), f"{len(emp)} emparejamientos, todos en man")
rid = h[0]["jugadores"][0]["nflId"]
p = httpx.get(f"{B}/api/receptores/{rid}").json()
ok(p["perfil"]["nflId"] == rid and len(p["jugadas"]) > 0, "perfil de receptor")
lst = httpx.get(f"{B}/api/partidos/2021101707/jugadas").json()
ok(any(x["playId"] == 3837 and x["anulada"] and x["castigo"] for x in lst), "lista de jugadas marca la jugada anulada")

t = time.time()
j = httpx.get(f"{B}/api/jugada/2021101707/3837").json()
dt = time.time() - t
ok(len(j["jugadores"]) == 22 and j["receptores"], f"visor: 22 jugadores, {len(j['receptores'])} receptores ({dt:.2f} s)")
c = j["meta"]["castigos"]
ok(j["meta"]["anulada"] and [x["jugador"] for x in c] == ["Travis Kelce", "Kamren Curl"], "castigos de la jugada de Hill")
for x in c:
    print(f"       {x['falta_es']} ({x['falta']}) · {x['jugador']} {x['posicion']} ({x['equipo']}) · {x['estado']} · {x['motivo']}")
hill = next(r for r in j["receptores"] if r["nombre"] == "Tyreek Hill")
k = j["pase"] - j["snap"]
ok(abs(hill["serie"]["dsa"][k] - 78.6) < 1.5, f"DSA de Hill al pase = {hill['serie']['dsa'][k]} (METHODOLOGY: 78,6)")
t = time.time()
httpx.get(f"{B}/api/jugada/2021101707/3837")
ok(time.time() - t < 2, f"visor con caché: {time.time() - t:.2f} s (RNF-6: < 2 s)")
ok(httpx.get(f"{B}/api/jugada/2021101707/1").status_code == 404, "jugada inexistente -> 404")
print("\nRESULTADO:", "TODO OK" if not fallos else f"{len(fallos)} fallos")
sys.exit(1 if fallos else 0)
