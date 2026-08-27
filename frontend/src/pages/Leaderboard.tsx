import { useEffect, useState } from 'react'
import { fetchLeaderboard } from '../api/client'
import { Link } from 'react-router-dom'

export default function Leaderboard() {
  const [rows, setRows] = useState<any[]>([])
  const [sort, setSort] = useState('btfi_score')
  useEffect(()=>{ fetchLeaderboard().then(setRows).catch(()=>{}) }, [])
  const sorted = [...rows].sort((a,b)=>{
    if (sort==='btfi_score') return b.btfi_score - a.btfi_score
    if (sort==='cagr') return b.cagr - a.cagr
    if (sort==='excess') return b.excess_cagr - a.excess_cagr
    return b.sharpe - a.sharpe
  })
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Leaderboard</h1>
      <div className="flex gap-2 text-xs">
        {['btfi_score','cagr','excess','sharpe'].map(k=>(
          <button key={k} onClick={()=>setSort(k)} className={`px-3 py-1 rounded ${sort===k?'bg-white text-black':'bg-zinc-800'}`}>{k}</button>
        ))}
      </div>
      <div className="bg-zinc-900 rounded overflow-auto">
        <table className="w-full text-xs">
          <thead className="text-zinc-500">
            <tr><th className="p-2 text-left">Experiment</th><th className="p-2">CAGR</th><th className="p-2">Excess</th><th className="p-2">Sharpe</th><th className="p-2">MaxDD</th><th className="p-2">5Y Win</th><th className="p-2">Score</th><th className="p-2">Verdict</th></tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {sorted.map(r=>(
              <tr key={r.id} className="hover:bg-zinc-800">
                <td className="p-2"><Link to={`/experiments/${r.id}`} className="underline">{r.experiment} {r.strategy}</Link></td>
                <td className="p-2 text-right">{(r.cagr*100).toFixed(1)}%</td>
                <td className="p-2 text-right">{(r.excess_cagr*100).toFixed(1)}%</td>
                <td className="p-2 text-right">{r.sharpe?.toFixed(2)}</td>
                <td className="p-2 text-right">{(r.max_drawdown*100).toFixed(1)}%</td>
                <td className="p-2 text-right">{r.win_rate_5y}%</td>
                <td className="p-2 text-right font-bold">{r.btfi_score}</td>
                <td className="p-2"><span className="px-2 py-1 bg-zinc-800 rounded text-[10px]">{r.verdict}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length===0 && <p className="p-4 text-sm text-zinc-500">No experiments yet.</p>}
      </div>
    </div>
  )
}
