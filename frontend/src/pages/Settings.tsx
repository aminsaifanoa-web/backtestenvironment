export default function Settings() {
  return (
    <div className="space-y-4 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>
      <div className="bg-zinc-900 rounded p-4">
        <h3 className="font-semibold">Research Methodology</h3>
        <p className="text-sm text-zinc-400 mt-2">The burden of proof is on the strategy, not the index. Default hypothesis: buy the S&P 500 and do nothing. A strategy needs meaningful outperformance, reasonable risk, persistence, robustness, survival after costs.</p>
        <ul className="text-xs text-zinc-500 mt-3 list-disc ml-4">
          <li>All backtests compare to S&P 500 proxy: SPY (dividend-inclusive).</li>
          <li>Execution: Signal at t → execute at t+1 close.</li>
          <li>Costs: 10 bps default, robustness tested at 0/10/25/50/100 bps.</li>
          <li>Rolling 1/3/5/10Y and start-date robustness auto-calculated.</li>
        </ul>
      </div>
      <div className="bg-zinc-900 rounded p-4">
        <h3 className="font-semibold">Data Source</h3>
        <p className="text-sm text-zinc-400">Yahoo Finance via yfinance is the ONLY external data source. No API key required. Keep yfinance calls inside data layer.</p>
      </div>
    </div>
  )
}
