# Metodología de SPI · Situational Player Intelligence

SPI mide cómo un receptor gana espacio frente a la defensa antes del pase, en qué momento lo gana y con qué tipo de
movimiento. Sus dos métricas, **DSA** (Dynamic Separation Advantage) y **SCS** (Separation Creation Signature), son
**experimentales y propias del proyecto**: no son estadísticas oficiales de la NFL.

Todas las cifras de este documento salen del dataset del repositorio `ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data`
(122 partidos, semanas 1 a 8 de 2021, solo jugadas de pase) y se reproducen con los scripts de la sección 12.
La auditoría de los datos está en `DATA_AUDIT.md`.

---

## 1. Unidad de análisis

Una **ruta** es un receptor (pff_role = "Pass Route") en una jugada. Se analizan 35.032 rutas de 7.583 jugadas. Las otras
974 jugadas no tienen evento de pase (capturas y scrambles) o de snap, y se excluyen.

Los defensores considerados son los de pff_role = "Coverage". Los pass rushers no cuentan para la separación.

## 2. Preprocesamiento

| Paso | Regla | Motivo |
|---|---|---|
| Frecuencia | 10 Hz, Δ = 0,1 s | `dis / s` = 0,100 en el tracking |
| Dirección | Si `playDirection = left`: x' = 120 − x, y' = 53,3 − y, ángulos + 180° | Todas las ofensivas atacan hacia +x y las rutas son comparables |
| Velocidad | v = s · (sin dir, cos dir) | Convención NGS (0° = +y, sentido horario), verificada con el desplazamiento real |
| Snap y pase | Primer frame del evento manual (`ball_snap`, `pass_forward`); si falta, el automático | El manual es la etiqueta humana; cambia 2.183 snaps y 2.706 pases respecto de tomar el primero de los dos |
| Profundidad | prof(t) = x_receptor(t) − x_balón(snap), recortada a [−5, 40] yd | Distancia a la línea de scrimmage |
| Faltantes | Frames ausentes quedan como NaN; no se interpola | No inventar posiciones |

**Fases.** Pre-pase [snap, pase], momento del pase y post-pase (pase, fin]. El tracking termina 0,5 s después del
pase, así que el post-pase solo se usa para Defensive Recovery. **Ninguna variable explicativa usa información posterior
al instante que describe** (todas las ventanas son causales).

## 3. Variables cuadro por cuadro

Para el receptor r en el frame t:

- **Defensor más cercano:** j*(t) = argmin_j ‖p_r(t) − p_j(t)‖.
- **Separación:** d(t) = min(‖p_r − p_j*‖, 10 yd). Por encima de 10 yd el receptor está libre y más distancia no agrega información. Solo el 4,9 % de las rutas llega al tope en el momento del pase.
- **Velocidad de separación instantánea** respecto de cada defensor j: d′_j = (r_j · u_j) / ‖r_j‖, con r_j = p_r − p_j y u_j = v_r − v_j. Es la derivada exacta de la distancia: positiva si el receptor se aleja.
- **Velocidad de separación V(t):** media de d′_j en los últimos 0,5 s [t − 4, t], con j = j*(t).
- **Aceleración de separación A(t):** (V_j(t) − V_j(t − 5)) / 0,5 s, con el mismo j = j*(t).
- **Desalineación** δ = (1 − cos Δdir) / 2 ∈ [0, 1] entre las trayectorias del receptor y de j*. No se calcula si alguno va a menos de 1 yd/s.
- **Persistencia** Pers(t) = segundos consecutivos hasta t con d ≥ τ (tope 3 s), con τ = 3,38 yd, la mediana de la separación al pase de los receptores objetivo.

**Por qué V y A usan la historia del defensor actual.** En zona, el defensor más cercano cambia (0,65 veces por ruta en
promedio). Si V se calculara mezclando defensores, cada relevo crearía un salto falso. Con la historia del defensor que
está más cerca *ahora*, un relevo no altera la serie (prueba `test_aceleracion_usa_la_historia_del_defensor_actual`).
La primera versión usaba la segunda derivada analítica de la distancia. Esa fórmula incluye un término geométrico que
saturaba el 23,8 % de las rutas, así que se reemplazó.

## 4. Dynamic Separation Advantage (DSA)

### 4.1 Qué pregunta responde

¿Qué tan favorable es la situación espacial y dinámica del receptor en este instante, comparada con la de cualquier
receptor a la misma profundidad en el momento del pase?

### 4.2 Cómo se eligen los componentes y sus pesos

Los pesos no se fijan a mano: los estima una regresión logística que relaciona el resultado del pase con la situación del receptor.

1. **Muestra:** los 7.264 pases con receptor objetivo identificado y resultado (63,2 % completos). El objetivo se
   recupera del texto `playDescription`. Se identificó en el 96,3 % de los pases, y una revisión manual de 50 casos dio 50 correctos.
2. **Modelo:** P(completo) = σ(β₀ + Σ_k β_k z_k + β_prof · z_prof), con penalización L2 leve. La profundidad entra
   **solo como control**, porque los pases largos se completan menos, y no forma parte del puntaje.
3. **Selección:** se parte de los cinco candidatos {d, V, A, δ, Pers}. Se elimina hacia atrás el componente cuya ausencia
   empeora menos el log-loss en validación cruzada de 5 pliegues **agrupados por partido**, mientras ese empeoramiento sea menor que 0,0005.

| Paso | Componentes | log-loss (CV) | AUC (CV) |
|---|---|---|---|
| Inicio | d, V, A, δ, Pers | 0,5817 | 0,7319 |
| Sin desalineación | d, V, A, Pers | 0,5813 | 0,7326 |
| Sin persistencia | d, V, A | 0,5812 | 0,7325 |

La desalineación y la persistencia **se probaron y se descartaron**: no agregan información una vez conocidas la
separación y su velocidad (correlación de Spearman persistencia-separación = 0,85). Se siguen reportando como datos
descriptivos, pero no entran en la DSA.

4. **Winsorización:** V y A se recortan en sus percentiles 1 y 99 en el momento del pase: V ∈ [−11,92; 8,11] yd/s y
   A ∈ [−9,80; 20,33] yd/s². Así, un valor extremo no domina el puntaje.

### 4.3 Fórmula

Puntaje bruto:

  S(t) = 0,633 · z_d(t) + 0,256 · z_V(t) + 0,151 · z_A(t)

donde z_k = (x_k − μ_k) / σ_k se estandariza con todas las rutas en el momento del pase.

| Componente | Peso | Error estándar |
|---|---|---|
| Separación d | 0,633 | 0,032 |
| Velocidad de separación V | 0,256 | 0,032 |
| Aceleración de separación A | 0,151 | 0,028 |

**Neutralidad respecto de la profundidad.** Sin corrección, la DSA tenía una correlación de −0,31 con la profundidad:
las rutas cortas puntuaban alto solo por ser cortas. Por eso se resta lo típico a cada profundidad:

  S_n(t) = S(t) − g(prof(t))

g es el puntaje medio de las rutas en el pase en 20 bandas de profundidad de igual tamaño, interpolado entre bandas.

**Escala 0-100:**

  DSA(t) = 100 · F(S_n(t))

F es la distribución empírica de S_n en el momento del pase de las 35.032 rutas.

### 4.4 Cómo leerla

- **DSA = 80** significa que el receptor está en una situación más favorable que el 80 % de los receptores en el momento
  del pase, comparado contra lo típico a su profundidad.
- En el momento del pase, la DSA es una medida calibrada. En los frames anteriores debe leerse como "si el pase saliera
  ahora": aplica la misma escala a instantes en los que todavía no se lanzó.
- Las gráficas del visor muestran V y A sin recortar. El puntaje sí usa los valores recortados.

### 4.5 Validación

Validación cruzada de 5 pliegues agrupados por partido: ningún partido aparece a la vez en entrenamiento y prueba.

| Modelo | log-loss | Brier | AUC |
|---|---|---|---|
| Solo intercepto | 0,6585 | 0,2329 | 0,500 |
| Profundidad | 0,6274 | 0,2187 | 0,651 |
| Separación + profundidad | 0,5930 | 0,2024 | 0,721 |
| **DSA neutral + profundidad** (CV anidada: pesos y g se estiman solo con los partidos de entrenamiento) | **0,5809** | **0,1972** | **0,732** |

**Calibración.** La tasa de completos sube de forma monótona con la DSA:

| DSA | 0-10 | 10-20 | 20-30 | 30-40 | 40-50 | 50-60 | 60-70 | 70-80 | 80-90 | 90-100 |
|---|---|---|---|---|---|---|---|---|---|---|
| Completos | 30 % | 38 % | 40 % | 49 % | 56 % | 67 % | 71 % | 74 % | 77 % | 81 % |

**Neutralidad.** La correlación de Spearman entre la DSA y la profundidad es −0,013; entre la DSA-OE y la profundidad, −0,008.

**Sensibilidad.** Se probaron 10 o 40 bandas, recortes p2,5-p97,5 y p0,5-p99,5, y un tope de separación de 8 yd.
En todas las variantes el AUC queda entre 0,7318 y 0,7324, se conservan los mismos tres componentes y el ranking de
receptores tiene una correlación ≥ 0,997 con el original. No se probaron variantes de la ventana de 0,5 s ni del inicio de ruta.

## 5. DSA sobre lo esperado (DSA-OE)

Un running back en el flat suele estar libre por diseño. Para comparar jugadores con roles distintos:

  DSA-OE(ruta) = DSA(pase) − media de DSA(pase) de las rutas con la misma alineación y el mismo tipo de cobertura

- **Alineación:** se agrupa `pff_positionLinedUp` en Abierto (LWR/RWR), Slot (S*WR), TE y Backfield (HB/FB/QB).
- **Tipo de cobertura:** `pff_passCoverageType` (Man / Zone / Other).
- Un DSA-OE de +7 significa 7 puntos más de ventaja que el promedio de su rol ante ese tipo de cobertura.

## 6. Creación de separación

| Métrica | Definición |
|---|---|
| **Quiebre** m | **Último** mínimo de d(t) en la fase de ruta [0,5 s, pase]. Se ignora el primer medio segundo porque el colchón del snap no es ventaja; en una meseta se toma el final |
| **Ganancia** G | d(pase) − d(m) |
| **Creación** | G ≥ 1 yd y el quiebre ocurre ≥ 0,2 s antes del pase. La cumple el 27,5 % de las rutas |
| **Separation Creation Time** | Tiempo snap → quiebre; mediana 1,7 s |
| **Separation Persistence** | Pers en el momento del pase (descriptiva, sección 3) |

## 7. Separation Creation Signature (SCS)

### 7.1 Qué pregunta responde

¿Qué hace el receptor con su cuerpo justo cuando empieza a ganar espacio?

### 7.2 Rasgos

Son cinco rasgos, todos del receptor. Se miden en la ventana [m − 1 s, m + 0,5 s], sin pasar del pase:

| Rasgo | Definición |
|---|---|
| Velocidad en el quiebre | s(m), en yd/s |
| Freno previo | Máxima desaceleración (−ds/dt) en el segundo previo, en yd/s². Se deriva de s porque la columna `a` del tracking no distingue frenar de acelerar |
| Aceleración posterior | Máxima ds/dt en el medio segundo posterior |
| Cambio de dirección | \|dir(m + 0,5 s) − dir(m − 0,5 s)\|, en grados |
| Cuerpo vs. carrera | \|o(m) − dir(m)\|: diferencia entre la orientación del cuerpo y la dirección de movimiento |

Freno y aceleración pasan por log(1 + x), porque la mitad de los casos vale 0. Después todos los rasgos se estandarizan.

### 7.3 Agrupamiento

- Se usa k-means++ sobre las 9.651 rutas con creación, con k de 2 a 6.
- Se elige el mayor k cuya silhouette esté a ≤ 0,01 de la mejor: **k = 3** (silhouette 0,343).
- Los nombres de los grupos se generan a partir de sus dos rasgos más distintivos.

| Firma | Rutas | Posiciones | Profundidad mediana | Ganancia media |
|---|---|---|---|---|
| A alta velocidad y cuerpo alineado con la carrera | 5.833 | WR 70 %, TE 22 % | 10,8 yd | 2,70 yd |
| Desde baja velocidad y cuerpo girado respecto a la carrera | 1.894 | TE 36 %, WR 33 %, RB 30 % | 1,3 yd | 2,69 yd |
| Freno marcado y cambio de dirección fuerte | 1.924 | WR 61 %, TE 24 % | 7,0 yd | 2,37 yd |

**Interpretación futbolística.** La primera firma reúne rutas que ganan espacio en carrera (verticales y cruces); la tercera,
rutas de corte con frenada; la segunda, salidas cortas desde casi parado cerca de la línea (flat, salidas del backfield).
Es una interpretación: el dataset no etiqueta el tipo de ruta.

**Estabilidad.** En 10 réplicas bootstrap, el índice de Rand ajustado (ARI) contra la partición original fue 0,936 en
promedio y 0,833 como mínimo. La silhouette es baja (0,34), así que las firmas son **una partición reproducible de un
continuo de movimientos, no categorías naturalmente separadas**.

**Comparación entre receptores.** La firma de cada receptor es la proporción de sus creaciones que cae en cada grupo.

## 8. Emparejamientos y Defensive Recovery

**Posible emparejamiento.** Es el defensor que fue el más cercano en más frames de la fase de ruta. Su **confianza** es la
fracción de esos frames. Se usa si la confianza es ≥ 0,5.
**No es la asignación real**: el dataset no indica quién cubre a quién.

**Parejas receptor-defensor solo en cobertura man.** En zona, el defensor más cercano refleja el área que cubre el
esquema, no un duelo. La estabilidad del defensor más cercano medida en los datos:

| Cobertura | Rutas | Confianza media | Cambios del defensor más cercano por ruta |
|---|---|---|---|
| Man | 9.952 | 0,885 | 0,52 |
| Zone | 23.141 | 0,845 | 0,65 |

Incluso en man, el defensor más cercano cambia a veces. El emparejamiento sigue siendo una inferencia.

**Defensive Recovery** = (d_j(pase) − d_j(pase + k)) / (0,1 · k), con j el posible emparejamiento y k = min(5, frames disponibles) ≥ 2.
- Unidad: yd/s; positivo significa que el defensor cierra.
- Solo se calcula en pases dirigidos a ese receptor.
- En promedio la separación sigue creciendo tras el pase: −0,85 yd/s.
- Es la única métrica que usa información posterior al pase.

## 9. Agregación por jugador

- **Encogimiento** de promedios con poca muestra: x̃ = (n · x̄ + 30 · μ) / (n + 30), con μ = 0 para la DSA-OE y 25 % para la consistencia.
- **Consistencia:** proporción de rutas en el cuartil superior de la DSA de su propio rol (lo esperado es 25 %).
- Toda tabla y todo hallazgo muestra su tamaño de muestra.

## 10. Coach Intelligence

Los hallazgos se generan con reglas fijas a partir de los agregados.
- **Mínimos de muestra:** 120 rutas por receptor, 40 rutas contra man, 15 pases por defensor y 4 rutas por pareja.
- **Ocho campos por hallazgo:** qué ocurrió, quiénes, cuándo, movimiento, métricas, si se repite, qué aprender y limitaciones.
- **Reglas de redacción:** toda recomendación empieza con "Si…" y no se usan verbos causales. Las pruebas verifican las tres cosas.
- Las asociaciones que se reportan son observacionales.

## 11. Ejemplos con jugadas reales

### 11.1 Ventaja amplia en una ruta corta, contra zona

**Partido 2021101100, jugada 2365.** BAL vs. IND, 2.º y 10, Cover-6 (zona).
Descripción: "L.Jackson pass short right to M.Brown to IND 12 for 7 yards". Receptor: Marquise Brown, objetivo, pase completo.

| Instante | t (s) | Separación (yd) | V (yd/s) | Profundidad (yd) | DSA | Defensor más cercano |
|---|---|---|---|---|---|---|
| Snap | 0,0 | 6,59 | 0,00 | −1,9 | 59,1 | Tyquan Lewis |
| Quiebre | 0,5 | 6,59 | −0,24 | −1,8 | 58,2 | Tyquan Lewis |
| Pase | 2,3 | 7,61 | 0,42 | 3,0 | 97,3 | Isaiah Rodgers |

- Brown sale con más de 6 yd de colchón y gana 1,03 yd más. A 3 yd de la línea, 7,6 yd de espacio es muy poco común, y por eso la DSA llega a 97.
- Firma: «Desde baja velocidad y cuerpo girado» (velocidad en el quiebre 1,1 yd/s, aceleración posterior 6,4 yd/s²).
- El defensor más cercano cambió una vez durante la ruta.
- Esta jugada muestra el uso de la neutralidad: una ruta corta y abierta puntúa alto porque supera lo típico a su profundidad.

### 11.2 Separación creada contra cobertura man

**Partido 2021101707, jugada 3837.** KC vs. WAS, 3.º y 5, Cover-1 (man).
Descripción: "P.Mahomes pass short middle to T.Hill ran ob at WAS 30 for 19 yards".
Receptor: Tyreek Hill, objetivo. Posible emparejamiento: Kendall Fuller (confianza 1,00, sin cambios de defensor).

**La jugada fue anulada ("No Play") por castigos compensados.** Hubo dos faltas, registradas en `foulName1-2` / `foulNFLId1-2` de `plays.csv`:

| Equipo | Jugador | Posición | Falta | Acción |
|---|---|---|---|---|
| KC (ofensiva) | Travis Kelce | TE | Low Block | Bloqueo ilegal por debajo de la cintura |
| WAS (defensa) | Kamren Curl | FS | Defensive Holding | Sujetar ilegalmente a un jugador ofensivo |

Como las faltas se compensan, la jugada se repite: `prePenaltyPlayResult` = 19 yd, pero `playResult` = 0 y `penaltyYards` = 0.
`passResult` sigue marcado como "C". Ninguna de las dos faltas involucra a Hill ni a Fuller, así que el movimiento que se
analiza es real; lo que no cuenta oficialmente es el resultado (ver limitación 7).

| Instante | t (s) | Separación (yd) | V (yd/s) | Profundidad (yd) | DSA |
|---|---|---|---|---|---|
| Snap | 0,0 | 3,84 | 0,06 | −1,0 | 23,9 |
| Quiebre | 3,6 | 0,90 | −5,04 | 14,1 | 12,1 |
| Pase | 7,1 | 2,63 | 9,09 (sin recortar) | 13,5 | 78,6 |

- Fuller cierra hasta 0,9 yd a los 3,6 s.
- Hill frena (freno previo de 5,9 yd/s²), cambia de dirección 49° y gana 1,72 yd hasta el pase.
- Al soltarse el balón, la separación crece a 9 yd/s. Por eso la DSA pasa de 12 a 79 aunque la separación sea solo de 2,6 yd.
- Firma: «Freno marcado y cambio de dirección fuerte».
- Este es el caso que la DSA quiere capturar: una ventaja dinámica que una medición instantánea de distancia no muestra.

## 12. Limitaciones

1. **Ocho semanas de una temporada** (2021). Las muestras por pareja receptor-defensor son pequeñas: de 5.122 parejas en man, solo 555 tienen ≥ 4 rutas.
2. **Sin asignación defensiva.** Los emparejamientos son inferidos y solo se forman en cobertura man.
3. **Sin tipo de ruta.** Las firmas SCS no se pueden validar contra etiquetas.
4. **Solo 0,5 s después del pase.** No se mide la separación en la recepción, el punto de captura ni las yardas después de la recepción.
5. **El objetivo depende del texto.** Queda sin identificar el 3,7 % de los pases, en su mayoría balones tirados fuera.
6. **Asociación, no causalidad.** La decisión del QB, la presión, la precisión y la habilidad de atrapar no se controlan. La DSA mide espacio y dinámica, no calidad del receptor en sentido amplio.
7. **Jugadas anuladas.** 489 de las 8.557 jugadas (5,7 %) dicen "No Play" en su descripción y siguen en `plays.csv` y en
   el análisis. Su movimiento es real, pero su resultado no cuenta oficialmente. Por `passResult`: I 289, C 133, R 30, S 23, IN 14.
   Las faltas más comunes en esas jugadas son Defensive Pass Interference (134), Offensive Holding (105), Defensive
   Holding (45), Roughing the Passer (41), Defensive Offside (35) y Offensive Pass Interference (31).
   **Efecto en la DSA:** en una interferencia defensiva, el pase suele quedar como incompleto aunque el receptor haya sido
   sujetado o golpeado. Esas jugadas entran al ajuste como "no completo", lo que puede subestimar un poco el valor de la separación.
   **Decisión del equipo:** las jugadas anuladas se mantienen en la DSA. El visor indica que hubo castigo, la falta (traducida),
   su motivo, el jugador que la cometió y su estado (aplicada, rechazada o compensada), a partir de `foulName1-3` / `foulNFLId1-3`.
8. **Umbrales a priori sin probar:** la ventana de 0,5 s, el inicio de ruta a 0,5 s, la ganancia mínima de 1 yd y la velocidad mínima de 1 yd/s.
9. **Los recortes de V y A** se calculan con todos los datos antes de la validación cruzada. Solo son percentiles, así que el impacto esperado es mínimo, pero no es una validación completamente anidada.

## 13. Reproducibilidad

| Qué | Cómo |
|---|---|
| Auditoría de datos | `python -m backend.tools.audit_data`, `audit_extra`, `audit_extra2` |
| Motor completo y criterios de aceptación | `python -u -m backend.tools.run_engine` |
| Validación (objetivos, sensibilidad, SCS, memoria) | `python -u -m backend.tools.validate_b` |
| Ejemplos de la sección 11 | `python -u -m backend.tools.ejemplos_metodologia` |
| Pruebas | `python -m pytest backend/tests` (56 pruebas) |

Semillas fijas en los pliegues de la validación cruzada (7), k-means (11), silhouette (3), el bootstrap (7) y la muestra de objetivos (2021).
Python en `.venv`, solo con las dependencias del stack (pandas, numpy, FastAPI); el clustering y la regresión están implementados en numpy.
