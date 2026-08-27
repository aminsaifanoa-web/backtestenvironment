import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, BarChart, Bar } from 'recharts'

export function GrowthChart({ equity, benchmark }: { equity: any[], benchmark: any[] }) {
  const data = equity.map((p, i) => ({
    date: p.date,
    strategy: p.value,
    benchmark: benchmark[i]?.value ?? null,
  }))
  return (
    <div className="h-72 bg-zinc-900 rounded p-4">
      <h3 className="text-sm font-semibold mb-2">Growth of $10,000</h3>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart data={data}>
          <XAxis dataKey="date" hide />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="strategy" stroke="#22c55e" dot={false} strokeWidth={2} />
          <Line type="monotone" dataKey="benchmark" stroke="#52525b" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function AnnualBar({ data }: { data: any[] }) {
  return (
    <div className="h-64 bg-zinc-900 rounded p-4">
      <h3 className="text-sm font-semibold mb-2">Annual Returns</h3>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={data}>
          <XAxis dataKey="year" tick={{ fontSize: 10 }} />
          <YAxis tickFormatter={(v)=>`${(v*100).toFixed(0)}%`} tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v: number)=>`${(v*100).toFixed(1)}%`} />
          <Bar dataKey="strategy" fill="#22c55e" />
          <Bar dataKey="benchmark" fill="#71717a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
