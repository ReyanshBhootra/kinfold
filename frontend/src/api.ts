const base = (import.meta as ImportMeta & {env: {VITE_API_URL?: string}}).env.VITE_API_URL || ''
// Self-declared researcher name for the case activity log (not authentication). Set from the top-bar badge.
export const RESEARCHER_KEY = 'kinfold-researcher'
export function researcherName(): string { try { return localStorage.getItem(RESEARCHER_KEY) || '' } catch { return '' } }
const researcherHeader = (): Record<string, string> => { const n = researcherName(); return n ? {'X-Kinfold-Researcher': n} : {} }
export async function api<T>(path: string, body?: unknown): Promise<T> {
 const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 120000)
 try {
  const response = await fetch(`${base}${path}`, { signal: controller.signal, headers: researcherHeader(), ...(body !== undefined ? { method: 'POST', headers: {'Content-Type':'application/json', ...researcherHeader()}, body: JSON.stringify(body) } : {}) })
  if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(typeof error.detail === 'string' ? error.detail : `Request failed (${response.status}). Please check the backend.`) }
  return await response.json() as T
 } catch(error) { if (error instanceof TypeError) throw new Error('Cannot reach the local API. Start the backend on port 8000, then retry.'); throw error }
 finally { clearTimeout(timeout) }
}
