"""Coach Intelligence: hallazgos generados a partir de los resultados (ningún número está escrito a mano).

Cada hallazgo responde: qué ocurrió, quiénes, cuándo, qué movimiento, qué métricas, si se repite, qué aprender y
qué limitaciones tiene. Las recomendaciones son condicionales ("si ... entonces ...").
Para no confundir "estar libre por diseño" (p. ej. un RB en el flat) con "crear ventaja", las comparaciones entre
jugadores usan la DSA sobre lo esperado para su alineación (DSA-OE) y excluyen el backfield cuando corresponde.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .scs import NOMBRE_RASGO

MIN_RUTAS = 120
MIN_MAN = 40
MIN_OBJ_DEF = 15
MIN_EMP = 4
RUTEROS = ["Abierto", "Slot", "TE"]
ABIERTOS = ["Abierto", "Slot"]


def _f(x, d=1, suf=""):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "s/d"
    return f"{x:,.{d}f}{suf}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(x, d=0):
    return "s/d" if x is None or (isinstance(x, float) and np.isnan(x)) else _f(100 * x, d, "%")


def _signo(x, d=1):
    return ("+" if x >= 0 else "") + _f(x, d)


def _ejemplo(R: pd.DataFrame, filtro: pd.Series, orden: str = "dsa") -> dict | None:
    sub = R[filtro]
    if not len(sub):
        return None
    r = sub.sort_values(["objetivo", orden], ascending=False).iloc[0]
    return {"gameId": int(r.gameId), "playId": int(r.playId), "nflId": int(r.nflId)}


def generar(m) -> list[dict]:
    R, rec, dfs, emp, scs, dsa = m.rutas, m.receptores, m.defensores, m.emparejamientos, m.scs, m.dsa
    H: list[dict] = []
    nombres = {g["id"]: g["nombre"] for g in scs.grupos}
    lim_emp = ("El emparejamiento es inferido (defensor más cercano predominante durante la ruta); no es la "
               "asignación real de la defensa, que el dataset no incluye.")

    # 1. Receptores que generan ventaja de forma consistente (sobre lo esperado para su rol)
    base = rec[(rec.rutas >= MIN_RUTAS) & rec.alineacion.isin(RUTEROS)].sort_values("dsa_oe_ajustada", ascending=False)
    if len(base):
        top = base.head(5)
        r0 = top.iloc[0]
        dom = int(np.nanargmax([np.nan_to_num(r0.get(f"scs_{j}", 0)) for j in range(scs.k)]))
        H.append({
            "id": "consistencia",
            "pregunta": "¿Qué receptores generan separación con mayor consistencia?",
            "titulo": f"{r0.displayName} supera en {_f(r0.dsa_oe, 1)} puntos la DSA esperada para su rol",
            "que_ocurrio": (f"Entre receptores alineados abiertos, en slot o como TE con al menos {MIN_RUTAS} rutas, "
                            f"{r0.displayName} ({r0.equipo}, {r0.officialPosition}, alineación habitual: {r0.alineacion}) tiene la mayor "
                            f"DSA sobre lo esperado. El {_pct(r0.consistencia)} de sus rutas termina en el cuartil superior de su rol "
                            f"(lo esperado es 25%)."),
            "jugadores": [{"nflId": int(x.nflId), "nombre": x.displayName, "equipo": x.equipo, "rol": "receptor",
                           "valor": f"{_signo(x.dsa_oe_ajustada)} DSA-OE ajustada · {int(x.rutas)} rutas"} for x in top.itertuples()],
            "cuando": f"Cuando crea separación, la ventaja empieza a crecer en la mediana {_f(r0.t_creacion, 1)} s después del snap.",
            "movimiento": f"Su firma más frecuente al crear separación es «{nombres.get(dom, 's/d')}» "
                          f"({_pct(r0.get(f'scs_{dom}', np.nan))} de sus {int(r0.n_creaciones)} creaciones).",
            "metricas": [
                {"nombre": "Rutas analizadas", "valor": f"{int(r0.rutas)}"},
                {"nombre": "DSA media al pase", "valor": _f(r0.dsa_media, 1)},
                {"nombre": "DSA sobre lo esperado (ajustada por muestra)", "valor": _signo(r0.dsa_oe_ajustada)},
                {"nombre": "Separación media al pase", "valor": _f(r0.sep_pase, 2, " yd")},
                {"nombre": "Rutas con creación de separación", "valor": _pct(r0.tasa_creacion)},
            ],
            "repeticion": f"Sí: se sostiene en {int(r0.rutas)} rutas de {R[R.nflId == r0.nflId].gameId.nunique()} partidos.",
            "aprendizaje": (f"Si la defensa rival no ajusta ayuda sobre {r0.displayName}, los datos de estas 8 semanas lo señalan como "
                            f"el receptor con mayor ventaja sobre lo esperado para su rol en el momento del pase; puede considerarse "
                            f"como primera lectura en conceptos cuyo tiempo de pase sea posterior a {_f(r0.t_creacion, 1)} s."),
            "limitaciones": "La DSA mide espacio y dinámica, no capacidad de atrapar ni precisión del QB. Solo semanas 1-8 de 2021.",
            "ejemplo": _ejemplo(R, R.nflId == r0.nflId),
        })

    # 2. Movimientos que preceden la separación (SCS)
    cmp = []
    for g in scs.grupos:
        sub = R[(R.scs == g["id"]) & R.alineacion.isin(ABIERTOS)]
        ob = sub[sub.objetivo]
        cmp.append({"g": g, "n": len(sub), "gan": sub.ganancia.mean(), "oe": sub.dsa_oe.mean(),
                    "comp": ob.completo.mean() if len(ob) >= 30 else np.nan, "n_obj": len(ob),
                    "man": sub[sub.pff_passCoverageType == "Man"].ganancia.mean(),
                    "zona": sub[sub.pff_passCoverageType == "Zone"].ganancia.mean()})
    cmp = [c for c in cmp if c["n"] >= 100]
    if len(cmp) >= 2:
        cmp.sort(key=lambda c: -c["gan"])
        a, b = cmp[0], cmp[-1]
        corta = min(scs.grupos, key=lambda g: g["profundidad_mediana"])
        H.append({
            "id": "firmas",
            "pregunta": "¿Qué tipo de movimientos preceden a una separación importante?",
            "titulo": (f"En receptores abiertos, las creaciones con firma «{a['g']['nombre']}» terminan con "
                       f"{_f(a['gan'] - b['gan'], 2)} yd más de ganancia que las de «{b['g']['nombre']}»"),
            "que_ocurrio": (f"Los datos agrupan {sum(g['n'] for g in scs.grupos):,} creaciones de separación en {scs.k} firmas de movimiento "
                            f"(k-means, silhouette {_f(scs.silhouettes[scs.k], 2)}). Entre receptores abiertos o en slot, la firma "
                            f"«{a['g']['nombre']}» gana en promedio {_f(a['gan'], 2)} yd desde el punto de máxima cobertura hasta el pase, "
                            f"contra {_f(b['gan'], 2)} yd de «{b['g']['nombre']}». La firma «{corta['nombre']}» aparece sobre todo cerca de "
                            f"la línea (mediana {_f(corta['profundidad_mediana'], 1)} yd, {_f(corta['t_quiebre_mediana'], 1)} s tras el snap): "
                            f"son salidas cortas desde casi parado, compatibles con rutas al flat y salidas del backfield."),
            "jugadores": [],
            "cuando": f"«{a['g']['nombre']}»: quiebre en la mediana a {_f(a['g']['t_quiebre_mediana'], 1)} s del snap y a "
                      f"{_f(a['g']['profundidad_mediana'], 1)} yd de la línea.",
            "movimiento": "Mediana de la firma: " + "; ".join(f"{NOMBRE_RASGO[k]} {_f(v, 1)}" for k, v in a["g"]["mediana"].items()),
            "metricas": [{"nombre": c["g"]["nombre"],
                          "valor": f"+{_f(c['gan'], 2)} yd · DSA-OE {_signo(c['oe'])} · {c['n']:,} rutas · completo "
                                   f"{_pct(c['comp'])} ({c['n_obj']} pases)"} for c in cmp],
            "repeticion": f"Cada firma reúne entre {min(c['n'] for c in cmp):,} y {max(c['n'] for c in cmp):,} rutas de receptores abiertos o en slot.",
            "aprendizaje": (f"Si se busca separación tardía con receptores abiertos, la firma «{a['g']['nombre'].lower()}» es la que se "
                            f"asocia con más ganancia en estos datos (contra man {_f(a['man'], 2)} yd, contra zona {_f(a['zona'], 2)} yd); "
                            f"conviene revisar en video qué rutas la producen en el propio playbook."),
            "limitaciones": "Las firmas son grupos estadísticos sobre 5 rasgos del receptor; no son rutas del playbook "
                            "(el dataset no etiqueta el tipo de ruta). Asociación, no causalidad.",
            "ejemplo": _ejemplo(R, (R.scs == a["g"]["id"]) & R.alineacion.isin(ABIERTOS)),
        })

    # 3. Cuándo se genera la ventaja
    cre = R[R.creada & R.alineacion.isin(RUTEROS)]
    if len(cre):
        lead = cre.t_pase - cre.t_quiebre
        man = cre[cre.pff_passCoverageType == "Man"]
        zon = cre[cre.pff_passCoverageType == "Zone"]
        Rr = R[R.alineacion.isin(RUTEROS)]
        H.append({
            "id": "cuando",
            "pregunta": "¿En qué momento de la ruta suele generarse la ventaja?",
            "titulo": f"La ventaja final nace {_f(lead.median(), 1)} s antes del pase (mediana)",
            "que_ocurrio": (f"En {len(cre):,} rutas de receptores (sin backfield) que crearon separación, el punto de máxima cobertura "
                            f"ocurre en la mediana a {_f(cre.t_quiebre.median(), 1)} s del snap; el {_pct((lead <= 1.0).mean())} de las "
                            f"creaciones empieza en el último segundo antes del pase."),
            "jugadores": [],
            "cuando": f"Contra man: {_f(man.t_quiebre.median(), 1)} s tras el snap; contra zona: {_f(zon.t_quiebre.median(), 1)} s.",
            "movimiento": "Quiebre = mínimo de separación en la fase de ruta (≥ 0,5 s tras el snap) seguido de ≥ 1 yd de ganancia al pase.",
            "metricas": [
                {"nombre": "Rutas que crean separación contra man", "valor": _pct(Rr[Rr.pff_passCoverageType == 'Man'].creada.mean())},
                {"nombre": "Rutas que crean separación contra zona", "valor": _pct(Rr[Rr.pff_passCoverageType == 'Zone'].creada.mean())},
                {"nombre": "Ganancia media contra man", "valor": _f(man.ganancia.mean(), 2, " yd")},
                {"nombre": "Ganancia media contra zona", "valor": _f(zon.ganancia.mean(), 2, " yd")},
            ],
            "repeticion": "Patrón agregado de toda la liga (semanas 1-8).",
            "aprendizaje": ("Si el QB suelta el balón antes del quiebre, el receptor suele estar todavía en su punto de máxima "
                            "cobertura; contra man se observan menos creaciones de separación, por lo que conviene que los tiempos de la "
                            "progresión coincidan con el momento en que la separación empieza a crecer."),
            "limitaciones": "El quiebre se mide contra el defensor más cercano en cada instante (incluye relevos en zona).",
            "ejemplo": _ejemplo(R, R.creada & (R.pff_passCoverageType == "Man") & R.alineacion.isin(ABIERTOS)),
        })

    # 4. Lanzar a la separación que crece
    ob = R[R.objetivo & R.completo.notna()]
    banda = ob[(ob.sep_pase >= 2) & (ob.sep_pase <= 4)]
    if len(banda) > 100:
        crece, cae = banda[banda.vsep > 0], banda[banda.vsep <= 0]
        H.append({
            "id": "tendencia",
            "pregunta": "¿Importa si la separación está creciendo cuando se lanza?",
            "titulo": (f"Con 2 a 4 yd de separación, los pases se completaron {_pct(crece.completo.mean())} cuando la separación crecía "
                       f"y {_pct(cae.completo.mean())} cuando se cerraba"),
            "que_ocurrio": (f"En {len(banda):,} pases a receptores con 2 a 4 yd de separación, los completos son "
                            f"{_pct(crece.completo.mean())} si la separación crecía en el último medio segundo ({len(crece):,} pases) "
                            f"y {_pct(cae.completo.mean())} si el defensor estaba cerrando ({len(cae):,} pases)."),
            "jugadores": [],
            "cuando": "Medido en los 0,5 s previos a que el balón sale de la mano del QB.",
            "movimiento": "La velocidad de separación indica si el receptor se aleja del defensor o si el defensor está cerrando.",
            "metricas": [
                {"nombre": "Peso de la separación en la DSA", "valor": _f(dsa.pesos.get("sep", np.nan), 2)},
                {"nombre": "Peso de la velocidad de separación", "valor": _f(dsa.pesos.get("vsep", np.nan), 2) if "vsep" in dsa.pesos else "excluida"},
                {"nombre": "Persistencia (tiempo abierto)", "valor": "incluida" if "persist" in dsa.componentes
                 else "excluida: no mejora la predicción una vez conocida la separación"},
            ],
            "repeticion": "La velocidad de separación conserva su peso en validación cruzada por partido (ver Metodología).",
            "aprendizaje": ("Si dos receptores tienen un espacio parecido, en estos datos se completaron más los pases al receptor que "
                            "estaba ganando espacio que al que llevaba más tiempo abierto; es un criterio a entrenar en la lectura del QB."),
            "limitaciones": "Asociación observacional: la decisión del QB, la presión y la precisión no se controlan.",
            "ejemplo": _ejemplo(R, R.objetivo & R.sep_pase.between(2, 4) & (R.vsep > 1)),
        })

    # 5. Receptores que castigan la cobertura man
    mm = rec[(rec.rutas_man >= MIN_MAN) & rec.alineacion.isin(RUTEROS)].copy()
    if len(mm):
        mm["oe_man_aj"] = (mm.dsa_oe_man * mm.rutas_man) / (mm.rutas_man + 30)
        mm = mm.sort_values("oe_man_aj", ascending=False)
        x0 = mm.iloc[0]
        H.append({
            "id": "man",
            "pregunta": "¿Qué receptores aprovechar contra cobertura man?",
            "titulo": f"Contra man, {x0.displayName} supera lo esperado por {_f(x0.dsa_oe_man, 1)} puntos de DSA",
            "que_ocurrio": (f"Entre receptores con al menos {MIN_MAN} rutas contra cobertura man (según PFF), {x0.displayName} "
                            f"({x0.equipo}) es quien obtuvo más ventaja por encima de lo esperado para su alineación."),
            "jugadores": [{"nflId": int(x.nflId), "nombre": x.displayName, "equipo": x.equipo, "rol": "receptor",
                           "valor": f"{_signo(x.dsa_oe_man)} vs man · {int(x.rutas_man)} rutas"} for x in mm.head(5).itertuples()],
            "cuando": "Medido en el momento del pase.",
            "movimiento": "Ver la firma SCS del jugador en la pestaña Receptores.",
            "metricas": [
                {"nombre": "Rutas contra man", "valor": f"{int(x0.rutas_man)}"},
                {"nombre": "DSA-OE contra zona", "valor": _signo(x0.dsa_oe_zona) if not np.isnan(x0.dsa_oe_zona) else "s/d"},
            ],
            "repeticion": f"Promedio sobre {int(x0.rutas_man)} rutas contra man.",
            "aprendizaje": (f"Si el rival juega man en situaciones clave (p. ej. 3.er down), {x0.displayName} es candidato a recibir la "
                            f"primera lectura, sujeto a confirmarlo en video."),
            "limitaciones": "El tipo de cobertura es la etiqueta de PFF por jugada; no indica quién cubría a quién.",
            "ejemplo": _ejemplo(R, (R.nflId == x0.nflId) & (R.pff_passCoverageType == "Man")),
        })

    # 6. Defensores que recuperan más rápido tras el pase
    d = dfs[(dfs.objetivos >= MIN_OBJ_DEF) & dfs.recuperacion.notna()].sort_values("recuperacion", ascending=False)
    if len(d):
        d0 = d.iloc[0]
        liga = float(R[R.objetivo & (R.def_conf >= 0.5)].recuperacion.mean())
        H.append({
            "id": "recuperacion",
            "pregunta": "¿Qué defensores recuperan más rápidamente la posición?",
            "titulo": f"{d0.displayName} reduce la separación {_f(d0.recuperacion, 2)} yd/s tras el pase; el promedio de la liga es {_f(liga, 2)} yd/s",
            "que_ocurrio": (f"Entre defensores con al menos {MIN_OBJ_DEF} pases dirigidos al receptor que cubrían, {d0.displayName} "
                            f"({d0.equipo}, {d0.officialPosition}) es quien más reduce la separación en el medio segundo posterior al pase. "
                            f"En promedio la separación sigue creciendo tras el pase (valor negativo); él la reduce."),
            "jugadores": [{"nflId": int(x.nflId), "nombre": x.displayName, "equipo": x.equipo, "rol": "defensor",
                           "valor": f"{_f(x.recuperacion, 2)} yd/s · {int(x.objetivos)} pases"} for x in d.head(5).itertuples()],
            "cuando": "Entre el pase y 0,5 s después (último tramo disponible en el tracking).",
            "movimiento": "Reacción y aceleración hacia el receptor una vez que el balón está en el aire.",
            "metricas": [
                {"nombre": "Pases evaluados", "valor": f"{int(d0.objetivos)}"},
                {"nombre": "Separación permitida al pase", "valor": _f(d0.sep_permitida, 2, " yd")},
                {"nombre": "DSA-OE permitida (ajustada)", "valor": _signo(d0.dsa_oe_permitida_ajustada)},
            ],
            "repeticion": f"Promedio sobre {int(d0.objetivos)} pases.",
            "aprendizaje": (f"Si el plan ataca a {d0.displayName}, la ventana real de lanzamiento puede ser más corta de lo que sugiere la "
                            "separación al pase; vale la pena evaluar balones rápidos o rutas que lo alejen del balón."),
            "limitaciones": lim_emp + " Solo hay 0,5 s de tracking después del pase.",
            "ejemplo": _ejemplo(R, (R.defId == d0.nflId) & R.objetivo),
        })

    # 7. Emparejamientos vulnerables: solo cobertura man (A5) y receptores abiertos o en slot
    e = emp[(emp.rutas >= MIN_EMP) & emp.alineacion.isin(ABIERTOS)].sort_values("dsa_oe", ascending=False)
    if len(e):
        e0 = e.iloc[0]
        cal = m.resumen.get("emparejamiento", {})
        conf_man = cal.get("Man", {}).get("confianza_media", np.nan)
        conf_zona = cal.get("Zone", {}).get("confianza_media", np.nan)
        H.append({
            "id": "emparejamientos",
            "pregunta": "¿Qué emparejamientos presentan vulnerabilidades?",
            "titulo": f"En cobertura man, {e0.receptor} vs. {e0.defensor}: {_signo(e0.dsa_oe, 0)} puntos de DSA sobre lo esperado en {int(e0.rutas)} rutas",
            "que_ocurrio": (f"Solo con jugadas en cobertura man (según PFF) y receptores abiertos o en slot con al menos {MIN_EMP} rutas "
                            f"frente al mismo defensor, {e0.receptor} ({e0.equipo_of}) obtuvo la mayor ventaja sobre lo esperado frente a "
                            f"{e0.defensor} ({e0.equipo_def}, {e0.pos_defensor}). En man el defensor más cercano es más estable "
                            f"(confianza media {_pct(conf_man)}) que en zona ({_pct(conf_zona)}), por eso las parejas en zona no se usan."),
            "jugadores": [{"nflId": int(x.nflId), "nombre": f"{x.receptor} vs. {x.defensor}", "equipo": f"{x.equipo_of}-{x.equipo_def}",
                           "rol": "emparejamiento", "valor": f"{_signo(x.dsa_oe, 0)} DSA-OE · {int(x.rutas)} rutas"} for x in e.head(5).itertuples()],
            "cuando": "Medido en el momento del pase.",
            "movimiento": "Abra la jugada de ejemplo en el visor para observar el quiebre.",
            "metricas": [
                {"nombre": "DSA media al pase", "valor": _f(e0.dsa_media, 1)},
                {"nombre": "Separación media al pase", "valor": _f(e0.sep_pase, 2, " yd")},
                {"nombre": "Confianza del emparejamiento", "valor": _pct(e0.conf_media)},
                {"nombre": "Cobertura", "valor": "Man (PFF)"},
            ],
            "repeticion": f"Solo {int(e0.rutas)} rutas: es una señal para revisar en video, no una conclusión.",
            "aprendizaje": ("Si el emparejamiento se repite en el próximo partido con cobertura man, es candidato a revisarse en video "
                            "junto con la firma de movimiento dominante del receptor."),
            "limitaciones": lim_emp + " Muestras pequeñas por pareja; solo cobertura man.",
            "ejemplo": _ejemplo(R, (R.nflId == e0.nflId) & (R.defId == e0.defId) & (R.pff_passCoverageType == "Man")),
        })
    return H
