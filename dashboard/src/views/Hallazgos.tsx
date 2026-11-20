import { Insignia, Tarjeta } from '../components/ui'
import { num } from '../format'
import type { Destino, Hallazgo, Resumen } from '../types'

type Props = { hallazgos: Hallazgo[]; resumen: Resumen; abrir: (d: Destino) => void }

const CAMPOS: [keyof Hallazgo, string][] = [
  ['que_ocurrio', 'Qué ocurrió'], ['cuando', 'Cuándo'], ['movimiento', 'Movimiento'], ['repeticion', '¿Se repite?'],
]

export default function Hallazgos({ hallazgos, resumen, abrir }: Props) {
  return (
    <div className="space-y-5">
      <section className="tarjeta p-5 bg-gradient-to-br from-noche-900 to-cesped-900/40">
        <h1 className="text-xl font-semibold text-slate-50">¿Cómo, cuándo y con qué movimiento crea ventaja un receptor?</h1>
        <p className="text-sm text-slate-300 mt-1 max-w-4xl">
          SPI analiza el tracking cuadro por cuadro (10 Hz) de {resumen.rutas.toLocaleString('es-MX')} rutas en {resumen.jugadas_analizadas.toLocaleString('es-MX')} jugadas
          de pase de {resumen.partidos} partidos (semanas {resumen.semanas[0]}-{resumen.semanas[resumen.semanas.length - 1]} de 2021, {resumen.equipos} equipos).
          La <b>DSA</b> (0-100) mide la ventaja dinámica del receptor sobre el defensor más cercano, sin premiar las rutas cortas;
          la <b>SCS</b> describe el movimiento con el que la crea.
        </p>
        <div className="flex flex-wrap gap-6 mt-4 text-sm">
          <div><div className="etiqueta">AUC de la DSA (validación por partido)</div><div className="text-lg font-semibold text-ventaja">{num(resumen.validacion.dsa_neutral_profundidad.auc, 3)}</div></div>
          <div><div className="etiqueta">Baseline: solo separación</div><div className="text-lg font-semibold">{num(resumen.validacion.baseline_sep_profundidad.auc, 3)}</div></div>
          <div><div className="etiqueta">Completos con DSA 90-100</div><div className="text-lg font-semibold">{num(100 * resumen.validacion.calibracion[resumen.validacion.calibracion.length - 1].tasa_completo, 0)}%</div></div>
          <div><div className="etiqueta">Completos con DSA 0-10</div><div className="text-lg font-semibold">{num(100 * resumen.validacion.calibracion[0].tasa_completo, 0)}%</div></div>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {hallazgos.map(h => (
          <Tarjeta key={h.id} className="flex flex-col">
            <div className="etiqueta text-ventaja">{h.pregunta}</div>
            <h2 className="text-base font-semibold text-slate-50 mt-1 mb-3">{h.titulo}</h2>
            <dl className="space-y-2 text-sm">
              {CAMPOS.map(([k, e]) => (
                <div key={k}><dt className="etiqueta">{e}</dt><dd className="text-slate-300">{String(h[k])}</dd></div>
              ))}
            </dl>
            {h.jugadores.length > 0 && (
              <div className="mt-3">
                <div className="etiqueta mb-1">Jugadores</div>
                <div className="flex flex-wrap gap-1.5">
                  {h.jugadores.map((j, n) => <Insignia key={n} tono={j.rol === 'defensor' ? 'azul' : 'ambar'}>{j.nombre} · {j.equipo} · {j.valor}</Insignia>)}
                </div>
              </div>
            )}
            <div className="mt-3">
              <div className="etiqueta mb-1">Métricas que lo respaldan</div>
              <ul className="text-sm space-y-0.5">
                {h.metricas.map((m, n) => <li key={n} className="flex justify-between gap-3 border-b border-noche-800 py-0.5"><span className="text-slate-400">{m.nombre}</span><span className="tabular-nums text-right">{m.valor}</span></li>)}
              </ul>
            </div>
            <div className="mt-3 rounded-lg bg-ventaja/5 border border-ventaja/25 p-3">
              <div className="etiqueta text-ventaja">Qué puede aprender el coach</div>
              <p className="text-sm text-slate-200">{h.aprendizaje}</p>
            </div>
            <p className="text-[11px] text-slate-500 mt-2"><b>Limitaciones:</b> {h.limitaciones}</p>
            {h.ejemplo && (
              <button className="boton mt-3 self-start" onClick={() => abrir(h.ejemplo!)}>Ver jugada de ejemplo en el visor →</button>
            )}
          </Tarjeta>
        ))}
      </div>
    </div>
  )
}
