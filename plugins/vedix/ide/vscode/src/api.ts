// src/api.ts — Thin HTTP client over the Vedix.ai SaaS API with CLI fallback.
//
// The user configures behaviour through three settings (see package.json
// `contributes.configuration`):
//   - vedix.useSaas:       boolean — if false, every call falls back to
//                          spawning the local `vedix` CLI via cliRunner.
//   - vedix.saasBaseUrl:   string  — base URL of the Vedix.ai API.
//   - vedix.saasToken:     string  — JWT used as the `Authorization` bearer.
//
// Node 18+ exposes `fetch` natively, so no extra dep is required.

import * as vscode from "vscode";
import { runCli } from "./cliRunner";

interface VedixConfig {
  base: string;
  token: string;
  useSaas: boolean;
}

function cfg(): VedixConfig {
  const c = vscode.workspace.getConfiguration("vedix");
  return {
    base: c.get<string>("saasBaseUrl") ?? "https://api.vedix.ai",
    token: c.get<string>("saasToken") ?? "",
    useSaas: c.get<boolean>("useSaas") ?? false,
  };
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const c = cfg();
  if (!c.useSaas) {
    throw new Error("call() requires SaaS mode; use runCli() for CLI mode");
  }
  const r = await fetch(`${c.base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${c.token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`Vedix API ${r.status}: ${body}`);
  }
  return r.json() as Promise<T>;
}

export interface NewJobSetup {
  topic: string;
  discipline: string;
  language: string;
  venue: string;
  hypothesis_style: string;
  experiment_type: string;
  primary_metric: string;
  expected_direction: string;
  tolerance: number;
}

export interface NewJobResponse {
  job_id?: string;
  jobId?: string;
  state?: string;
}

export async function newJob(setup: NewJobSetup): Promise<NewJobResponse> {
  if (!cfg().useSaas) {
    return runCli<NewJobResponse>([
      "new",
      "--topic", setup.topic,
      "--discipline", setup.discipline,
      "--language", setup.language,
      "--venue", setup.venue,
      "--json",
    ]);
  }
  return call<NewJobResponse>("/v1/api/jobs", {
    method: "POST",
    body: JSON.stringify(setup),
  });
}

export async function switchVenue(jobId: string, venue: string): Promise<unknown> {
  if (!cfg().useSaas) {
    return runCli(["switch", "venue", "--job", jobId, "--venue", venue, "--json"]);
  }
  return call(`/v1/api/jobs/${jobId}/switch-venue`, {
    method: "POST",
    body: JSON.stringify({ venue }),
  });
}

export interface AuditResponse {
  status: string;
  mismatches?: unknown[];
}

export async function runReproAudit(jobId: string): Promise<AuditResponse> {
  if (!cfg().useSaas) {
    return runCli<AuditResponse>([
      "audit-reproducibility",
      "--job", jobId,
      "--json",
    ]);
  }
  return call<AuditResponse>(`/v1/api/jobs/${jobId}/audit-reproducibility`, {
    method: "POST",
  });
}
