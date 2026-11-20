import { useEffect, useState } from 'react'
import { api, query } from '../api'
import { Aviso, Cargando, Insignia, Tarjeta, ValorDSA } from '../components/ui'
import { num, pct, signo } from '../format'
import type { Emparejamiento } from '../types'

export default function Emparejamientos({ equipos }: { equipos: string[] }) {
  const [ofensiva, setOfensiva] = useState('')
  const [defensa, setDefensa] = useState('')
  const [minimo, setMinimo] = useState(4)
  const [filas, setFilas] = useState<Emparejamiento[] | null>(null)

  useEffect(() => {
    setFilas(null)
    api<Emparejamiento[]>('emparejamientos' + query({ ofensiva, defensa, min_rutas: minimo })).then(setFilas)
  }, [ofensiva, defensa, minimo])

  return (
    <Tarjeta titulo="Duelos receptor-defensor en cobertura man"
      subtitulo="Posibles emparejamientos: defensor más cercano durante más tiempo de la ruta, solo en jugadas que PFF clasifica como man">
      <div className="flex flex-wrap gap-2 mb-3 items-center">
        <select className="control" value={ofensiva} onChange={e => setOfensiva(e.target.value)}>
          <option value="">Cualquier ofensiva</option>
          {equipos.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <span className="text-slate-500 text-sm">vs.</span>
        <select className="control" value={defensa} onChange={e => setDefensa(e.target.value)}>
          <option value="">Cualquier defensa</option>
          {equipos.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        <label className="text-xs text-slate-400 flex items-center gap-2">Mínimo de rutas
          <input type="number" min={1} className="control w-16" value={minimo} onChange={e => setMinimo(Number(e.target.value) || 1)} />
        </label>
        <span className="ml-auto"><Insignia tono="ambar">Muestras pequeñas: revisar en video</Insignia></span>
      </div>
      {!filas ? <Cargando /> : (
        <div className="overflow-x-auto max-h-[620px]">
          <table className="tabla w-full text-sm">
            <thead className="sticky top-0 bg-noche-900"><tr>
              <th>Receptor</th><th>Defensor</th><th>Equipos</th><th>Alineación</th><th className="text-right">Rutas</th>
              <th className="text-right">DSA-OE</th><th className="text-right">DSA media</th><th className="text-right">Sep. al pase</th>
              <th className="text-right">Pases</th><th className="text-right">Completos</th><th className="text-right">Confianza</th>
            </tr></thead>
            <tbody>
              {filas.map(e => (
                <tr key={`${e.nflId}-${e.defId}`} className="!cursor-default">
                  <td className="font-medium text-slate-100">{e.receptor} <span className="text-slate-500 text-xs">{e.pos_receptor}</span></td>
                  <td>{e.defensor} <span className="text-slate-500 text-xs">{e.pos_defensor}</span></td>
                  <td>{e.equipo_of} vs {e.equipo_def}</td><td>{e.alineacion}</td>
                  <td className="text-right tabular-nums">{e.rutas}</td>
                  <td className={`text-right tabular-nums font-semibold ${e.dsa_oe >= 0 ? 'text-ventaja' : 'text-alerta'}`}>{signo(e.dsa_oe, 0)}</td>
                  <td className="text-right"><ValorDSA v={e.dsa_media} /></td>
                  <td className="text-right tabular-nums">{num(e.sep_pase, 2)} yd</td>
                  <td className="text-right tabular-nums">{e.objetivos}</td>
                  <td className="text-right tabular-nums">{num(e.completos, 0)}</td>
                  <td className="text-right tabular-nums">{pct(e.conf_media)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filas.length === 0 && <p className="text-sm text-slate-400 p-4">Sin duelos con esos filtros.</p>}
        </div>
      )}
      <Aviso>
        En zona, el defensor más cercano refleja el área que cubre el esquema y no un duelo; por eso solo se usan jugadas en man.
        Aun en man, el defensor más cercano puede no ser el asignado: es una inferencia, no la asignación real.
      </Aviso>
    </Tarjeta>
  )
}
