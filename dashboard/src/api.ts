// Rutas relativas SIN diagonal inicial: la app se publica en una subruta del hosting.
export class ErrorApi extends Error {
  constructor(public status: number, mensaje: string) { super(mensaje) }
}

export async function api<T>(ruta: string): Promise<T> {
  const r = await fetch(`api/${ruta}`)
  if (!r.ok) throw new ErrorApi(r.status, `Error ${r.status} en ${ruta}`)
  return (await r.json()) as T
}

export function query(params: Record<string, string | number | undefined | null>): string {
  const q = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return q.length ? '?' + q.map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&') : ''
}
