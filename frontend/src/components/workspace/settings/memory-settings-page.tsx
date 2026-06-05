"use client";

import { useDeferredValue, useRef, useState } from "react";
import { toast } from "sonner";
import { Streamdown } from "streamdown";

import { useI18n } from "@/core/i18n/hooks";
import { exportMemory } from "@/core/memory/api";
import {
  useClearMemory,
  useCreateMemoryFact,
  useDeleteMemoryFact,
  useImportMemory,
  useMemory,
  useUpdateMemoryFact,
} from "@/core/memory/hooks";
import type {
  MemoryFactInput,
  MemoryFactPatchInput,
} from "@/core/memory/types";
import { streamdownPlugins } from "@/core/streamdown/plugins";

import { FactDeleteDialog } from "./memory/fact-delete-dialog";
import { FactEditorDialog } from "./memory/fact-editor-dialog";
import { FactsList } from "./memory/facts-list";
import { MemoryClearDialog } from "./memory/memory-clear-dialog";
import { MemoryImportDialog } from "./memory/memory-import-dialog";
import { MemoryToolbar } from "./memory/memory-toolbar";
import {
  DEFAULT_FACT_FORM_STATE,
  type FactFormState,
  type MemoryFact,
  type MemoryViewFilter,
  type PendingImport,
} from "./memory/types";
import {
  buildMemorySectionGroups,
  isImportedMemory,
  isMemorySummaryEmpty,
  summariesToMarkdown,
} from "./memory/utils";
import { SettingsSection } from "./settings-section";

export function MemorySettingsPage() {
  const { t } = useI18n();
  const { memory, isLoading, error } = useMemory();
  const clearMemory = useClearMemory();
  const createMemoryFact = useCreateMemoryFact();
  const deleteMemoryFact = useDeleteMemoryFact();
  const importMemoryMutation = useImportMemory();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const updateMemoryFact = useUpdateMemoryFact();
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [factToDelete, setFactToDelete] = useState<MemoryFact | null>(null);
  const [factToEdit, setFactToEdit] = useState<MemoryFact | null>(null);
  const [factEditorOpen, setFactEditorOpen] = useState(false);
  const [factForm, setFactForm] = useState<FactFormState>(
    DEFAULT_FACT_FORM_STATE,
  );
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<MemoryViewFilter>("all");
  const [pendingImport, setPendingImport] = useState<PendingImport | null>(
    null,
  );
  const [isExporting, setIsExporting] = useState(false);
  const deferredQuery = useDeferredValue(query);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  const clearAllLabel = t.settings.memory.clearAll ?? "Clear all memory";
  const clearAllConfirmTitle =
    t.settings.memory.clearAllConfirmTitle ?? "Clear all memory?";
  const clearAllConfirmDescription =
    t.settings.memory.clearAllConfirmDescription ??
    "This will remove all saved summaries and facts. This action cannot be undone.";
  const clearAllSuccess =
    t.settings.memory.clearAllSuccess ?? "All memory cleared";
  const factDeleteSuccess =
    t.settings.memory.factDeleteSuccess ?? "Fact deleted";
  const addFactSuccess = t.settings.memory.addFactSuccess;
  const editFactSuccess = t.settings.memory.editFactSuccess;
  const factValidationContent = t.settings.memory.factValidationContent;
  const factValidationConfidence = t.settings.memory.factValidationConfidence;
  const noFacts = t.settings.memory.noFacts ?? "No saved facts yet.";
  const summaryReadOnly = t.settings.memory.summaryReadOnly;
  const memoryFullyEmpty =
    t.settings.memory.memoryFullyEmpty ?? "No memory saved yet.";
  const noMatches = t.settings.memory.noMatches ?? "No matching memory found";
  const exportSuccess =
    t.settings.memory.exportSuccess ?? t.common.exportSuccess;
  const importSuccess = t.settings.memory.importSuccess ?? "Memory imported";

  const sectionGroups = memory ? buildMemorySectionGroups(memory, t) : [];
  const filteredSectionGroups = sectionGroups
    .map((group) => ({
      ...group,
      sections: group.sections.filter((section) =>
        normalizedQuery
          ? `${section.title} ${section.summary}`
              .toLowerCase()
              .includes(normalizedQuery)
          : true,
      ),
    }))
    .filter((group) => group.sections.length > 0);

  const filteredFacts = memory
    ? memory.facts.filter((fact) =>
        normalizedQuery
          ? `${fact.content} ${fact.category}`
              .toLowerCase()
              .includes(normalizedQuery)
          : true,
      )
    : [];

  const showSummaries = filter !== "facts";
  const showFacts = filter !== "summaries";
  const shouldRenderSummariesBlock =
    showSummaries && (filteredSectionGroups.length > 0 || !normalizedQuery);
  const shouldRenderFactsBlock =
    showFacts &&
    (filteredFacts.length > 0 || !normalizedQuery || filter === "facts");
  const hasMatchingVisibleContent =
    !memory ||
    (showSummaries && filteredSectionGroups.length > 0) ||
    (showFacts && filteredFacts.length > 0);

  async function handleExportMemory() {
    try {
      setIsExporting(true);
      const exportedMemory = await exportMemory();
      const fileName = `deerflow-memory-${(exportedMemory.lastUpdated || new Date().toISOString()).replace(/[:.]/g, "-")}.json`;
      const blob = new Blob([JSON.stringify(exportedMemory, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success(exportSuccess);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExporting(false);
    }
  }

  async function handleImportFileSelection(event: {
    target: HTMLInputElement;
  }) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!isImportedMemory(parsed)) {
        toast.error(t.settings.memory.importInvalidFile);
        return;
      }
      setPendingImport({
        fileName: file.name,
        memory: parsed,
      });
    } catch {
      toast.error(t.settings.memory.importInvalidFile);
    }
  }

  async function handleConfirmImport() {
    if (!pendingImport) {
      return;
    }

    try {
      await importMemoryMutation.mutateAsync(pendingImport.memory);
      toast.success(importSuccess);
      setPendingImport(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleClearMemory() {
    try {
      await clearMemory.mutateAsync();
      toast.success(clearAllSuccess);
      setClearDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDeleteFact() {
    if (!factToDelete) return;

    const factId = factToDelete.id;
    const factContent = factToDelete.content;
    const factCategory = factToDelete.category;
    const factConfidence = factToDelete.confidence;

    setFactToDelete(null);

    try {
      await deleteMemoryFact.mutateAsync(factId);
      toast.success(
        factDeleteSuccess,
        {
          action: {
            label: "撤销",
            onClick: () => {
              void createMemoryFact
                .mutateAsync({
                  content: factContent,
                  category: factCategory,
                  confidence: factConfidence,
                })
                .catch(() => {
                  // Undo failed, ignore
                });
            },
          },
        }
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  function openCreateFactDialog() {
    setFactToEdit(null);
    setFactForm(DEFAULT_FACT_FORM_STATE);
    setFactEditorOpen(true);
  }

  function openEditFactDialog(fact: MemoryFact) {
    setFactToEdit(fact);
    setFactForm({
      content: fact.content,
      category: fact.category,
      confidence: String(fact.confidence),
    });
    setFactEditorOpen(true);
  }

  async function handleSaveFact() {
    const trimmedContent = factForm.content.trim();
    if (!trimmedContent) {
      toast.error(factValidationContent);
      return;
    }

    const confidence = Number(factForm.confidence);
    if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
      toast.error(factValidationConfidence);
      return;
    }

    const input: MemoryFactInput = {
      content: trimmedContent,
      category: factForm.category.trim() || "context",
      confidence,
    };

    try {
      if (factToEdit) {
        const patchInput: MemoryFactPatchInput = {
          content: input.content,
          category: input.category,
          confidence: input.confidence,
        };
        await updateMemoryFact.mutateAsync({
          factId: factToEdit.id,
          input: patchInput,
        });
        toast.success(editFactSuccess);
      } else {
        await createMemoryFact.mutateAsync(input);
        toast.success(addFactSuccess);
      }
      setFactEditorOpen(false);
      setFactToEdit(null);
      setFactForm(DEFAULT_FACT_FORM_STATE);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }

  const isFactFormPending =
    createMemoryFact.isPending || updateMemoryFact.isPending;

  return (
    <>
      <SettingsSection
        title={t.settings.memory.title}
        description={t.settings.memory.description}
      >
        {isLoading ? (
          <div className="text-muted-foreground text-sm">
            {t.common.loading}
          </div>
        ) : error ? (
          <div>Error: {error.message}</div>
        ) : !memory ? (
          <div className="text-muted-foreground text-sm">
            {t.settings.memory.empty}
          </div>
        ) : (
          <div className="space-y-4">
            {isMemorySummaryEmpty(memory) && memory.facts.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
                {memoryFullyEmpty}
              </div>
            ) : null}

            <MemoryToolbar
              query={query}
              onQueryChange={setQuery}
              filter={filter}
              onFilterChange={setFilter}
              fileInputRef={fileInputRef}
              onImportFile={handleImportFileSelection}
              isImporting={importMemoryMutation.isPending}
              isExporting={isExporting}
              onExport={() => void handleExportMemory()}
              onAddFact={openCreateFactDialog}
              isClearing={clearMemory.isPending}
              onClear={() => setClearDialogOpen(true)}
            />

            {!hasMatchingVisibleContent && normalizedQuery ? (
              <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
                {noMatches}
              </div>
            ) : null}

            {shouldRenderSummariesBlock ? (
              <div className="rounded-lg border p-4">
                <div className="text-muted-foreground mb-4 text-sm">
                  {summaryReadOnly}
                </div>
                <Streamdown
                  className="size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
                  {...streamdownPlugins}
                >
                  {summariesToMarkdown(memory, filteredSectionGroups, t)}
                </Streamdown>
              </div>
            ) : null}

            {shouldRenderFactsBlock ? (
              <div className="rounded-lg border p-4">
                <div className="mb-4">
                  <h3 className="text-base font-medium">
                    {t.settings.memory.markdown.facts}
                  </h3>
                </div>
                <FactsList
                  facts={filteredFacts}
                  noMatches={noMatches}
                  noFacts={noFacts}
                  normalizedQuery={normalizedQuery}
                  onEdit={openEditFactDialog}
                  onDelete={setFactToDelete}
                />
              </div>
            ) : null}
          </div>
        )}
      </SettingsSection>

      <MemoryClearDialog
        open={clearDialogOpen}
        isPending={clearMemory.isPending}
        confirmTitle={clearAllConfirmTitle}
        confirmDescription={clearAllConfirmDescription}
        confirmLabel={clearAllLabel}
        onOpenChange={setClearDialogOpen}
        onConfirm={() => void handleClearMemory()}
      />

      <FactEditorDialog
        open={factEditorOpen}
        factToEdit={factToEdit}
        factForm={factForm}
        setFactForm={setFactForm}
        isPending={isFactFormPending}
        onOpenChange={(open) => {
          setFactEditorOpen(open);
          if (!open) {
            setFactToEdit(null);
            setFactForm(DEFAULT_FACT_FORM_STATE);
          }
        }}
        onSave={() => void handleSaveFact()}
      />

      <FactDeleteDialog
        factToDelete={factToDelete}
        isPending={deleteMemoryFact.isPending}
        onOpenChange={(open) => {
          if (!open) {
            setFactToDelete(null);
          }
        }}
        onConfirm={() => void handleDeleteFact()}
      />

      <MemoryImportDialog
        pendingImport={pendingImport}
        isPending={importMemoryMutation.isPending}
        onOpenChange={(open) => {
          if (!open) {
            setPendingImport(null);
          }
        }}
        onConfirm={() => void handleConfirmImport()}
      />
    </>
  );
}
