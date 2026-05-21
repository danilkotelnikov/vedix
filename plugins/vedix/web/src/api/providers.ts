import { api } from "./client";

export interface Provider {
  name: string;
  region: string;
  added_at: number;
}

export interface ProviderChain {
  chain: string[];
}

/** The 14 provider IDs accepted by the BYOK service (matches B2). */
export const PROVIDER_IDS = [
  "anthropic",
  "openai",
  "google",
  "openrouter",
  "together",
  "deepseek",
  "qwen",
  "moonshot",
  "zhipu",
  "gigachat",
  "yandexgpt",
  "mistral",
  "cohere",
  "local",
] as const;

export type ProviderId = (typeof PROVIDER_IDS)[number];

export const listProviders = (): Promise<Provider[]> =>
  api<Provider[]>("/v1/api/providers");

export const addProvider = (
  name: string,
  api_key: string,
  extra: Record<string, unknown> = {},
): Promise<{ ok: true }> =>
  api<{ ok: true }>("/v1/api/providers", {
    method: "POST",
    body: JSON.stringify({ name, api_key, ...extra }),
  });

export const removeProvider = (name: string): Promise<void> =>
  api<void>(`/v1/api/providers/${name}`, { method: "DELETE" });

export const getChain = (): Promise<ProviderChain> =>
  api<ProviderChain>("/v1/api/providers/chain");

export const setChain = (chain: string[]): Promise<{ ok: true }> =>
  api<{ ok: true }>("/v1/api/providers/chain", {
    method: "POST",
    body: JSON.stringify({ chain }),
  });
