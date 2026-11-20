"""Castigos de una jugada (decisión del equipo: las jugadas anuladas NO se excluyen de la DSA; solo se informa
que hubo castigo, quién lo cometió y por qué).

Fuente: columnas foulName1-3 / foulNFLId1-3 de plays.csv. El estado (aplicado, rechazado, compensado, anula la
jugada) se lee del texto oficial playDescription. Las 29 faltas del mapa son todas las que aparecen en el dataset.
"""
from __future__ import annotations

import math

import pandas as pd

FALTAS: dict[str, tuple[str, str]] = {
    "Defensive Pass Interference": ("Interferencia defensiva de pase", "El defensor impidió ilegalmente que el receptor pudiera atrapar el balón"),
    "Offensive Holding": ("Sujeción ofensiva", "Un jugador ofensivo sujetó ilegalmente a un defensor"),
    "Defensive Holding": ("Sujeción defensiva", "Un defensor sujetó ilegalmente a un jugador ofensivo que no tenía el balón"),
    "Roughing the Passer": ("Rudeza innecesaria contra el pasador", "Contacto ilegal o tardío contra el quarterback después de lanzar"),
    "Defensive Offside": ("Fuera de lugar defensivo", "Un defensor cruzó la línea de scrimmage antes del snap"),
    "Unnecessary Roughness": ("Rudeza innecesaria", "Contacto excesivo o fuera de la jugada"),
    "Illegal Use of Hands": ("Uso ilegal de las manos", "Contacto con las manos a la cabeza o al cuello de un rival"),
    "Offensive Pass Interference": ("Interferencia ofensiva de pase", "El receptor empujó o bloqueó ilegalmente al defensor durante el pase"),
    "Face Mask (15 Yards)": ("Máscara (15 yardas)", "Un jugador sujetó y jaló la máscara del casco de un rival"),
    "Illegal Contact": ("Contacto ilegal", "El defensor hizo contacto con el receptor más allá de 5 yardas antes del pase"),
    "Intentional Grounding": ("Lanzamiento intencional al suelo", "El quarterback lanzó sin receptor elegible cerca para evitar una captura"),
    "Taunting": ("Provocación", "Conducta provocadora hacia un rival"),
    "Ineligible Downfield Pass": ("Inelegible adelantado en pase", "Un liniero ofensivo avanzó demasiado antes de que se lanzara el pase"),
    "Illegal Formation": ("Formación ilegal", "La ofensiva no tenía el número requerido de jugadores en la línea"),
    "Unsportsmanlike Conduct": ("Conducta antideportiva", "Acción contraria al espíritu deportivo"),
    "Lowering the Head to Initiate Contact": ("Bajar la cabeza para iniciar contacto", "Contacto iniciado con la parte superior del casco"),
    "Illegal Touch Pass": ("Toque ilegal de pase", "Un jugador inelegible tocó el pase primero"),
    "Illegal Blindside Block": ("Bloqueo ilegal por el lado ciego", "Bloqueo hacia la propia línea de gol contra un rival que no lo veía"),
    "Illegal Motion": ("Movimiento ilegal", "Un jugador ofensivo se movía hacia la línea en el snap"),
    "Horse Collar Tackle": ("Tacleada por el cuello", "Derribar al rival jalándolo del interior del cuello o de las hombreras"),
    "Tripping": ("Zancadilla", "Usar la pierna para hacer caer a un rival"),
    "Disqualification": ("Descalificación", "Falta que implica la expulsión del jugador"),
    "Illegal Shift": ("Desplazamiento ilegal", "Jugadores ofensivos no se detuvieron el tiempo requerido antes del snap"),
    "Illegal Forward Pass": ("Pase adelantado ilegal", "Pase hacia adelante lanzado más allá de la línea de scrimmage o un segundo pase"),
    "Low Block": ("Bloqueo bajo", "Bloqueo ilegal por debajo de la cintura"),
    "Illegal Block Above the Waist": ("Bloqueo ilegal por encima de la cintura", "Bloqueo por la espalda por encima de la cintura"),
    "Chop Block": ("Bloqueo chop", "Un jugador bloquea bajo a un rival que ya está siendo bloqueado arriba"),
    "Illegal Substitution": ("Sustitución ilegal", "Cambio de jugadores fuera del reglamento"),
    "Clipping": ("Bloqueo por la espalda (clipping)", "Bloqueo por detrás a la altura de las piernas"),
}


def _estado(desc: str, falta: str) -> str:
    """Estado de una falta según el fragmento de la narración que la sigue."""
    if not isinstance(desc, str):
        return "aplicada"
    i = desc.find(falta)
    frag = desc[i: i + 120].lower() if i >= 0 else desc.lower()
    corte = frag.find("penalty on", len(falta))
    frag = frag[:corte] if corte > 0 else frag
    if "declined" in frag:
        return "rechazada"
    if "offsetting" in frag:
        return "compensada"
    return "aplicada"


def anulada(desc: str) -> bool:
    return isinstance(desc, str) and "no play" in desc.lower()


def castigos(fila: pd.Series, jugadores: pd.DataFrame, equipos: dict[int, str] | None = None) -> list[dict]:
    """Lista de castigos de una fila de plays.csv. `equipos`: nflId -> equipo (del tracking), opcional."""
    nom = jugadores.set_index("nflId")
    out = []
    for i in (1, 2, 3):
        falta = fila.get(f"foulName{i}")
        if not isinstance(falta, str):
            continue
        pid = fila.get(f"foulNFLId{i}")
        pid = None if pid is None or (isinstance(pid, float) and math.isnan(pid)) else int(pid)
        es, motivo = FALTAS.get(falta, (falta, "Falta registrada en el dataset sin descripción adicional"))
        out.append({
            "falta": falta, "falta_es": es, "motivo": motivo, "estado": _estado(fila.get("playDescription"), falta),
            "nflId": pid, "jugador": nom.displayName.get(pid) if pid is not None else None,
            "posicion": nom.officialPosition.get(pid) if pid is not None else None,
            "equipo": (equipos or {}).get(pid) if pid is not None else None,
        })
    return out
