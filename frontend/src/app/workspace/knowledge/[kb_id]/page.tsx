"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import {
  deleteDocument,
  deleteKnowledgeBase,
  getKnowledgeBase,
  listDocuments,
  searchKnowledgeBase,
  uploadDocument,
  type Document,
  type KnowledgeBase,
  type SearchResult,
} from "@/core/knowledge";
import { formatTimeAgo } from "@/core/utils/datetime";
import { UploadIcon, SearchIcon, TrashIcon, FileIcon, RefreshCwIcon } from "lucide-react";

export default function KnowledgeDetailPage() {
  const { t } = useI18n();
  const params = useParams();
  const router = useRouter();
  const kbId = params.kb_id as string;

  const [kb, setKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    document.title = kb ? `${kb.name} - ${t.knowledge.pageTitle}` : t.knowledge.pageTitle;
  }, [kb, t.knowledge.pageTitle]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [kbData, docsData] = await Promise.all([
          getKnowledgeBase(kbId),
          listDocuments(kbId),
        ]);
        setKb(kbData);
        setDocuments(docsData);
      } catch (err) {
        console.error("Failed to load knowledge base:", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [kbId]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const doc = await uploadDocument(kbId, file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      console.error("Failed to upload document:", err);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteDoc = async (docId: string) => {
    if (!confirm(t.knowledge.deleteConfirm)) return;
    try {
      await deleteDocument(kbId, docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setSearching(true);
    try {
      const results = await searchKnowledgeBase(kbId, searchQuery.trim());
      setSearchResults(results.results);
    } catch (err) {
      console.error("Failed to search:", err);
    } finally {
      setSearching(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this knowledge base?")) return;
    try {
      await deleteKnowledgeBase(kbId);
      router.push("/workspace/knowledge");
    } catch (err) {
      console.error("Failed to delete knowledge base:", err);
    }
  };

  if (loading) {
    return (
      <WorkspaceContainer>
        <WorkspaceHeader />
        <WorkspaceBody>
          <div className="flex items-center justify-center py-8">
            {t.common.loading}
          </div>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  if (!kb) {
    return (
      <WorkspaceContainer>
        <WorkspaceHeader />
        <WorkspaceBody>
          <div className="text-center py-8">Knowledge base not found</div>
        </WorkspaceBody>
      </WorkspaceContainer>
    );
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader>
        <div className="flex gap-2">
          <label className="cursor-pointer">
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md,.csv"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
            />
            <Button size="sm" className="gap-1" disabled={uploading} asChild>
              <span>
                <UploadIcon className="size-4" />
                {uploading ? t.common.loading : t.knowledge.upload}
              </span>
            </Button>
          </label>
          <Button size="sm" variant="destructive" onClick={handleDelete}>
            <TrashIcon className="size-4 mr-1" />
            {t.common.delete}
          </Button>
        </div>
      </WorkspaceHeader>
      <WorkspaceBody>
        <div className="flex size-full flex-col">
          <main className="min-h-0 flex-1">
            <div className="mx-auto w-full max-w-(--container-width-md) py-8 space-y-6">
              <div>
                <h1 className="text-2xl font-bold">{kb.name}</h1>
                {kb.description && (
                  <p className="text-muted-foreground mt-1">{kb.description}</p>
                )}
              </div>

              <form onSubmit={handleSearch} className="flex gap-2">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t.knowledge.searchPlaceholder}
                  className="flex-1"
                />
                <Button type="submit" disabled={searching}>
                  <SearchIcon className="size-4 mr-1" />
                  {searching ? t.common.loading : t.knowledge.search}
                </Button>
              </form>

              {searchResults !== null && (
                <div className="space-y-4">
                  <h2 className="text-lg font-medium">
                    {searchResults.length > 0
                      ? `${searchResults.length} results`
                      : t.knowledge.noResults}
                  </h2>
                  {searchResults.map((result, idx) => (
                    <div key={idx} className="rounded-lg border p-4">
                      <div className="text-sm text-muted-foreground mb-2">
                        {result.document_name} (score: {result.similarity_score.toFixed(2)})
                      </div>
                      <p className="text-sm">{result.chunk_content}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-4">
                <h2 className="text-lg font-medium">{t.knowledge.documents}</h2>
                {documents.length === 0 ? (
                  <p className="text-muted-foreground">{t.knowledge.noDocuments}</p>
                ) : (
                  <div className="space-y-2">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between rounded-lg border p-4"
                      >
                        <div className="flex items-center gap-3">
                          <FileIcon className="size-5 text-muted-foreground" />
                          <div>
                            <div className="font-medium">{doc.original_name}</div>
                            <div className="text-sm text-muted-foreground">
                              {doc.file_type.toUpperCase()} - {doc.file_size} bytes
                              {doc.status === "ready" && ` - ${doc.chunk_count} chunks`}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center rounded-full px-2 py-1 text-xs ${
                              doc.status === "ready"
                                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                                : doc.status === "processing"
                                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100"
                                  : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100"
                            }`}
                          >
                            {t.knowledge.status[doc.status as keyof typeof t.knowledge.status]}
                          </span>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteDoc(doc.id)}
                          >
                            <TrashIcon className="size-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}
