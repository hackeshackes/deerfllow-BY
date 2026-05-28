"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

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
  const { t } = useI18n();
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
        throw new Error(t.admin.workspaces.loadFailed);
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
      setError(err instanceof Error ? err.message : t.admin.workspaces.loadFailed);
    }
  }

  useEffect(() => {
    void loadData();
  }, [t.admin.workspaces.loadFailed]);

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
      setError(body?.detail ?? t.admin.workspaces.createWorkspaceFailed);
      return;
    }
    setName("");
    setStatusMessage(t.admin.workspaces.workspaceCreated);
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
      setError(body?.detail ?? t.admin.workspaces.addMemberFailed);
      return;
    }
    setStatusMessage(t.admin.workspaces.memberAddedToWorkspace);
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
      setError(body?.detail ?? t.admin.workspaces.updateWorkspaceFailed);
      return;
    }
    setEditingWorkspaceId(null);
    setEditingWorkspaceName("");
    setStatusMessage(t.admin.workspaces.workspaceNameUpdated);
    await loadData();
  }

  async function deleteWorkspace(workspace: WorkspaceRecord) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(t.admin.workspaces.confirmDeleteWorkspace.replace("{name}", workspace.name));
    if (!confirmed) return;
    const response = await fetch(`/api/workspaces/${workspace.id}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? t.admin.workspaces.deleteWorkspaceFailed);
      return;
    }
    setStatusMessage(t.admin.workspaces.workspaceDeleted.replace("{name}", workspace.name));
    await loadData();
  }

  async function removeMember(workspace: WorkspaceRecord, user: WorkspaceMemberRecord) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(t.admin.workspaces.confirmRemoveMember.replace("{name}", user.name).replace("{email}", user.email).replace("{workspace}", workspace.name));
    if (!confirmed) return;
    const response = await fetch(`/api/workspaces/${workspace.id}/members/${user.id}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? t.admin.workspaces.removeMemberFailed);
      return;
    }
    setStatusMessage(t.admin.workspaces.memberRemovedFromWorkspace.replace("{name}", user.name).replace("{workspace}", workspace.name));
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
      setError(body?.detail ?? t.admin.workspaces.updateMemberRoleFailed);
      return;
    }
    setStatusMessage(t.admin.workspaces.memberRoleUpdated.replace("{name}", user.name));
    await loadData();
  }

  function getRoleLabel(role: string) {
    if (role === "owner") return t.admin.workspaces.owner;
    if (role === "admin") return t.admin.workspaces.admin;
    return t.admin.workspaces.member;
  }

  return (
    <AdminPageShell title={t.admin.workspaces.title} description={t.admin.workspaces.description}>
      <Card>
        <CardHeader>
          <CardTitle>{t.admin.workspaces.workspaceManagement}</CardTitle>
          <CardDescription>{t.admin.workspaces.workspaceManagementDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="flex gap-3" onSubmit={createWorkspace}>
            <Input placeholder={t.admin.workspaces.workspaceNamePlaceholder} value={name} onChange={(event) => setName(event.target.value)} required />
            <Button>{t.admin.workspaces.createSharedWorkspace}</Button>
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
            <Button disabled={!selectedWorkspaceId || !selectedUserId}>{t.admin.workspaces.addMember}</Button>
          </form>

          {error && <p className="text-sm text-rose-600">{error}</p>}
          {statusMessage && <p className="text-sm text-emerald-700">{statusMessage}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.workspaces.workspaceOverview}</CardTitle>
          <CardDescription>{t.admin.workspaces.workspaceOverviewDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {workspaces.map((workspace) => (
            <div key={workspace.id} className="rounded-2xl border px-4 py-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  {editingWorkspaceId === workspace.id ? (
                    <div className="flex items-center gap-2">
                      <Input value={editingWorkspaceName} onChange={(event) => setEditingWorkspaceName(event.target.value)} className="h-9 w-72" />
                      <Button size="sm" onClick={() => void saveWorkspaceName(workspace.id)}>{t.admin.workspaces.save}</Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingWorkspaceId(null)}>{t.admin.workspaces.cancel}</Button>
                    </div>
                  ) : (
                    <div className="font-medium">{workspace.name}</div>
                  )}
                  <div className="text-muted-foreground mt-1">
                    {workspace.default_personal ? t.admin.workspaces.personalSpace : t.admin.workspaces.sharedSpace} · {t.admin.workspaces.yourRole}：
                    {getRoleLabel(workspace.role)}
                  </div>
                </div>
                <div className="text-right text-sm text-slate-500">
                  <div>{workspace.member_count} {t.admin.workspaces.members}</div>
                  <div>{workspace.thread_count ?? 0} {t.admin.workspaces.threads} · {workspace.agent_count ?? 0} {t.admin.workspaces.agents}</div>
                  <div>{workspace.upload_file_count ?? 0} {t.admin.workspaces.uploads} · {workspace.artifact_file_count ?? 0} {t.admin.workspaces.artifacts}</div>
                  <div>{workspace.default_personal ? t.admin.workspaces.onlyVisibleToYourself : t.admin.workspaces.workspaceMembersCanCollaborate}</div>
                  {!workspace.default_personal && sessionRole === "owner" && editingWorkspaceId !== workspace.id && (
                    <div className="mt-3 flex justify-end gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setEditingWorkspaceId(workspace.id); setEditingWorkspaceName(workspace.name); }}>
                        {t.admin.workspaces.editWorkspace}
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => void deleteWorkspace(workspace)}>
                        {t.admin.workspaces.deleteWorkspace}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
              {!workspace.default_personal && (workspace.members?.length ?? 0) > 0 && (
                <div className="mt-4 rounded-2xl border bg-slate-50/60 p-3">
                  <div className="mb-2 text-sm font-medium text-slate-700">{t.admin.workspaces.workspaceMembersCanCollaborate}</div>
                  <div className="space-y-2">
                    {workspace.members?.map((member) => (
                      <div key={member.id} className="flex items-center justify-between rounded-xl bg-white px-3 py-2 text-sm">
                        <div>
                          <div className="font-medium">{member.name}</div>
                          <div className="text-slate-500">{member.email} · {getRoleLabel(member.role)}</div>
                        </div>
                        {sessionRole === "owner" && member.role !== "owner" && (
                          <div className="flex items-center gap-2">
                            <select
                              className="border-input bg-background rounded-lg border px-2 py-1 text-xs"
                              value={member.role}
                              onChange={(event) => void updateMemberRole(workspace, member, event.target.value)}
                            >
                              <option value="member">{t.admin.workspaces.member}</option>
                              <option value="admin">{t.admin.workspaces.admin}</option>
                            </select>
                            <Button size="sm" variant="outline" onClick={() => void removeMember(workspace, member)}>
                              {t.admin.workspaces.removeMember}
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