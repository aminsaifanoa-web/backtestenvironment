import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import { GrowthChart, AnnualBar } from '../components/Charts'

export default function ExperimentDetail() {
  const { id } = useParams()
  const [exp, setExp] = useState<any>(null)
  const [md, setMd] = useState<string>('')
  useEffect(()=>{
    api(`/experiments/${id}`).then(setExp).catch(()=>{})
  }, [id])
  const loadMd = async () => {
    const txt = await api(`/experiments/${id}/markdown`)
    setMd(txt as any)
  }
  if (!exp) return <p>Loading…</p>
  const res = exp.results || {}
  const metrics = res.metrics || {}
  const rolling = res.rolling || {}
  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-black">BTFI #{String(exp.id).padStart(3,'0')} — {exp.title}</h1>
      <p className="text-sm text-zinc-400">Verdict: <span className="font-bold text-white">{exp.verdict}</span> — {res.reason}</p>
      {res.warnings?.map((w:string,i:number)=><p key={i} className="text-xs bg-amber-950 border border-amber-800 rounded p-2 text-amber-200">{w}</p>)}
      <div className="grid md:grid-cols-3 gap-3 text-sm">
        <div className="bg-zinc-900 rounded p-3"><p className="text-xs text-zinc-500">CAGR</p><p className="font-bold">{(metrics.cagr*100).toFixed(2)}% vs {(metrics.benchmark_cagr*100).toFixed(2)}%</p></div>
        <div className="bg-zinc-900 rounded p-3"><p className="text-xs text-zinc-500">Sharpe / MaxDD</p><p className="font-bold">{metrics.sharpe?.toFixed(2)} / {(metrics.max_drawdown*100).toFixed(1)}%</p></div>
        <div className="bg-zinc-900 rounded p-3"><p className="text-xs text-zinc-500">BTFI Score</p><p className="font-bold">{exp.btfi_score}</p></div>
      </div>
      {res.equity_curve && <GrowthChart equity={res.equity_curve} benchmark={res.benchmark_curve} />}
      {res.annual && <AnnualBar data={res.annual} />}

      <div className="bg-zinc-900 rounded p-4">
        <h3 className="font-semibold mb-2">Rolling Analysis</h3>
        <div className="grid md:grid-cols-4 gap-3 text-xs">
          {['1Y','3Y','5Y','10Y'].map(k=>(
            <div key={k} className="bg-zinc-800 rounded p-3">
              <p className="font-bold">{k}</p>
              <p>Win {rolling[k]?.beat_pct ?? 0}% ({rolling[k]?.total_periods ?? 0} periods)</p>
              <p>Median excess {(rolling[k]?.median_excess*100 ?? 0).toFixed(2)}%</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={loadMd} className="px-4 py-2 bg-white text-black font-semibold rounded">Generate Publication</button>
        <a href={`http://localhost:8000/experiments/${exp.id}/markdown`} target="_blank" className="px-4 py-2 bg-zinc-800 rounded">Export Markdown</a>
      </div>
      {md && <pre className="bg-zinc-900 rounded p-4 text-xs whitespace-pre-wrap overflow-auto max-h-[600px]">{md}</pre>}
    </div>
  )
}
