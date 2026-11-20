const es = (d: number) => new Intl.NumberFormat('es-MX', { minimumFractionDigits: d, maximumFractionDigits: d })

export function num(v: number | null | undefined, d = 1): string {
  return v === null || v === undefined || Number.isNaN(v) ? '–' : es(d).format(v)
}
export function pct(v: number | null | undefined, d = 0): string {
  return v === null || v === undefined || Number.isNaN(v) ? '–' : es(d).format(100 * v) + '%'
}
export function signo(v: number | null | undefined, d = 1): string {
  return v === null || v === undefined || Number.isNaN(v) ? '–' : (v >= 0 ? '+' : '') + es(d).format(v)
}

export const RESULTADO: Record<string, string> = { C: 'Completo', I: 'Incompleto', IN: 'Intercepción', S: 'Captura', R: 'Scramble' }
export const ESTADO_CASTIGO: Record<string, string> = { aplicada: 'Aplicada', rechazada: 'Rechazada', compensada: 'Compensada' }
export const EVENTO: Record<string, string> = {
  ball_snap: 'Snap', autoevent_ballsnap: 'Snap (auto)', pass_forward: 'Pase', autoevent_passforward: 'Pase (auto)',
  play_action: 'Play action', man_in_motion: 'Motion', line_set: 'Línea lista', pass_arrived: 'Llegada del pase',
  pass_outcome_caught: 'Atrapado', pass_outcome_incomplete: 'Incompleto', qb_sack: 'Captura', run: 'Corre',
}

/** Color de la DSA (0-100): rojo -> ámbar -> verde. */
export function colorDSA(v: number | null | undefined): string {
  if (v === null || v === undefined) return '#64748b'
  if (v >= 75) return '#34d399'
  if (v >= 50) return '#a3e635'
  if (v >= 25) return '#f5b942'
  return '#f87171'
}
