"use client";

import { Trash2Icon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

import { AdminPageShell } from "./admin-page-shell";

type SkillRecord = {
  name: string;
  description: string;
  description_zh?: string | null;
  display_name_zh?: string | null;
  enabled: boolean;
  category: string;
  version?: string | null;
  author?: string | null;
  source?: string | null;
};

function isMeaningfulChinese(value?: string | null) {
  return Boolean(value && /[\u4e00-\u9fff]/.test(value));
}

export function SkillsAdminPage() {
  const [skills, setSkills] = useState<SkillRecord[]>([]);
  const [url, setUrl] = useState("");
  const [renameTo, setRenameTo] = useState("");
  const [conflictStrategy, setConflictStrategy] = useState("error");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [installing, setInstalling] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; skill: SkillRecord | null }>({
    open: false,
    skill: null,
  });
  const [deleting, setDeleting] = useState(false);

  async function loadSkills() {
    const response = await fetch("/api/skills");
    if (!response.ok) {
      throw new Error("加载技能失败");
    }
    const payload = (await response.json()) as { skills: SkillRecord[] };
    setSkills(payload.skills);
  }

  useEffect(() => {
    void loadSkills().catch((err) => setError(err instanceof Error ? err.message : "加载技能失败"));
  }, []);

  async function toggleSkill(skill: SkillRecord, enabled: boolean) {
    const response = await fetch(`/api/skills/${skill.name}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? "更新技能失败");
    }
    await loadSkills();
  }

  async function installRemoteSkill(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInstalling(true);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/skills/install/remote", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, conflict_strategy: conflictStrategy, rename_to: renameTo || null }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "远程安装技能失败");
      }
      setUrl("");
      setRenameTo("");
      setMessage("远程技能已安装，默认处于禁用状态，请按需启用。");
      await loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : "远程安装技能失败");
    } finally {
      setInstalling(false);
    }
  }

  async function saveLocalization(skill: SkillRecord) {
    const response = await fetch(`/api/admin/skills/${skill.name}/metadata`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ display_name_zh: draftTitle ?? null, description_zh: draftDescription ?? null }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? "保存技能中文信息失败");
    }
    setEditingName(null);
    setDraftTitle("");
    setDraftDescription("");
    await loadSkills();
  }

  async function deleteSkill() {
    if (!deleteConfirm.skill) return;
    setDeleting(true);
    try {
      const response = await fetch(`/api/skills/custom/${deleteConfirm.skill.name}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(body?.detail ?? "删除技能失败");
      }
      await loadSkills();
      setDeleteConfirm({ open: false, skill: null });
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除技能失败");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AdminPageShell title="技能管理" description="查看当前技能清单、切换启用状态，并从远程地址安装新的 skill 包。">
      <Card>
        <CardHeader>
          <CardTitle>远程安装</CardTitle>
          <CardDescription>输入可访问的 `.skill` / `.zip` / `.tar.gz` 地址，安装后默认会保持禁用状态。</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1.6fr_0.8fr_0.8fr_auto]" onSubmit={installRemoteSkill}>
            <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/my-skill.skill" required />
            <select className="border-input bg-background rounded-xl border px-3 py-2" value={conflictStrategy} onChange={(event) => setConflictStrategy(event.target.value)}>
              <option value="error">冲突时报错</option>
              <option value="replace">覆盖同名技能</option>
              <option value="rename">重命名安装</option>
            </select>
            <Input value={renameTo} onChange={(event) => setRenameTo(event.target.value)} placeholder="重命名（可选）" />
            <Button disabled={installing}>{installing ? "安装中..." : "安装技能"}</Button>
          </form>
          {message && <p className="mt-4 text-sm text-emerald-600">{message}</p>}
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>技能清单</CardTitle>
          <CardDescription>中文优先展示技能描述，并允许直接切换启用状态。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {skills.map((skill) => (
            <div key={skill.name} className="rounded-2xl border px-4 py-4">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <div className="font-medium">{isMeaningfulChinese(skill.display_name_zh) ? skill.display_name_zh : skill.name}</div>
                  <div className="text-sm leading-6 text-slate-500">{isMeaningfulChinese(skill.description_zh) ? skill.description_zh : skill.description}</div>
                  <div className="text-xs text-slate-400">分类：{skill.category} · 作者：{skill.author ?? "—"} · 版本：{skill.version ?? "—"}</div>
                  <div className="text-xs text-slate-400">来源：{skill.source ?? "内置/本地"}</div>
                  {editingName === skill.name && (
                    <div className="mt-3 space-y-3 rounded-2xl border bg-slate-50 p-3">
                      <Input value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} placeholder="中文显示名称" />
                      <Textarea value={draftDescription} onChange={(event) => setDraftDescription(event.target.value)} placeholder="中文技能简介" />
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => void saveLocalization(skill).catch((err) => setError(err instanceof Error ? err.message : "保存技能中文信息失败"))}>保存中文信息</Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingName(null)}>取消</Button>
                      </div>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setEditingName(skill.name);
                      setDraftTitle(isMeaningfulChinese(skill.display_name_zh) ? skill.display_name_zh ?? "" : skill.name);
                      setDraftDescription(isMeaningfulChinese(skill.description_zh) ? skill.description_zh ?? "" : skill.description);
                    }}
                  >
                    中文化
                  </Button>
                  {skill.category === "custom" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive hover:text-destructive"
                      onClick={() => setDeleteConfirm({ open: true, skill })}
                    >
                      <Trash2Icon className="size-4" />
                    </Button>
                  )}
                  <div className="text-sm text-slate-500">{skill.enabled ? "已启用" : "已禁用"}</div>
                  <Switch checked={skill.enabled} onCheckedChange={(checked) => void toggleSkill(skill, checked).catch((err) => setError(err instanceof Error ? err.message : "更新技能失败"))} />
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Dialog open={deleteConfirm.open} onOpenChange={(open) => !open && setDeleteConfirm({ open: false, skill: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除技能</DialogTitle>
            <DialogDescription>
              确定要删除技能 &quot;{deleteConfirm.skill?.name}&quot; 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm({ open: false, skill: null })}>
              取消
            </Button>
            <Button variant="destructive" onClick={deleteSkill} disabled={deleting}>
              {deleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
