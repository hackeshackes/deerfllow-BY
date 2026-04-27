"use client";

import { DatabaseIcon, EditIcon, GlobeIcon, PlusIcon, Share2Icon, Trash2Icon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  loadKnowledgeBases,
  shareKnowledgeBase,
  updateKnowledgeBase,
  type KnowledgeBase,
} from "@/core/knowledge";
import { formatTimeAgo } from "@/core/utils/datetime";

type CurrentUser = {
  id: string;
  active_workspace_id?: string;
};

export function UserKnowledgePage() {
  const { t } = useI18n();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      loadKnowledgeBases(),
      fetch("/api/users/me").then((r) => r.json()),
    ])
      .then(([kbs, user]) => {
        setKnowledgeBases(kbs);
        setCurrentUser(user);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleRefresh = async () => {
    try {
      const kbs = await loadKnowledgeBases();
      setKnowledgeBases(kbs);
    } catch (err) {
      console.error("Failed to refresh knowledge bases:", err);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="rounded-3xl border bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 px-6 py-6 text-white shadow-sm">
        <div className="mt-3 text-2xl font-semibold tracking-tight">
          {t.settings.knowledge?.title ?? "知识库管理"}
        </div>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-200">
          {t.settings.knowledge?.description ?? "管理个人知识库、全局知识库、共享知识库"}
        </p>
      </div>

      <Tabs defaultValue="all">
        <div className="flex justify-between">
          <TabsList>
            <TabsTrigger value="all">{t.settings.knowledge?.allTab ?? "全部"}</TabsTrigger>
            <TabsTrigger value="mine">{t.settings.knowledge?.mineTab ?? "我的创建"}</TabsTrigger>
            <TabsTrigger value="global">{t.settings.knowledge?.globalTab ?? "全局知识库"}</TabsTrigger>
          </TabsList>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <PlusIcon className="size-4" />
            {t.knowledge.createKnowledgeBase}
          </Button>
        </div>

        <TabsContent value="all">
          <AllKnowledgeList
            knowledgeBases={knowledgeBases}
            currentUser={currentUser}
            loading={loading}
            onRefresh={handleRefresh}
          />
        </TabsContent>
        <TabsContent value="mine">
          <MyKnowledgeList
            knowledgeBases={knowledgeBases}
            currentUser={currentUser}
            loading={loading}
            onRefresh={handleRefresh}
          />
        </TabsContent>
        <TabsContent value="global">
          <GlobalKnowledgeList
            knowledgeBases={knowledgeBases}
            loading={loading}
          />
        </TabsContent>
      </Tabs>

      <CreateKnowledgeDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSuccess={handleRefresh}
      />
    </div>
  );
}

function AllKnowledgeList({
  knowledgeBases,
  currentUser,
  loading,
  onRefresh,
}: {
  knowledgeBases: KnowledgeBase[];
  currentUser: CurrentUser | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  const { t } = useI18n();
  const [editDialog, setEditDialog] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });
  const [shareDialog, setShareDialog] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });

  if (loading) return <div className="text-muted-foreground text-sm">{t.common.loading}</div>;

  if (knowledgeBases.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <DatabaseIcon className="size-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">{t.knowledge.empty}</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {knowledgeBases.map((kb) => {
          const isOwner = kb.user_id === currentUser?.id;
          const isGlobal = kb.is_global;
          const isSharedToWorkspace = !isOwner && !isGlobal && kb.shared_to.includes(currentUser?.active_workspace_id ?? "");

          return (
            <Card key={kb.id}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  {isGlobal ? (
                    <GlobeIcon className="size-5 text-blue-500" />
                  ) : (
                    <DatabaseIcon className="size-5" />
                  )}
                  {kb.name}
                  {isGlobal && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                      {t.settings.knowledge?.globalBadge ?? "全局"}
                    </span>
                  )}
                </CardTitle>
                <CardDescription className="line-clamp-2">
                  {kb.description ?? t.knowledge.descriptionPlaceholder}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>{kb.document_count} {t.knowledge.documents}</span>
                  <span>{formatTimeAgo(kb.updated_at)}</span>
                </div>
                <div className="flex gap-2">
                  {isOwner && !isGlobal && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        onClick={() => setEditDialog({ open: true, kb })}
                      >
                        <EditIcon className="size-4" />
                        {t.common.edit}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        onClick={() => setShareDialog({ open: true, kb })}
                      >
                        <Share2Icon className="size-4" />
                        {t.common.share}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-destructive hover:text-destructive"
                        onClick={() => setDeleteConfirm({ open: true, kb })}
                      >
                        <Trash2Icon className="size-4" />
                      </Button>
                    </>
                  )}
                  {isSharedToWorkspace && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => setShareDialog({ open: true, kb })}
                    >
                      <Share2Icon className="size-4" />
                      {t.common.share}
                    </Button>
                  )}
                  {isGlobal && (
                    <span className="text-xs text-muted-foreground italic">
                      {t.settings.knowledge?.readOnly ?? "只读"}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <EditKnowledgeDialog
        open={editDialog.open}
        kb={editDialog.kb}
        onClose={() => setEditDialog({ open: false, kb: null })}
        onSuccess={onRefresh}
      />

      <DeleteKnowledgeDialog
        open={deleteConfirm.open}
        kb={deleteConfirm.kb}
        onClose={() => setDeleteConfirm({ open: false, kb: null })}
        onSuccess={onRefresh}
      />

      <ShareKnowledgeDialog
        open={shareDialog.open}
        kb={shareDialog.kb}
        onClose={() => setShareDialog({ open: false, kb: null })}
        onSuccess={onRefresh}
      />
    </>
  );
}

function MyKnowledgeList({
  knowledgeBases,
  currentUser,
  loading,
  onRefresh,
}: {
  knowledgeBases: KnowledgeBase[];
  currentUser: CurrentUser | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  const { t } = useI18n();
  const [editDialog, setEditDialog] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });
  const [deleteConfirm, setDeleteConfirm] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });
  const [shareDialog, setShareDialog] = useState<{ open: boolean; kb: KnowledgeBase | null }>({
    open: false,
    kb: null,
  });

  const myKnowledge = useMemo(
    () => knowledgeBases.filter((kb) => kb.user_id === currentUser?.id && !kb.is_global),
    [knowledgeBases, currentUser],
  );

  if (loading) return <div className="text-muted-foreground text-sm">{t.common.loading}</div>;

  if (myKnowledge.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <DatabaseIcon className="size-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">{t.settings.knowledge?.emptyMine ?? "暂无个人知识库"}</p>
        <p className="text-sm text-muted-foreground">{t.knowledge.empty}</p>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {myKnowledge.map((kb) => (
          <Card key={kb.id}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <DatabaseIcon className="size-5" />
                {kb.name}
              </CardTitle>
              <CardDescription className="line-clamp-2">
                {kb.description ?? t.knowledge.descriptionPlaceholder}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>{kb.document_count} {t.knowledge.documents}</span>
                <span>{formatTimeAgo(kb.updated_at)}</span>
              </div>
              {kb.shared_to.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {t.knowledge.sharedWorkspaces}: {kb.shared_to.length}
                </p>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1"
                  onClick={() => setEditDialog({ open: true, kb })}
                >
                  <EditIcon className="size-4" />
                  {t.common.edit}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShareDialog({ open: true, kb })}
                >
                  <Share2Icon className="size-4" />
                  {t.common.share}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                  onClick={() => setDeleteConfirm({ open: true, kb })}
                >
                  <Trash2Icon className="size-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <EditKnowledgeDialog
        open={editDialog.open}
        kb={editDialog.kb}
        onClose={() => setEditDialog({ open: false, kb: null })}
        onSuccess={onRefresh}
      />

      <DeleteKnowledgeDialog
        open={deleteConfirm.open}
        kb={deleteConfirm.kb}
        onClose={() => setDeleteConfirm({ open: false, kb: null })}
        onSuccess={onRefresh}
      />

      <ShareKnowledgeDialog
        open={shareDialog.open}
        kb={shareDialog.kb}
        onClose={() => setShareDialog({ open: false, kb: null })}
        onSuccess={onRefresh}
      />
    </>
  );
}

function GlobalKnowledgeList({
  knowledgeBases,
  loading,
}: {
  knowledgeBases: KnowledgeBase[];
  loading: boolean;
}) {
  const { t } = useI18n();

  const globalKnowledge = useMemo(
    () => knowledgeBases.filter((kb) => kb.is_global),
    [knowledgeBases],
  );

  if (loading) return <div className="text-muted-foreground text-sm">{t.common.loading}</div>;

  if (globalKnowledge.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <GlobeIcon className="size-12 text-muted-foreground mb-4" />
        <p className="text-muted-foreground">{t.settings.knowledge?.emptyGlobal ?? "暂无全局知识库"}</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {globalKnowledge.map((kb) => (
        <Card key={kb.id}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-base">
              <GlobeIcon className="size-5 text-blue-500" />
              {kb.name}
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                {t.settings.knowledge?.globalBadge ?? "全局"}
              </span>
            </CardTitle>
            <CardDescription className="line-clamp-2">
              {kb.description ?? t.knowledge.descriptionPlaceholder}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{kb.document_count} {t.knowledge.documents}</span>
              <span>{formatTimeAgo(kb.updated_at)}</span>
            </div>
            <div className="flex gap-2">
              <span className="text-xs text-muted-foreground italic">
                {t.settings.knowledge?.readOnly ?? "只读"}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function CreateKnowledgeDialog({
  open,
  onClose,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError(t.settings.knowledge?.nameRequired ?? "名称不能为空");
      return;
    }
    setError(null);
    setCreating(true);
    try {
      await createKnowledgeBase(name.trim(), description.trim() || undefined);
      setName("");
      setDescription("");
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setCreating(false);
    }
  };

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      setName("");
      setDescription("");
      setError(null);
    }
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.knowledge.createKnowledgeBase}</DialogTitle>
          <DialogDescription>
            {t.settings.knowledge?.createDescription ?? "创建一个新的知识库用于存储和检索文档"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">{t.knowledge.name}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t.knowledge.namePlaceholder}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">{t.knowledge.description}</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t.knowledge.descriptionPlaceholder}
              className="mt-1"
              rows={3}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            {t.common.cancel}
          </Button>
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? t.common.loading : t.common.create}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditKnowledgeDialog({
  open,
  kb,
  onClose,
  onSuccess,
}: {
  open: boolean;
  kb: KnowledgeBase | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (kb) {
      setName(kb.name);
      setDescription(kb.description ?? "");
    }
  }, [kb]);

  const handleUpdate = async () => {
    if (!kb || !name.trim()) {
      setError(t.settings.knowledge?.nameRequired ?? "名称不能为空");
      return;
    }
    setError(null);
    setUpdating(true);
    try {
      await updateKnowledgeBase(kb.id, name.trim(), description.trim() || undefined);
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新失败");
    } finally {
      setUpdating(false);
    }
  };

  if (!kb) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.common.edit} {kb.name}</DialogTitle>
          <DialogDescription>
            {t.settings.knowledge?.editDescription ?? "更新知识库的名称和描述"}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">{t.knowledge.name}</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t.knowledge.namePlaceholder}
              className="mt-1"
            />
          </div>
          <div>
            <label className="text-sm font-medium">{t.knowledge.description}</label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t.knowledge.descriptionPlaceholder}
              className="mt-1"
              rows={3}
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t.common.cancel}
          </Button>
          <Button onClick={handleUpdate} disabled={updating}>
            {updating ? t.common.loading : t.common.save}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteKnowledgeDialog({
  open,
  kb,
  onClose,
  onSuccess,
}: {
  open: boolean;
  kb: KnowledgeBase | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useI18n();
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!kb) return;
    setDeleting(true);
    try {
      await deleteKnowledgeBase(kb.id);
      onSuccess();
      onClose();
    } catch (err) {
      console.error("Failed to delete knowledge base:", err);
    } finally {
      setDeleting(false);
    }
  };

  if (!kb) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.knowledge.delete}</DialogTitle>
          <DialogDescription>
            {t.settings.knowledge?.deleteConfirm ?? `确定要删除知识库 "${kb.name}" 吗？此操作无法撤销。`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t.common.cancel}
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
            {deleting ? t.common.loading : t.common.delete}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ShareKnowledgeDialog({
  open,
  kb,
  onClose,
  onSuccess,
}: {
  open: boolean;
  kb: KnowledgeBase | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const { t } = useI18n();
  const [workspaceId, setWorkspaceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sharing, setSharing] = useState(false);

  const handleShare = async () => {
    if (!kb || !workspaceId.trim()) {
      setError(t.settings.knowledge?.workspaceRequired ?? "工作区 ID 不能为空");
      return;
    }
    setError(null);
    setSharing(true);
    try {
      await shareKnowledgeBase(kb.id, workspaceId.trim());
      setWorkspaceId("");
      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "分享失败");
    } finally {
      setSharing(false);
    }
  };

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      setWorkspaceId("");
      setError(null);
    }
    onClose();
  };

  if (!kb) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t.knowledge.shareToWorkspace}</DialogTitle>
          <DialogDescription>
            {kb.name}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">{t.settings.knowledge?.workspaceId ?? "工作区 ID"}</label>
            <Input
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              placeholder={t.settings.knowledge?.workspaceIdPlaceholder ?? "输入目标工作区 ID"}
              className="mt-1"
            />
          </div>
          {kb.shared_to.length > 0 && (
            <div className="text-sm text-muted-foreground">
              <p>{t.knowledge.sharedWorkspaces}: {kb.shared_to.length}</p>
            </div>
          )}
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            {t.common.cancel}
          </Button>
          <Button onClick={handleShare} disabled={sharing}>
            {sharing ? t.common.loading : t.common.share}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
