import { getBackendBaseURL } from "../config";

import type { Model } from "./types";

export async function loadModels() {
  const res = await fetch(`${getBackendBaseURL()}/api/models`);
  const { models } = (await res.json()) as { models: Model[] };
  return models;
}

export async function loadAdminModels() {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/models`);
  const { models } = (await res.json()) as { models: Model[] };
  return models;
}

export async function saveAdminModel(payload: Partial<Model> & { name: string; use: string; model: string }) {
  const isNew = !payload.name;
  const url = isNew ? `${getBackendBaseURL()}/api/admin/models` : `${getBackendBaseURL()}/api/admin/models/${payload.name}`;
  const method = isNew ? "POST" : "PATCH";
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return (await res.json()) as Model;
}

export async function testAdminModel(name: string) {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/models/${name}/test`, { method: "POST" });
  return (await res.json()) as { ok: boolean; message: string };
}

export async function reloadAdminModels(name: string) {
  const res = await fetch(`${getBackendBaseURL()}/api/admin/models/${name}/reload`, { method: "POST" });
  return (await res.json()) as { models: Model[] };
}
