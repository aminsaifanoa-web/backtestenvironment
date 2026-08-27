import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function DataQuality() {
  const [data, setData] = useState<any>(null)
  useEffect(()=>{ api('/data-quality').then(setData).catch(()=>{}) }, [])
  if (!data) return <p>Loading…</p>
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Data Quality</h1>
      <div className="bg-zinc-900 rounded p-4">
        <p className="text-sm">Cache size: <span className="font-bold">{data.cache_size_mb} MB</span></p>
        <p className="text-xs text-zinc-500">Provider: {data.provider} • Cache dir: {data.cache_dir}</p>
        <p className="text-xs text-zinc-500 mt-2">Datasets: {data.datasets.length} cached files</p>
        <div className="mt-3">
          {data.warnings.map((w:string,i:number)=><p key={i} className="text-xs bg-amber-950 border border-amber-800 rounded p-2 text-amber-200 mb-1">{w}</p>)}
        </div>
        <button onClick={async()=>{ await api('/cache/clear', {method:'POST'}); location.reload() }} className="mt-3 px-3 py-1 bg-zinc-800 rounded text-xs">Clear Cache</button>
      </div>
      <div className="bg-zinc-900 rounded p-4 overflow-auto max-h-[400px]">
        <h3 className="font-semibold text-sm mb-2">Cached Datasets</h3>
        <table className="w-full text-xs">
          <thead className="text-zinc-500"><tr><th className="p-1 text-left">File</th><th className="p-1">Size KB</th><th className="p-1">Modified</th></tr></thead>
          <tbody className="divide-y divide-zinc-800">
            {data.datasets.slice(0,50).map((d:any,i:number)=>(
              <tr key={i}><td className="p-1">{d.file || d.ticker || JSON.stringify(d).slice(0,60)}</td><td className="p-1 text-right">{d.size_kb ?? '-'}</td><td className="p-1">{d.modified ?? d.last_updated ?? '-'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
