import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  PROVIDER_IDS,
  addProvider,
  getChain,
  listProviders,
  removeProvider,
  setChain,
  type ProviderId,
} from "../api/providers";

/**
 * BYOK Providers page. Lets the user:
 *   - list configured providers + the region they were keyed in for
 *   - add a new provider with an API key
 *   - remove an existing provider
 *   - reorder the active provider chain (drag-free, up/down buttons)
 */
export function ProvidersPage(): JSX.Element {
  const qc = useQueryClient();

  const providersQuery = useQuery({
    queryKey: ["providers"],
    queryFn: listProviders,
  });

  const chainQuery = useQuery({
    queryKey: ["providers", "chain"],
    queryFn: getChain,
  });

  const addMut = useMutation({
    mutationFn: ({ name, key }: { name: ProviderId; key: string }) =>
      addProvider(name, key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["providers"] });
    },
  });

  const removeMut = useMutation({
    mutationFn: removeProvider,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["providers"] });
      qc.invalidateQueries({ queryKey: ["providers", "chain"] });
    },
  });

  const chainMut = useMutation({
    mutationFn: setChain,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["providers", "chain"] });
    },
  });

  const providers = providersQuery.data ?? [];
  const chain = chainQuery.data?.chain ?? [];

  const [name, setName] = useState<ProviderId>("anthropic");
  const [key, setKey] = useState("");

  const onAdd = () => {
    if (!key.trim()) return;
    addMut.mutate(
      { name, key: key.trim() },
      {
        onSuccess: () => setKey(""),
      },
    );
  };

  const moveChain = (idx: number, delta: -1 | 1) => {
    const next = [...chain];
    const swap = idx + delta;
    if (swap < 0 || swap >= next.length) return;
    [next[idx], next[swap]] = [next[swap]!, next[idx]!];
    chainMut.mutate(next);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <header>
        <h1 className="text-2xl font-bold">BYOK providers</h1>
        <p className="text-sm text-gray-500 mt-1">
          Bring your own keys. Vedix never sees plaintext keys after they
          leave your browser; they are encrypted at rest by the SaaS.
        </p>
      </header>

      <section className="vedix-card p-4 space-y-3">
        <h2 className="font-semibold">Add provider</h2>
        <div className="flex flex-col md:flex-row gap-2">
          <select
            value={name}
            onChange={(e) => setName(e.target.value as ProviderId)}
            className="vedix-input md:w-48"
          >
            {PROVIDER_IDS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="API key"
            className="vedix-input flex-1"
            type="password"
            autoComplete="off"
          />
          <button
            onClick={onAdd}
            disabled={!key.trim() || addMut.isPending}
            className="vedix-button"
          >
            {addMut.isPending ? "Adding…" : "Add"}
          </button>
        </div>
        {addMut.isError && (
          <p className="text-red-600 text-sm">
            {(addMut.error as Error).message}
          </p>
        )}
      </section>

      <section className="vedix-card p-4">
        <h2 className="font-semibold mb-3">
          Configured ({providers.length})
        </h2>
        {providersQuery.isLoading && (
          <p className="text-gray-500 text-sm">Loading…</p>
        )}
        {!providersQuery.isLoading && providers.length === 0 && (
          <p className="text-gray-500 text-sm">No providers yet.</p>
        )}
        <ul className="divide-y divide-gray-100">
          {providers.map((p) => (
            <li
              key={p.name}
              className="flex justify-between items-center py-2"
            >
              <span>
                <strong>{p.name}</strong>
                <span className="text-sm text-gray-500 ml-2">
                  ({p.region}, added {formatDate(p.added_at)})
                </span>
              </span>
              <button
                onClick={() => removeMut.mutate(p.name)}
                disabled={removeMut.isPending}
                className="text-red-600 hover:underline text-sm"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section className="vedix-card p-4">
        <h2 className="font-semibold mb-3">Active chain</h2>
        <p className="text-xs text-gray-500 mb-3">
          Vedix tries providers top-down. If one fails or hits a quota,
          the next takes over.
        </p>
        {chainQuery.isLoading && (
          <p className="text-gray-500 text-sm">Loading…</p>
        )}
        {chain.length === 0 && !chainQuery.isLoading && (
          <p className="text-gray-500 text-sm">No chain configured yet.</p>
        )}
        <ol className="space-y-1">
          {chain.map((entry, idx) => (
            <li
              key={`${entry}-${idx}`}
              className="flex items-center justify-between border border-gray-100 rounded px-3 py-1.5"
            >
              <span>
                <span className="text-gray-400 font-mono mr-3">{idx + 1}.</span>
                <strong>{entry}</strong>
              </span>
              <span className="flex gap-1">
                <button
                  onClick={() => moveChain(idx, -1)}
                  disabled={idx === 0 || chainMut.isPending}
                  aria-label="Move up"
                  className="px-2 py-0.5 text-sm border rounded disabled:opacity-30"
                >
                  ↑
                </button>
                <button
                  onClick={() => moveChain(idx, 1)}
                  disabled={idx === chain.length - 1 || chainMut.isPending}
                  aria-label="Move down"
                  className="px-2 py-0.5 text-sm border rounded disabled:opacity-30"
                >
                  ↓
                </button>
              </span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}

function formatDate(ts: number): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleDateString();
}
