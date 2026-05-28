"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

import { AdminPageShell } from "./admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type UserRecord = {
  id: string;
  email: string;
  role: "owner" | "member";
  name: string;
  status: "invited" | "active" | "disabled";
  invited_at?: string | null;
  activated_at?: string | null;
  last_login_at?: string | null;
  invite?: {
    token: string;
    expires_at: string;
    activation_path: string;
  } | null;
};

export function UsersAdminPage() {
  const { t } = useI18n();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedUserId, setCopiedUserId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  function formatTime(value?: string | null) {
    return value ? new Date(value).toLocaleString() : "—";
  }

  function statusLabel(status: UserRecord["status"]) {
    if (status === "invited") return t.admin.users.pendingActivation;
    if (status === "active") return t.admin.users.normal;
    return t.admin.users.accountDisabled;
  }

  async function loadUsers() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/users");
      if (!response.ok) {
        throw new Error(t.admin.users.loadFailed);
      }
      const payload = (await response.json()) as { users: UserRecord[] };
      setUsers(payload.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.users.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [t.admin.users.loadFailed]);

  async function handleCreateUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setStatusMessage(null);
    try {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, role: "member" }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? t.admin.users.createMemberFailed);
      }
      setEmail("");
      setName("");
      setStatusMessage(t.admin.users.memberCreated);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.users.createMemberFailed);
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(user: UserRecord) {
    setError(null);
    setStatusMessage(null);
    const nextStatus = user.status === "disabled" ? (user.activated_at ? "active" : "invited") : "disabled";
    const response = await fetch(`/api/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? t.admin.users.createMemberFailed);
    }
    setStatusMessage(nextStatus === "disabled" ? t.admin.users.accountDisabled_ : t.admin.users.accountRestored);
    await loadUsers();
  }

  async function resendInvite(user: UserRecord) {
    setError(null);
    setStatusMessage(null);
    const response = await fetch(`/api/users/${user.id}/invite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expires_in_hours: 72 }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? t.admin.users.createMemberFailed);
    }
    setStatusMessage(t.admin.users.inviteResent);
    await loadUsers();
  }

  async function deleteUser(user: UserRecord) {
    setError(null);
    setStatusMessage(null);
    const confirmed = window.confirm(t.admin.users.confirmDeleteUser.replace("{email}", user.email));
    if (!confirmed) {
      return;
    }

    const response = await fetch(`/api/users/${user.id}`, { method: "DELETE" });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? t.admin.users.createMemberFailed);
    }
    setStatusMessage(t.admin.users.userDeleted.replace("{email}", user.email));
    await loadUsers();
  }

  async function copyInviteLink(user: UserRecord) {
    const invitePath = user.invite?.activation_path;
    if (!invitePath) return;
    await navigator.clipboard.writeText(`${window.location.origin}${invitePath}`);
    setCopiedUserId(user.id);
    window.setTimeout(() => setCopiedUserId(null), 1500);
  }

  return (
    <AdminPageShell title={t.admin.users.title} description={t.admin.users.description}>
      <Card>
        <CardHeader>
          <CardTitle>{t.admin.users.userManagement}</CardTitle>
          <CardDescription>{t.admin.users.userManagementDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1.4fr_1fr_auto]" onSubmit={handleCreateUser}>
            <Input type="email" placeholder={t.admin.users.memberEmailPlaceholder} value={email} onChange={(event) => setEmail(event.target.value)} required />
            <Input placeholder={t.admin.users.displayNamePlaceholder} value={name} onChange={(event) => setName(event.target.value)} />
            <Button disabled={creating}>{creating ? t.admin.users.creating : t.admin.users.createInvitedMember}</Button>
          </form>
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
          {statusMessage && <p className="mt-4 text-sm text-emerald-700">{statusMessage}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.users.memberList}</CardTitle>
          <CardDescription>{t.admin.users.memberListDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-slate-500">{t.admin.users.loadingMembers}</p>
          ) : (
            <div className="overflow-hidden rounded-2xl border">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 font-medium">{t.admin.users.member}</th>
                    <th className="px-4 py-3 font-medium">{t.admin.users.email}</th>
                    <th className="px-4 py-3 font-medium">{t.admin.users.role}</th>
                    <th className="px-4 py-3 font-medium">{t.admin.users.status}</th>
                    <th className="px-4 py-3 font-medium">{t.admin.users.inviteInfo}</th>
                    <th className="px-4 py-3 font-medium">{t.admin.users.lastLogin}</th>
                    <th className="px-4 py-3 font-medium text-right">{t.admin.users.operations}</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-t align-top">
                      <td className="px-4 py-3">{user.name}</td>
                      <td className="px-4 py-3 text-slate-600">{user.email}</td>
                      <td className="px-4 py-3">{user.role === "owner" ? t.admin.users.owner : t.admin.users.member}</td>
                      <td className="px-4 py-3">{statusLabel(user.status)}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {user.invite ? (
                          <div className="space-y-1">
                            <div>{t.admin.users.inviteTime}：{formatTime(user.invited_at)}</div>
                            <div>{t.admin.users.expiresTime}：{new Date(user.invite.expires_at).toLocaleString()}</div>
                            <button className="text-primary cursor-pointer text-xs underline" type="button" onClick={() => void copyInviteLink(user)}>
                              {copiedUserId === user.id ? t.admin.users.copied : t.admin.users.copyInviteLink}
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-1">
                            <div>{t.admin.users.inviteTime}：{formatTime(user.invited_at)}</div>
                            <div>{t.admin.users.activationTime}：{formatTime(user.activated_at)}</div>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{formatTime(user.last_login_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {user.role === "owner" ? null : (
                          <div className="flex justify-end gap-2">
                            {user.status === "invited" && (
                              <Button variant="outline" size="sm" onClick={() => void resendInvite(user)}>
                                {t.admin.users.resendInvite}
                              </Button>
                            )}
                            <Button variant="outline" size="sm" onClick={() => void toggleStatus(user)}>
                              {user.status === "disabled" ? t.admin.users.restoreAccount : t.admin.users.disableAccount}
                            </Button>
                            <Button variant="destructive" size="sm" onClick={() => void deleteUser(user).catch((err) => setError(err instanceof Error ? err.message : t.admin.users.createMemberFailed))}>
                              {t.admin.users.deleteUser}
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </AdminPageShell>
  );
}