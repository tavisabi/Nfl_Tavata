import { useEffect, useState } from 'react'
import { api, query } from '../api'
import { Aviso, Cargando, Tarjeta, ValorDSA } from '../components/ui'
import { num, pct, signo } from '../format'
import type { Defensor } from '../types'

type Orden = 'dsa_oe_permitida_ajustada' | 'recuperacion' | 'sep_permitida'

export default function Defensores({ equipos }: { equipos: string[] }) {
  const [equipo, setEquipo] = useState('')
  const [minimo, setMinimo] = useState(80)
  const [orden, setOrden] = useState<Orden>('dsa_oe_permitida_ajustada')
  const [filas, setFilas] = useState<Defensor[] | null>(null)

  useEffect(() => {
    setFilas(null)
    api<Defensor[]>('defensores' + query({ equipo, min_rutas: minimo })).then(setFilas)
  }, [equipo, minimo])

  const ordenadas = [...(filas ?? [])].sort((a, b) => {
    if (orden === 'recuperacion') return (b.objetivos >= 10 ? b.recuperacion ?? -99 : -99) - (a.objetivos >= 10 ? a.recuperacion ?? -99 : -99)
    if (orden === 'sep_permitida') return a.sep_permitida - b.sep_permitida
    return a.dsa_oe_permitida_ajustada - b.dsa_oe_permitida_ajustada
  })

  return (
    <Tarjeta titulo="Defensores: cuánta ventaja permiten y qué tan rápido recuperan"
      subtitulo="Calculado sobre las rutas en las que fueron el posible emparejamiento (confianza ≥ 50 %)">
      <div className="flex flex-wrap gap-2 mb-3 items-center">
        <select className="control" value={equipo} onChange={e => setEquipo(e.target.value)}>
          <option value="">Todos los equipos</option>
          {equipos.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <label className="text-xs text-slate-400 flex items-center gap-2">Mínimo de rutas
          <input type="number" min={10} step={10} className="control w-20" value={minimo} onChange={e => setMinimo(Number(e.target.value) || 10)} />
        </label>
        <select className="control" value={orden} onChange={e => setOrden(e.target.value as Orden)}>
          <option value="dsa_oe_permitida_ajustada">Ordenar: menos ventaja permitida</option>
          <option value="recuperacion">Ordenar: recuperación más rápida tras el pase</option>
          <option value="sep_permitida">Ordenar: menor separación permitida</option>
        </select>
      </div>
      {!filas ? <Cargando /> : (
        <div className="overflow-x-auto max-h-[620px]">
          <table className="tabla w-full text-sm">
            <thead className="sticky top-0 bg-noche-900"><tr>
              <th>Defensor</th><th>Equipo</th><th className="text-right">Rutas</th><th className="text-right">DSA-OE permitida aj.</th>
              <th className="text-right">DSA permitida</th><th className="text-right">Sep. permitida</th><th className="text-right">Pases en su zona</th>
              <th className="text-right">Completos</th><th className="text-right">Recuperación</th><th className="text-right">Rutas en man</th><th className="text-right">Confianza</th>
            </tr></thead>
            <tbody>
              {ordenadas.map(d => (
                <tr key={d.nflId} className="!cursor-default">
                  <td className="font-medium text-slate-100">{d.displayName} <span className="text-slate-500 text-xs">{d.officialPosition}</span></td>
                  <td>{d.equipo}</td><td className="text-right tabular-nums">{d.rutas}</td>
                  <td className={`text-right tabular-nums font-semibold ${d.dsa_oe_permitida_ajustada <= 0 ? 'text-ventaja' : 'text-alerta'}`}>{signo(d.dsa_oe_permitida_ajustada)}</td>
                  <td className="text-right"><ValorDSA v={d.dsa_permitida} /></td>
                  <td className="text-right tabular-nums">{num(d.sep_permitida, 2)} yd</td>
                  <td className="text-right tabular-nums">{d.objetivos}</td>
                  <td className="text-right tabular-nums">{d.objetivos ? `${num(d.completos_permitidos, 0)} (${pct(d.completos_permitidos / d.objetivos)})` : '–'}</td>
                  <td className="text-right tabular-nums">{d.objetivos >= 10 ? `${signo(d.recuperacion, 2)} yd/s` : '–'}</td>
                  <td className="text-right tabular-nums">{d.rutas_man}</td>
                  <td className="text-right tabular-nums">{pct(d.conf_media)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Aviso>
        DSA-OE permitida negativa (verde) = los receptores que cubre obtienen menos ventaja que lo esperado para su rol. Recuperación =
        yardas por segundo que reduce la separación en el medio segundo posterior al pase, en pases dirigidos a su receptor (se muestra con ≥ 10 pases);
        en promedio la separación sigue creciendo tras el pase, por eso los valores suelen ser negativos. El emparejamiento es inferido: el dataset no indica quién cubre a quién.
      </Aviso>
    </Tarjeta>
  )
}
