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
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [copiedUserId, setCopiedUserId] = useState<string | null>(null);

  function formatTime(value?: string | null) {
    return value ? new Date(value).toLocaleString() : "—";
  }

  function statusLabel(status: UserRecord["status"]) {
    if (status === "invited") return "待激活";
    if (status === "active") return "正常";
    return "已禁用";
  }

  async function loadUsers() {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/users");
      if (!response.ok) {
        throw new Error("加载成员失败");
      }
      const payload = (await response.json()) as { users: UserRecord[] };
      setUsers(payload.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载成员失败");
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
        throw new Error(body?.detail ?? "创建成员失败");
      }
      setEmail("");
      setName("");
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建成员失败");
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
      throw new Error(body?.detail ?? "更新成员状态失败");
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
      throw new Error(body?.detail ?? "重新邀请失败");
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
          <CardTitle>用户管理</CardTitle>
          <CardDescription>创建受邀成员、发出激活链接，并管理当前 BY 部署的访问权限。</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1.4fr_1fr_auto]" onSubmit={handleCreateUser}>
            <Input type="email" placeholder="成员邮箱，例如 member@example.com" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <Input placeholder="显示名称，例如 市场负责人" value={name} onChange={(event) => setName(event.target.value)} />
            <Button disabled={creating}>{creating ? "创建中..." : "创建受邀成员"}</Button>
          </form>
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>成员列表</CardTitle>
          <CardDescription>受邀成员需要通过一次性激活链接设置密码后，才能正式登录使用。</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-slate-500">正在加载成员信息...</p>
          ) : (
            <div className="overflow-hidden rounded-2xl border">
              <table className="w-full text-left text-sm">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 font-medium">成员</th>
                    <th className="px-4 py-3 font-medium">邮箱</th>
                    <th className="px-4 py-3 font-medium">角色</th>
                    <th className="px-4 py-3 font-medium">状态</th>
                    <th className="px-4 py-3 font-medium">邀请信息</th>
                    <th className="px-4 py-3 font-medium">最近登录</th>
                    <th className="px-4 py-3 font-medium text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id} className="border-t align-top">
                      <td className="px-4 py-3">{user.name}</td>
                      <td className="px-4 py-3 text-slate-600">{user.email}</td>
                      <td className="px-4 py-3">{user.role === "owner" ? "拥有者" : "成员"}</td>
                      <td className="px-4 py-3">{statusLabel(user.status)}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {user.invite ? (
                          <div className="space-y-1">
                            <div>邀请时间：{formatTime(user.invited_at)}</div>
                            <div>过期时间：{new Date(user.invite.expires_at).toLocaleString()}</div>
                            <button className="text-primary cursor-pointer text-xs underline" type="button" onClick={() => void copyInviteLink(user)}>
                              {copiedUserId === user.id ? "已复制" : "复制激活链接"}
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-1">
                            <div>邀请时间：{formatTime(user.invited_at)}</div>
                            <div>激活时间：{formatTime(user.activated_at)}</div>
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600">{formatTime(user.last_login_at)}</td>
                      <td className="px-4 py-3 text-right">
                        {user.role === "owner" ? null : (
                          <div className="flex justify-end gap-2">
                            {user.status === "invited" && (
                              <Button variant="outline" size="sm" onClick={() => void resendInvite(user)}>
                                重新邀请
                              </Button>
                            )}
                            <Button variant="outline" size="sm" onClick={() => void toggleStatus(user)}>
                              {user.status === "disabled" ? "恢复使用" : "禁用账号"}
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
