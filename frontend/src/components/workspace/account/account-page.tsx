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
};

export function AccountPage() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      setError(body?.detail ?? "Failed to change password");
      return;
    }
    setCurrentPassword("");
    setNewPassword("");
    setMessage("Password updated.");
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Manage your BY account profile and access.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <div className="text-muted-foreground text-sm">Name</div>
            <div className="mt-1 font-medium">{user?.name ?? "Loading..."}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">Email</div>
            <div className="mt-1 font-medium">{user?.email ?? "Loading..."}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">Role</div>
            <div className="mt-1 font-medium capitalize">{user?.role ?? "-"}</div>
          </div>
          <div>
            <div className="text-muted-foreground text-sm">Current workspace</div>
            <div className="mt-1 font-medium">{user?.active_workspace_name ?? "-"}</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Security</CardTitle>
          <CardDescription>Update your account password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1fr_1fr_auto]" onSubmit={handlePasswordChange}>
            <Input type="password" placeholder="Current password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required />
            <Input type="password" placeholder="New password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required minLength={8} />
            <Button>Update password</Button>
          </form>
          {message && <p className="mt-4 text-sm text-emerald-600">{message}</p>}
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
