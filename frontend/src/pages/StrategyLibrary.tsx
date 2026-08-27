import { useEffect, useState } from 'react'
import { fetchStrategies } from '../api/client'
import { Link } from 'react-router-dom'

const cats = ["Passive","Value","Momentum","Quality","Growth","Dividend","Factor","Contrarian","Technical","Macro","Weird","Experimental","Multifactor"]

export default function StrategyLibrary() {
  const [strats, setStrats] = useState<any[]>([])
  const [cat, setCat] = useState<string>('All')
  useEffect(()=>{ fetchStrategies().then(setStrats).catch(()=>{}) }, [])
  const filtered = cat==='All' ? strats : strats.filter(s=>s.category===cat)
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Strategy Library</h1>
      <div className="flex flex-wrap gap-2">
        <button onClick={()=>setCat('All')} className={`px-3 py-1 rounded text-xs ${cat==='All'?'bg-white text-black':'bg-zinc-800'}`}>All</button>
        {cats.map(c=><button key={c} onClick={()=>setCat(c)} className={`px-3 py-1 rounded text-xs ${cat===c?'bg-white text-black':'bg-zinc-800'}`}>{c}</button>)}
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(s=>(
          <div key={s.id} className="bg-zinc-900 rounded p-4">
            <p className="text-xs text-zinc-500">{s.category}</p>
            <p className="font-semibold">{s.name}</p>
            <p className="text-xs text-zinc-400 mt-1">{s.description}</p>
            <p className="text-xs text-zinc-500 mt-2">Metric: {s.metric} • Rebalance: {s.rebalance}</p>
            <Link to="/new" className="text-xs underline mt-2 inline-block">Use this strategy →</Link>
          </div>
        ))}
      </div>
    </div>
  )
}
