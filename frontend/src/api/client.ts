const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function api(path: string, opts: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || res.statusText)
  }
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res.text()
}

export const fetchStrategies = () => api('/strategies')
export const fetchExperiments = () => api('/experiments')
export const fetchLeaderboard = () => api('/leaderboard')
export const runBacktest = (body: any) => api('/backtests', { method: 'POST', body: JSON.stringify(body) })
export const fetchDataQuality = () => api('/data-quality')
