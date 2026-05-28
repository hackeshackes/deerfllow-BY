"use client";

import { Trash2Icon } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";

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
  const { t } = useI18n();
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
      throw new Error(t.admin.skills.loadFailed);
    }
    const payload = (await response.json()) as { skills: SkillRecord[] };
    setSkills(payload.skills);
  }

  useEffect(() => {
    void loadSkills().catch((err) => setError(err instanceof Error ? err.message : t.admin.skills.loadFailed));
  }, [t.admin.skills.loadFailed]);

  async function toggleSkill(skill: SkillRecord, enabled: boolean) {
    const response = await fetch(`/api/skills/${skill.name}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail ?? t.admin.skills.updateSkillFailed);
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
        throw new Error(body?.detail ?? t.admin.skills.remoteInstallFailed);
      }
      setUrl("");
      setRenameTo("");
      setMessage(t.admin.skills.installSuccess);
      await loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.skills.remoteInstallFailed);
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
      throw new Error(body?.detail ?? t.admin.skills.saveLocalizationFailed);
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
        throw new Error(body?.detail ?? t.admin.skills.deleteSkillFailed);
      }
      await loadSkills();
      setDeleteConfirm({ open: false, skill: null });
    } catch (err) {
      setError(err instanceof Error ? err.message : t.admin.skills.deleteSkillFailed);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <AdminPageShell title={t.admin.skills.title} description={t.admin.skills.description}>
      <Card>
        <CardHeader>
          <CardTitle>{t.admin.skills.remoteInstall}</CardTitle>
          <CardDescription>{t.admin.skills.remoteInstallDescription}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-[1.6fr_0.8fr_0.8fr_auto]" onSubmit={installRemoteSkill}>
            <Input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://example.com/my-skill.skill" required />
            <select className="border-input bg-background rounded-xl border px-3 py-2" value={conflictStrategy} onChange={(event) => setConflictStrategy(event.target.value)}>
              <option value="error">{t.admin.skills.conflictError}</option>
              <option value="replace">{t.admin.skills.conflictReplace}</option>
              <option value="rename">{t.admin.skills.conflictRename}</option>
            </select>
            <Input value={renameTo} onChange={(event) => setRenameTo(event.target.value)} placeholder={t.admin.skills.renamePlaceholder} />
            <Button disabled={installing}>{installing ? t.admin.skills.installing : t.admin.skills.installSkill}</Button>
          </form>
          {message && <p className="mt-4 text-sm text-emerald-600">{message}</p>}
          {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t.admin.skills.skillList}</CardTitle>
          <CardDescription>{t.admin.skills.skillListDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {skills.map((skill) => (
            <div key={skill.name} className="rounded-2xl border px-4 py-4">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-2">
                  <div className="font-medium">{isMeaningfulChinese(skill.display_name_zh) ? skill.display_name_zh : skill.name}</div>
                  <div className="text-sm leading-6 text-slate-500">{isMeaningfulChinese(skill.description_zh) ? skill.description_zh : skill.description}</div>
                  <div className="text-xs text-slate-400">{t.admin.skills.category}：{skill.category} · {t.admin.skills.author}：{skill.author ?? "—"} · {t.admin.skills.version}：{skill.version ?? "—"}</div>
                  <div className="text-xs text-slate-400">{t.admin.skills.source}：{skill.source ?? t.admin.skills.builtIn}</div>
                  {editingName === skill.name && (
                    <div className="mt-3 space-y-3 rounded-2xl border bg-slate-50 p-3">
                      <Input value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} placeholder={t.admin.skills.displayNamePlaceholder || "Chinese display name"} />
                      <Textarea value={draftDescription} onChange={(event) => setDraftDescription(event.target.value)} placeholder={t.admin.skills.skillDescriptionPlaceholder || "Chinese skill description"} />
                      <div className="flex gap-2">
                        <Button size="sm" onClick={() => void saveLocalization(skill).catch((err) => setError(err instanceof Error ? err.message : t.admin.skills.saveLocalizationFailed))}>{t.admin.skills.saveLocalization}</Button>
                        <Button size="sm" variant="outline" onClick={() => setEditingName(null)}>{t.admin.skills.cancel}</Button>
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
                    {t.admin.skills.localization}
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
                  <div className="text-sm text-slate-500">{skill.enabled ? t.admin.skills.enabled : t.admin.skills.disabled}</div>
                  <Switch checked={skill.enabled} onCheckedChange={(checked) => void toggleSkill(skill, checked).catch((err) => setError(err instanceof Error ? err.message : t.admin.skills.updateSkillFailed))} />
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Dialog open={deleteConfirm.open} onOpenChange={(open) => !open && setDeleteConfirm({ open: false, skill: null })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.admin.skills.deleteSkill}</DialogTitle>
            <DialogDescription>
              {t.admin.skills.deleteConfirm.replace("{name}", deleteConfirm.skill?.name ?? "")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm({ open: false, skill: null })}>
              {t.admin.skills.cancel}
            </Button>
            <Button variant="destructive" onClick={deleteSkill} disabled={deleting}>
              {deleting ? t.admin.skills.deleting : t.admin.skills.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
