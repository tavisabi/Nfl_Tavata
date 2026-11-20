# SPI · Situational Player Intelligence — Requisitos

Estado del documento: **borrador para revisión del equipo** (adopción de Spec-Driven Development con el proyecto ya
en implementación). Ningún requisito nuevo se implementa hasta que este documento sea aprobado.

## Introducción

SPI es una herramienta para entrenadores de la NFL que convierte el tracking cuadro por cuadro (10 Hz) en información
sobre cómo un receptor genera ventaja espacial frente a la defensa, cuándo ocurre y qué movimientos la preceden.
Usa exclusivamente el dataset del repositorio `ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data`
(122 partidos, semanas 1-8 de la temporada 2021, solo jugadas de pase). Ver `DATA_AUDIT.md`.

Pregunta central: ¿qué movimientos y características de aceleración, orientación y trayectoria permiten que un
receptor genere ventaja sobre su defensor, y cómo puede usar esa información un entrenador?

### Leyenda de estado

| Estado | Significado |
|---|---|
| ✅ Verificado | Implementado y comprobado con pruebas automáticas o ejecución registrada |
| 🟡 Sin verificar | Implementado, pero no se ha comprobado su funcionamiento completo |
| 🔴 Defecto | Implementado con un error conocido |
| ⚪ No existe | No implementado |
| ⏸ Pendiente de decisión | Requiere aprobación del equipo antes de implementarse o modificarse |

### Glosario

- **Ruta**: un receptor (pff_role = "Pass Route") en una jugada.
- **Defensor de cobertura**: jugador con pff_role = "Coverage".
- **Separación**: distancia euclidiana (yd) entre el receptor y el defensor de cobertura más cercano en un frame.
- **Snap / Pase**: primer frame con evento `ball_snap`/`autoevent_ballsnap` y `pass_forward`/`autoevent_passforward`.
- **Objetivo**: receptor al que se dirigió el pase, recuperado de `playDescription`.
- **Posible emparejamiento**: defensor que fue el más cercano durante más frames de la fase de ruta. No es la asignación real.
- **DSA**: Dynamic Separation Advantage, métrica experimental propia (no oficial de la NFL).
- **SCS**: Separation Creation Signature, firma de movimiento al crear separación.

---

## Requisitos funcionales

### RF-1 Auditoría y acceso a datos
**Historia:** Como analista, quiero que cada cálculo parta de datos verificados, para no sacar conclusiones de datos inexistentes.

1. EL SISTEMA DEBE leer `games.csv`, `plays.csv`, `players.csv`, `pffScoutingData.csv` y `tracking/tracking_[gameId].csv` desde `data/` con rutas relativas a la raíz del proyecto. — ✅
2. EL SISTEMA NO DEBE modificar ni escribir archivos en `data/`. — ✅ (solo `read_csv`; revisado en código)
3. CUANDO una jugada tenga `playDirection = left`, EL SISTEMA DEBE transformar x' = 120 − x, y' = 53,3 − y, ángulos + 180°, para que la ofensiva ataque hacia +x. — ✅ (`test_estandarizacion_jugada_izquierda`, `test_ofensiva_ataca_hacia_x_positivo_tras_estandarizar`)
4. EL SISTEMA DEBE documentar en `DATA_AUDIT.md` archivos, columnas, llaves, relaciones, frecuencia, eventos, faltantes y limitaciones. — 🟡 (scripts `backend/tools/audit_*.py` ejecutados; `DATA_AUDIT.md` redactado en esta revisión)

### RF-2 Identificación del receptor objetivo
1. EL SISTEMA DEBE identificar el objetivo de cada pase C/I/IN cruzando el nombre citado en `playDescription` con los jugadores "Pass Route" de esa jugada. — ✅ (8 casos en `test_targets_stats.py`; 7.287 de 7.565 pases = 96,3 %)
2. SI el cruce no es único o el pase no tiene destinatario, EL SISTEMA DEBE dejar la ruta sin objetivo en lugar de adivinar. — ✅
3. EL SISTEMA DEBE validar una muestra manual de cruces contra el texto original. — ⚪ (riesgo R-6)

### RF-3 Motor cuadro por cuadro
1. EL SISTEMA DEBE reconstruir, para cada ruta, las series de posición, velocidad (s, dir) y orientación desde el snap hasta el último frame disponible. — ✅
2. EL SISTEMA DEBE calcular por frame la separación al defensor de cobertura más cercano, su primera derivada (velocidad de separación) y su segunda derivada (aceleración de separación) con las fórmulas analíticas de `design.md §3`. — ✅ (`test_derivadas_coinciden_con_diferencias_finitas`, `test_velocidad_relativa_*`)
3. EL SISTEMA DEBE calcular la desalineación de trayectorias receptor-defensor y marcarla como no disponible cuando alguno se mueva a menos de 1 yd/s. — ✅ (`test_desalineacion`)
4. EL SISTEMA DEBE distinguir tres fases: pre-pase [snap, pase], momento del pase y post-pase (pase, fin]. Ninguna variable explicativa debe usar información posterior al instante evaluado. — ✅ (`test_media_ventana_es_causal`)
5. CUANDO una jugada no tenga evento de snap o de pase, o no tenga receptores o defensores con tracking, EL SISTEMA DEBE excluirla y contar el motivo. — ✅ (`test_jugada_sin_pase_se_descarta`, `test_sin_receptores_o_defensores`; 974 jugadas excluidas)
6. CUANDO falten frames de un jugador, EL SISTEMA DEBE representarlos como NaN sin interpolar. — ✅ (`test_frames_faltantes_quedan_como_nan`)
7. EL SISTEMA DEBE identificar el momento de creación de separación (quiebre) como **el último** mínimo de separación de la fase de ruta seguido de ≥ GANANCIA_MIN de ganancia. — ✅ (A1; `test_defensor_que_frena_genera_creacion`, `test_quiebre_en_meseta_es_el_ultimo_minimo`)
8. CUANDO una jugada tenga eventos manual y automático de snap o de pase, EL SISTEMA DEBE usar el manual; el automático solo si falta el manual. — ✅ (A2; 2 pruebas)
9. EL SISTEMA DEBE calcular la velocidad y la aceleración de separación respecto del defensor más cercano en cada instante, usando la historia de ese mismo defensor, para que un relevo de zona no genere saltos falsos. — ✅ (A3; `test_cambio_de_defensor_cercano_sin_saltos`, `test_aceleracion_usa_la_historia_del_defensor_actual`)

### RF-4 Dynamic Separation Advantage (DSA)
1. EL SISTEMA DEBE calcular la DSA en cada frame posterior al snap y en el momento del pase, en escala 0-100 (percentil respecto de todas las rutas en el momento del pase). — ✅ (ejecución registrada: 35.032 rutas)
2. EL SISTEMA DEBE estimar los pesos de los componentes a partir de los datos (regresión logística de completo sobre pases con objetivo, con la profundidad como control) y no con pesos asignados a mano. — ✅
3. EL SISTEMA DEBE conservar un componente solo si mejora el log-loss en validación cruzada agrupada por partido. — ✅ (persistencia y desalineación eliminadas; ver design §4)
4. EL SISTEMA DEBE reportar la comparación contra baselines (solo intercepto, profundidad, separación + profundidad). — ✅ (AUC 0,500 / 0,651 / 0,721 / DSA 0,733 / DSA neutral 0,732)
5. EL SISTEMA DEBE reportar la calibración (tasa de completo por decil de DSA). — ✅ (30 % en 0-10 → 81 % en 90-100, monótona)
6. EL SISTEMA DEBE calcular la DSA sobre lo esperado (DSA-OE) por alineación × tipo de cobertura para comparar jugadores con roles distintos. — ✅ (ejecución registrada; ρ con la profundidad = −0,008)
7. EL SISTEMA DEBE documentar la sensibilidad de la DSA a los umbrales fijados a priori (SEP_MAX, INICIO_RUTA, VENTANA, τ, bandas). — ⚪ (riesgo R-3, tarea B2)
8. La DSA DEBE ser neutral a la profundidad del receptor: |ρ de Spearman(DSA, profundidad)| < 0,1 y |ρ(DSA-OE, profundidad)| < 0,1. — ✅ (A4; −0,013 y −0,008; 3 pruebas)
9. Los componentes V y A DEBEN winsorizarse en percentiles calculados de los datos (p1-p99), con < 5 % de rutas en los límites en el momento del pase. — ✅ (A3; 2,0 % y 2,0 %)

### RF-5 Separation Creation Signature (SCS)
1. EL SISTEMA DEBE extraer 5 rasgos del receptor alrededor del quiebre (velocidad, freno previo, aceleración posterior, cambio de dirección, divergencia cuerpo-carrera) sin usar información posterior al pase. — ✅
2. EL SISTEMA DEBE agrupar las creaciones de separación con k-means y elegir k por silhouette. — ✅ (k = 3, silhouette 0,339 en la última ejecución verificada)
3. EL SISTEMA DEBE validar que los grupos tengan sentido futbolístico y reportar su composición por posición y profundidad. — 🟡 Parcial: la composición se reporta, pero un grupo mezcla salidas del backfield con rutas (riesgo R-8).
4. EL SISTEMA DEBE permitir comparar la distribución de firmas entre receptores. — 🟡 (datos en `/api/receptores`, sin interfaz)

### RF-6 Métricas complementarias
1. Separation Persistence: segundos consecutivos con separación ≥ τ al instante evaluado. — ✅ calculada; se reporta como descriptiva (excluida de la DSA por redundancia).
2. Separation Creation Time: tiempo snap → quiebre. — ✅ (defecto D-1 corregido; mediana 1,7 s)
3. Defensive Recovery: reducción de separación (yd/s) del posible emparejamiento en los ≤ 0,5 s posteriores al pase. — 🟡 calculada; ventana post-pase limitada (riesgo R-9).
4. Relative Acceleration: incluida como componente de la DSA (aceleración de separación). — ✅
5. Route Movement Profile: cubierto por la SCS; no se implementa como métrica separada (evitar redundancia). — ⏸

### RF-7 Emparejamientos y comparación
1. EL SISTEMA DEBE inferir un posible emparejamiento por ruta (defensor más cercano en más frames de la fase de ruta) con su confianza (fracción de frames). — ✅ (`test_defensor_que_frena_genera_creacion` verifica el emparejamiento; el fallo es solo por D-1)
2. EL SISTEMA DEBE etiquetar estos resultados como "posible emparejamiento" y explicar la limitación. — 🟡 (en textos de hallazgos; falta en interfaz)
3. EL SISTEMA DEBE agregar por receptor, defensor y pareja con tamaño de muestra y encogimiento hacia la media. — ✅ (ejecución registrada)
4. EL SISTEMA DEBE formar parejas receptor-defensor solo con jugadas en cobertura man y reportar la estabilidad del defensor más cercano en man y en zona. — ✅ (A5; man 0,52 cambios/ruta vs. zona 0,65; 1 prueba)

### RF-8 Visualización principal (campo interactivo)
1. EL SISTEMA DEBE mostrar un campo con jugadores, equipos diferenciados, dorsales, trayectorias, línea de scrimmage y línea receptor-defensor. — ⚪ (existe el endpoint de datos `/api/jugada/{gameId}/{playId}`, sin verificar; no hay interfaz)
2. EL SISTEMA DEBE reproducir cuadro por cuadro con play/pausa, control de velocidad y barra de tiempo. — ⚪
3. CUANDO el usuario seleccione un jugador, EL SISTEMA DEBE destacar su trayectoria y mostrar sus métricas. — ⚪
4. EL SISTEMA DEBE mostrar gráficas sincronizadas con la reproducción: separación, velocidad relativa, aceleración relativa y DSA. — ⚪
5. EL SISTEMA DEBE marcar en las gráficas el snap, el quiebre y el pase. — ⚪

### RF-9 Coach Intelligence
1. EL SISTEMA DEBE generar hallazgos con: qué ocurrió, jugadores, cuándo, movimiento, métricas, repetición, aprendizaje y limitaciones. — ✅ (7 hallazgos en la ejecución real; `test_hallazgos_tienen_los_ocho_campos`)
2. Todo número de un hallazgo DEBE calcularse a partir de los datos. — ✅ (`test_cifras_salen_de_los_datos`)
3. Las recomendaciones DEBEN empezar con "Si…" y no usar lenguaje causal. — ✅ (A6; `test_recomendaciones_condicionales_y_sin_lenguaje_causal` + revisión manual de la ejecución real)
4. Cada hallazgo DEBE enlazar a una jugada de ejemplo abrible en el visor. — 🟡 (el enlace existe en datos; no hay visor)

### RF-10 Modelos predictivos
1. EL SISTEMA DEBE comparar cualquier modelo con baselines, validar por partido y evitar fuga de información. — ✅ para el modelo de completo que calibra la DSA.
2. EL SISTEMA PUEDE incluir un modelo de predicción temprana de separación (p. ej., separación al pase a partir del primer segundo de ruta) SOLO si el equipo lo aprueba y la validación supera al baseline. — ⏸

### RF-11 API
1. `GET /health` DEBE responder `{"status": "ok"}` desde el arranque, aunque el análisis siga calculándose. — 🟡 (código revisado; no probado por HTTP)
2. Toda la API DEBE estar bajo `/api/...`; mientras el análisis cargue, los endpoints de datos DEBEN responder 503 con el progreso. — 🟡 (sin pruebas HTTP)
3. Endpoints: `/api/estado`, `/api/resumen`, `/api/equipos`, `/api/receptores[/{id}]`, `/api/defensores`, `/api/emparejamientos`, `/api/hallazgos`, `/api/partidos[/{id}/jugadas]`, `/api/jugada/{g}/{p}`. — 🟡 (implementados; ninguno probado por HTTP)

### RF-12 Entregables
1. README de 3 a 5 oraciones (qué construimos, qué revela, quién lo usaría). — ⚪
2. Métrica original documentada (`METHODOLOGY.md`). — ⚪ (contenido base en `design.md`, pendiente de revisión)
3. ZIP vía `.\.hackathon\setup.cmd --entregar`. — ⚪
4. Repositorio público en GitHub. — ⚪ (git no está instalado; licencia de datos sin confirmar, R-12)
5. Capturas de pantalla o demo. — ⚪

---

## Requisitos no funcionales

| ID | Requisito | Estado |
|---|---|---|
| RNF-1 | Stack fijo: Python 3.12.12, FastAPI 0.115.14, pandas 2.2.3, numpy 2.1.3; React 18.3.1, Vite 5.4.21, TS 5.7.3, Tailwind 3.4.19, Recharts 3.10.1. Sin dependencias nuevas (no scikit-learn/scipy). | ✅ (solo se importan paquetes del stack) |
| RNF-2 | Python siempre dentro de `.venv`. | ✅ |
| RNF-3 | El servidor es efímero: todo se calcula en memoria al arrancar; no se escribe en disco. | ✅ (el caché de `explore_dsa.py` es de desarrollo, fuera del proyecto, y la app no lo usa) |
| RNF-4 | El análisis completo debe estar listo en ≤ 3 min tras el arranque. | ✅ 75-80 s medidos en esta laptop (sin medir en el hosting) |
| RNF-5 | Memoria máxima del proceso documentada. | ✅ Pico de 685 MB durante la carga; 180 MB en reposo (B5) |
| RNF-6 | El visor debe responder una jugada en ≤ 2 s (≤ 0,3 s con caché). | 🟡 Sin medir |
| RNF-7 | El dashboard usa rutas relativas sin diagonal inicial (`fetch('api/...')`) y `base: './'`; proxy de `/api` a `localhost:8000` en desarrollo. | ⚪ (frontend sin construir; proxy no configurado) |
| RNF-8 | Interfaz en español, profesional, responsive, sin saturar; cada gráfica responde una pregunta. | ⚪ |
| RNF-9 | Cada métrica muestra su tamaño de muestra; ninguna conclusión se presenta sin él. | 🟡 (en API y hallazgos; falta interfaz) |
| RNF-10 | No se usan servicios de AWS; la IA queda fuera del alcance salvo aprobación. | ✅ |
| RNF-11 | Reproducibilidad: semillas fijas en k-means, pliegues y silhouette. | ✅ |
| RNF-12 | Toda nueva funcionalidad requiere especificación aprobada, criterios de aceptación y pruebas. | Vigente desde esta revisión |
