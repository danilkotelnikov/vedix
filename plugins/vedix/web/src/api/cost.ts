import { api, buildUrl } from "./client";

export interface CostBreakdown {
  /** Provider key, e.g. "anthropic". */
  provider?: string;
  /** Or an agent class, e.g. "reviewer". */
  agent_class?: string;
  usd: number;
}

export interface CostReport {
  total_usd: number;
  per_provider: Array<{ provider: string; usd: number }>;
  per_agent: Array<{ agent_class: string; usd: number }>;
  /** ISO 8601 lower bound of the window, e.g. "2026-04-22T00:00:00Z". */
  window_start?: string;
  /** Optional time-series for the chart pane. */
  series?: Array<{ ts: string; usd: number }>;
}

/**
 * Fetch the cost ledger.
 *
 * `since` accepts the same compact format the API uses ("24h", "7d",
 * "30d", "90d"). Defaults to the last 30 days.
 */
export const getCostReport = (since: string = "30d"): Promise<CostReport> =>
  api<CostReport>(buildUrl("/v1/api/cost", { since }));
