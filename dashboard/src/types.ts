export type Estado = { estado: 'inactivo' | 'cargando' | 'listo' | 'error'; progreso: number; mensaje: string; error: string | null }

export type Metrica = { nombre: string; valor: string }
export type Implicado = { nflId: number; nombre: string; equipo: string; rol: string; valor: string }
export type Ejemplo = { gameId: number; playId: number; nflId: number } | null

export type Hallazgo = {
  id: string; pregunta: string; titulo: string; que_ocurrio: string; jugadores: Implicado[]; cuando: string
  movimiento: string; metricas: Metrica[]; repeticion: string; aprendizaje: string; limitaciones: string; ejemplo: Ejemplo
}

export type CV = { log_loss: number; brier: number; auc: number }
export type GrupoSCS = {
  id: number; nombre: string; n: number; mediana: Record<string, number>; ganancia_media: number
  profundidad_mediana: number; t_quiebre_mediana: number; posiciones: Record<string, number>
  tasa_completo: number | null; objetivos: number; vs_man: number | null; vs_zona: number | null
}
export type Resumen = {
  partidos: number; jugadas_analizadas: number; jugadas_totales: number; rutas: number; receptores: number
  defensores: number; equipos: number; semanas: number[]; objetivos: number; segundos_carga: number; tau: number
  componentes: { id: string; nombre: string; peso: number; error: number }[]
  validacion: {
    n_objetivos: number; tasa_completo: number; baseline_intercepto: CV; baseline_profundidad: CV
    baseline_sep_profundidad: CV; dsa_profundidad: CV; dsa_neutral_profundidad: CV
    calibracion: { rango: string; n: number; tasa_completo: number }[]
    spearman_profundidad: { dsa_bruta: number; dsa: number; dsa_oe?: number }
    saturacion_pase: Record<string, number>
  }
  seleccion: { paso: string; componentes: string[]; log_loss: number; auc: number }[]
  emparejamiento: Record<string, { rutas: number; confianza_media: number; cambios_def_media: number }>
  scs: { k: number; silhouettes: Record<string, number>; grupos: GrupoSCS[]; rasgos: Record<string, string> }
}

export type Receptor = {
  nflId: number; displayName: string; officialPosition: string; equipo: string; alineacion: string; rutas: number
  objetivos: number; completos: number; dsa_media: number; dsa_oe: number; dsa_oe_ajustada: number; consistencia: number
  sep_pase: number; persistencia: number; tasa_creacion: number; t_creacion: number | null; ganancia: number | null
  dsa_oe_man: number | null; rutas_man: number; dsa_oe_zona: number | null; rutas_zona: number; n_creaciones: number
  [k: `scs_${number}`]: number | null
}

export type JugadaPerfil = {
  gameId: number; playId: number; week: number; defensiveTeam: string; pff_passCoverage: string; pff_passCoverageType: string
  dsa: number; dsa_oe: number; sep_pase: number; ganancia: number; t_quiebre: number; t_pase: number; profundidad: number
  scs: number; objetivo: boolean; completo: number | null; passResult: string; defensor: string | null; def_conf: number
}

export type PerfilReceptor = {
  perfil: Receptor; jugadas: JugadaPerfil[]
  por_cobertura: { pff_passCoverage: string; rutas: number; dsa: number; sep: number }[]
  distribucion_dsa: number[]; liga_scs: number[]
}

export type Defensor = {
  nflId: number; displayName: string; officialPosition: string; equipo: string; rutas: number; dsa_permitida: number
  dsa_oe_permitida: number; dsa_oe_permitida_ajustada: number; sep_permitida: number; objetivos: number
  completos_permitidos: number; recuperacion: number | null; conf_media: number; rutas_man: number; dsa_oe_permitida_man: number | null
}

export type Emparejamiento = {
  nflId: number; defId: number; receptor: string; pos_receptor: string; defensor: string; pos_defensor: string
  equipo_of: string; equipo_def: string; alineacion: string; rutas: number; dsa_media: number; dsa_oe: number
  sep_pase: number; conf_media: number; objetivos: number; completos: number
}

export type Partido = { gameId: number; week: number; gameDate: string; homeTeamAbbr: string; visitorTeamAbbr: string }
export type JugadaLista = {
  playId: number; quarter: number; gameClock: string; down: number; yardsToGo: number; possessionTeam: string
  passResult: string; pff_passCoverage: string; playDescription: string; dsa_max: number; castigo: boolean; anulada: boolean
}

export type Castigo = {
  falta: string; falta_es: string; motivo: string; estado: 'aplicada' | 'rechazada' | 'compensada'
  nflId: number | null; jugador: string | null; posicion: string | null; equipo: string | null
}

export type JugadorTrk = {
  nflId: number; nombre: string; posicion: string; dorsal: number | null; lado: 'ofensiva' | 'defensa'; rol: string
  x: (number | null)[]; y: (number | null)[]; s: (number | null)[]; o: (number | null)[]
}

export type SerieReceptor = {
  t: number[]; sep: (number | null)[]; vsep: (number | null)[]; asep: (number | null)[]; desal: (number | null)[]
  persist: (number | null)[]; prof: (number | null)[]; dsa: (number | null)[]; cercano: (number | null)[]
}

export type ReceptorJugada = {
  nflId: number; nombre: string; posicion: string; defensorPrincipal: number | null; confianza: number
  objetivo: boolean; scs: number
  resumen: { t_pase: number; sep_pase: number; t_quiebre?: number; ganancia?: number; creada?: boolean; profundidad?: number
    vel_quiebre?: number; freno?: number; acel_post?: number; giro?: number; def_conf?: number; cambios_def?: number }
  serie: SerieReceptor
}

export type Jugada = {
  gameId: number; playId: number; frames: number; snap: number; pase: number; losX: number
  meta: {
    descripcion: string; ofensiva: string; defensa: string; cuarto: number; down: number; distancia: number
    cobertura: string; tipoCobertura: string; formacion: string | null; resultado: string; yardas: number
    playAction: boolean; anulada: boolean; castigos: Castigo[]
  }
  jugadores: JugadorTrk[]; balon: { x: (number | null)[]; y: (number | null)[] }
  eventos: { frame: number; evento: string }[]; receptores: ReceptorJugada[]
}

export type Destino = { gameId: number; playId: number; nflId?: number }
