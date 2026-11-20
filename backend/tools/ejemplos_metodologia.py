"""Extrae los valores de jugadas reales que se citan como ejemplo en METHODOLOGY.md (solo lectura)."""
import warnings

warnings.simplefilter("ignore")
from backend.main import _limpio  # noqa: E402
from backend.spi import viewer  # noqa: E402
from backend.spi.engine import motor  # noqa: E402

motor._correr()
print("pesos:", motor.dsa.pesos, "| recortes:", motor.dsa.recortes, "| tau:", round(motor.dsa.tau, 2))
print("grupos SCS:", [(g["id"], g["nombre"]) for g in motor.scs.grupos])
for h in ("consistencia", "emparejamientos"):
    ej = next(x for x in motor.hallazgos if x["id"] == h)["ejemplo"]
    j = _limpio(viewer.jugada(motor, ej["gameId"], ej["playId"]))
    rec = next(r for r in j["receptores"] if r["nflId"] == ej["nflId"])
    s, res = rec["serie"], rec["resumen"]
    p = j["pase"] - j["snap"]
    m = round(res["t_quiebre"] * 10)
    nombres = {x["nflId"]: x["nombre"] for x in j["jugadores"]}
    print(f"\n### {h}: gameId {j['gameId']} playId {j['playId']}")
    print("descripcion:", j["meta"]["descripcion"])
    print("meta:", {k: j["meta"][k] for k in ("ofensiva", "defensa", "cobertura", "tipoCobertura", "down", "distancia", "resultado")})
    print("receptor:", rec["nombre"], "| objetivo:", rec["objetivo"], "| scs:", rec["scs"],
          "| def. principal:", nombres.get(rec["defensorPrincipal"]), "conf", rec["confianza"])
    print("resumen:", res)
    for etiqueta, t in (("snap", 0), ("snap+0.5s", 5), ("quiebre", m), ("pase", p)):
        print(f"  {etiqueta:10s} t={s['t'][t]} sep={s['sep'][t]} V={s['vsep'][t]} A={s['asep'][t]} prof={s['prof'][t]} "
              f"DSA={s['dsa'][t]} cercano={nombres.get(s['cercano'][t])}")
