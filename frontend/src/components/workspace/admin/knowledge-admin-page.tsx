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
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeBase | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [creatingGlobal, setCreatingGlobal] = useState(false);
  const [newKbName, setNewKbName] = useState("");
  const [newKbDesc, setNewKbDesc] = useState("");

  // Edit dialog state
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
        throw new Error(data?.detail ?? "加载知识库失败");
      }
      const data = (await res.json()) as { knowledge_bases: KnowledgeBase[] };
      setKnowledgeBases(data.knowledge_bases);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载知识库失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  async function handleDelete(kb: KnowledgeBase) {
    setDeleting(true);
    try {
      const res = await fetch(`/api/admin/knowledge/${kb.id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { detail?: string } | null;
        throw new Error(data?.detail ?? "删除失败");
      }
      toast.success(`知识库 "${kb.name}" 已删除`);
      setDeleteTarget(null);
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  async function handleCreateGlobal() {
    if (!newKbName.trim()) {
      toast.error("请输入知识库名称");
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
        throw new Error(data?.detail ?? "创建失败");
      }
      toast.success(`全局知识库 "${newKbName}" 创建成功`);
      setNewKbName("");
      setNewKbDesc("");
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "创建失败");
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
      toast.error("请输入知识库名称");
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
        throw new Error(data?.detail ?? "更新失败");
      }
      toast.success(`知识库 "${editName}" 已更新`);
      closeEditDialog();
      await loadData();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "更新失败");
    } finally {
      setUpdating(false);
    }
  }

  const globalKbs = knowledgeBases.filter((kb) => kb.is_global);

  return (
    <AdminPageShell title="知识库管理" description="管理全局知识库，查看所有用户知识库。">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GlobeIcon className="size-5" />
              创建全局知识库
            </CardTitle>
            <CardDescription>全局知识库对所有用户可见，仅管理员可编辑和删除。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Input
                placeholder="知识库名称"
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                className="max-w-sm"
              />
              <Input
                placeholder="描述（可选）"
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                className="max-w-sm"
              />
              <Button onClick={() => void handleCreateGlobal()} disabled={creatingGlobal || !newKbName.trim()}>
                {creatingGlobal ? "创建中..." : "创建全局知识库"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {globalKbs.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GlobeIcon className="size-5" />
                全局知识库 ({globalKbs.length})
              </CardTitle>
              <CardDescription>所有用户均可检索这些知识库。</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="py-8 text-center text-sm text-slate-500">加载中...</div>
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
                            <Badge variant="outline" className="text-xs">全局</Badge>
                          </div>
                          {kb.description && <div className="mt-1 text-sm text-slate-500">{kb.description}</div>}
                          <div className="mt-1 flex gap-3 text-xs text-slate-400">
                            <span>{kb.document_count} 个文档</span>
                            <span>创建者: {kb.user_id}</span>
                            <span>{new Date(kb.created_at).toLocaleDateString("zh-CN")}</span>
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
              所有知识库 ({knowledgeBases.length})
            </CardTitle>
            <CardDescription>系统中全部知识库，包括用户私有知识库和共享知识库。</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="py-8 text-center text-sm text-slate-500">加载中...</div>
            ) : error ? (
              <div className="py-8 text-center text-sm text-red-500">{error}</div>
            ) : knowledgeBases.length === 0 ? (
              <div className="py-8 text-center text-sm text-slate-500">暂无知识库</div>
            ) : (
              <div className="space-y-3">
                {knowledgeBases.map((kb) => (
                  <div key={kb.id} className="flex items-center justify-between rounded-2xl border p-4">
                    <div className="flex items-center gap-3">
                      <BookOpenIcon className="size-5 text-slate-400" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{kb.name}</span>
                          {kb.is_global && <Badge variant="outline" className="text-xs">全局</Badge>}
                          {kb.visibility === "workspace" && <Badge variant="secondary" className="text-xs">工作区共享</Badge>}
                          {kb.visibility === "private" && <Badge variant="secondary" className="text-xs">私有</Badge>}
                        </div>
                        {kb.description && <div className="mt-1 text-sm text-slate-500">{kb.description}</div>}
                        <div className="mt-1 flex gap-3 text-xs text-slate-400">
                          <span>{kb.document_count} 个文档</span>
                          <span>创建者: {kb.user_id}</span>
                          <span>{new Date(kb.created_at).toLocaleDateString("zh-CN")}</span>
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
            <DialogTitle>编辑知识库</DialogTitle>
            <DialogDescription>
              修改知识库的名称、描述和类型
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">名称</label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                placeholder="知识库名称"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">描述</label>
              <Input
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                placeholder="描述（可选）"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">类型</label>
              <Select value={editVisibility} onValueChange={setEditVisibility}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="private">私有</SelectItem>
                  <SelectItem value="workspace">工作区共享</SelectItem>
                  <SelectItem value="global">全局</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeEditDialog}>
              取消
            </Button>
            <Button onClick={() => void handleUpdate()} disabled={updating}>
              {updating ? "更新中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteTarget !== null} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除知识库</DialogTitle>
            <DialogDescription>
              确定要删除知识库 &quot;{deleteTarget?.name}&quot; 吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteTarget && void handleDelete(deleteTarget)}
              disabled={deleting}
            >
              {deleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminPageShell>
  );
}
