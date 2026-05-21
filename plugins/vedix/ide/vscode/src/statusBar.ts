// src/statusBar.ts — Persistent status-bar item for the Vedix extension.
//
// Always visible (right-aligned) with a beaker icon. Clicking it opens the
// progress panel for a user-supplied job id. When SaaS routing is enabled,
// we additionally poll the cost-ledger endpoint every five minutes and
// surface the running USD total inline.

import * as vscode from "vscode";

const POLL_INTERVAL_MS = 5 * 60 * 1000;

interface CostResponse {
  total_usd?: number;
}

export function registerStatusBar(ctx: vscode.ExtensionContext): void {
  const item = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100,
  );
  item.text = "$(beaker) Vedix";
  item.tooltip = "Vedix: click to open the progress panel";
  item.command = "vedix.openPanel";
  item.show();
  ctx.subscriptions.push(item);

  const c = vscode.workspace.getConfiguration("vedix");
  if (!c.get<boolean>("useSaas")) {
    // CLI-only mode — leave the status bar with the static label.
    return;
  }

  const refresh = async (): Promise<void> => {
    try {
      const base = c.get<string>("saasBaseUrl") ?? "https://api.vedix.ai";
      const token = c.get<string>("saasToken") ?? "";
      const r = await fetch(`${base}/v1/api/cost?since=30d`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) return;
      const d = (await r.json()) as CostResponse;
      if (typeof d.total_usd === "number") {
        item.text = `$(beaker) Vedix · $${d.total_usd.toFixed(2)}`;
      }
    } catch {
      // Swallow — the status bar should never throw an error to the user.
    }
  };

  void refresh();
  const interval = setInterval(() => {
    void refresh();
  }, POLL_INTERVAL_MS);
  ctx.subscriptions.push({ dispose: () => clearInterval(interval) });
}
