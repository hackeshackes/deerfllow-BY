/** Connector type — mirrors the backend `BaseConnector.name` registry. */
export type ConnectorType = "feishu" | "dingtalk" | "wecom" | "email" | "slack" | "jira" | "linear";

export interface RegisteredConnector {
  name: string;
  display_name: string;
}

export interface DLQItem {
  id: string;
  connector: string;
  error: string;
  attempts: number;
  timestamp: string;
  message?: { text?: string; target?: Record<string, unknown> };
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    credentials: "include",
  });
  if (!resp.ok) {
    throw new Error(`${resp.status}: ${await resp.text()}`);
  }
  return resp.json() as Promise<T>;
}

export const connectorsApi = {
  /** List connectors currently registered with the runtime. */
  list: () => fetchJSON<{ connectors: RegisteredConnector[] }>("/api/connectors"),

  /** List DLQ entries — most recent first. */
  listDLQ: (limit = 50) =>
    fetchJSON<{ items: DLQItem[] }>(`/api/connectors/dlq?limit=${limit}`),

  /** Drop a single DLQ entry. */
  deleteDLQ: async (id: string): Promise<void> => {
    const resp = await fetch(
      `/api/connectors/dlq/${encodeURIComponent(id)}`,
      { method: "DELETE", credentials: "include" },
    );
    if (!resp.ok && resp.status !== 204) {
      throw new Error(`${resp.status}: ${await resp.text()}`);
    }
  },
};
