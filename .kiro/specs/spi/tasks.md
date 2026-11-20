# SPI — Plan de tareas

Regla vigente: ninguna tarea se inicia sin aprobación explícita del equipo. Cada tarea cumple sus criterios de aceptación
y sus pruebas antes de marcarse como terminada. El orden propuesto es: correcciones → validación → metodología → interfaz → entrega.

## Registro de defectos y riesgos

| ID | Tipo | Descripción | Estado |
|---|---|---|---|
| D-1 | Defecto | Con empates, el quiebre tomaba el **primer** mínimo | ✅ Resuelto (A1) |
| D-2 | Decisión no justificada | Snap/pase = el primero entre manual y automático | ✅ Resuelto (A2): manual con prioridad |
| R-1 | Metodológico | Aceleración de separación saturada (23,8 % en el pase) por el término geométrico de d″ | ✅ Resuelto (A3): 2,0 % |
| R-2 | Metodológico | d′ y d″ saltaban al cambiar el defensor más cercano | ✅ Resuelto (A3): V y A usan la historia del defensor actual |
| R-3 | Riesgo | Umbrales a priori sin análisis de sensibilidad | ✅ Mitigado (B2): bandas, recortes y tope robustos; ventana e inicio de ruta sin probar |
| R-4 | Interpretación | La DSA por frame aplica la calibración del pase a frames anteriores ("si el pase saliera ahora") | Abierto (documentar en C1) |
| R-5 | Metodológico | La DSA no era neutral a la profundidad (ρ = −0,31) | ✅ Resuelto (A4): ρ = −0,013 |
| R-6 | Validación | Sin revisión manual del cruce de objetivos | ✅ Resuelto (B1): 50/50 |
| R-7 | Validación | Emparejamientos en zona interpretados como duelos | ✅ Resuelto (A5): solo man; calidad medida |
| R-8 | Metodológico | SCS con silhouette baja (0,34) | ✅ Mitigado (B3): estable (ARI 0,94); se declara como partición de un continuo |
| R-9 | Datos | Defensive Recovery usa 2-5 frames post-pase y el defensor inferido | Abierto (limitación declarada) |
| R-10 | No funcional | Memoria del proceso sin medir | ✅ Resuelto (B5): pico 685 MB |
| R-11 | Despliegue | Montar `dashboard/dist` en "/" puede chocar con el hosting | Abierto |
| R-12 | Legal | El repositorio de datos no tiene licencia | Abierto (E4) |
| D-3 | Redacción | Frases causales o más fuertes que la evidencia | ✅ Resuelto (A6) |
| D-4 | Mantenimiento | `tools/audit_extra.py` conserva la expresión regular sesgada original | Abierto (baja) |
| D-5 | Pruebas | Sin pruebas para `scs`, `viewer` ni la API HTTP | Parcial: `dsa`, `aggregates` e `insights` ya tienen pruebas |
| R-14 | Datos | 489 jugadas "No Play" (5,7 %) se analizan; 134 con interferencia defensiva entran al ajuste de la DSA como pases no completos | Aceptado por el equipo (A7): se mantienen y se informa el castigo |
| R-13 | Interpretación | Incluso en man, el defensor más cercano cambia 0,52 veces por ruta: el emparejamiento sigue siendo inferido | Abierto (declarado en hallazgos) |

## Tareas

### Fase A — Correcciones (aprobadas y terminadas)

- [x] **A1. Último mínimo del quiebre.**
  - Evidencia: `ultimo_minimo()`; pasan `test_defensor_que_frena_genera_creacion` y `test_quiebre_en_meseta_es_el_ultimo_minimo`.
  - Efecto: rutas con creación 27,0 % → 27,5 %; quiebre mediano 1,7 s.
- [x] **A2. Regla de eventos: manual con prioridad.**
  - Evidencia: `frame_evento()`; pasan `test_evento_manual_tiene_prioridad_sobre_el_automatico` y `test_evento_automatico_se_usa_si_falta_el_manual`.
  - Conteo: el snap cambia en 2.183 jugadas y el pase en 2.706 (`audit_extra2.py`); registrado en DATA_AUDIT §5 y §8.
- [x] **A3. Componente de aceleración.**
  - Cambios: V y A respecto del defensor más cercano actual (opción a); winsorización p1-p99 (opción b).
  - Criterios: saturación en el pase < 5 % → **2,0 %** ✅; CV ≥ AUC 0,730 / ≤ log-loss 0,5832 → **0,7325 / 0,5812** ✅; prueba controlada de cambio de defensor ✅.
- [x] **A4. DSA neutral a la profundidad.**
  - Cambios: S_n = S − g(prof) con 20 bandas de cuantiles (en el puntaje mismo, no solo en la DSA-OE).
  - Criterios: |ρ(DSA-OE, prof)| < 0,1 → **0,008** ✅ (DSA: 0,013; por alineación ≤ 0,060).
  - CV anidada de la DSA neutral: AUC 0,732 / log-loss 0,5809 (sigue superando a separación + profundidad: 0,721 / 0,5930).
  - Rankings (receptores abiertos, slot o TE con ≥ 120 rutas, por DSA-OE ajustada):
    - antes: Marquez Callaway, Laviska Shenault, Michael Pittman, Marquise Brown, Freddie Swain;
    - después: Marquise Brown, Elijah Moore, DK Metcalf, Laviska Shenault, Michael Pittman.
- [x] **A5. Emparejamientos solo en cobertura man.**
  - Evidencia: `aggregates.emparejamientos` filtra man; pasa `test_emparejamientos_solo_usan_cobertura_man`.
  - Tasa de cambio de defensor: man 0,52 por ruta (confianza 0,885) frente a zona 0,65 (0,845).
  - Resultado: 5.122 parejas, 555 con ≥ 4 rutas. El hallazgo 7 pasó de un LB en zona a un CB en man (Tyreek Hill vs. Kendall Fuller, 7 rutas).
- [x] **A6. Redacción de hallazgos.**
  - Evidencia: 4 pruebas de estructura (8 campos), recomendaciones que empiezan con "Si…", ausencia de verbos causales y cifras que cambian al cambiar los datos.
  - Además se revisaron a mano los textos de la ejecución real (3 frases corregidas).

- [x] **A7. Jugadas con castigo (decisión del equipo: NO se excluyen de la DSA).**
  - Cambio: `penalties.py` traduce las 29 faltas del dataset con su motivo y lee del texto si fue aplicada, rechazada o compensada.
    El visor (`meta.castigos`, `meta.anulada`) y la lista de jugadas (`castigo`, `anulada`) lo informan.
  - Pruebas: `test_penalties.py` (3 pruebas, incluida la cobertura de las 29 faltas reales).

### Fase B — Validación breve (aprobada; `backend/tools/validate_b.py`, `backend/tests/test_api.py`)

- [x] **B1.** 50 objetivos aleatorios (semilla 2021) revisados contra el texto: **50/50 correctos** (incluye un "intended for ... INTERCEPTED").
- [x] **B2.** Sensibilidad (CV anidada por partido; ρ = Spearman del ranking de receptores ≥ 120 rutas contra la versión base):

| Variante | AUC | log-loss | ρ profundidad | ρ ranking |
|---|---|---|---|---|
| Base (20 bandas, p1-p99, tope 10 yd) | 0,7320 | 0,5809 | −0,013 | 1,000 |
| 10 bandas | 0,7322 | 0,5808 | −0,024 | 1,000 |
| 40 bandas | 0,7320 | 0,5809 | −0,012 | 1,000 |
| Recorte p2,5-p97,5 | 0,7324 | 0,5806 | −0,012 | 0,999 |
| Recorte p0,5-p99,5 | 0,7318 | 0,5810 | −0,013 | 1,000 |
| Tope de separación 8 yd | 0,7322 | 0,5801 | −0,022 | 0,997 |

  En todas las variantes quedan los mismos componentes (d, V, A). **Robusta.** No se probaron VENTANA ni INICIO_RUTA, porque exigen reprocesar el tracking (pendiente menor).
- [x] **B3.** SCS bootstrap (10 réplicas, k = 3): **ARI medio 0,936, mínimo 0,833** (≥ 0,7). Los grupos son estables aunque la silhouette sea baja (0,34): es una partición reproducible de un continuo, no grupos naturalmente separados. Se declara así en la metodología.
- [x] **B4.** 5 pruebas HTTP: `/health` responde 200 durante la carga, los endpoints de datos responden 503, los catálogos dan 32 equipos y 122 partidos, y una ruta inexistente da 404. Pasan las 56 pruebas.
- [x] **B5.** Carga completa en 75 s; memoria pico 685 MB (en la carga, con 4 hilos) y 180 MB en reposo una vez listo.
- [ ] **B6.** Pruebas unitarias de `dsa.ajustar` y `scs`: se pospone (cubierto indirectamente por B2 y B3).

### Fase C — Metodología

- [x] **C1.** `METHODOLOGY.md`: fórmulas, validación, sensibilidad, 2 ejemplos con jugadas reales (valores de `tools/ejemplos_metodologia.py`) y 9 limitaciones (incluye R-4 y R-13). **Pendiente de tu revisión.**
- [ ] **C2.** Marcar `design.md` como versión aprobada (tras tu revisión de C1).

### Fase D — Interfaz (requiere una especificación de UI aprobada)

- [ ] **D1.** Especificación de pantallas: visor de jugada, Receptores, Defensores, Emparejamientos, Hallazgos y Metodología, con la pregunta que responde cada gráfica.
- [ ] **D2.** Proxy `/api` en `vite.config.ts`, cliente con rutas relativas `api/...`.
- [ ] **D3.** Campo SVG, reproducción, selección, línea de separación y gráficas sincronizadas (RF-8).
- [ ] **D4.** Vistas de comparación y hallazgos (RF-5.4, RF-7, RF-9).
- [ ] **D5.** Estados de carga (503 con progreso) y de error.

### Fase E — Entrega

- [ ] **E1.** README de 3 a 5 oraciones.
- [ ] **E2.** Ejecutar `.\.hackathon\setup.cmd --check` y `--entregar`.
- [ ] **E3.** Capturas de pantalla.
- [ ] **E4.** GitHub: requiere instalar git y decidir sobre los datos (R-12).
