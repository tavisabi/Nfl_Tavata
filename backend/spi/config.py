"""Constantes del proyecto. Cada valor está justificado en METHODOLOGY.md o en DATA_AUDIT.md."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATA = RAIZ / "data"
TRACKING = DATA / "tracking"

FPS = 10                      # verificado: dis / s = 0.100 (DATA_AUDIT.md)
DT = 1.0 / FPS
CAMPO_LARGO = 120.0
CAMPO_ANCHO = 53.3

EVENTOS_SNAP = ("ball_snap", "autoevent_ballsnap")
EVENTOS_PASE = ("pass_forward", "autoevent_passforward")
# A2: el evento manual (etiquetado por una persona) tiene prioridad; el automático solo se usa si falta el manual.
SNAP_MANUAL, SNAP_AUTO = "ball_snap", "autoevent_ballsnap"
PASE_MANUAL, PASE_AUTO = "pass_forward", "autoevent_passforward"

PROF_MIN, PROF_MAX = -5.0, 40.0   # yd: rango de profundidad (receptor - línea de scrimmage) usado en el ajuste
BANDAS_PROF = 20                  # A4: bandas por cuantiles para estimar la DSA típica a cada profundidad

VENTANA = 5                   # 0.5 s: ventana para promediar velocidad/aceleración relativa y desalineación
INICIO_RUTA = 5               # la fase de ruta empieza 0.5 s después del snap (se ignora el cushion inicial)
SEP_MAX = 10.0                # yd: por encima de 10 yd la separación no añade información (receptor libre)
VSEP_MAX = 20.0               # yd/s: solo límite físico de seguridad (A3); el recorte real es por percentiles en la DSA
ASEP_MAX = 40.0               # yd/s²: solo límite físico de seguridad (A3)
RECORTE_PCT = (0.01, 0.99)    # A3: winsorización de V y A en los percentiles 1-99 de las rutas en el momento del pase
VEL_MIN = 1.0                 # yd/s: por debajo, la dirección de movimiento no es confiable
GANANCIA_MIN = 1.0            # yd: ganancia mínima de separación para considerar que hubo "creación"
PERSIST_MAX = 3.0             # s: recorte de persistencia
