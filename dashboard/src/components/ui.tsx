import type { ReactNode } from 'react'
import { colorDSA, num } from '../format'

export function Tarjeta({ titulo, subtitulo, children, className = '', accion }: {
  titulo?: ReactNode; subtitulo?: ReactNode; children: ReactNode; className?: string; accion?: ReactNode
}) {
  return (
    <section className={`tarjeta p-4 ${className}`}>
      {(titulo || accion) && (
        <header className="flex items-start justify-between gap-3 mb-3">
          <div>
            {titulo && <h3 className="text-sm font-semibold text-slate-100">{titulo}</h3>}
            {subtitulo && <p className="text-xs text-slate-400 mt-0.5">{subtitulo}</p>}
          </div>
          {accion}
        </header>
      )}
      {children}
    </section>
  )
}

export function Dato({ etiqueta, valor, nota, color }: { etiqueta: string; valor: ReactNode; nota?: ReactNode; color?: string }) {
  return (
    <div>
      <div className="etiqueta">{etiqueta}</div>
      <div className="text-lg font-semibold tabular-nums" style={color ? { color } : undefined}>{valor}</div>
      {nota && <div className="text-[11px] text-slate-500">{nota}</div>}
    </div>
  )
}

export function Insignia({ children, tono = 'neutro' }: { children: ReactNode; tono?: 'neutro' | 'verde' | 'ambar' | 'rojo' | 'azul' }) {
  const t = {
    neutro: 'bg-noche-700 text-slate-300', verde: 'bg-ventaja/15 text-ventaja', ambar: 'bg-ofensa/15 text-ofensa',
    rojo: 'bg-alerta/15 text-alerta', azul: 'bg-defensa/15 text-defensa',
  }[tono]
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${t}`}>{children}</span>
}

export function ValorDSA({ v, grande = false }: { v: number | null | undefined; grande?: boolean }) {
  return <span className={`tabular-nums font-semibold ${grande ? 'text-2xl' : ''}`} style={{ color: colorDSA(v) }}>{num(v, 0)}</span>
}

export function Barra({ valor, max = 1, color = '#34d399' }: { valor: number; max?: number; color?: string }) {
  const w = Math.max(0, Math.min(100, (100 * valor) / max))
  return (
    <div className="h-1.5 w-full bg-noche-700 rounded">
      <div className="h-1.5 rounded" style={{ width: `${w}%`, background: color }} />
    </div>
  )
}

export function Cargando({ texto = 'Cargando…' }: { texto?: string }) {
  return (
    <div className="flex items-center gap-3 text-slate-400 text-sm p-6">
      <span className="h-4 w-4 rounded-full border-2 border-ventaja border-t-transparent animate-spin" />
      {texto}
    </div>
  )
}

export function Aviso({ children }: { children: ReactNode }) {
  return <p className="text-[11px] text-slate-500 leading-relaxed">{children}</p>
}
