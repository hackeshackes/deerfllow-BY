"use client";

import { PlusIcon, ShareIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import {
  createKnowledgeBase,
  loadKnowledgeBases,
  shareKnowledgeBase,
  type KnowledgeBase,
} from "@/core/knowledge";
import { formatTimeAgo } from "@/core/utils/datetime";

type CurrentUser = {
  id: string;
  active_workspace_id?: string;
};

export default function KnowledgePage() {
  const { t } = useI18n();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [activeTab, setActiveTab] = useState("workspace");
  const [sharingKb, setSharingKb] = useState<KnowledgeBase | null>(null);
  const [shareWorkspaceId, setShareWorkspaceId] = useState("");
  const [sharing, setSharing] = useState(false);
  const [newVisibility, setNewVisibility] = useState<string>("private");

  useEffect(() => {
    document.title = `资料库 - ${t.pages.appName}`;
    Promise.all([
      loadKnowledgeBases(),
      fetch("/api/users/me")
        .then((r) => (r.ok ? r.json() : null))
        .catch(() => null),
    ])
      .then(([kbs, user]) => {
        // Defensive: when /api/users/me returns 401 we set `user` to null
        // instead of an error envelope so later filter callbacks stay safe.
        setKnowledgeBases(Array.isArray(kbs) ? kbs : []);
        setCurrentUser(
          user && typeof user === "object" && "id" in user
            ? (user as CurrentUser)
            : null,
        );
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [t.knowledge.pageTitle, t.pages.appName]);

  const privateKnowledge = useMemo(
    () =>
      knowledgeBases.filter(
        (kb) => kb.user_id === currentUser?.id && kb.visibility === "private",
      ),
    [knowledgeBases, currentUser],
  );

  const currentWorkspaceKnowledge = useMemo(
    () =>
      knowledgeBases.filter(
        (kb) =>
          !kb.is_global &&
          (kb.workspace_id === currentUser?.active_workspace_id ||
            kb.shared_to.includes(currentUser?.active_workspace_id ?? "")),
      ),
    [knowledgeBases, currentUser],
  );

  const globalKnowledge = useMemo(
    () => knowledgeBases.filter((kb) => kb.is_global),
    [knowledgeBases],
  );

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    setCreating(true);
    try {
      const kb = await createKnowledgeBase(newName.trim(), undefined, newVisibility);
      setKnowledgeBases((prev) => [kb, ...prev]);
      setNewName("");
      setNewVisibility("private");
      setShowCreate(false);
    } catch (err) {
      console.error("Failed to create knowledge base:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleShare = async () => {
    if (!sharingKb || !shareWorkspaceId.trim()) return;
    setSharing(true);
    try {
      await shareKnowledgeBase(sharingKb.id, shareWorkspaceId.trim());
      setKnowledgeBases((prev) =>
        prev.map((kb) =>
          kb.id === sharingKb.id
            ? { ...kb, shared_to: [...kb.shared_to, shareWorkspaceId.trim()] }
            : kb,
        ),
      );
      setSharingKb(null);
      setShareWorkspaceId("");
    } catch (err) {
      console.error("Failed to share knowledge base:", err);
    } finally {
      setSharing(false);
    }
  };

  const renderKnowledgeList = (kbs: KnowledgeBase[]) => {
    if (kbs.length === 0) {
      return (
        <div className="text-center text-muted-foreground py-8">
          {activeTab === "private" ? t.knowledge.empty : t.knowledge.emptyScope}
        </div>
      );
    }
    return (
      <div className="space-y-4">
        {kbs.map((kb) => (
          <div
            key={kb.id}
            className="border rounded-lg p-4 transition-colors hover:bg-muted/50"
          >
            <Link href={`/workspace/knowledge/${kb.id}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{kb.name}</h3>
                  {kb.description && (
                    <p className="text-muted-foreground text-sm">
                      {kb.description}
                    </p>
                  )}
                  {kb.shared_to.length > 0 && (
                    <p className="text-muted-foreground text-xs mt-1">
                      {t.knowledge.sharedWorkspaces}: {kb.shared_to.length}
                    </p>
                  )}
                  <p className="text-muted-foreground text-xs mt-1">
                    {t.knowledge.visibility.label}: {kb.is_global ? t.knowledge.visibility.global : kb.visibility === "workspace" ? t.knowledge.visibility.workspace : t.knowledge.visibility.private}
                  </p>
                </div>
                <div className="text-right text-sm text-muted-foreground">
                  <div>{kb.document_count} {t.knowledge.documents}</div>
                  <div>{formatTimeAgo(kb.updated_at)}</div>
                </div>
              </div>
            </Link>
            {kb.user_id === currentUser?.id && (
              <div className="mt-2 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSharingKb(kb)}
                >
                  <ShareIcon className="size-4 mr-1" />
                  {t.knowledge.share}
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        {showCreate ? (
          <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t.knowledge.namePlaceholder}
              className="w-48"
              autoFocus
            />
            <Select value={newVisibility} onValueChange={setNewVisibility}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder={t.knowledge.type} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="private">{t.knowledge.visibility.private}</SelectItem>
                <SelectItem value="workspace">{t.knowledge.visibility.workspace}</SelectItem>
              </SelectContent>
            </Select>
            <Button type="submit" size="sm" disabled={creating}>
              {creating ? t.common.loading : t.common.create}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                setShowCreate(false);
                setNewName("");
                setNewVisibility("private");
              }}
            >
              {t.common.cancel}
            </Button>
          </form>
        ) : (
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon className="size-4 mr-1" />
            {t.knowledge.addKnowledgeBase}
          </Button>
        )}
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <main className="min-h-0 flex-1">
            <div className="mx-auto w-full max-w-(--container-width-md) py-8">
              {loading ? (
                <div className="text-center text-muted-foreground">
                  {t.common.loading}
                </div>
              ) : (
                <Tabs value={activeTab} onValueChange={setActiveTab}>
                  <TabsList>
                      <TabsTrigger value="workspace">
                        {t.knowledge.currentSpaceKnowledge}
                      </TabsTrigger>
                      <TabsTrigger value="private">
                        {t.knowledge.myPrivateKnowledge}
                      </TabsTrigger>
                      <TabsTrigger value="global">
                        {t.knowledge.globalKnowledge}
                      </TabsTrigger>
                    </TabsList>
                  <TabsContent value="workspace" className="mt-4">
                    {renderKnowledgeList(currentWorkspaceKnowledge)}
                  </TabsContent>
                  <TabsContent value="private" className="mt-4">
                    {renderKnowledgeList(privateKnowledge)}
                  </TabsContent>
                  <TabsContent value="global" className="mt-4">
                    {renderKnowledgeList(globalKnowledge)}
                  </TabsContent>
                </Tabs>
              )}
            </div>
          </main>
        </div>
      </WorkspaceBody>

      <Dialog open={!!sharingKb} onOpenChange={() => setSharingKb(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t.knowledge.shareToWorkspace}</DialogTitle>
            <DialogDescription>
              {sharingKb?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Input
              value={shareWorkspaceId}
              onChange={(e) => setShareWorkspaceId(e.target.value)}
              placeholder={t.knowledge.workspaceKnowledge}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSharingKb(null)}
            >
              {t.common.cancel}
            </Button>
            <Button onClick={handleShare} disabled={sharing}>
              {sharing ? t.common.loading : t.knowledge.share}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </WorkspaceContainer>
  );
}
