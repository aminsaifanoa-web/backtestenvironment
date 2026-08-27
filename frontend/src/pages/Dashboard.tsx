import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchExperiments, fetchLeaderboard } from '../api/client'

export default function Dashboard() {
  const [exps, setExps] = useState<any[]>([])
  const [board, setBoard] = useState<any[]>([])
  useEffect(() => {
    fetchExperiments().then(setExps).catch(()=>{})
    fetchLeaderboard().then(setBoard).catch(()=>{})
  }, [])
  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-800 rounded-2xl p-8">
        <h1 className="text-4xl font-black">WELCOME TO BTFI</h1>
        <p className="text-xl text-zinc-400 mt-2">Buy the Fucking Index.</p>
        <p className="text-zinc-500 mt-2 max-w-2xl">Test whether your brilliant investment idea actually beats the S&P 500. Rigorous, transparent, reproducible.</p>
        <Link to="/new" className="inline-block mt-6 px-6 py-3 bg-white text-black font-bold rounded hover:bg-zinc-200">RUN YOUR FIRST EXPERIMENT →</Link>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <div className="bg-zinc-900 rounded p-4">
          <p className="text-xs text-zinc-500">Experiments</p>
          <p className="text-2xl font-bold">{exps.length}</p>
        </div>
        <div className="bg-zinc-900 rounded p-4">
          <p className="text-xs text-zinc-500">Best Excess CAGR</p>
          <p className="text-2xl font-bold">{board[0] ? (board[0].excess_cagr*100).toFixed(2)+'%' : '—'}</p>
        </div>
        <div className="bg-zinc-900 rounded p-4">
          <p className="text-xs text-zinc-500">Top Verdict</p>
          <p className="text-sm font-bold">{board[0]?.verdict ?? 'No data yet'}</p>
        </div>
      </div>

      <div>
        <h2 className="font-semibold mb-2">Recent Experiments</h2>
        <div className="bg-zinc-900 rounded divide-y divide-zinc-800">
          {exps.slice(0,5).map(e=>(
            <Link key={e.id} to={`/experiments/${e.id}`} className="flex justify-between p-3 hover:bg-zinc-800">
              <span>BTFI #{String(e.id).padStart(3,'0')} {e.title}</span>
              <span className={`text-xs px-2 py-1 rounded ${e.verdict?.includes('WORKS')?'bg-green-900 text-green-200': e.verdict?.includes('COSTS')?'bg-amber-900 text-amber-200':'bg-zinc-800'}`}>{e.verdict}</span>
            </Link>
          ))}
          {exps.length===0 && <p className="p-4 text-sm text-zinc-500">No experiments yet. Run one in <Link to="/new" className="underline">New Experiment</Link>.</p>}
        </div>
      </div>
    </div>
  )
}
