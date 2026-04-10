"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type WorkspaceRecord = {
  id: string;
  name: string;
  role: string;
  default_personal: boolean;
  member_count: number;
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

  const sharedWorkspaces = useMemo(
    () => workspaces.filter((workspace) => !workspace.default_personal),
    [workspaces],
  );

  async function loadData() {
    try {
      const [workspacesResponse, usersResponse] = await Promise.all([
        fetch("/api/workspaces"),
        fetch("/api/users"),
      ]);
      if (!workspacesResponse.ok || !usersResponse.ok) {
        throw new Error("加载空间数据失败");
      }
      const workspacesPayload = (await workspacesResponse.json()) as {
        workspaces: WorkspaceRecord[];
      };
      const usersPayload = (await usersResponse.json()) as { users: UserRecord[] };
      setWorkspaces(workspacesPayload.workspaces);
      setUsers(usersPayload.users);
      setSelectedWorkspaceId(
        workspacesPayload.workspaces.find((workspace) => !workspace.default_personal)?.id ?? "",
      );
      setSelectedUserId(usersPayload.users.find((user) => user.id !== "owner")?.id ?? "");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载空间数据失败");
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
      setError(body?.detail ?? "创建空间失败");
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
      setError(body?.detail ?? "添加成员失败");
      return;
    }
    await loadData();
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>空间管理</CardTitle>
          <CardDescription>为团队创建共享空间，并把成员加入对应的协作区域。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="flex gap-3" onSubmit={createWorkspace}>
            <Input placeholder="空间名称，例如 市场调研组" value={name} onChange={(event) => setName(event.target.value)} required />
            <Button>创建共享空间</Button>
          </form>

          <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={addMember}>
            <select className="border-input bg-background rounded-xl border px-3 py-2" value={selectedWorkspaceId} onChange={(event) => setSelectedWorkspaceId(event.target.value)}>
              {sharedWorkspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
            <select className="border-input bg-background rounded-xl border px-3 py-2" value={selectedUserId} onChange={(event) => setSelectedUserId(event.target.value)}>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}（{user.email}）
                </option>
              ))}
            </select>
            <Button disabled={!selectedWorkspaceId || !selectedUserId}>添加成员</Button>
          </form>

          {error && <p className="text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>空间概览</CardTitle>
          <CardDescription>清晰区分个人空间与共享空间，帮助团队成员理解数据归属。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {workspaces.map((workspace) => (
            <div key={workspace.id} className="rounded-2xl border px-4 py-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-medium">{workspace.name}</div>
                  <div className="text-muted-foreground mt-1">
                    {workspace.default_personal ? "个人空间" : "共享空间"} · 你的身份：
                    {workspace.role === "owner" ? "拥有者" : workspace.role === "admin" ? "管理员" : "成员"}
                  </div>
                </div>
                <div className="text-right text-sm text-slate-500">
                  <div>{workspace.member_count} 名成员</div>
                  <div>{workspace.default_personal ? "仅自己可见" : "空间成员可协作"}</div>
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
