import { useEffect, useState } from 'react'
import { api } from './api'
import { Cargando } from './components/ui'
import type { Destino, Estado, Hallazgo, Resumen } from './types'
import Defensores from './views/Defensores'
import Emparejamientos from './views/Emparejamientos'
import Hallazgos from './views/Hallazgos'
import Metodologia from './views/Metodologia'
import Receptores from './views/Receptores'
import Visor from './views/Visor'

type Vista = 'hallazgos' | 'visor' | 'receptores' | 'defensores' | 'emparejamientos' | 'metodologia'
const VISTAS: [Vista, string][] = [
  ['hallazgos', 'Hallazgos'], ['visor', 'Visor de jugada'], ['receptores', 'Receptores'],
  ['defensores', 'Defensores'], ['emparejamientos', 'Emparejamientos'], ['metodologia', 'Metodología'],
]

export default function App() {
  const [estado, setEstado] = useState<Estado | null>(null)
  const [resumen, setResumen] = useState<Resumen | null>(null)
  const [hallazgos, setHallazgos] = useState<Hallazgo[]>([])
  const [equipos, setEquipos] = useState<string[]>([])
  const [vista, setVista] = useState<Vista>('hallazgos')
  const [destino, setDestino] = useState<Destino | null>(null)
  const [fallo, setFallo] = useState<string | null>(null)

  // UI-1: mientras el análisis carga en el servidor, se consulta el progreso.
  useEffect(() => {
    let vivo = true
    const consultar = async () => {
      try {
        const e = await api<Estado>('estado')
        if (!vivo) return
        setEstado(e)
        if (e.estado === 'listo') {
          const [r, h, eq] = await Promise.all([api<Resumen>('resumen'), api<Hallazgo[]>('hallazgos'), api<string[]>('equipos')])
          if (vivo) { setResumen(r); setHallazgos(h); setEquipos(eq) }
          return
        }
        if (e.estado !== 'error') window.setTimeout(consultar, 1500)
      } catch {
        if (vivo) { setFallo('No se pudo conectar con el servidor. Reintentando…'); window.setTimeout(consultar, 3000) }
      }
    }
    consultar()
    return () => { vivo = false }
  }, [])

  // UI-11: el hash de la URL indica la vista (y la jugada en el visor): #visor/{gameId}/{playId}/{nflId}
  useEffect(() => {
    const leer = () => {
      const [v, g, p, n] = window.location.hash.replace(/^#/, '').split('/')
      if (VISTAS.some(([x]) => x === v)) setVista(v as Vista)
      if (v === 'visor' && g && p) setDestino({ gameId: Number(g), playId: Number(p), nflId: n ? Number(n) : undefined })
    }
    leer()
    window.addEventListener('hashchange', leer)
    return () => window.removeEventListener('hashchange', leer)
  }, [])
  const ir = (v: Vista) => { setVista(v); window.history.replaceState(null, '', `#${v}`) }
  const abrir = (d: Destino) => {
    setDestino({ ...d }); setVista('visor')
    window.history.replaceState(null, '', `#visor/${d.gameId}/${d.playId}${d.nflId ? '/' + d.nflId : ''}`)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-noche-700 bg-noche-950/90 backdrop-blur sticky top-0 z-10">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-ventaja to-cesped-700 grid place-items-center font-black text-noche-950">SPI</div>
            <div>
              <div className="font-semibold text-slate-50 leading-tight">Situational Player Intelligence</div>
              <div className="text-[11px] text-slate-400">Cómo, cuándo y con qué movimiento crea ventaja un receptor · NFL 2021, semanas 1-8</div>
            </div>
          </div>
          {resumen && (
            <nav className="flex flex-wrap gap-1 ml-auto">
              {VISTAS.map(([v, n]) => (
                <button key={v} onClick={() => ir(v)} className={`boton ${vista === v ? 'boton-activo' : ''}`}>{n}</button>
              ))}
            </nav>
          )}
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-4 py-5">
        {!resumen && (
          <div className="tarjeta p-8 max-w-xl mx-auto mt-16 text-center">
            {estado?.estado === 'error' ? (
              <p className="text-alerta">El análisis falló en el servidor: {estado.error}</p>
            ) : (
              <>
                <Cargando texto={estado?.mensaje || fallo || 'Preparando el análisis…'} />
                <div className="h-2 bg-noche-700 rounded mt-2">
                  <div className="h-2 bg-ventaja rounded transition-all" style={{ width: `${Math.round(100 * (estado?.progreso ?? 0))}%` }} />
                </div>
                <p className="text-xs text-slate-500 mt-3">El servidor procesa los 122 partidos de tracking al arrancar (alrededor de 1-2 minutos).</p>
              </>
            )}
          </div>
        )}
        {resumen && vista === 'hallazgos' && <Hallazgos hallazgos={hallazgos} resumen={resumen} abrir={abrir} />}
        {resumen && vista === 'visor' && <Visor destino={destino} grupos={resumen.scs.grupos} />}
        {resumen && vista === 'receptores' && <Receptores equipos={equipos} grupos={resumen.scs.grupos} abrir={abrir} />}
        {resumen && vista === 'defensores' && <Defensores equipos={equipos} />}
        {resumen && vista === 'emparejamientos' && <Emparejamientos equipos={equipos} />}
        {resumen && vista === 'metodologia' && <Metodologia resumen={resumen} />}
      </main>
      <footer className="max-w-[1600px] mx-auto px-4 pb-6 text-[11px] text-slate-500">
        Datos: NFL Big Data Bowl (Next Gen Stats) y PFF, repositorio ThompsonJamesBliss/nfl-big-data-bowl-regional-event-data. DSA y SCS son métricas experimentales del proyecto.
      </footer>
    </div>
  )
}
