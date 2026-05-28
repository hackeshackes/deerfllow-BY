"use client";

import { BookOpenIcon, GlobeIcon, PencilIcon, TrashIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AdminPageShell } from "@/components/workspace/admin/admin-page-shell";
import { useI18n } from "@/core/i18n/hooks";

type KnowledgeBase = {
  id: string;
  user_id: string;
  workspace_id: string | null;
  visibility: string;
  name: string;
  description: string | null;
  embedding_model: string;
  document_count: number;
  created_at: string;
  updated_at: string;
  is_global: boolean;
};

export function KnowledgeAdminPage() {
  const { t } = useI18n();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [creatingGlobal, setCreatingGlobal] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");

  const [editTarget, setEditTarget] = useState<KnowledgeBase | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editVisibility, setEditVisibility] = useState<string>("private");
  const [editIsGlobal, setEditIsGlobal] = useState(false);
  const [updating, setUpdating] = useState(false);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/admin/knowledge");
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.knowledge.loadFailed);
      }
      const data = (await res.json()) as { knowledge_bases: KnowledgeBase[] };
      setKnowledgeBases(data.knowledge_bases);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.admin.knowledge.loadFailed);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, [t.admin.knowledge.loadFailed]);

  async function handleDelete(kb: KnowledgeBase) {
    setDeleting(true);
    try {
      const res = await fetch(`/api/admin/knowledge/${kb.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.knowledge.delete);
      }
      toast.success(`${t.admin.knowledge.delete} "${kb.name}"`);
      setDeleteTarget(null);
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t.admin.knowledge.delete);
    } finally {
      setDeleting(false);
    }
  }

  async function handleCreateGlobal() {
    if (!newKbName.trim()) {
      toast.error(t.admin.knowledge.name);
      return;
    }
    setCreatingGlobal(true);
    try {
      const res = await fetch("/api/knowledge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKbName.trim(), description: newKbDesc.trim(), is_global: true }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.knowledge.delete);
      }
      toast.success(`"${newKbName}" ${t.admin.knowledge.globalKnowledgeBases}`);
      setNewKbName("");
      setNewKbDesc("");
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t.admin.knowledge.delete);
    } finally {
      setCreatingGlobal(false);
    }
  }

  function openEditDialog(kb: KnowledgeBase) {
    setEditTarget(kb);
    setEditName(kb.name);
    setEditDescription(kb.description ?? "");
    setEditVisibility(kb.visibility);
    setEditIsGlobal(kb.is_global);
  }

  function closeEditDialog() {
    setEditTarget(null);
    setEditName("");
    setEditDescription("");
    setEditVisibility("private");
    setEditIsGlobal(false);
  }

  async function handleUpdate() {
    if (!editTarget || !editName.trim()) {
      toast.error(t.admin.knowledge.name);
      return;
    }
    setUpdating(true);
    try {
      const res = await fetch(`/api/admin/knowledge/${editTarget.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editName.trim(),
          description: editDescription.trim() || null,
          visibility: editVisibility,
          is_global: editIsGlobal,
        }),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? t.admin.knowledge.delete);
      }
      toast.success(`"${editName}" ${t.admin.knowledge.globalKnowledgeBases}`);
      closeEditDialog();
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : t.admin.knowledge.delete);
    } finally {
      setUpdating(false);
    }
  }

  const globalKbs = knowledgeBases.filter((kb) => kb.is_global);

  return (
    <AdminPageShell title={t.admin.knowledge.title} description={t.admin.knowledge.description}>
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GlobeIcon className="size-5" />
              {t.admin.knowledge.createGlobalKb}
            </CardTitle>
            <CardDescription>{t.admin.knowledge.globalKbDescription}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder={t.admin.knowledge.namePlaceholder}
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                className="max-w-sm"
              />
              <Input
                placeholder={t.admin.knowledge.descriptionPlaceholder}
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                className="max-w-sm"
              />
              <Button onClick={() => void handleCreateGlobal()} disabled={creatingGlobal || !newKbName.trim()}>
                {creatingGlobal ? t.admin.knowledge.creating : t.admin.knowledge.create}
              </Button>
            </div>
          </CardContent>
        </Card>

        {globalKbs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GlobeIcon className="size-5" />
                {t.admin.knowledge.globalKnowledgeBases} ({globalKbs.length})
              </CardTitle>
              <CardDescription>{t.admin.knowledge.allUsersCanSearch}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="py-8 text-center text-sm text-slate-500">{t.admin.knowledge.loading}</div>
              ) : error ? (
                <div className="py-8 text-center text-sm text-red-500">{error}</div>
              ) : (
                <div className="space-y-3">
                  {globalKbs.map((kb) => (
                    <div key={kb.id} className="flex items-center justify-between rounded-2xl border p-4">
                      <div className="flex items-center gap-3">
                        <BookOpenIcon className="size-5 text-slate-400" />
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{kb.name}</span>
                            <Badge variant="outline" className="text-xs">{t.admin.knowledge.global}</Badge>
                          </div>
                          {kb.description && <div className="mt-1 text-sm text-slate-500">{kb.description}</div>}
                          <div className="mt-1 flex gap-3 text-xs text-slate-400">
                            <span>{kb.document_count} {t.admin.knowledge.documents}</span>
                            <span>{t.admin.knowledge.createdBy}: {kb.user_id}</span>
                            <span>{new Date(kb.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditDialog(kb)}
                        >
                          <PencilIcon className="size-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-600 hover:bg-red-50"
                          onClick={() => setDeleteTarget(kb)}
                        >
                          <TrashIcon className="size-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpenIcon className="size-5" />
              {t.admin.knowledge.allKnowledgeBases} ({knowledgeBases.length})
            </CardTitle>
            <CardDescription>{t.admin.knowledge.allKnowledgeBasesDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-sm text-slate-500">{t.admin.knowledge.loading}</div>
            ) : error ? (
              <div className="py-8 text-center text-sm text-red-500">{error}</div>
            ) : knowledgeBases.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">{t.admin.knowledge.noKnowledgeBases}</div>
            ) : (
              <div className="space-y-3">
                {knowledgeBases.map((kb) => (
                  <div key={kb.id} className="flex items-center justify-between rounded-2xl border p-4">
                    <div className="flex items-center gap-3">
                      <BookOpenIcon className="size-5 text-slate-400" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{kb.name}</span>
                          {kb.is_global && <Badge variant="outline" className="text-xs">{t.admin.knowledge.global}</Badge>}
                          {kb.visibility === "workspace" && <Badge variant="secondary" className="text-xs">{t.admin.knowledge.workspaceShared}</Badge>}
                          {kb.visibility === "private" && <Badge variant="secondary" className="text-xs">{t.admin.knowledge.private}</Badge>}
                        </div>
                        {kb.description && <div className="mt-1 text-sm text-slate-500">{kb.description}</div>}
                        <div className="mt-1 flex gap-3 text-xs text-slate-400">
                          <span>{kb.document_count} {t.admin.knowledge.documents}</span>
                          <span>{t.admin.knowledge.createdBy}: {kb.user_id}</span>
                          <span>{new Date(kb.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditDialog(kb)}
                      >
                        <PencilIcon className="size-4" />
                      </Button>
                      {kb.is_global && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-500 hover:text-red-600 hover:bg-red-50"
                          onClick={() => setDeleteTarget(kb)}
                        >
                          <TrashIcon className="size-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={editTarget !== null} onOpenChange={(open) => !open && closeEditDialog()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.admin.knowledge.editKnowledgeBase}</DialogTitle>
            <DialogDescription>
              {t.admin.knowledge.updateKnowledgeBase}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">{t.admin.knowledge.name}</label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder={t.admin.knowledge.namePlaceholder}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t.admin.knowledge.descriptionLabel}</label>
              <Input
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder={t.admin.knowledge.descriptionPlaceholder}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">{t.admin.knowledge.type}</label>
              <Select value={editVisibility} onValueChange={setEditVisibility}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">{t.admin.knowledge.private}</SelectItem>
                  <SelectItem value="workspace">{t.admin.knowledge.workspaceShared}</SelectItem>
                  <SelectItem value="global">{t.admin.knowledge.global}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog}>
              {t.admin.knowledge.cancel}
            </Button>
            <Button onClick={() => void handleUpdate()} disabled={updating}>
              {updating ? t.admin.knowledge.updating : t.admin.knowledge.update}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteTarget !== null} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.admin.knowledge.deleteConfirm.replace("{name}", deleteTarget?.name ?? "")}</DialogTitle>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              {t.admin.knowledge.cancel}
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteTarget && void handleDelete(deleteTarget)}
              disabled={deleting}
            >
              {deleting ? t.admin.knowledge.deleting : t.admin.knowledge.remove}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}