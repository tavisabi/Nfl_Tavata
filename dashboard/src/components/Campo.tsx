import { useMemo } from 'react'
import type { Jugada } from '../types'
import { num } from '../format'

const LARGO = 120
const ANCHO = 53.3

type Props = {
  jugada: Jugada
  frame: number                       // 1-based
  receptor: number | null
  onSeleccionar: (nflId: number) => void
  estelas: boolean
}

function ruta(xs: (number | null)[], ys: (number | null)[], hasta: number, desde = 0): string {
  let d = ''
  for (let i = desde; i < Math.min(hasta, xs.length); i++) {
    const x = xs[i], y = ys[i]
    if (x === null || y === null) continue
    d += (d ? 'L' : 'M') + x.toFixed(2) + ' ' + y.toFixed(2)
  }
  return d
}

export default function Campo({ jugada, frame, receptor, onSeleccionar, estelas }: Props) {
  const i = frame - 1
  const t = frame - jugada.snap                           // índice en las series (empiezan en el snap)
  const rec = jugada.receptores.find(r => r.nflId === receptor) ?? null
  const cercano = rec && t >= 0 && t < rec.serie.cercano.length ? rec.serie.cercano[t] : null
  const principal = rec?.defensorPrincipal ?? null
  const receptoresIds = useMemo(() => new Set(jugada.receptores.map(r => r.nflId)), [jugada])
  const porId = useMemo(() => new Map(jugada.jugadores.map(j => [j.nflId, j])), [jugada])
  const jr = receptor !== null ? porId.get(receptor) : undefined
  const jd = cercano !== null ? porId.get(cercano) : undefined
  const primerDown = jugada.losX + jugada.meta.distancia
  const sep = rec && t >= 0 ? rec.serie.sep[t] : null

  const lineas = []
  for (let x = 10; x <= 110; x += 5) {
    lineas.push(<line key={x} x1={x} x2={x} y1={0} y2={ANCHO} stroke="#ffffff" strokeOpacity={x % 10 === 0 ? 0.35 : 0.15} strokeWidth={x % 10 === 0 ? 0.18 : 0.1} />)
  }
  const numeros = []
  for (let k = 1; k <= 9; k++) {
    const x = 10 + 10 * k
    const n = Math.min(k * 10, 100 - k * 10)
    for (const y of [5, ANCHO - 3.5]) {
      numeros.push(<text key={`${x}-${y}`} x={x} y={y} fill="#ffffff" fillOpacity={0.35} fontSize={2.6} textAnchor="middle" fontWeight={600}>{n}</text>)
    }
  }
  const hash = []
  for (let x = 11; x < 110; x++) {
    for (const y of [ANCHO / 2 - 3.08, ANCHO / 2 + 3.08]) hash.push(<line key={`${x}-${y}`} x1={x} x2={x} y1={y - 0.4} y2={y + 0.4} stroke="#fff" strokeOpacity={0.2} strokeWidth={0.08} />)
  }

  return (
    <svg viewBox={`-2 -2 ${LARGO + 4} ${ANCHO + 4}`} className="w-full h-auto select-none" role="img" aria-label="Campo de juego">
      <defs>
        <linearGradient id="cesped" x1="0" x2="1">
          {Array.from({ length: 12 }).map((_, k) => (
            <stop key={k} offset={`${(k / 12) * 100}%`} stopColor={k % 2 ? '#124e30' : '#14583a'} />
          ))}
        </linearGradient>
      </defs>
      <rect x={0} y={0} width={LARGO} height={ANCHO} fill="url(#cesped)" rx={0.6} />
      <rect x={0} y={0} width={10} height={ANCHO} fill="#0c3a24" />
      <rect x={110} y={0} width={10} height={ANCHO} fill="#0c3a24" />
      <text x={5} y={ANCHO / 2} fill="#fff" fillOpacity={0.25} fontSize={3} textAnchor="middle" transform={`rotate(-90 5 ${ANCHO / 2})`} fontWeight={700} letterSpacing={0.6}>{jugada.meta.defensa}</text>
      <text x={115} y={ANCHO / 2} fill="#fff" fillOpacity={0.25} fontSize={3} textAnchor="middle" transform={`rotate(90 115 ${ANCHO / 2})`} fontWeight={700} letterSpacing={0.6}>ANOTACIÓN</text>
      {lineas}{hash}{numeros}
      <rect x={0} y={0} width={LARGO} height={ANCHO} fill="none" stroke="#fff" strokeOpacity={0.6} strokeWidth={0.25} />

      {/* Línea de scrimmage y de primer down */}
      <line x1={jugada.losX} x2={jugada.losX} y1={0} y2={ANCHO} stroke="#5ab4ff" strokeWidth={0.3} strokeOpacity={0.9} />
      {primerDown < 110 && <line x1={primerDown} x2={primerDown} y1={0} y2={ANCHO} stroke="#facc15" strokeWidth={0.3} strokeOpacity={0.9} />}

      {/* Estelas */}
      {estelas && jugada.jugadores.map(j => (
        <path key={`e${j.nflId}`} d={ruta(j.x, j.y, i + 1)} fill="none" stroke={j.lado === 'ofensiva' ? '#f5b942' : '#5ab4ff'} strokeOpacity={0.18} strokeWidth={0.15} />
      ))}
      {jd && <path d={ruta(jd.x, jd.y, i + 1, Math.max(0, jugada.snap - 1))} fill="none" stroke="#5ab4ff" strokeWidth={0.32} strokeDasharray="0.8 0.5" />}
      {jr && <path d={ruta(jr.x, jr.y, i + 1, Math.max(0, jugada.snap - 1))} fill="none" stroke="#f5b942" strokeWidth={0.4} />}

      {/* Línea de separación */}
      {jr && jd && jr.x[i] !== null && jd.x[i] !== null && (
        <g>
          <line x1={jr.x[i]!} y1={jr.y[i]!} x2={jd.x[i]!} y2={jd.y[i]!} stroke="#34d399" strokeWidth={0.28} strokeDasharray="0.5 0.35" />
          <g transform={`translate(${(jr.x[i]! + jd.x[i]!) / 2} ${(jr.y[i]! + jd.y[i]!) / 2 - 1.6})`}>
            <rect x={-3.2} y={-1.25} width={6.4} height={2.2} rx={0.5} fill="#070b14" fillOpacity={0.85} stroke="#34d399" strokeWidth={0.12} />
            <text x={0} y={0.4} fontSize={1.45} fill="#34d399" textAnchor="middle" fontWeight={700}>{num(sep, 1)} yd</text>
          </g>
        </g>
      )}

      {/* Jugadores */}
      {jugada.jugadores.map(j => {
        const x = j.x[i], y = j.y[i]
        if (x === null || y === null) return null
        const o = j.o[i]
        const esRec = receptoresIds.has(j.nflId)
        const sel = j.nflId === receptor
        const esPrincipal = j.nflId === principal
        const color = j.lado === 'ofensiva' ? '#f5b942' : '#5ab4ff'
        const ox = o !== null ? Math.sin((o * Math.PI) / 180) * 1.5 : 0
        const oy = o !== null ? Math.cos((o * Math.PI) / 180) * 1.5 : 0
        return (
          <g key={j.nflId} onClick={esRec ? () => onSeleccionar(j.nflId) : undefined} style={{ cursor: esRec ? 'pointer' : 'default' }}>
            <title>{`${j.nombre} · ${j.posicion}${j.dorsal !== null ? ' #' + j.dorsal : ''}`}</title>
            {o !== null && <line x1={x} y1={y} x2={x + ox} y2={y + oy} stroke={color} strokeWidth={0.18} strokeOpacity={0.8} />}
            {sel && <circle cx={x} cy={y} r={1.75} fill="none" stroke="#ffffff" strokeWidth={0.22} />}
            {esPrincipal && !sel && <circle cx={x} cy={y} r={1.6} fill="none" stroke="#5ab4ff" strokeWidth={0.18} strokeDasharray="0.45 0.3" />}
            <circle cx={x} cy={y} r={1.05} fill={color} fillOpacity={esRec || j.lado === 'defensa' ? 1 : 0.55} stroke="#070b14" strokeWidth={0.12} />
            {j.dorsal !== null && <text x={x} y={y + 0.42} fontSize={1.05} textAnchor="middle" fill="#070b14" fontWeight={800}>{j.dorsal}</text>}
          </g>
        )
      })}

      {/* Balón */}
      {jugada.balon.x[i] !== null && jugada.balon.y[i] !== null && (
        <ellipse cx={jugada.balon.x[i]!} cy={jugada.balon.y[i]!} rx={0.55} ry={0.35} fill="#8b5a2b" stroke="#fff" strokeWidth={0.08} />
      )}
    </svg>
  )
}
