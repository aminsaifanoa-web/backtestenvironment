import { Link, useLocation } from 'react-router-dom'

const nav = [
  { path: '/', label: 'Dashboard' },
  { path: '/new', label: 'New Experiment' },
  { path: '/experiments', label: 'Experiments' },
  { path: '/library', label: 'Strategy Library' },
  { path: '/leaderboard', label: 'Leaderboard' },
  { path: '/data-quality', label: 'Data Quality' },
  { path: '/settings', label: 'Settings' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const loc = useLocation()
  return (
    <div className="min-h-screen flex bg-zinc-950 text-zinc-100">
      <aside className="w-64 border-r border-zinc-800 p-6 hidden md:block">
        <div className="mb-8">
          <h1 className="text-2xl font-black tracking-tight">BTFI</h1>
          <p className="text-xs text-zinc-500">Buy The Fucking Index</p>
        </div>
        <nav className="space-y-1">
          {nav.map(n => (
            <Link key={n.path} to={n.path} className={`block px-3 py-2 rounded text-sm ${loc.pathname===n.path ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-900'}`}>
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="mt-10 p-3 bg-zinc-900 rounded text-xs text-zinc-400">
          <p className="font-semibold text-zinc-200">⚠️ Data Limits</p>
          <p className="mt-1">Historical constituents & PIT fundamentals unavailable via yfinance. Bias warnings shown per experiment.</p>
        </div>
      </aside>
      <main className="flex-1 p-6 md:p-8 overflow-auto">{children}</main>
    </div>
  )
}
