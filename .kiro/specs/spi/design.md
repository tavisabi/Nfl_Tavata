# SPI — Diseño (arquitectura y metodología **tal como están implementadas**)

Estado: **descripción del estado actual tras las correcciones A1-A6 (aprobadas y verificadas)**, pendiente de la
revisión de metodología (Fase C). Los valores provienen de la ejecución completa de `backend/tools/run_engine.py`
(122 partidos, 80,2 s).

## 1. Arquitectura

```
data/ (solo lectura)
  │
  ▼
loader.py ──► targets.py (objetivo desde playDescription)
  │
  ▼
pipeline.py ──(por partido, 4 hilos)──► play_analysis.py ──► kinematics.py (funciones puras)
  │                                        │
  │  rutas (1 fila por receptor-jugada) + series por frame
  ▼
engine.py (hilo en segundo plano al arrancar)
  ├─► dsa.py      (ajuste de pesos, CV, CDF)          ──► stats.py (logística, CV, AUC, k-means, silhouette)
  ├─► scs.py      (rasgos, k-means, nombres)          ──► stats.py
  ├─► aggregates.py (receptores, defensores, parejas)
  └─► insights.py (Coach Intelligence)
  │
  ▼
main.py (FastAPI)  /health · /api/* · monta dashboard/dist si existe
  └─► viewer.py (jugada cuadro por cuadro; relee tracking con caché LRU de 6 partidos)

dashboard/ (React + Vite + Tailwind + Recharts) ── NO IMPLEMENTADO (solo la plantilla)
```

| Módulo | Responsabilidad | Pruebas |
|---|---|---|
| `config.py` | Constantes y umbrales | — |
| `loader.py` | Lectura de CSV, estandarización de dirección, caché del visor | estandarización, datos reales |
| `targets.py` | Receptor objetivo desde texto | 9 casos |
| `kinematics.py` | Velocidad, derivadas, separación y derivadas analíticas, desalineación, ventanas causales | 9 pruebas |
| `play_analysis.py` | Matrices [jugador, frame], defensor más cercano, V y A por defensor actual, resumen por ruta, posible emparejamiento | 17 pruebas |
| `pipeline.py` | Recorre 122 partidos, une contexto y objetivo | indirecta (ejecución) |
| `stats.py` | Logística IRLS, CV por grupo, AUC, Spearman, k-means++, silhouette | 4 pruebas |
| `dsa.py` | Selección de componentes, pesos, winsorización, neutralidad de profundidad, escala 0-100 | 5 pruebas |
| `scs.py` | Firmas de movimiento | ninguna (B3) |
| `aggregates.py` | Perfiles con encogimiento; parejas solo en man | 1 prueba (A5) |
| `insights.py` | 7 hallazgos | 4 pruebas (A6) |
| `engine.py` | Orquestación y estado | ejecución manual (`tools/run_engine.py`) |
| `viewer.py` | Datos del visor | ejecución manual (0,2 s por jugada) |
| `main.py` | API | **ninguna prueba HTTP** |
| `tools/*` | Auditoría y exploración (desarrollo; no los usa la app) | — |

## 2. Notación y preprocesamiento

- Frame t a 10 Hz, Δ = 0,1 s. t = 0 es el snap; P es el índice del pase.
- Snap y pase (**A2**): primer frame del evento manual (`ball_snap`, `pass_forward`); si falta, el automático
  (`autoevent_ballsnap`, `autoevent_passforward`). Cambia el snap en 2.183 jugadas y el pase en 2.706 respecto de la regla anterior.
- Coordenadas estandarizadas (ataque hacia +x). Velocidad v = s·(sin dir, cos dir).
- Profundidad del receptor: prof(t) = x_r(t) − x_balón(snap).
- Receptores R: pff_role = "Pass Route". Defensores D: pff_role = "Coverage" (los pass rushers no cuentan).

## 3. Separación y derivadas

Defensor más cercano: j*(t) = argmin_j ‖p_r(t) − p_j(t)‖.

- Separación: d(t) = min(‖p_r − p_j*‖, 10 yd)
- Velocidad instantánea respecto de cada defensor j: d′_j = (r_j·u_j)/‖r_j‖, con r_j = p_r − p_j y u_j = v_r − v_j (límite físico ±20 yd/s)
- **Velocidad de separación (A3)**: V(t) = media de d′_j en [t−4, t], con j = j*(t) (historia del defensor más cercano **actual**)
- **Aceleración de separación (A3)**: A(t) = (V_j(t) − V_j(t−5)) / 0,5 s, con el mismo j = j*(t); al inicio de la serie se usa el rezago disponible (límite físico ±40 yd/s²)
- Desalineación: δ = (1 − cos Δdir)/2 ∈ [0, 1], NaN si s_r o s_j* < 1 yd/s

Usar la historia del defensor actual elimina dos problemas de la versión anterior: los saltos falsos en los relevos
de zona (R-2) y el término geométrico (‖u‖² − d′²)/‖r‖ de d″, que saturaba el 23,8 % de las rutas en el pase (R-1).
Prueba controlada: `test_cambio_de_defensor_cercano_sin_saltos` y `test_aceleracion_usa_la_historia_del_defensor_actual`.

## 4. DSA (implementación actual)

Componentes en cada t: d(t), V(t), A(t), M(t) = media de δ en [t−4, t] y persistencia
Pers(t) = 0,1 s × (frames consecutivos hasta t con d ≥ τ), tope 3 s; τ = mediana de d(P) entre objetivos = 3,38 yd.

**Winsorización (A3)**: V y A se recortan en sus percentiles 1 y 99 en el momento del pase
(los límites se guardan en el modelo y se aplican igual a cada frame del visor). Saturación resultante: 2,0 % en V y 2,0 % en A;
la separación queda en el tope de 10 yd en el 4,9 % de las rutas.

**Ajuste de pesos.** Sobre los 7.264 pases con objetivo identificado y resultado:
P(completo) = σ(β₀ + Σ_k β_k z_k + β_prof z_prof), con z estandarizado y penalización L2 de 10⁻³·n.
La profundidad (x del receptor − línea de scrimmage, recortada a [−5, 40]) es solo un control.

**Selección.** Se parte de {d, V, A, M, Pers} y se elimina hacia atrás el componente cuya ausencia menos empeora el log-loss
en CV de 5 pliegues agrupados por partido, mientras el empeoramiento sea < 0,0005.

| Paso | Componentes | log-loss | AUC |
|---|---|---|---|
| todos | d, V, A, M, Pers | 0,5817 | 0,7319 |
| sin M | d, V, A, Pers | 0,5813 | 0,7326 |
| sin Pers | d, V, A | 0,5812 | 0,7325 |

**Puntaje bruto.** S(t) = Σ_k w_k (x_k(t) − μ_k)/σ_k, con μ y σ calculados sobre todas las rutas en P, y
w_k = β_k · σ_k / σ_k^objetivos.

| Componente | Peso w | Error estándar |
|---|---|---|
| Separación d | 0,633 | 0,032 |
| Velocidad de separación V | 0,256 | 0,032 |
| Aceleración de separación A | 0,151 | 0,028 |

**Neutralidad respecto de la profundidad (A4).** S_n(t) = S(t) − g(prof(t)), donde g es el puntaje medio de las rutas
en P por 20 bandas de profundidad de igual tamaño (cuantiles), interpolado linealmente entre las medianas de cada banda
y constante fuera del rango. La profundidad se recorta a [−5, 40] yd.

DSA(t) = 100 · F̂(S_n(t)), donde F̂ es la CDF empírica de S_n(P) sobre las 35.032 rutas.
DSA-OE = DSA(P) − media de DSA(P) en la misma alineación (Abierto/Slot/TE/Backfield/Otro) × pff_passCoverageType.

| Correlación de Spearman con la profundidad | Antes de A4 | Después de A4 |
|---|---|---|
| DSA | −0,310 | −0,013 |
| DSA-OE | — | −0,008 (por alineación: Abierto −0,036, Slot 0,020, TE 0,011, Backfield 0,060) |

**Validación (CV por partido, 5 pliegues).**

| Modelo | log-loss | Brier | AUC |
|---|---|---|---|
| Solo intercepto | 0,6585 | 0,2329 | 0,500 |
| Profundidad | 0,6274 | 0,2187 | 0,651 |
| Separación + profundidad | 0,5930 | 0,2024 | 0,721 |
| Componentes DSA (d, V, A) + profundidad | 0,5812 | 0,1973 | 0,733 |
| DSA neutral + profundidad (CV anidada: pesos y g se estiman solo con los partidos de entrenamiento) | 0,5809 | 0,1972 | 0,732 |

Los límites de la winsorización se calculan con todos los datos antes de la CV (solo percentiles; fuga mínima, documentada).
Calibración (tasa de completo por decil de DSA neutral): 30 %, 38 %, 40 %, 49 %, 56 %, 67 %, 71 %, 74 %, 77 %, 81 %.

## 5. Creación de separación, SCS y métricas complementarias

- **Quiebre (A1)** m = **último** argmin de d(t) en t ∈ [0,5 s, P] (en una meseta, su final); ganancia G = d(P) − d(m);
  hay creación si G ≥ 1 yd y P − m ≥ 0,2 s. En la ejecución, 27,5 % de las rutas crean separación; quiebre mediano 1,7 s.
- **Rasgos SCS** (solo del receptor, ventana [m − 1 s, m + 0,5 s] ∩ [0, P]): s(m); freno = max(0, −min ds/dt) antes de m;
  acel_post = max(0, max ds/dt) después de m; giro = |dir(m+5) − dir(m−5)|; div_orient = |o(m) − dir(m)|.
  Se aplica log1p a freno y acel_post, se estandariza y se corre k-means++ (6 inicios) con k ∈ {2..6}.
  Se elige el mayor k cuya silhouette esté a ≤ 0,01 de la mejor: k = 3 (silhouettes 0,333; 0,343; 0,250; 0,252; 0,268).

| Grupo (nombre automático) | n | Posiciones | Profundidad mediana | Ganancia media |
|---|---|---|---|---|
| A alta velocidad y cuerpo alineado | 5.833 | WR 70 %, TE 22 % | 10,8 yd | 2,70 yd |
| Desde baja velocidad y cuerpo girado | 1.894 | TE 36 %, WR 33 %, RB 30 % | 1,3 yd | 2,69 yd |
| Freno marcado y cambio de dirección fuerte | 1.924 | WR 61 %, TE 24 % | 7,0 yd | 2,37 yd |

- **Posible emparejamiento**: moda de j*(t) en [0,5 s, P]; confianza = fracción de frames. Se usa si la confianza es ≥ 0,5.
  **A5**: las parejas receptor-defensor solo se forman con jugadas en cobertura man (PFF). Calidad medida:

| Cobertura | Rutas | Confianza media | Cambios de defensor más cercano por ruta | Rutas con confianza ≥ 0,5 |
|---|---|---|---|---|
| Man | 9.952 | 0,885 | 0,52 | 97,5 % |
| Zone | 23.141 | 0,845 | 0,65 | 95,9 % |

  La diferencia existe pero es moderada: incluso en man, el defensor más cercano no es necesariamente el asignado.
- **Defensive Recovery**: (d_j(P) − d_j(P+k))/(0,1·k) con k = min(5, frames disponibles) ≥ 2, para el posible emparejamiento j y solo en pases dirigidos a ese receptor. Positivo = el defensor cierra. Media de la liga: −0,90 yd/s.
- **Encogimiento** de promedios: (n·x̄ + 30·μ)/(n + 30).

## 6. Clasificación de decisiones

| Decisión | Valor | Justificación |
|---|---|---|
| Frecuencia 10 Hz | dis/s = 0,100 | ✅ datos |
| Convención de ángulos | (sin, cos) | ✅ prueba con datos reales |
| Objetivo desde texto | 96,3 % | ✅ datos, ⚠ falta revisión manual |
| Pesos de la DSA | logística + CV | ✅ datos |
| Exclusión de persistencia y desalineación | CV | ✅ datos |
| Escala percentil 0-100 | CDF empírica | ✅ interpretable; ⚠ ver R-4 |
| τ = mediana de separación de objetivos | 3,38 yd | ⚠ elección razonable, sin análisis de sensibilidad |
| Evento manual con prioridad sobre el automático (A2) | — | ✅ aprobada; el manual es la etiqueta humana |
| SEP_MAX = 10 yd | 4,9 % de rutas en el tope en el pase | ⚠ a priori (B2) |
| Winsorización p1-p99 de V y A (A3) | 2,0 % / 2,0 % | ✅ aprobada |
| Ventana de 0,5 s, inicio de ruta a 0,5 s, ganancia ≥ 1 yd, velocidad mínima 1 yd/s | — | ⚠ a priori (B2) |
| Neutralidad por 20 bandas de profundidad (A4) | ρ = −0,013 | ✅ aprobada; el número de bandas es a priori |
| Parejas solo en cobertura man (A5) | — | ✅ aprobada |
| Regla de k (± 0,01) | k = 3 | ⚠ a priori; estructura débil (silhouette 0,34) |
| Confianza de emparejamiento ≥ 0,5; PRIOR = 30; mínimos de los hallazgos (120, 40, 15, 4 rutas) | — | ⚠ a priori |
| Montar `dashboard/dist` en "/" | — | ⚠ falta confirmar con el hosting |
