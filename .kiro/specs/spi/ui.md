# SPI — Especificación de la interfaz (D1)

Público: entrenadores y analistas de un staff NFL. Idioma: español. Tema oscuro deportivo, sin saturar.
Stack: React 18 + Vite 5 + TypeScript + Tailwind 3 + Recharts 3. Todas las rutas son relativas (`api/...`, sin `/` inicial).

## Navegación

Una barra superior con 6 vistas: **Hallazgos** (inicio) · **Visor de jugada** · **Receptores** · **Defensores** ·
**Emparejamientos** · **Metodología**. Desde cualquier hallazgo, receptor o jugada se puede abrir el visor en la jugada correspondiente.

## Vistas

| Vista | Pregunta que responde | Contenido |
|---|---|---|
| Hallazgos | ¿Qué debe saber el coach? | 7 tarjetas con los 8 campos; jugadores implicados; botón "Ver jugada" |
| Visor | ¿Cómo y cuándo se generó la ventaja en esta jugada? | Campo SVG + reproducción + 3 gráficas sincronizadas + panel del receptor + castigos |
| Receptores | ¿Quién crea ventaja de forma consistente y con qué movimiento? | Tabla filtrable (equipo, alineación, mínimo de rutas); perfil; comparación de 2 receptores |
| Defensores | ¿Quién permite menos ventaja y quién recupera más rápido? | Tabla filtrable con DSA-OE permitida, separación permitida y recuperación |
| Emparejamientos | ¿Qué duelos en man presentan vulnerabilidades? | Tabla filtrable (ofensiva, defensa, mínimo de rutas), etiquetada como "posible emparejamiento, solo man" |
| Metodología | ¿Puedo confiar en la métrica? | Pesos, validación contra baselines, calibración, firmas SCS, limitaciones |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| UI-1 | Mientras el análisis carga, se muestra el progreso de `/api/estado` y no hay errores; al terminar, la app se habilita sola |
| UI-2 | El campo muestra yardas, zonas de anotación, línea de scrimmage y de primer down, 22 jugadores (ofensiva y defensa con colores distintos), dorsales y balón |
| UI-3 | Reproducción con play/pausa, paso adelante/atrás, barra de tiempo y velocidades 0,25×, 0,5×, 1× y 2× |
| UI-4 | Al seleccionar un receptor: se resaltan su trayectoria y la de su defensor más cercano, y se dibuja la línea de separación con su distancia en el frame actual |
| UI-5 | Las gráficas (separación; velocidad y aceleración de separación; DSA) tienen un cursor sincronizado con el frame y marcan el quiebre y el pase |
| UI-6 | El panel del receptor muestra DSA al pase, separación, ganancia, quiebre, firma SCS y posible emparejamiento con su confianza |
| UI-7 | Si la jugada tuvo castigo, se muestra la falta en español, su motivo, el jugador y su estado; si fue anulada, se indica "Jugada anulada" |
| UI-8 | Toda tabla y todo hallazgo muestra el tamaño de muestra |
| UI-9 | El build (`npm run build`, que incluye `tsc --noEmit`) termina sin errores y no hay rutas con `/` inicial |
| UI-10 | La interfaz es usable desde 1280 px de ancho; en pantallas estrechas las columnas se apilan |
| UI-11 | La vista activa se refleja en el hash de la URL (`#receptores`, `#visor/{gameId}/{playId}/{nflId}`) para compartir enlaces a una jugada |
