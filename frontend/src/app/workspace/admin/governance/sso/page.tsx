"use client";

import { useEffect, useState } from "react";

import { identityApi } from "@/core/identity/api";
import type { OIDCProvider } from "@/core/identity/types";

export default function SSOPage() {
  const [providers, setProviders] = useState<OIDCProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    identityApi
      .listProviders()
      .then(setProviders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }
  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-2xl font-bold">SSO Providers</h1>
      <table className="w-full border">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Issuer</th>
            <th>Enabled</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => (
            <tr key={p.id}>
              <td>{p.name}</td>
              <td>{p.type}</td>
              <td>{p.issuer_url}</td>
              <td>{p.enabled ? "✓" : "✗"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
