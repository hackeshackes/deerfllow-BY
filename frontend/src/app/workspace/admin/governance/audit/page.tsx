"use client";

import { useEffect, useState } from "react";

import { identityApi } from "@/core/identity/api";
import type { AuditEvent } from "@/core/identity/types";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterActor, setFilterActor] = useState("");

  useEffect(() => {
    setLoading(true);
    void identityApi
      .queryAudit({ actor_id: filterActor || undefined, limit: 100 })
      .then((d) => {
        setEvents(d.events);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [filterActor]);

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-bold">Audit Log</h1>
      <div className="mb-4 flex gap-2">
        <input
          className="border p-2"
          placeholder="Filter by actor ID"
          value={filterActor}
          onChange={(e) => setFilterActor(e.target.value)}
        />
        <button
          className="bg-blue-500 px-4 py-2 text-white"
          onClick={async () => {
            const csv = await identityApi.exportAuditCSV();
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "audit.csv";
            a.click();
          }}
        >
          Export CSV
        </button>
      </div>
      {loading ? (
        <div>Loading...</div>
      ) : (
        <table className="w-full border text-sm">
          <thead>
            <tr>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Success</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.occurred_at}</td>
                <td>{e.actor_id}</td>
                <td>{e.action}</td>
                <td>
                  {e.resource_type}/{e.resource_id}
                </td>
                <td>{e.success ? "✓" : "✗"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
