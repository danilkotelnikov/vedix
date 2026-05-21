// src/extension.ts — Vedix Research Workbench entrypoint.
//
// The host invokes activate() on startup (see "activationEvents" in package.json).
// We register commands, the status-bar item, and the citation hover provider.

import * as vscode from "vscode";
import { registerCommands } from "./commands";
import { registerStatusBar } from "./statusBar";
import { registerCitationHover } from "./citationHover";

export function activate(ctx: vscode.ExtensionContext): void {
  console.log("[vedix] extension activated");
  registerCommands(ctx);
  registerStatusBar(ctx);
  registerCitationHover(ctx);
}

export function deactivate(): void {
  // Subscriptions registered through ctx.subscriptions are disposed automatically.
}
