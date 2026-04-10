"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type SessionUser = {
  id: string;
  email: string;
  role: string;
  name: string;
  status: string;
  active_workspace_name?: string | null;
  active_workspace_role?: string | null;
};

export function AccountPage() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const workspaceType = user?.active_workspace_name?.includes("Personal") ? "个人空间" : "共享空间";

  useEffect(() => {
    async function loadUser() {
      const response = await fetch("/api/users/me");
      if (!response.ok) return;
      const payload = (await response.json()) as SessionUser;
      setUser(payload);
    }
    void loadUser();
  }, []);

  async function handlePasswordChange(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    const response = await fetch("/api/account/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail ?? "修改密码失败，请稍后重试");
      return;
    }
    setCurrentPassword("");
    setNewPassword("");
    setMessage("密码已更新。");
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>账号信息</CardTitle>
          <CardDescription>查看你的账号资料、当前协作空间与权限信息。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="text-muted-foreground text-sm">姓名</div>
            <div className="mt-1 font-medium">{user?.name ?? "加载中..."}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">邮箱</div>
            <div className="mt-1 font-medium">{user?.email ?? "加载中..."}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">系统角色</div>
            <div className="mt-1 font-medium">{user?.role === "owner" ? "拥有者" : "成员"}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">当前空间</div>
            <div className="mt-1 font-medium">{user?.active_workspace_name ?? "-"}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">空间类型</div>
            <div className="mt-1 font-medium">{user ? workspaceType : "-"}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">当前空间身份</div>
            <div className="mt-1 font-medium">{user?.active_workspace_role === "owner" ? "空间拥有者" : user?.active_workspace_role === "admin" ? "空间管理员" : user?.active_workspace_role === "member" ? "空间成员" : "-"}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>协作说明</CardTitle>
          <CardDescription>帮助你区分个人空间与共享空间中的内容边界。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border bg-slate-50 px-4 py-4">
            <div className="font-medium">个人空间</div>
            <p className="text-muted-foreground mt-2 text-sm leading-6">
              适合保存你自己的对话、思路和实验性任务。个人记忆与个人智能体默认仅自己可见。
            </p>
          </div>
          <div className="rounded-2xl border bg-slate-50 px-4 py-4">
            <div className="font-medium">共享空间</div>
            <p className="text-muted-foreground mt-2 text-sm leading-6">
              适合团队协作。共享空间中的对话、上传文件和产物会对该空间成员开放，便于共同推进任务。
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>安全设置</CardTitle>
          <CardDescription>修改你的登录密码。</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={handlePasswordChange}>
            <Input type="password" placeholder="当前密码" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
            <Input type="password" placeholder="新密码" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} />
            <Button>更新密码</Button>
          </form>
          {message && <p className="mt-4 text-sm text-emerald-600">{message}</p>}
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
