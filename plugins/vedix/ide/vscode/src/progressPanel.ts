// src/progressPanel.ts — Webview panel that tails a job's SSE event stream.
//
// We open the panel in the column beside the active editor and inject a tiny
// HTML page that opens an EventSource to /v1/api/jobs/<id>/events. Each event
// is appended to a <pre> tag. The page also sets a CSP that allows only the
// configured SaaS base URL as the `connect-src`.

import * as vscode from "vscode";

export function openProgressPanel(
  ctx: vscode.ExtensionContext,
  jobId: string,
): vscode.WebviewPanel {
  const panel = vscode.window.createWebviewPanel(
    "vedixProgress",
    `Vedix job ${jobId.slice(0, 8)}`,
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true,
    },
  );

  const c = vscode.workspace.getConfiguration("vedix");
  const base = c.get<string>("saasBaseUrl") ?? "https://api.vedix.ai";
  const token = c.get<string>("saasToken") ?? "";
  const useSaas = c.get<boolean>("useSaas") ?? false;

  // For CLI-only users we cannot tail an SSE stream — show a static message.
  if (!useSaas) {
    panel.webview.html = renderCliFallback(jobId);
    ctx.subscriptions.push(panel);
    return panel;
  }

  panel.webview.html = renderSse(base, token, jobId);
  ctx.subscriptions.push(panel);
  return panel;
}

function renderSse(base: string, token: string, jobId: string): string {
  const safeBase = escapeHtml(base);
  const safeToken = encodeURIComponent(token);
  const safeJobId = escapeHtml(jobId);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src ${safeBase};" />
  <style>
    body { font-family: var(--vscode-editor-font-family, monospace); color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); padding: 12px; }
    h3 { margin-top: 0; }
    pre { white-space: pre-wrap; word-break: break-word; }
    .status { color: var(--vscode-descriptionForeground); font-size: 12px; }
  </style>
</head>
<body>
  <h3>Vedix job ${safeJobId}</h3>
  <div class="status" id="status">connecting...</div>
  <pre id="log"></pre>
  <script>
    const status = document.getElementById("status");
    const log = document.getElementById("log");
    const url = "${safeBase}/v1/api/jobs/${safeJobId}/events?token=${safeToken}";
    const es = new EventSource(url);
    es.onopen = () => { status.textContent = "streaming"; };
    es.onmessage = (e) => {
      log.textContent += "\\n" + e.data;
      window.scrollTo(0, document.body.scrollHeight);
    };
    es.onerror = () => { status.textContent = "stream error (will retry automatically)"; };
  </script>
</body>
</html>`;
}

function renderCliFallback(jobId: string): string {
  const safeJobId = escapeHtml(jobId);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';" />
  <style>
    body { font-family: var(--vscode-editor-font-family, monospace); padding: 12px; }
    code { background: var(--vscode-textBlockQuote-background); padding: 2px 4px; }
  </style>
</head>
<body>
  <h3>Vedix job ${safeJobId}</h3>
  <p>SaaS routing is disabled — live progress streaming is unavailable.</p>
  <p>To tail progress from the local CLI, run:</p>
  <p><code>vedix logs --job ${safeJobId} --follow</code></p>
</body>
</html>`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
