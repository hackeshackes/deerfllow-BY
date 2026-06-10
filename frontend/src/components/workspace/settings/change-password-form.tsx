"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
    <Card>
      <CardHeader>
        <CardTitle>安全设置</CardTitle>
        <CardDescription>修改你的登录密码。</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={handlePasswordChange}>
          <Input type="password" placeholder="当前密码" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
          <Input type="password" placeholder="新密码" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} />
          <Button type="submit">更新密码</Button>
        </form>
        {message && <p className="mt-4 text-sm text-emerald-600">{message}</p>}
        {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
      </CardContent>
    </Card>
  );
}
