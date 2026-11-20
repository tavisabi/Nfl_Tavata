import { useEffect, useMemo, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import Campo from '../components/Campo'
import { Aviso, Cargando, Dato, Insignia, Tarjeta, ValorDSA } from '../components/ui'
import { ESTADO_CASTIGO, EVENTO, RESULTADO, colorDSA, num, pct } from '../format'
import type { Destino, GrupoSCS, Jugada, JugadaLista, Partido } from '../types'

const VELOCIDADES = [0.25, 0.5, 1, 2]

type Props = { destino: Destino | null; grupos: GrupoSCS[] }

export default function Visor({ destino, grupos }: Props) {
  const [partidos, setPartidos] = useState<Partido[]>([])
  const [gameId, setGameId] = useState<number | null>(destino?.gameId ?? null)
  const [lista, setLista] = useState<JugadaLista[]>([])
  const [playId, setPlayId] = useState<number | null>(destino?.playId ?? null)
  const [jugada, setJugada] = useState<Jugada | null>(null)
  const [cargando, setCargando] = useState(false)
  const [frame, setFrame] = useState(1)
  const [jugando, setJugando] = useState(false)
  const [vel, setVel] = useState(1)
  const [receptor, setReceptor] = useState<number | null>(destino?.nflId ?? null)
  const [estelas, setEstelas] = useState(false)
  const [filtro, setFiltro] = useState('')

  useEffect(() => { api<Partido[]>('partidos').then(p => { setPartidos(p); setGameId(g => g ?? p[0]?.gameId ?? null) }) }, [])
  useEffect(() => {
    if (destino) { setGameId(destino.gameId); setPlayId(destino.playId); setReceptor(destino.nflId ?? null) }
  }, [destino])
  useEffect(() => {
    if (gameId === null) return
    api<JugadaLista[]>(`partidos/${gameId}/jugadas`).then(l => {
      setLista(l)
      setPlayId(p => (p !== null && l.some(x => x.playId === p) ? p : l[0]?.playId ?? null))
    })
  }, [gameId])
  useEffect(() => {
    if (gameId === null || playId === null) return
    setCargando(true); setJugando(false)
    api<Jugada>(`jugada/${gameId}/${playId}`).then(j => {
      setJugada(j)
      setFrame(Math.max(1, j.snap))
      setReceptor(r => (r !== null && j.receptores.some(x => x.nflId === r) ? r : j.receptores[0]?.nflId ?? null))
    }).finally(() => setCargando(false))
  }, [gameId, playId])

  useEffect(() => {
    if (!jugando || !jugada) return
    const id = window.setInterval(() => {
      setFrame(f => { if (f >= jugada.frames) { setJugando(false); return f } return f + 1 })
    }, 100 / vel)
    return () => window.clearInterval(id)
  }, [jugando, vel, jugada])

  const rec = jugada?.receptores.find(r => r.nflId === receptor) ?? null
  const datos = useMemo(() => rec ? rec.serie.t.map((t, k) => ({
    t, sep: rec.serie.sep[k], vsep: rec.serie.vsep[k], asep: rec.serie.asep[k], dsa: rec.serie.dsa[k],
  })) : [], [rec])
  const tActual = jugada ? (frame - jugada.snap) / 10 : 0
  const k = jugada ? frame - jugada.snap : -1
  const nombres = useMemo(() => new Map(jugada?.jugadores.map(j => [j.nflId, j.nombre]) ?? []), [jugada])
  const listaFiltrada = lista.filter(l => !filtro || l.playDescription.toLowerCase().includes(filtro.toLowerCase()))
  const partido = partidos.find(p => p.gameId === gameId)

  const marcas = (
    <>
      {rec?.resumen.t_quiebre !== undefined && rec.resumen.creada && <ReferenceLine x={rec.resumen.t_quiebre} stroke="#f5b942" strokeDasharray="3 3" label={{ value: 'quiebre', fill: '#f5b942', fontSize: 10, position: 'insideTopLeft' }} />}
      {rec && <ReferenceLine x={rec.resumen.t_pase} stroke="#34d399" strokeDasharray="3 3" label={{ value: 'pase', fill: '#34d399', fontSize: 10, position: 'insideTopRight' }} />}
      {tActual >= 0 && <ReferenceLine x={tActual} stroke="#ffffff" strokeWidth={1.5} />}
    </>
  )
  const ejeX = <XAxis dataKey="t" type="number" domain={[0, 'dataMax']} tick={{ fill: '#94a3b8', fontSize: 10 }} tickFormatter={v => `${v}s`} stroke="#2a3c5e" />
  const tooltip = <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #2a3c5e', fontSize: 12 }} labelFormatter={v => `t = ${v} s tras el snap`} formatter={(v: unknown) => num(typeof v === 'number' ? v : null, 2)} />

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[300px_1fr] gap-4">
      {/* Selector de jugada */}
      <Tarjeta titulo="Elegir jugada" subtitulo="Solo jugadas analizadas (con snap, pase y rutas)">
        <select className="control w-full mb-2" value={gameId ?? ''} onChange={e => { setGameId(Number(e.target.value)); setPlayId(null) }}>
          {partidos.map(p => <option key={p.gameId} value={p.gameId}>Sem. {p.week} · {p.visitorTeamAbbr} @ {p.homeTeamAbbr}</option>)}
        </select>
        <input className="control w-full mb-2" placeholder="Buscar (p. ej. un apellido)" value={filtro} onChange={e => setFiltro(e.target.value)} />
        <div className="max-h-[520px] overflow-y-auto -mx-1 pr-1 space-y-1">
          {listaFiltrada.map(l => (
            <button key={l.playId} onClick={() => setPlayId(l.playId)}
              className={`w-full text-left px-2 py-1.5 rounded-md border text-xs ${l.playId === playId ? 'border-ventaja/60 bg-ventaja/10' : 'border-transparent hover:bg-noche-800'}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-400">Q{l.quarter} {l.gameClock} · {l.down}.º y {l.yardsToGo} · {l.possessionTeam}</span>
                <span className="flex items-center gap-1">
                  {l.castigo && <Insignia tono={l.anulada ? 'rojo' : 'ambar'}>{l.anulada ? 'Anulada' : 'Castigo'}</Insignia>}
                  <ValorDSA v={l.dsa_max} />
                </span>
              </div>
              <div className="text-slate-300 line-clamp-2 mt-0.5">{l.playDescription}</div>
            </button>
          ))}
        </div>
        <Aviso>El número a la derecha es la DSA máxima de la jugada en el momento del pase.</Aviso>
      </Tarjeta>

      <div className="space-y-4 min-w-0">
        {cargando && <Cargando texto="Cargando jugada…" />}
        {jugada && (
          <>
            <Tarjeta>
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Insignia tono="ambar">{jugada.meta.ofensiva} ataca</Insignia>
                <Insignia tono="azul">{jugada.meta.defensa} defiende</Insignia>
                <Insignia>{jugada.meta.down}.º y {jugada.meta.distancia}</Insignia>
                <Insignia>{jugada.meta.cobertura} · {jugada.meta.tipoCobertura === 'Man' ? 'man' : jugada.meta.tipoCobertura === 'Zone' ? 'zona' : jugada.meta.tipoCobertura}</Insignia>
                {jugada.meta.formacion && <Insignia>{jugada.meta.formacion}</Insignia>}
                {jugada.meta.playAction && <Insignia>Play action</Insignia>}
                <Insignia tono={jugada.meta.resultado === 'C' ? 'verde' : 'neutro'}>{RESULTADO[jugada.meta.resultado] ?? jugada.meta.resultado} · {jugada.meta.yardas} yd</Insignia>
                {jugada.meta.anulada && <Insignia tono="rojo">Jugada anulada</Insignia>}
                {partido && <span className="text-xs text-slate-500 ml-auto">Semana {partido.week} · {partido.gameDate}</span>}
              </div>
              <p className="text-sm text-slate-300">{jugada.meta.descripcion}</p>
              {jugada.meta.castigos.length > 0 && (
                <div className="mt-3 rounded-lg border border-ofensa/30 bg-ofensa/5 p-3">
                  <div className="etiqueta text-ofensa mb-1">Hubo castigo{jugada.meta.castigos.length > 1 ? 's' : ''}{jugada.meta.anulada ? ' · la jugada fue anulada' : ''}</div>
                  <ul className="space-y-1 text-sm">
                    {jugada.meta.castigos.map((c, n) => (
                      <li key={n}>
                        <span className="font-semibold text-slate-100">{c.falta_es}</span>
                        <span className="text-slate-400"> ({c.falta})</span>
                        {' — '}{c.jugador ? <>{c.jugador}{c.posicion ? `, ${c.posicion}` : ''}{c.equipo ? ` (${c.equipo})` : ''}</> : 'jugador no registrado'}
                        {' · '}<span className="text-slate-400">{ESTADO_CASTIGO[c.estado]}</span>
                        <div className="text-xs text-slate-400">Motivo: {c.motivo}.</div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Tarjeta>

            <div className="grid grid-cols-1 2xl:grid-cols-[1fr_320px] gap-4">
              <Tarjeta className="!p-3">
                <Campo jugada={jugada} frame={frame} receptor={receptor} onSeleccionar={setReceptor} estelas={estelas} />
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <button className="boton w-20" onClick={() => { if (frame >= jugada.frames) setFrame(1); setJugando(j => !j) }}>{jugando ? '❚❚ Pausa' : '▶ Play'}</button>
                  <button className="boton" onClick={() => { setJugando(false); setFrame(f => Math.max(1, f - 1)) }} aria-label="Frame anterior">◀</button>
                  <button className="boton" onClick={() => { setJugando(false); setFrame(f => Math.min(jugada.frames, f + 1)) }} aria-label="Frame siguiente">▶</button>
                  <button className="boton" onClick={() => { setJugando(false); setFrame(jugada.snap) }}>Snap</button>
                  <button className="boton" onClick={() => { setJugando(false); setFrame(jugada.pase) }}>Pase</button>
                  <input type="range" min={1} max={jugada.frames} value={frame} onChange={e => { setJugando(false); setFrame(Number(e.target.value)) }} className="flex-1 min-w-[160px] accent-emerald-400" />
                  <div className="flex gap-1">
                    {VELOCIDADES.map(v => <button key={v} className={`boton !px-2 ${vel === v ? 'boton-activo' : ''}`} onClick={() => setVel(v)}>{v}×</button>)}
                  </div>
                  <label className="flex items-center gap-1 text-xs text-slate-400"><input type="checkbox" checked={estelas} onChange={e => setEstelas(e.target.checked)} /> Estelas</label>
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-400">
                  <span className="tabular-nums">Frame {frame}/{jugada.frames} · {tActual >= 0 ? `${num(tActual, 1)} s tras el snap` : `${num(-tActual, 1)} s antes del snap`}</span>
                  {jugada.eventos.filter(e => e.frame === frame).map(e => <Insignia key={e.evento}>{EVENTO[e.evento] ?? e.evento}</Insignia>)}
                  <span className="ml-auto flex gap-3">
                    <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-ofensa mr-1" />Ofensiva</span>
                    <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-defensa mr-1" />Defensa</span>
                    <span><span className="inline-block w-3 h-0.5 bg-defensa mr-1 align-middle" />Scrimmage</span>
                    <span><span className="inline-block w-3 h-0.5 bg-yellow-400 mr-1 align-middle" />Primer down</span>
                  </span>
                </div>
                <Aviso>Dirección estandarizada: la ofensiva siempre ataca hacia la derecha. Clic en un receptor para analizarlo; el anillo punteado azul marca su posible emparejamiento.</Aviso>
              </Tarjeta>

              <Tarjeta titulo="Receptores de la jugada" subtitulo="DSA en el momento del pase">
                <div className="space-y-1.5">
                  {jugada.receptores.map(r => {
                    const d = r.serie.dsa[jugada.pase - jugada.snap]
                    return (
                      <button key={r.nflId} onClick={() => setReceptor(r.nflId)}
                        className={`w-full flex items-center justify-between px-2 py-1.5 rounded-md border text-sm ${r.nflId === receptor ? 'border-ofensa/60 bg-ofensa/10' : 'border-noche-700 hover:bg-noche-800'}`}>
                        <span className="text-left">{r.nombre} <span className="text-slate-500 text-xs">{r.posicion}</span>{r.objetivo && <span className="ml-1"><Insignia tono="verde">objetivo</Insignia></span>}</span>
                        <ValorDSA v={d} />
                      </button>
                    )
                  })}
                </div>
                {rec && (
                  <div className="mt-4 pt-3 border-t border-noche-700 grid grid-cols-2 gap-3">
                    <Dato etiqueta="DSA ahora" valor={<ValorDSA v={k >= 0 ? rec.serie.dsa[k] : null} />} nota="0-100, neutral a la profundidad" />
                    <Dato etiqueta="Separación ahora" valor={`${num(k >= 0 ? rec.serie.sep[k] : null, 1)} yd`} />
                    <Dato etiqueta="DSA al pase" valor={<ValorDSA v={rec.serie.dsa[jugada.pase - jugada.snap]} />} />
                    <Dato etiqueta="Separación al pase" valor={`${num(rec.resumen.sep_pase, 1)} yd`} />
                    <Dato etiqueta="Quiebre" valor={rec.resumen.creada ? `${num(rec.resumen.t_quiebre, 1)} s` : 'sin creación'} nota={rec.resumen.creada ? `ganancia +${num(rec.resumen.ganancia, 1)} yd` : 'ganancia < 1 yd'} />
                    <Dato etiqueta="Profundidad al pase" valor={`${num(rec.resumen.profundidad, 1)} yd`} />
                    <div className="col-span-2">
                      <div className="etiqueta">Firma de movimiento (SCS)</div>
                      <div className="text-sm">{rec.scs >= 0 ? grupos.find(g => g.id === rec.scs)?.nombre ?? '–' : 'No aplica (sin creación de separación)'}</div>
                    </div>
                    <div className="col-span-2">
                      <div className="etiqueta">Posible emparejamiento</div>
                      <div className="text-sm">{rec.defensorPrincipal !== null ? nombres.get(rec.defensorPrincipal) : '–'} <span className="text-slate-500">· confianza {pct(rec.confianza)}</span></div>
                      <Aviso>Defensor más cercano durante más tiempo de la ruta. No es la asignación real de la defensa.</Aviso>
                    </div>
                  </div>
                )}
              </Tarjeta>
            </div>

            {rec && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <Tarjeta titulo="Separación (yd)" subtitulo="¿Cuánto espacio hay entre el receptor y el defensor más cercano?">
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                      <CartesianGrid stroke="#1d2c47" />{ejeX}
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" domain={[0, 10]} />
                      {tooltip}{marcas}
                      <Line type="monotone" dataKey="sep" name="Separación" stroke="#34d399" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                </Tarjeta>
                <Tarjeta titulo="Velocidad y aceleración relativas" subtitulo="¿El receptor gana o pierde espacio, y cada vez más rápido?">
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                      <CartesianGrid stroke="#1d2c47" />{ejeX}
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" />
                      {tooltip}{marcas}
                      <ReferenceLine y={0} stroke="#475569" />
                      <Line type="monotone" dataKey="vsep" name="Velocidad (yd/s)" stroke="#f5b942" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls />
                      <Line type="monotone" dataKey="asep" name="Aceleración (yd/s²)" stroke="#a78bfa" dot={false} strokeWidth={1.5} isAnimationActive={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="flex gap-3 text-[11px] text-slate-400"><span className="text-ofensa">— velocidad (yd/s)</span><span className="text-violet-400">— aceleración (yd/s²)</span></div>
                </Tarjeta>
                <Tarjeta titulo="DSA a lo largo de la jugada" subtitulo="¿En qué momento el receptor pasa a estar en ventaja?">
                  <ResponsiveContainer width="100%" height={180}>
                    <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                      <CartesianGrid stroke="#1d2c47" />{ejeX}
                      <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" domain={[0, 100]} />
                      {tooltip}{marcas}
                      <ReferenceLine y={75} stroke="#34d399" strokeOpacity={0.4} strokeDasharray="2 4" />
                      <Line type="monotone" dataKey="dsa" name="DSA" stroke={colorDSA(rec.serie.dsa[jugada.pase - jugada.snap])} dot={false} strokeWidth={2} isAnimationActive={false} connectNulls />
                    </LineChart>
                  </ResponsiveContainer>
                  <Aviso>Antes del pase, la DSA se lee como "si el pase saliera en este instante". La línea punteada marca el cuartil superior (75).</Aviso>
                </Tarjeta>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
