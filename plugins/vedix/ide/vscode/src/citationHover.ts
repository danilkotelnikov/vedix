// src/citationHover.ts — Hover provider for citation keys in .tex / .md files.
//
// Matches three forms commonly emitted by Vedix manuscripts:
//   - Pandoc-style:   [@smith2024]
//   - LaTeX:          \cite{smith2024, jones2023}
//   - LaTeX variants: \citep{...} / \citet{...} / \citeauthor{...}
//
// The tooltip surfaces the matched key and a pointer to the "Open Provenance"
// action (which will be wired up by the SGCA provenance ledger in B13/B11).

import * as vscode from "vscode";

const CITATION_RX = /\[@[\w:.\-]+\]|\\cite[a-z]*\{[\w:,.\-\s]+\}/;

export function registerCitationHover(ctx: vscode.ExtensionContext): void {
  ctx.subscriptions.push(
    vscode.languages.registerHoverProvider(
      [{ language: "latex" }, { language: "markdown" }],
      {
        provideHover(doc, pos) {
          const range = doc.getWordRangeAtPosition(pos, CITATION_RX);
          if (!range) return;
          const matched = doc.getText(range);
          const md = new vscode.MarkdownString(
            `**Vedix citation** \`${escapeMd(matched)}\`\n\n` +
              `Open the Provenance Ledger to inspect this citation's load-bearing verdict ` +
              `(counterfactual probe). Use the command palette: \`Vedix: Open Progress Panel\`.`,
          );
          md.isTrusted = false;
          return new vscode.Hover(md, range);
        },
      },
    ),
  );
}

function escapeMd(s: string): string {
  return s.replace(/`/g, "\\`");
}
