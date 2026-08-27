import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchExperiments } from '../api/client'

export default function Experiments() {
  const [exps, setExps] = useState<any[]>([])
  useEffect(()=>{ fetchExperiments().then(setExps).catch(()=>{}) }, [])
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Experiments</h1>
      <div className="bg-zinc-900 rounded divide-y divide-zinc-800">
        {exps.map(e=>(
          <Link key={e.id} to={`/experiments/${e.id}`} className="flex justify-between items-center p-4 hover:bg-zinc-800">
            <div>
              <p className="font-semibold">BTFI #{String(e.id).padStart(3,'0')} — {e.title}</p>
              <p className="text-xs text-zinc-500">{e.created_at} • Score {e.btfi_score}</p>
            </div>
            <span className="text-xs px-2 py-1 bg-zinc-800 rounded">{e.verdict}</span>
          </Link>
        ))}
        {exps.length===0 && <p className="p-4 text-zinc-500 text-sm">No experiments yet.</p>}
      </div>
    </div>
  )
}
