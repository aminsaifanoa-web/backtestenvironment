import { useEffect, useState } from 'react'
import { api, fetchStrategies } from '../api/client'

export default function NewExperiment() {
  const [strategies, setStrategies] = useState<any[]>([])
  const [form, setForm] = useState<any>({
    strategy_id: 'low_pe',
    universe: 'sp500',
    top_n: 20,
    weighting: 'equal',
    rebalance: 'annual',
    transaction_cost_bps: 10,
    slippage_bps: 5,
    start_date: '2010-01-01',
    end_date: '2024-12-31',
    benchmark: 'SPY',
    formula: '',
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string>('')

  useEffect(()=>{ fetchStrategies().then(setStrategies).catch(()=>{}) }, [])

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const body: any = { ...form, top_n: Number(form.top_n), transaction_cost_bps: Number(form.transaction_cost_bps), slippage_bps: Number(form.slippage_bps) }
      if (!body.formula) delete body.formula
      const res = await api('/backtests', { method: 'POST', body: JSON.stringify(body) })
      setResult(res)
    } catch (e: any) {
      setError(e.message || String(e))
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold">New Experiment</h1>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-zinc-900 rounded p-4 space-y-4">
          <label className="block text-sm">Strategy Template
            <select value={form.strategy_id} onChange={e=>setForm({...form, strategy_id:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2">
              {strategies.map(s=> <option key={s.id} value={s.id}>{s.name} — {s.category}</option>)}
            </select>
          </label>
          <div className="p-3 bg-amber-950 border border-amber-800 rounded text-xs text-amber-200">
            ⚠️ Historical constituent data unavailable. Survivorship bias may materially affect results.<br/>
            ⚠️ Potential look-ahead bias: historical publication dates are unavailable for this fundamental dataset.
          </div>
          <label className="block text-sm">Universe
            <select value={form.universe} onChange={e=>setForm({...form, universe:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2">
              <option value="sp500">S&P 500 (current constituents)</option>
              <option value="AAPL,MSFT,NVDA,AMZN,META,GOOGL">Mega-cap 6</option>
            </select>
          </label>
          <label className="block text-sm">Top N / Selection
            <input type="number" value={form.top_n} onChange={e=>setForm({...form, top_n:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            <span className="text-xs text-zinc-500">Alternatives: 5, 10, 15, 20, 25, 30, 50</span>
          </label>
          <label className="block text-sm">Weighting
            <select value={form.weighting} onChange={e=>setForm({...form, weighting:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2">
              <option value="equal">Equal weight</option>
              <option value="market_cap">Market cap</option>
              <option value="inverse_vol">Inverse volatility</option>
              <option value="score">Score weighted</option>
            </select>
          </label>
          <label className="block text-sm">Rebalance
            <select value={form.rebalance} onChange={e=>setForm({...form, rebalance:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="semiannual">Semi-annually</option>
              <option value="annual">Annually</option>
            </select>
          </label>
        </div>

        <div className="bg-zinc-900 rounded p-4 space-y-4">
          <label className="block text-sm">Custom Formula (optional)
            <input value={form.formula} onChange={e=>setForm({...form, formula:e.target.value})} placeholder="e.g. 0.5*rank(fcf_yield)+0.5*rank(roic)" className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            <span className="text-xs text-zinc-500">Functions: rank, zscore, percentile, mean, median, min, max. Ops: + - * / &gt; &lt; AND OR</span>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">Transaction cost (bps)
              <input type="number" value={form.transaction_cost_bps} onChange={e=>setForm({...form, transaction_cost_bps:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            </label>
            <label className="block text-sm">Slippage (bps)
              <input type="number" value={form.slippage_bps} onChange={e=>setForm({...form, slippage_bps:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">Start Date
              <input type="date" value={form.start_date} onChange={e=>setForm({...form, start_date:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            </label>
            <label className="block text-sm">End Date
              <input type="date" value={form.end_date} onChange={e=>setForm({...form, end_date:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            </label>
          </div>
          <label className="block text-sm">Benchmark
            <input value={form.benchmark} onChange={e=>setForm({...form, benchmark:e.target.value})} className="w-full mt-1 bg-zinc-800 border border-zinc-700 rounded px-2 py-2" />
            <span className="text-xs text-zinc-500">S&P 500 proxy: SPY</span>
          </label>
          <button onClick={run} disabled={loading} className="w-full py-3 bg-white text-black font-bold rounded hover:bg-zinc-200 disabled:opacity-50">
            {loading ? 'RUNNING…' : 'RUN →'}
          </button>
          {error && <div className="p-3 bg-red-950 border border-red-800 rounded text-sm text-red-200">
            <p className="font-semibold">BACKTEST FAILED</p>
            <p>{error}</p>
          </div>}
        </div>
      </div>

      {result && (
        <div className="bg-zinc-900 rounded p-6 space-y-4">
          <h2 className="text-xl font-bold">BTFI #{result.experiment_id} — {result.verdict}</h2>
          <p className="text-sm text-zinc-400">{result.verdict_reason}</p>
          <div className="grid md:grid-cols-4 gap-3 text-sm">
            <div className="bg-zinc-800 rounded p-3"><p className="text-zinc-500 text-xs">CAGR</p><p className="font-bold">{(result.metrics.cagr*100).toFixed(2)}% vs {(result.metrics.benchmark_cagr*100).toFixed(2)}%</p></div>
            <div className="bg-zinc-800 rounded p-3"><p className="text-zinc-500 text-xs">Excess</p><p className="font-bold">{(result.metrics.excess_cagr*100).toFixed(2)}%</p></div>
            <div className="bg-zinc-800 rounded p-3"><p className="text-zinc-500 text-xs">Sharpe</p><p className="font-bold">{result.metrics.sharpe.toFixed(2)}</p></div>
            <div className="bg-zinc-800 rounded p-3"><p className="text-zinc-500 text-xs">BTFI Score</p><p className="font-bold">{result.btfi_score.btfi_score}</p></div>
          </div>
          <div className="text-xs text-zinc-500">
            <p>5Y win rate: {result.rolling?.['5Y']?.beat_pct ?? 0}% | Cost robustness: {result.cost_robustness?.map((c:any)=>`${c.cost_bps}bps:${(c.excess*100).toFixed(1)}%`).join(' | ')}</p>
            <p>Warnings: {result.warnings?.join(' | ')}</p>
          </div>
          <a href={`http://localhost:8000/experiments/${result.id}/markdown`} target="_blank" className="text-sm underline">Generate Publication Markdown →</a>
        </div>
      )}
    </div>
  )
}
