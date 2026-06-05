"use client";

import { useDeferredValue, useState } from "react";

import { useI18n } from "@/core/i18n/hooks";
import { useMemory } from "@/core/memory/hooks";

import { FactDeleteDialog } from "./memory/fact-delete-dialog";
import { FactEditorDialog } from "./memory/fact-editor-dialog";
import { MemoryClearDialog } from "./memory/memory-clear-dialog";
import { MemoryFactsBlock } from "./memory/memory-facts-block";
import { MemoryImportDialog } from "./memory/memory-import-dialog";
import { MemorySummaryView } from "./memory/memory-summary-view";
import { MemoryToolbar } from "./memory/memory-toolbar";
import {
  DEFAULT_FACT_FORM_STATE,
  type MemoryViewFilter,
} from "./memory/types";
import { useMemoryActions } from "./memory/use-memory-actions";
import {
  buildMemorySectionGroups,
  isMemorySummaryEmpty,
} from "./memory/utils";
import { SettingsSection } from "./settings-section";

export function MemorySettingsPage() {
  const { t } = useI18n();
  const { memory, isLoading, error } = useMemory();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<MemoryViewFilter>("all");
  const deferredQuery = useDeferredValue(query);
  const normalizedQuery = deferredQuery.trim().toLowerCase();

  const {
    clearDialogOpen,
    setClearDialogOpen,
    factToDelete,
    setFactToDelete,
    factToEdit,
    setFactToEdit,
    factEditorOpen,
    setFactEditorOpen,
    factForm,
    setFactForm,
    pendingImport,
    setPendingImport,
    isExporting,
    fileInputRef,
    clearMemory,
    importMemoryMutation,
    deleteMemoryFact,
    isFactFormPending,
    handleExportMemory,
    handleImportFileSelection,
    handleConfirmImport,
    handleClearMemory,
    handleDeleteFact,
    handleSaveFact,
    openCreateFactDialog,
    openEditFactDialog,
  } = useMemoryActions();

  const clearAllLabel = t.settings.memory.clearAll ?? "Clear all memory";
  const clearAllConfirmTitle =
    t.settings.memory.clearAllConfirmTitle ?? "Clear all memory?";
  const clearAllConfirmDescription =
    t.settings.memory.clearAllConfirmDescription ??
    "This will remove all saved summaries and facts. This action cannot be undone.";
  const noFacts = t.settings.memory.noFacts ?? "No saved facts yet.";
  const memoryFullyEmpty =
    t.settings.memory.memoryFullyEmpty ?? "No memory saved yet.";
  const noMatches = t.settings.memory.noMatches ?? "No matching memory found";

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
              <MemorySummaryView
                memory={memory}
                filteredSectionGroups={filteredSectionGroups}
              />
            ) : null}

            {shouldRenderFactsBlock ? (
              <MemoryFactsBlock
                facts={filteredFacts}
                noMatches={noMatches}
                noFacts={noFacts}
                normalizedQuery={normalizedQuery}
                onEdit={openEditFactDialog}
                onDelete={setFactToDelete}
              />
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
