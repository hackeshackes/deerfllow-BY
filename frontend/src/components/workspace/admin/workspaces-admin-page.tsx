"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { AdminPageShell } from "./admin-page-shell";

type WorkspaceRecord = {
  id: string;
  name: string;
  role: string;
  default_personal: boolean;
  member_count: number;
  thread_count?: number;
  upload_file_count?: number;
  artifact_file_count?: number;
  agent_count?: number;
  members?: Array<{
    id: string;
    name: string;
    email: string;
    role: string;
  }>;
};

type WorkspaceMemberRecord = NonNullable<WorkspaceRecord["members"]>[number];

type UserRecord = {
  id: string;
  email: string;
  name: string;
};

export function WorkspacesAdminPage() {
  const [workspaces, setWorkspaces] = useState<WorkspaceRecord[]>([]);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [sessionRole, setSessionRole] = useState<"owner" | "member">("member");
  const [name, setName] = useState("");
  const [editingWorkspaceId, setEditingWorkspaceId] = useState<string | null>(null);
  const [editingWorkspaceName, setEditingWorkspaceName] = useState("");
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [selectedUserId, setSelectedUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const sharedWorkspaces = useMemo(
    () => workspaces.filter((workspace) => !workspace.default_personal),
    [workspaces],
  );

  async function loadData() {
    try {
      const [workspacesResponse, usersResponse, sessionResponse] = await Promise.all([
        fetch("/api/workspaces"),
        fetch("/api/users"),
        fetch("/api/session/me"),
      ]);
      if (!workspacesResponse.ok || !usersResponse.ok || !sessionResponse.ok) {
        throw new Error("加载空间数据失败");
      }
      const workspacesPayload = (await workspacesResponse.json()) as {
        workspaces: WorkspaceRecord[];
      };
      const usersPayload = (await usersResponse.json()) as { users: UserRecord[] };
      const sessionPayload = (await sessionResponse.json()) as { role: "owner" | "member" };
      setWorkspaces(workspacesPayload.workspaces);
      setUsers(usersPayload.users);
      setSessionRole(sessionPayload.role);
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
    setStatusMessage(null);
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
    setStatusMessage("共享空间已创建");
    await loadData();
  }

  async function addMember(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatusMessage(null);
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
    setStatusMessage("成员已加入共享空间");
    await loadData();
  }

  async function saveWorkspaceName(workspaceId: string) {
    setError(null);
    setStatusMessage(null);
    const response = await fetch(`/api/workspaces/${workspaceId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editingWorkspaceName }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "更新空间失败");
      return;
    }
    setEditingWorkspaceId(null);
    setEditingWorkspaceName("");
    setStatusMessage("空间名称已更新");
    await loadData();
  }

  async function deleteWorkspace(workspace: WorkspaceRecord) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(`确认删除共享空间 ${workspace.name} 吗？该空间下的线程、文件和成员关系将一并移除。`);
    if (!confirmed) return;
    const response = await fetch(`/api/workspaces/${workspace.id}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "删除空间失败");
      return;
    }
    setStatusMessage(`空间 ${workspace.name} 已删除`);
    await loadData();
  }

  async function removeMember(workspace: WorkspaceRecord, user: WorkspaceMemberRecord) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(`确认将 ${user.name}（${user.email}）移出空间 ${workspace.name} 吗？`);
    if (!confirmed) return;
    const response = await fetch(`/api/workspaces/${workspace.id}/members/${user.id}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "移除成员失败");
      return;
    }
    setStatusMessage(`已将 ${user.name} 移出空间 ${workspace.name}`);
    await loadData();
  }

  async function updateMemberRole(workspace: WorkspaceRecord, user: WorkspaceMemberRecord, role: string) {
    setError(null);
    setStatusMessage(null);
    const response = await fetch(`/api/workspaces/${workspace.id}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: user.id, role }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "更新成员角色失败");
      return;
    }
    setStatusMessage(`已更新 ${user.name} 的空间角色`);
    await loadData();
  }

  return (
    <AdminPageShell title="空间管理" description="为团队创建共享空间，查看空间规模，并把成员加入对应的协作区域。">
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
          {statusMessage && <p className="text-sm text-emerald-700">{statusMessage}</p>}
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
                  {editingWorkspaceId === workspace.id ? (
                    <div className="flex items-center gap-2">
                      <Input value={editingWorkspaceName} onChange={(event) => setEditingWorkspaceName(event.target.value)} className="h-9 w-72" />
                      <Button size="sm" onClick={() => void saveWorkspaceName(workspace.id)}>保存</Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingWorkspaceId(null)}>取消</Button>
                    </div>
                  ) : (
                    <div className="font-medium">{workspace.name}</div>
                  )}
                  <div className="text-muted-foreground mt-1">
                    {workspace.default_personal ? "个人空间" : "共享空间"} · 你的身份：
                    {workspace.role === "owner" ? "拥有者" : workspace.role === "admin" ? "管理员" : "成员"}
                  </div>
                </div>
                <div className="text-right text-sm text-slate-500">
                  <div>{workspace.member_count} 名成员</div>
                  <div>{workspace.thread_count ?? 0} 个线程 · {workspace.agent_count ?? 0} 个智能体</div>
                  <div>{workspace.upload_file_count ?? 0} 个上传 · {workspace.artifact_file_count ?? 0} 个产物</div>
                  <div>{workspace.default_personal ? "仅自己可见" : "空间成员可协作"}</div>
                  {!workspace.default_personal && sessionRole === "owner" && editingWorkspaceId !== workspace.id && (
                    <div className="mt-3 flex justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setEditingWorkspaceId(workspace.id); setEditingWorkspaceName(workspace.name); }}>
                        编辑空间
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void deleteWorkspace(workspace)}>
                        删除空间
                      </Button>
                    </div>
                  )}
                </div>
              </div>
              {!workspace.default_personal && (workspace.members?.length ?? 0) > 0 && (
                <div className="mt-4 rounded-2xl border bg-slate-50/60 p-3">
                  <div className="mb-2 text-sm font-medium text-slate-700">空间成员</div>
                  <div className="space-y-2">
                    {workspace.members?.map((member) => (
                      <div key={member.id} className="flex items-center justify-between rounded-xl bg-white px-3 py-2 text-sm">
                        <div>
                          <div className="font-medium">{member.name}</div>
                          <div className="text-slate-500">{member.email} · {member.role}</div>
                        </div>
                        {sessionRole === "owner" && member.role !== "owner" && (
                          <div className="flex items-center gap-2">
                            <select
                              className="border-input bg-background rounded-lg border px-2 py-1 text-xs"
                              value={member.role}
                              onChange={(event) => void updateMemberRole(workspace, member, event.target.value)}
                            >
                              <option value="member">member</option>
                              <option value="admin">admin</option>
                            </select>
                            <Button size="sm" variant="outline" onClick={() => void removeMember(workspace, member)}>
                              移除成员
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}
