"""Corre el motor completo de forma síncrona e imprime los criterios de aceptación (herramienta de validación)."""
import json
import time
import warnings

warnings.simplefilter("ignore")
from backend.main import _limpio, jugada, resumen  # noqa: E402
from backend.spi import stats as S  # noqa: E402
from backend.spi.engine import motor  # noqa: E402

t = time.time()
motor._correr()
print("estado:", motor.estado, motor.error, "| s:", round(time.time() - t, 1))
res = _limpio(resumen())
v = res["validacion"]
print("componentes:", [(c["id"], round(c["peso"], 3), round(c["error"], 3)) for c in res["componentes"]])
print("seleccion:", [(s["paso"], s["log_loss"], s["auc"]) for s in res["seleccion"]])
for k in ("baseline_intercepto", "baseline_profundidad", "baseline_sep_profundidad", "dsa_profundidad", "dsa_neutral_profundidad"):
    print(f"CV {k:28s}", v[k])
print("saturacion en el pase:", v["saturacion_pase"])
print("spearman con profundidad:", v["spearman_profundidad"])
print("calibracion:", [(c["rango"], c["n"], round(c["tasa_completo"], 3)) for c in v["calibracion"]])
print("emparejamiento:", res["emparejamiento"])
print("tau:", res["tau"], "| rutas:", res["rutas"], "| motivos:", res["motivos_exclusion"])
R = motor.rutas
print("creadas: %.3f | t_quiebre mediana creadas: %.2f" % (R.creada.mean(), R[R.creada].t_quiebre.median()))
print("spearman(dsa_oe, profundidad) por alineacion:",
      {a: round(S.spearman(g.dsa_oe.to_numpy(), g.profundidad.to_numpy()), 3) for a, g in R.groupby("alineacion")})
for g in res["scs"]["grupos"]:
    print("SCS", g["id"], g["nombre"], g["n"], g["posiciones"], round(g["ganancia_media"], 2), g["profundidad_mediana"])
print("silhouettes:", res["scs"]["silhouettes"])
print("\n### HALLAZGOS")
for h in motor.hallazgos:
    print("-", h["titulo"])
    print("   ", h["que_ocurrio"][:500])
    print("    APRENDIZAJE:", h["aprendizaje"])
    for j in h["jugadores"]:
        print("     ", j["nombre"], j["equipo"], j["valor"])
    for mt in h["metricas"]:
        print("     *", mt["nombre"], mt["valor"])
r = motor.receptores
print("\n### TOP RECEPTORES (rutas>=120, no backfield)")
print(r[(r.rutas >= 120) & (r.alineacion != "Backfield")].sort_values("dsa_oe_ajustada", ascending=False).head(10)[
    ["displayName", "equipo", "officialPosition", "alineacion", "rutas", "dsa_media", "dsa_oe", "consistencia", "sep_pase"]].round(2).to_string())
print("\n### TOP RECEPTORES (rutas>=120, todos)")
print(r[r.rutas >= 120].sort_values("dsa_media", ascending=False).head(6)[
    ["displayName", "officialPosition", "alineacion", "rutas", "dsa_media", "dsa_oe"]].round(2).to_string())
d = motor.defensores
print("\n### DEFENSORES (rutas>=100) que menos ventaja permiten")
print(d[d.rutas >= 100].sort_values("dsa_oe_permitida_ajustada").head(8)[
    ["displayName", "equipo", "officialPosition", "rutas", "dsa_oe_permitida", "sep_permitida", "objetivos", "recuperacion"]].round(2).to_string())
e = motor.emparejamientos
print("\n### EMPAREJAMIENTOS (solo man):", len(e), "parejas;", int((e.rutas >= 4).sum()), "con >= 4 rutas")
h0 = motor.hallazgos[0]["ejemplo"]
t = time.time()
j = jugada(h0["gameId"], h0["playId"])
print("\nvisor: s=", round(time.time() - t, 2), "frames", j["frames"], "snap", j["snap"], "pase", j["pase"], "jugadores", len(j["jugadores"]),
      "receptores", [(x["nombre"], x["serie"]["dsa"][j["pase"] - j["snap"]]) for x in j["receptores"]])
