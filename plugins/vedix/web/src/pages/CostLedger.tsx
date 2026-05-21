import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getCostReport, type CostReport } from "../api/cost";

const WINDOWS: Array<{ value: string; label: string }> = [
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
];

export function CostLedgerPage(): JSX.Element {
  const [window, setWindow] = useState("30d");
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["cost", window],
    queryFn: () => getCostReport(window),
  });

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Cost ledger</h1>
        <select
          value={window}
          onChange={(e) => setWindow(e.target.value)}
          className="vedix-input"
        >
          {WINDOWS.map((w) => (
            <option key={w.value} value={w.value}>
              {w.label}
            </option>
          ))}
        </select>
      </header>

      {isLoading && <p className="text-gray-500">Loading…</p>}
      {isError && (
        <p className="text-red-600">{(error as Error).message}</p>
      )}
      {data && <CostBreakdown report={data} />}
    </div>
  );
}

function CostBreakdown({ report }: { report: CostReport }): JSX.Element {
  const providerMax = Math.max(...report.per_provider.map((p) => p.usd), 0.01);
  const agentMax = Math.max(...report.per_agent.map((a) => a.usd), 0.01);

  return (
    <div className="space-y-6">
      <section className="vedix-card p-6">
        <p className="text-sm text-gray-500">Total spend</p>
        <p className="text-4xl font-bold mt-1">${report.total_usd.toFixed(2)}</p>
        {report.window_start && (
          <p className="text-xs text-gray-400 mt-1">
            Since {new Date(report.window_start).toLocaleDateString()}
          </p>
        )}
      </section>

      <section className="vedix-card p-4">
        <h2 className="font-semibold mb-3">By provider</h2>
        {report.per_provider.length === 0 ? (
          <p className="text-gray-500 text-sm">No spend recorded.</p>
        ) : (
          <ul className="space-y-2">
            {report.per_provider.map((p) => (
              <li key={p.provider}>
                <div className="flex justify-between text-sm">
                  <span>{p.provider}</span>
                  <span className="font-mono">${p.usd.toFixed(2)}</span>
                </div>
                <Bar value={p.usd} max={providerMax} color="bg-brand-500" />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="vedix-card p-4">
        <h2 className="font-semibold mb-3">By agent class</h2>
        {report.per_agent.length === 0 ? (
          <p className="text-gray-500 text-sm">No spend recorded.</p>
        ) : (
          <ul className="space-y-2">
            {report.per_agent.map((a) => (
              <li key={a.agent_class}>
                <div className="flex justify-between text-sm">
                  <span>{a.agent_class}</span>
                  <span className="font-mono">${a.usd.toFixed(2)}</span>
                </div>
                <Bar value={a.usd} max={agentMax} color="bg-amber-500" />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function Bar({
  value,
  max,
  color,
}: {
  value: number;
  max: number;
  color: string;
}): JSX.Element {
  const pct = Math.max(2, Math.round((value / max) * 100));
  return (
    <div className="h-2 bg-gray-100 rounded overflow-hidden">
      <div
        className={`h-full ${color}`}
        style={{ width: `${pct}%` }}
        role="presentation"
      />
    </div>
  );
}
