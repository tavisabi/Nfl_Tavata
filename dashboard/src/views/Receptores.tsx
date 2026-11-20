import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, query } from '../api'
import { Aviso, Barra, Cargando, Dato, Insignia, Tarjeta, ValorDSA } from '../components/ui'
import { RESULTADO, num, pct, signo } from '../format'
import type { Destino, GrupoSCS, PerfilReceptor, Receptor } from '../types'

type Props = { equipos: string[]; grupos: GrupoSCS[]; abrir: (d: Destino) => void }
const ALINEACIONES = ['Abierto', 'Slot', 'TE', 'Backfield']
const COLORES_SCS = ['#f5b942', '#5ab4ff', '#a78bfa', '#34d399', '#f87171', '#94a3b8']

function firma(r: Receptor, k: number): number[] {
  return Array.from({ length: k }, (_, j) => (r[`scs_${j}`] as number | null) ?? 0)
}

export default function Receptores({ equipos, grupos, abrir }: Props) {
  const [equipo, setEquipo] = useState('')
  const [alin, setAlin] = useState('Abierto,Slot,TE')
  const [minimo, setMinimo] = useState(80)
  const [filas, setFilas] = useState<Receptor[] | null>(null)
  const [sel, setSel] = useState<number | null>(null)
  const [perfil, setPerfil] = useState<PerfilReceptor | null>(null)
  const [comparar, setComparar] = useState<number[]>([])

  useEffect(() => {
    setFilas(null)
    api<Receptor[]>('receptores' + query({ equipo, min_rutas: minimo })).then(setFilas)
  }, [equipo, minimo])
  useEffect(() => {
    if (sel === null) { setPerfil(null); return }
    api<PerfilReceptor>(`receptores/${sel}`).then(setPerfil)
  }, [sel])

  const visibles = (filas ?? []).filter(r => alin.split(',').includes(r.alineacion))
  const liga = perfil ? perfil.liga_scs.map(n => n / perfil.liga_scs.reduce((a, b) => a + b, 0)) : []
  const comparados = (filas ?? []).filter(r => comparar.includes(r.nflId))
  const alternar = (id: number) => setComparar(c => c.includes(id) ? c.filter(x => x !== id) : [...c, id].slice(-2))

  return (
    <div className="space-y-4">
      <Tarjeta titulo="Receptores que crean ventaja" subtitulo="Ordenados por DSA sobre lo esperado para su alineación y tipo de cobertura (ajustada por tamaño de muestra)">
        <div className="flex flex-wrap gap-2 mb-3 items-center">
          <select className="control" value={equipo} onChange={e => setEquipo(e.target.value)}>
            <option value="">Todos los equipos</option>
            {equipos.map(e => <option key={e} value={e}>{e}</option>)}
          </select>
          <select className="control" value={alin} onChange={e => setAlin(e.target.value)}>
            <option value="Abierto,Slot,TE">Abiertos, slot y TE</option>
            {ALINEACIONES.map(a => <option key={a} value={a}>{a}</option>)}
            <option value={ALINEACIONES.join(',')}>Todas las alineaciones</option>
          </select>
          <label className="text-xs text-slate-400 flex items-center gap-2">Mínimo de rutas
            <input type="number" min={10} step={10} className="control w-20" value={minimo} onChange={e => setMinimo(Number(e.target.value) || 10)} />
          </label>
          <span className="text-xs text-slate-500 ml-auto">Marca hasta 2 receptores para compararlos · clic en una fila para ver el perfil</span>
        </div>
        {!filas ? <Cargando /> : (
          <div className="overflow-x-auto max-h-[440px]">
            <table className="tabla w-full text-sm">
              <thead className="sticky top-0 bg-noche-900"><tr>
                <th></th><th>Receptor</th><th>Equipo</th><th>Alineación</th><th className="text-right">Rutas</th>
                <th className="text-right">DSA-OE aj.</th><th className="text-right">DSA media</th><th className="text-right">En cuartil sup.</th>
                <th className="text-right">Sep. al pase</th><th className="text-right">Crea sep.</th><th className="text-right">Quiebre</th>
                <th className="text-right">vs man</th><th className="text-right">vs zona</th>
              </tr></thead>
              <tbody>
                {visibles.map(r => (
                  <tr key={r.nflId} onClick={() => setSel(r.nflId)} className={sel === r.nflId ? 'bg-noche-800' : ''}>
                    <td onClick={e => e.stopPropagation()}><input type="checkbox" checked={comparar.includes(r.nflId)} onChange={() => alternar(r.nflId)} /></td>
                    <td className="font-medium text-slate-100">{r.displayName} <span className="text-slate-500 text-xs">{r.officialPosition}</span></td>
                    <td>{r.equipo}</td><td>{r.alineacion}</td><td className="text-right tabular-nums">{r.rutas}</td>
                    <td className={`text-right tabular-nums font-semibold ${r.dsa_oe_ajustada >= 0 ? 'text-ventaja' : 'text-alerta'}`}>{signo(r.dsa_oe_ajustada)}</td>
                    <td className="text-right"><ValorDSA v={r.dsa_media} /></td>
                    <td className="text-right tabular-nums">{pct(r.consistencia)}</td>
                    <td className="text-right tabular-nums">{num(r.sep_pase, 1)} yd</td>
                    <td className="text-right tabular-nums">{pct(r.tasa_creacion)}</td>
                    <td className="text-right tabular-nums">{r.t_creacion !== null ? `${num(r.t_creacion, 1)} s` : '–'}</td>
                    <td className="text-right tabular-nums">{r.rutas_man >= 15 ? signo(r.dsa_oe_man) : '–'} <span className="text-slate-500 text-[10px]">({r.rutas_man})</span></td>
                    <td className="text-right tabular-nums">{r.rutas_zona >= 15 ? signo(r.dsa_oe_zona) : '–'} <span className="text-slate-500 text-[10px]">({r.rutas_zona})</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibles.length === 0 && <p className="text-sm text-slate-400 p-4">Sin receptores con esos filtros.</p>}
          </div>
        )}
        <Aviso>DSA-OE: puntos de DSA por encima (+) o por debajo (−) del promedio de las rutas con la misma alineación y tipo de cobertura. "En cuartil sup." = rutas en el 25 % superior de su rol (lo esperado es 25 %). vs man / zona entre paréntesis: número de rutas; se muestra con ≥ 15.</Aviso>
      </Tarjeta>

      {comparados.length === 2 && (
        <Tarjeta titulo={`Comparación: ${comparados[0].displayName} vs. ${comparados[1].displayName}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <table className="tabla text-sm w-full">
              <thead><tr><th>Métrica</th><th className="text-right">{comparados[0].displayName}</th><th className="text-right">{comparados[1].displayName}</th></tr></thead>
              <tbody>
                {([
                  ['Rutas', (r: Receptor) => String(r.rutas)],
                  ['DSA-OE ajustada', (r: Receptor) => signo(r.dsa_oe_ajustada)],
                  ['DSA media al pase', (r: Receptor) => num(r.dsa_media, 1)],
                  ['Rutas en cuartil superior', (r: Receptor) => pct(r.consistencia)],
                  ['Separación media al pase', (r: Receptor) => `${num(r.sep_pase, 2)} yd`],
                  ['Rutas que crean separación', (r: Receptor) => pct(r.tasa_creacion)],
                  ['Quiebre mediano', (r: Receptor) => r.t_creacion !== null ? `${num(r.t_creacion, 1)} s` : '–'],
                  ['Ganancia media al crear', (r: Receptor) => r.ganancia !== null ? `${num(r.ganancia, 2)} yd` : '–'],
                  ['DSA-OE vs man', (r: Receptor) => `${signo(r.dsa_oe_man)} (${r.rutas_man})`],
                  ['DSA-OE vs zona', (r: Receptor) => `${signo(r.dsa_oe_zona)} (${r.rutas_zona})`],
                ] as [string, (r: Receptor) => string][]).map(([n, f]) => (
                  <tr key={n} className="!cursor-default"><td className="text-slate-400">{n}</td><td className="text-right tabular-nums">{f(comparados[0])}</td><td className="text-right tabular-nums">{f(comparados[1])}</td></tr>
                ))}
              </tbody>
            </table>
            <div>
              <div className="etiqueta mb-2">Firma de movimiento: % de sus creaciones de separación</div>
              {grupos.map(g => (
                <div key={g.id} className="mb-3">
                  <div className="text-xs text-slate-300 mb-1">{g.nombre}</div>
                  {comparados.map((r, n) => (
                    <div key={r.nflId} className="flex items-center gap-2 text-[11px] mb-0.5">
                      <span className="w-24 truncate text-slate-400">{r.displayName.split(' ').slice(-1)[0]}</span>
                      <Barra valor={firma(r, grupos.length)[g.id]} color={n ? '#5ab4ff' : '#f5b942'} />
                      <span className="w-10 text-right tabular-nums">{pct(firma(r, grupos.length)[g.id])}</span>
                    </div>
                  ))}
                </div>
              ))}
              <Aviso>Basado en {comparados[0].n_creaciones} y {comparados[1].n_creaciones} creaciones de separación respectivamente.</Aviso>
            </div>
          </div>
        </Tarjeta>
      )}

      {sel !== null && !perfil && <Cargando texto="Cargando perfil…" />}
      {perfil && (
        <Tarjeta titulo={`${perfil.perfil.displayName} · ${perfil.perfil.equipo} · ${perfil.perfil.officialPosition}`}
          subtitulo={`Alineación habitual: ${perfil.perfil.alineacion} · ${perfil.perfil.rutas} rutas · ${perfil.perfil.objetivos} veces objetivo`}
          accion={<button className="boton" onClick={() => setSel(null)}>Cerrar</button>}>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-5">
            <Dato etiqueta="DSA-OE ajustada" valor={signo(perfil.perfil.dsa_oe_ajustada)} color={perfil.perfil.dsa_oe_ajustada >= 0 ? '#34d399' : '#f87171'} />
            <Dato etiqueta="DSA media al pase" valor={<ValorDSA v={perfil.perfil.dsa_media} />} />
            <Dato etiqueta="Rutas en cuartil superior" valor={pct(perfil.perfil.consistencia)} nota="esperado: 25%" />
            <Dato etiqueta="Separación al pase" valor={`${num(perfil.perfil.sep_pase, 2)} yd`} />
            <Dato etiqueta="Crea separación" valor={pct(perfil.perfil.tasa_creacion)} nota={`${perfil.perfil.n_creaciones} creaciones`} />
            <Dato etiqueta="Quiebre mediano" valor={perfil.perfil.t_creacion !== null ? `${num(perfil.perfil.t_creacion, 1)} s` : '–'} nota="tras el snap" />
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div>
              <div className="etiqueta mb-2">Firma de movimiento vs. la liga</div>
              {grupos.map(g => {
                const v = firma(perfil.perfil, grupos.length)[g.id]
                return (
                  <div key={g.id} className="mb-2">
                    <div className="flex justify-between text-xs"><span className="text-slate-300">{g.nombre}</span><span className="tabular-nums">{pct(v)} <span className="text-slate-500">(liga {pct(liga[g.id])})</span></span></div>
                    <Barra valor={v} color={COLORES_SCS[g.id]} />
                  </div>
                )
              })}
            </div>
            <div>
              <div className="etiqueta mb-2">Distribución de su DSA al pase</div>
              <ResponsiveContainer width="100%" height={170}>
                <BarChart data={perfil.distribucion_dsa.map((n, i) => ({ rango: `${i * 10}`, n }))} margin={{ left: -24, right: 4, top: 4 }}>
                  <CartesianGrid stroke="#1d2c47" vertical={false} />
                  <XAxis dataKey="rango" tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" allowDecimals={false} />
                  <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #2a3c5e', fontSize: 12 }} labelFormatter={v => `DSA ${v}-${Number(v) + 10}`} formatter={(v: unknown) => [String(v), 'rutas']} />
                  <Bar dataKey="n" fill="#34d399" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <div className="etiqueta mb-2">Por esquema de cobertura (≥ 5 rutas)</div>
              <table className="tabla w-full text-sm">
                <thead><tr><th>Cobertura</th><th className="text-right">Rutas</th><th className="text-right">DSA</th><th className="text-right">Sep.</th></tr></thead>
                <tbody>{perfil.por_cobertura.map(c => (
                  <tr key={c.pff_passCoverage} className="!cursor-default"><td>{c.pff_passCoverage}</td><td className="text-right tabular-nums">{c.rutas}</td><td className="text-right"><ValorDSA v={c.dsa} /></td><td className="text-right tabular-nums">{num(c.sep, 1)} yd</td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
          <div className="mt-5">
            <div className="etiqueta mb-2">Sus jugadas con más ventaja (clic para abrir en el visor)</div>
            <div className="overflow-x-auto max-h-72">
              <table className="tabla w-full text-sm">
                <thead className="sticky top-0 bg-noche-900"><tr><th>Sem.</th><th>Rival</th><th>Cobertura</th><th className="text-right">DSA</th><th className="text-right">DSA-OE</th><th className="text-right">Sep.</th><th className="text-right">Quiebre</th><th>Objetivo</th><th>Posible emparejamiento</th></tr></thead>
                <tbody>{perfil.jugadas.map(j => (
                  <tr key={`${j.gameId}-${j.playId}`} onClick={() => abrir({ gameId: j.gameId, playId: j.playId, nflId: perfil.perfil.nflId })}>
                    <td>{j.week}</td><td>{j.defensiveTeam}</td><td>{j.pff_passCoverage}</td>
                    <td className="text-right"><ValorDSA v={j.dsa} /></td><td className="text-right tabular-nums">{signo(j.dsa_oe)}</td>
                    <td className="text-right tabular-nums">{num(j.sep_pase, 1)} yd</td><td className="text-right tabular-nums">{num(j.t_quiebre, 1)} s</td>
                    <td>{j.objetivo ? <Insignia tono={j.passResult === 'C' ? 'verde' : 'neutro'}>{RESULTADO[j.passResult] ?? j.passResult}</Insignia> : <span className="text-slate-500">–</span>}</td>
                    <td className="text-slate-400">{j.defensor ?? '–'} {j.defensor && <span className="text-[10px]">({pct(j.def_conf)})</span>}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        </Tarjeta>
      )}
    </div>
  )
}
