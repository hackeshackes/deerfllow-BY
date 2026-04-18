"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import {
  createKnowledgeBase,
  loadKnowledgeBases,
  type KnowledgeBase,
} from "@/core/knowledge";
import { formatTimeAgo } from "@/core/utils/datetime";
import { PlusIcon, DatabaseIcon } from "lucide-react";

export default function KnowledgePage() {
  const { t } = useI18n();
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  useEffect(() => {
    document.title = `${t.knowledge.pageTitle} - ${t.pages.appName}`;
    loadKnowledgeBases()
      .then(setKnowledgeBases)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [t.knowledge.pageTitle, t.pages.appName]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    setCreating(true);
    try {
      const kb = await createKnowledgeBase(newName.trim());
      setKnowledgeBases((prev) => [kb, ...prev]);
      setNewName("");
      setShowCreate(false);
    } catch (err) {
      console.error("Failed to create knowledge base:", err);
    } finally {
      setCreating(false);
    }
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
              className="w-64"
              autoFocus
            />
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
              }}
            >
              {t.common.cancel}
            </Button>
          </form>
        ) : (
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <PlusIcon className="size-4 mr-1" />
            {t.knowledge.createKnowledgeBase}
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
              ) : knowledgeBases.length === 0 ? (
                <div className="text-center">
                  <DatabaseIcon className="mx-auto size-12 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground mb-4">{t.knowledge.empty}</p>
                  <Button onClick={() => setShowCreate(true)}>
                    {t.knowledge.createKnowledgeBase}
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {knowledgeBases.map((kb) => (
                    <Link
                      key={kb.id}
                      href={`/workspace/knowledge/${kb.id}`}
                    >
                      <div className="border rounded-lg p-4 transition-colors hover:bg-muted/50">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium">{kb.name}</h3>
                            {kb.description && (
                              <p className="text-muted-foreground text-sm">
                                {kb.description}
                              </p>
                            )}
                          </div>
                          <div className="text-right text-sm text-muted-foreground">
                            <div>{kb.document_count} documents</div>
                            <div>{formatTimeAgo(kb.updated_at)}</div>
                          </div>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
