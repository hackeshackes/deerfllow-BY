"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type WorkspaceRecord = {
  id: string;
  name: string;
  role: string;
  default_personal: boolean;
};

type UserRecord = {
  id: string;
  email: string;
  name: string;
};

export function WorkspacesAdminPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceRecord[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [name, setName] = useState("");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function loadData() {
    try {
      const [workspacesResponse, usersResponse] = await Promise.all([
        fetch("/api/workspaces"),
        fetch("/api/users"),
      ]);
      if (!workspacesResponse.ok || !usersResponse.ok) {
        throw new Error("Failed to load workspace data");
      }
      const workspacesPayload = (await workspacesResponse.json()) as {
        workspaces: WorkspaceRecord[];
      };
      const usersPayload = (await usersResponse.json()) as { users: UserRecord[] };
      setWorkspaces(workspacesPayload.workspaces);
      setUsers(usersPayload.users);
      setSelectedWorkspaceId(workspacesPayload.workspaces[0]?.id ?? "");
      setSelectedUserId(usersPayload.users.find((user) => user.id !== "owner")?.id ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace data");
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function createWorkspace(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const response = await fetch("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "Failed to create workspace");
      return;
    }
    setName("");
    await loadData();
  }

  async function addMember(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const response = await fetch(`/api/workspaces/${selectedWorkspaceId}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: selectedUserId, role: "member" }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "Failed to add member");
      return;
    }
    await loadData();
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Workspace management</CardTitle>
          <CardDescription>Create shared workspaces and add members.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="flex gap-3" onSubmit={createWorkspace}>
            <Input
              placeholder="Workspace name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
            <Button>Create workspace</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={addMember}>
            <select
              className="border-input bg-background rounded-xl border px-3 py-2"
              value={selectedWorkspaceId}
              onChange={(event) => setSelectedWorkspaceId(event.target.value)}
            >
              {workspaces.filter((workspace) => !workspace.default_personal).map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
            <select
              className="border-input bg-background rounded-xl border px-3 py-2"
              value={selectedUserId}
              onChange={(event) => setSelectedUserId(event.target.value)}
            >
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name} ({user.email})
                </option>
              ))}
            </select>
            <Button>Add member</Button>
          </form>

          {error && <p className="text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Visible workspaces</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {workspaces.map((workspace) => (
            <div key={workspace.id} className="rounded-2xl border px-4 py-3">
              <div className="font-medium">{workspace.name}</div>
              <div className="text-muted-foreground mt-1">
                {workspace.default_personal ? "Personal workspace" : "Shared workspace"} · role: {workspace.role}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
