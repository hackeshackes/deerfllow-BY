"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { connectorsApi, type DLQItem, type RegisteredConnector } from "@/core/connectors/api";

/**
 * Connector admin page — list registered connectors, surface DLQ entries,
 * and let an owner drop individual failed sends.
 */
export function ConnectorsAdminPage() {
  const [connectors, setConnectors] = useState<RegisteredConnector[]>([]);
  const [dlq, setDlq] = useState<DLQItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const reload = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      const [list, dlqResp] = await Promise.all([
        connectorsApi.list(),
        connectorsApi.listDLQ(50),
      ]);
      setConnectors(list.connectors);
      setDlq(dlqResp.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void reload();
  }, []);

  const onDelete = async (id: string): Promise<void> => {
    try {
      await connectorsApi.deleteDLQ(id);
      setDlq((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="flex flex-col gap-8 p-6" data-testid="connectors-admin-page">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Connectors</h1>
        <Button
          variant="outline"
          data-testid="reload-connectors"
          onClick={() => void reload()}
          disabled={isLoading}
        >
          {isLoading ? "Loading…" : "Reload"}
        </Button>
      </header>

      {error && (
        <div
          data-testid="connectors-error"
          className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </div>
      )}

      <section>
        <h2 className="mb-2 text-lg font-medium">Registered connectors</h2>
        <ul
          data-testid="connector-list"
          className="divide-y rounded border"
        >
          {connectors.length === 0 && (
            <li className="p-3 text-sm text-gray-500">No connectors registered yet.</li>
          )}
          {connectors.map((c) => (
            <li
              key={c.name}
              data-testid={`connector-${c.name}`}
              className="flex items-center justify-between p-3"
            >
              <span>
                <span className="font-medium">{c.display_name}</span>
                <span className="ml-2 text-xs text-gray-500">[{c.name}]</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-lg font-medium">Dead-letter queue</h2>
        <ul
          data-testid="dlq-list"
          className="divide-y rounded border"
        >
          {dlq.length === 0 && (
            <li className="p-3 text-sm text-gray-500">No failed messages.</li>
          )}
          {dlq.map((item) => (
            <li
              key={item.id}
              data-testid={`dlq-${item.id}`}
              className="flex items-start justify-between gap-4 p-3"
            >
              <div className="flex-1">
                <div className="text-sm">
                  <span className="font-medium">[{item.connector}]</span>{" "}
                  <span className="text-gray-600">{item.error}</span>
                </div>
                <div className="text-xs text-gray-500">
                  attempts={item.attempts} · {item.timestamp}
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => void onDelete(item.id)}
              >
                Drop
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
