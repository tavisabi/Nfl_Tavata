import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Aviso, Barra, Tarjeta } from '../components/ui'
import { num, pct } from '../format'
import type { Resumen } from '../types'

const LIMITACIONES = [
  'Solo 8 semanas de la temporada 2021 (122 partidos) y solo jugadas de pase.',
  'El dataset no indica quién cubre a quién: los emparejamientos son inferidos y solo se forman en cobertura man.',
  'El dataset no etiqueta el tipo de ruta: las firmas SCS son grupos estadísticos, no rutas del playbook.',
  'El tracking termina 0,5 s después del pase: no se mide la separación en la recepción.',
  'El receptor objetivo se recupera del texto oficial de la jugada (96,3 % de los pases; 50/50 correctos en una revisión manual).',
  'Asociación, no causalidad: la presión, la decisión del QB y la precisión no se controlan.',
  'Las jugadas anuladas por castigo se mantienen en el análisis; el visor indica la falta y su motivo.',
]

export default function Metodologia({ resumen }: { resumen: Resumen }) {
  const v = resumen.validacion
  const modelos = [
    ['Solo intercepto', v.baseline_intercepto], ['Profundidad', v.baseline_profundidad],
    ['Separación + profundidad', v.baseline_sep_profundidad], ['DSA neutral + profundidad', v.dsa_neutral_profundidad],
  ] as const
  const maxPeso = Math.max(...resumen.componentes.map(c => c.peso))

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Tarjeta titulo="Cómo se calcula la DSA" subtitulo="Dynamic Separation Advantage · métrica experimental propia, no oficial de la NFL">
        <ol className="text-sm text-slate-300 space-y-2 list-decimal pl-5">
          <li>En cada frame se mide la separación al defensor de cobertura más cercano, su velocidad (¿se abre o se cierra?) y su aceleración, en ventanas de 0,5 s que solo miran hacia atrás.</li>
          <li>Los pesos los estima una regresión logística sobre {v.n_objetivos.toLocaleString('es-MX')} pases con receptor objetivo identificado (completo sí/no), con la profundidad como control. Solo se conservan los componentes que mejoran la predicción en validación cruzada por partido.</li>
          <li>Al puntaje se le resta lo típico a la misma profundidad, para no premiar las rutas cortas, y se convierte en percentil 0-100.</li>
        </ol>
        <div className="mt-4 space-y-2">
          {resumen.componentes.map(c => (
            <div key={c.id}>
              <div className="flex justify-between text-xs"><span>{c.nombre}</span><span className="tabular-nums">peso {num(c.peso, 3)} ± {num(c.error, 3)}</span></div>
              <Barra valor={c.peso} max={maxPeso} />
            </div>
          ))}
        </div>
        <Aviso>Se probaron y descartaron la desalineación de trayectorias y la persistencia: no mejoran la predicción una vez conocida la separación. Correlación de la DSA con la profundidad: antes {num(v.spearman_profundidad.dsa_bruta, 2)}, ahora {num(v.spearman_profundidad.dsa, 3)}.</Aviso>
      </Tarjeta>

      <Tarjeta titulo="¿Predice algo?" subtitulo="Validación cruzada de 5 pliegues agrupados por partido (ningún partido en entrenamiento y prueba a la vez)">
        <table className="tabla w-full text-sm">
          <thead><tr><th>Modelo</th><th className="text-right">AUC</th><th className="text-right">Log-loss</th><th className="text-right">Brier</th></tr></thead>
          <tbody>{modelos.map(([n, m]) => (
            <tr key={n} className={`!cursor-default ${n.startsWith('DSA') ? 'text-ventaja font-semibold' : ''}`}>
              <td>{n}</td><td className="text-right tabular-nums">{num(m.auc, 3)}</td><td className="text-right tabular-nums">{num(m.log_loss, 4)}</td><td className="text-right tabular-nums">{num(m.brier, 4)}</td>
            </tr>
          ))}</tbody>
        </table>
        <div className="etiqueta mt-4 mb-1">Tasa de completos por rango de DSA al pase</div>
        <ResponsiveContainer width="100%" height={190}>
          <BarChart data={v.calibracion.map(c => ({ ...c, pct: 100 * c.tasa_completo }))} margin={{ left: -20, right: 4, top: 4 }}>
            <CartesianGrid stroke="#1d2c47" vertical={false} />
            <XAxis dataKey="rango" tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} stroke="#2a3c5e" domain={[0, 100]} unit="%" />
            <Tooltip contentStyle={{ background: '#0b1220', border: '1px solid #2a3c5e', fontSize: 12 }} formatter={(x: unknown) => [`${num(typeof x === 'number' ? x : null, 0)}%`, 'completos']} labelFormatter={l => `DSA ${l}`} />
            <Bar dataKey="pct" fill="#34d399" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
        <Aviso>Tasa global de completos entre los pases analizados: {pct(v.tasa_completo)}.</Aviso>
      </Tarjeta>

      <Tarjeta titulo="Firmas de movimiento (SCS)" subtitulo={`k-means sobre ${resumen.scs.grupos.reduce((a, g) => a + g.n, 0).toLocaleString('es-MX')} creaciones de separación · k = ${resumen.scs.k} · silhouette ${num(resumen.scs.silhouettes[String(resumen.scs.k)], 2)}`}>
        <div className="space-y-3">
          {resumen.scs.grupos.map(g => (
            <div key={g.id} className="border border-noche-700 rounded-lg p-3">
              <div className="font-medium text-slate-100 text-sm">{g.nombre}</div>
              <div className="text-xs text-slate-400 mt-1">
                {g.n.toLocaleString('es-MX')} rutas · profundidad mediana {num(g.profundidad_mediana, 1)} yd · quiebre a {num(g.t_quiebre_mediana, 1)} s ·
                ganancia media {num(g.ganancia_media, 2)} yd · {Object.entries(g.posiciones).map(([p, s]) => `${p} ${pct(s)}`).join(', ')}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">{Object.entries(g.mediana).map(([k, x]) => `${resumen.scs.rasgos[k]}: ${num(x, 1)}`).join(' · ')}</div>
            </div>
          ))}
        </div>
        <Aviso>Las firmas son estables (índice de Rand ajustado 0,94 en 10 réplicas bootstrap), pero la silhouette baja indica que son una partición reproducible de un continuo de movimientos, no categorías naturalmente separadas.</Aviso>
      </Tarjeta>

      <Tarjeta titulo="Limitaciones" subtitulo="Lo que los datos no permiten afirmar">
        <ul className="text-sm text-slate-300 space-y-2 list-disc pl-5">{LIMITACIONES.map(l => <li key={l}>{l}</li>)}</ul>
        <Aviso>Detalle completo en METHODOLOGY.md y DATA_AUDIT.md del repositorio. Carga del análisis: {num(resumen.segundos_carga, 0)} s.</Aviso>
      </Tarjeta>
    </div>
  )
}
