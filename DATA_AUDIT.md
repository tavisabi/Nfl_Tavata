# Auditoría del dataset

Fuente: repositorio público `ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data` (rama `main`), descargado como
ZIP en `data/` sin modificaciones. Tracking: NFL Next Gen Stats. Scouting: Pro Football Focus (PFF).
Todas las cifras se reproducen con `backend/tools/audit_data.py`, `audit_extra.py` y `audit_extra2.py` (solo lectura).
El significado de las variables proviene del README oficial del repositorio.

## 1. Archivos

| Archivo | Tamaño | Filas | Llave | Duplicados por llave |
|---|---|---|---|---|
| `games.csv` | 6,7 KB | 122 | gameId | 0 |
| `plays.csv` | 2,2 MB | 8.557 | gameId + playId | 0 |
| `players.csv` | 0,1 MB | 1.679 | nflId | 0 |
| `pffScoutingData.csv` | 12,4 MB | 188.254 | gameId + playId + nflId | 0 |
| `tracking/tracking_[gameId].csv` (122) | 810,5 MB | 8.314.178 | gameId + playId + nflId + frameId | 0 |

El repositorio no incluye un archivo de licencia (riesgo para publicar los datos en GitHub; ver `requirements.md` RF-12).

## 2. Alcance real

- Temporada 2021, semanas 1 a 8, del 09/09/2021 al 01/11/2021. **No es una temporada completa.**
- Partidos por semana: 16, 16, 16, 16, 16, 14, 13, 15 (122 en total).
- **32 equipos**, comprobados en `games.csv`; cada equipo jugó 7 u 8 partidos. Cada equipo tiene entre 203 y 339 jugadas en ofensiva y entre 223 y 331 en defensa.
- **Solo jugadas de dropback (pase).** `passResult`: C 4.620, I 2.755, S (captura) 543, R (scramble) 449, IN 190. No hay jugadas de carrera.
- 1.679 jugadores. Rutas (pff_role = "Pass Route") por posición oficial: WR 23.033, TE 9.064, RB 6.994, FB 385, QB 32, C 3, T 2.

## 3. Variables y significado

### games.csv
| Variable | Significado |
|---|---|
| gameId | Identificador único del partido |
| season, week | Temporada y semana |
| gameDate, gameTimeEastern | Fecha y hora de inicio (hora del Este) |
| homeTeamAbbr, visitorTeamAbbr | Equipo local y visitante (3 letras) |

### plays.csv (32 columnas)
| Variable | Significado | Faltantes |
|---|---|---|
| gameId, playId | Llave de la jugada (playId no es único entre partidos) | 0 |
| playDescription | Narración oficial de la jugada; **única fuente del receptor objetivo** | 0 |
| quarter, down, yardsToGo, gameClock | Situación de juego | 0 |
| possessionTeam, defensiveTeam | Ofensiva y defensa | 0 |
| yardlineSide, yardlineNumber, absoluteYardlineNumber | Posición de la línea de scrimmage | 125 / 0 / 1 |
| preSnapHomeScore, preSnapVisitorScore | Marcador antes del snap | 0 |
| passResult | C, I, S, IN, R | 0 |
| penaltyYards, foulName1-3, foulNFLId1-3 | Penalizaciones | mayoría vacíos (sin falta) |
| prePenaltyPlayResult, playResult | Yardas netas antes y después de penalización | 0 |
| offenseFormation, personnelO, personnelD, defendersInBox | Formación y personal | 7 / 1 / 1 / 7 |
| dropBackType | Tipo de dropback del QB | 528 |
| pff_playAction | 1 si hubo play action | 0 |
| pff_passCoverage | Esquema: Cover-3 2.665, Cover-1 2.011, Cover-2 1.085, Quarters 1.033, Cover-6 805, Red Zone 376, Cover-0 270, 2-Man 200, Bracket 47, Prevent 32, Goal Line 25, Miscellaneous 8 | 0 |
| pff_passCoverageType | Man 2.481, Zone 5.588, Other 488 | 0 |

**No existe columna de receptor objetivo, de tipo de ruta, de yardas después de la recepción ni de asignación defensiva.**

### players.csv
nflId, height (texto, p. ej. "6-2"), weight, birthDate (232 faltantes), collegeName (224 faltantes), officialPosition (19 valores), displayName.

### pffScoutingData.csv
| Variable | Significado | Aplica a |
|---|---|---|
| pff_role | Coverage 57.765, Pass Block 46.057, Pass Route 39.513, Pass Rush 36.362, Pass 8.557 | todos |
| pff_positionLinedUp | Alineación en el snap (56 valores; p. ej. LWR, RWR, SLWR, TE-L, HB-R) | todos |
| pff_hit, pff_hurry, pff_sack | Presión acreditada | defensivos (94.127 vacíos) |
| pff_beatenByDefender, pff_hitAllowed, pff_hurryAllowed, pff_sackAllowed | Fallos en protección | bloqueadores (140.167 vacíos) |
| pff_nflIdBlockedPlayer, pff_blockType, pff_backFieldBlock | Detalle del bloqueo | bloqueadores |

Por jugada hay de 1 a 5 receptores con rol Pass Route (media 4,62) y de 3 a 11 defensores de cobertura (media 6,75).

### tracking_[gameId].csv
| Variable | Significado | Unidad / rango observado |
|---|---|---|
| gameId, playId, nflId, frameId | Llaves (nflId vacío = balón) | frameId empieza en 1 |
| time | Marca de tiempo | **precisión de 1 s**: no sirve para medir la frecuencia |
| jerseyNumber, team | Dorsal y equipo ("football" para el balón) | |
| playDirection | Dirección de ataque: right 4.126 jugadas, left 4.431 | |
| x, y | Posición en el campo | yd; x ∈ [−3,55, 121,15], y ∈ [−4,53, 57,72] (incluye fuera del campo) |
| s | Rapidez | yd/s; [0, 29,34] |
| a | Magnitud de la aceleración | yd/s²; [0, 50,69]; **nunca negativa** |
| dis | Distancia recorrida desde el frame anterior | yd |
| o, dir | Orientación del cuerpo y dirección de movimiento | grados [0, 360]; vacíos en el balón |
| event | Evento etiquetado en ese frame | vacío en 92 % de filas |

## 4. Frecuencia, convenciones y ventana temporal

- **10 Hz**: la mediana de `dis / s` es 0,1002 (p10-p90: 0,095-0,106).
- **Ángulos**: 0° apunta a +y y crece en sentido horario; vector = (sin θ, cos θ). Verificado contra el desplazamiento real (`test_convencion_de_angulos_contra_desplazamiento_real`, coseno mediano > 0,95).
- **Ventana del tracking**: cada jugada empieza ~0,5 s antes del snap (mediana 5 frames; máximo 117) y termina **0,5 s después del pase** (5 frames en el 90 % de la muestra de 15 partidos; mínimo 2). Frames por jugada: mediana 39 (19 a 177).
- **Snap → pase**: mediana 2,7 s (p5 1,8 s, p95 5,0 s, máximo 19,2 s), en 7.583 jugadas.
- **`a` vs. derivada de `s`**: correlación mediana 0,658 con |ds/dt|. `a` es la magnitud total de la aceleración (incluye la componente lateral) y no distingue frenar de acelerar; para eso hay que derivar `s`.

## 5. Eventos

| Evento | Filas | Observación |
|---|---|---|
| ball_snap / autoevent_ballsnap | 196.236 / 86.641 | 3.756 jugadas tienen ambos; el automático va antes en 2.183 (diferencias de ±1-4 frames) |
| pass_forward / autoevent_passforward | 173.604 / 85.882 | 3.677 jugadas tienen ambos; el automático va antes en 2.706 (diferencias de ±1-3 frames) |
| pass_arrived, pass_outcome_caught / incomplete | 8.441 / 529 / 920 | casi nunca aparecen porque el tracking termina 0,5 s después del pase |
| qb_sack, qb_strip_sack, run | 10.373 / 1.334 / 10.902 | |
| play_action, man_in_motion, shift, line_set | 45.471 / 4.071 / 3.059 / 3.220 | |

Jugadas sin snap: 24. Jugadas sin evento de pase: 953 (capturas 513, scrambles 437, y 3 marcadas como C/I).

## 6. Relaciones entre archivos

```
games (gameId) 1──* plays (gameId, playId) 1──* pffScoutingData (gameId, playId, nflId) *──1 players (nflId)
                          1──* tracking (gameId, playId, nflId, frameId)              *──1 players (nflId)
```

- Las 8.557 jugadas de `plays` tienen tracking y scouting; no hay tracking sin jugada ni jugadas sin tracking.
- El 100 % de `pff.nflId` existe en `players`; el 100 % de los jugadores Pass Route/Coverage (97.278) tiene tracking en su jugada.
- Cada `tracking_[gameId].csv` contiene solo ese gameId (122/122).
- `gameId` y `playId` también enlazan con `old_game_id` / `play_id` de nflverse (según el README), pero **no se usan**: el proyecto se limita a los datos del repositorio.

## 7. Receptor objetivo (derivado)

El objetivo se recupera de `playDescription` ("... pass short right **to C.Godwin** ...", "... **intended for** X INTERCEPTED ...")
y se cruza con los Pass Route de la jugada. Resultado: 7.287 de 7.565 pases C/I/IN (96,3 %): C 99,7 %, I 90,6 %, IN 96,8 %.
Los no identificados son pases sin destinatario ("pass incomplete short right.", "Thrown away"). Tasa de completo: 61,1 % en
todos los pases y 63,2 % en los identificados, así que el cruce no introduce un sesgo grande. Una primera versión
sin corregir el punto final del nombre solo identificaba el 74,6 % y sesgaba la muestra hacia completos (81,5 %).

## 8. Calidad y limitaciones

1. **No hay asignación defensiva**: quién cubre a quién debe inferirse (posible emparejamiento).
2. **No hay tipo de ruta**: las firmas de movimiento no pueden validarse contra etiquetas de ruta.
3. **Post-pase de solo 0,5 s**: no se puede medir la separación en la recepción, el punto de captura ni las yardas después de la recepción.
4. **Pre-snap de ~0,5 s**: no se puede analizar el movimiento previo (motion, alineación cambiante) más allá del último medio segundo.
5. **Eventos duplicados** manuales/automáticos con 1-4 frames de diferencia. Regla adoptada (A2): **el evento manual
   tiene prioridad**; el automático solo se usa si falta el manual. Respecto de la regla anterior ("el primero de los
   dos"), cambia el frame del snap en 2.183 jugadas y el del pase en 2.706 (en todas, el automático iba antes).
6. **`time` con precisión de segundos**; la frecuencia se infiere de `dis / s`.
7. **Coordenadas fuera del campo** (x < 0, y > 53,3): son reales (jugadores fuera de los límites); no se recortan.
8. **Muestra limitada**: 8 semanas; un emparejamiento receptor-defensor rara vez supera 5 rutas.
9. Faltantes no críticos para el análisis: dropBackType (528), offenseFormation (7), defendersInBox (7).
