"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type UserRecord = {
  id: string;
  email: string;
  role: "owner" | "member";
  name: string;
  status: "invited" | "active" | "disabled";
  activated_at?: string | null;
  invite?: {
    token: string;
    expires_at: string;
    activation_path: string;
  } | null;
};

export function UsersAdminPage() {
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedUserId, setCopiedUserId] = useState<string | null>(null);

  async function loadUsers() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/users");
      if (!response.ok) {
        throw new Error("Failed to load users");
      }
      const payload = (await response.json()) as { users: UserRecord[] };
      setUsers(payload.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, []);

  async function handleCreateUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const response = await fetch("/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, role: "member" }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "Failed to create user");
      }
      setEmail("");
      setName("");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setCreating(false);
    }
  }

  async function toggleStatus(user: UserRecord) {
    const nextStatus = user.status === "disabled" ? (user.activated_at ? "active" : "invited") : "disabled";
    const response = await fetch(`/api/users/${user.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: nextStatus }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? "Failed to update user");
    }
    await loadUsers();
  }

  async function resendInvite(user: UserRecord) {
    const response = await fetch(`/api/users/${user.id}/invite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expires_in_hours: 72 }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? "Failed to resend invite");
    }
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
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>User management</CardTitle>
          <CardDescription>Create invited members and manage account access for this BY workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1.4fr_1fr_auto]" onSubmit={handleCreateUser}>
            <Input type="email" placeholder="member@example.com" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <Input placeholder="Display name" value={name} onChange={(event) => setName(event.target.value)} />
            <Button disabled={creating}>{creating ? "Creating..." : "Create invited user"}</Button>
          </form>
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>Invited users activate their accounts through a one-time invite link.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-slate-500">Loading users...</p>
          ) : (
            <div className="overflow-hidden rounded-2xl border">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Email</th>
                    <th className="px-4 py-3 font-medium">Role</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Invite</th>
                    <th className="px-4 py-3 font-medium text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-t align-top">
                      <td className="px-4 py-3">{user.name}</td>
                      <td className="px-4 py-3 text-slate-600">{user.email}</td>
                      <td className="px-4 py-3 capitalize">{user.role}</td>
                      <td className="px-4 py-3 capitalize">{user.status}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {user.invite ? (
                          <div className="space-y-1">
                            <div>Expires: {new Date(user.invite.expires_at).toLocaleString()}</div>
                            <button className="text-primary cursor-pointer text-xs underline" type="button" onClick={() => void copyInviteLink(user)}>
                              {copiedUserId === user.id ? "Copied" : "Copy activation link"}
                            </button>
                          </div>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {user.role === "owner" ? null : (
                          <div className="flex justify-end gap-2">
                            {user.status === "invited" && (
                              <Button variant="outline" size="sm" onClick={() => void resendInvite(user)}>
                                Resend invite
                              </Button>
                            )}
                            <Button variant="outline" size="sm" onClick={() => void toggleStatus(user)}>
                              {user.status === "disabled" ? "Re-enable" : "Disable"}
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
    </div>
  );
}
