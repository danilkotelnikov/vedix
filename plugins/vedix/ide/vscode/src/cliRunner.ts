// src/cliRunner.ts — Subprocess shim around the local `vedix` CLI.
//
// When the user has not provided a SaaS token / disabled SaaS routing, every
// extension action funnels through here. We spawn `vedix <args>`, collect
// stdout, and try to JSON-parse it; on parse failure we surface the raw text
// under `{ raw: ... }` so callers can still decide how to present it.

import { spawn } from "node:child_process";

export interface CliResult {
  raw?: string;
  [key: string]: unknown;
}

export function runCli<T = CliResult>(args: string[]): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const proc = spawn("vedix", args, { shell: false });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    proc.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to spawn 'vedix' CLI: ${err.message}`));
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        return reject(new Error(`vedix exited ${code}: ${stderr.trim()}`));
      }
      try {
        resolve(JSON.parse(stdout) as T);
      } catch {
        resolve({ raw: stdout } as T);
      }
    });
  });
}
