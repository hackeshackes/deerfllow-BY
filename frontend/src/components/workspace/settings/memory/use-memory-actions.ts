"use client";

import { useCallback, useRef, useState } from "react";
import { toast } from "sonner";

import { useI18n } from "@/core/i18n/hooks";
import { exportMemory } from "@/core/memory/api";
import {
  useClearMemory,
  useCreateMemoryFact,
  useDeleteMemoryFact,
  useImportMemory,
  useUpdateMemoryFact,
} from "@/core/memory/hooks";
import type {
  MemoryFactInput,
  MemoryFactPatchInput,
} from "@/core/memory/types";

import {
  DEFAULT_FACT_FORM_STATE,
  type FactFormState,
  type MemoryFact,
  type PendingImport,
} from "./types";
import { isImportedMemory } from "./utils";

export function useMemoryActions() {
  const { t } = useI18n();
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
  const [pendingImport, setPendingImport] = useState<PendingImport | null>(
    null,
  );
  const [isExporting, setIsExporting] = useState(false);

  const clearAllSuccess =
    t.settings.memory.clearAllSuccess ?? "All memory cleared";
  const factDeleteSuccess =
    t.settings.memory.factDeleteSuccess ?? "Fact deleted";
  const addFactSuccess = t.settings.memory.addFactSuccess;
  const editFactSuccess = t.settings.memory.editFactSuccess;
  const factValidationContent = t.settings.memory.factValidationContent;
  const factValidationConfidence = t.settings.memory.factValidationConfidence;
  const exportSuccess =
    t.settings.memory.exportSuccess ?? t.common.exportSuccess;
  const importSuccess = t.settings.memory.importSuccess ?? "Memory imported";

  const handleExportMemory = useCallback(async () => {
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
  }, [exportSuccess]);

  const handleImportFileSelection = useCallback(
    async (event: { target: HTMLInputElement }) => {
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
    },
    [t.settings.memory.importInvalidFile],
  );

  const handleConfirmImport = useCallback(async () => {
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
  }, [pendingImport, importMemoryMutation, importSuccess]);

  const handleClearMemory = useCallback(async () => {
    try {
      await clearMemory.mutateAsync();
      toast.success(clearAllSuccess);
      setClearDialogOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }, [clearMemory, clearAllSuccess]);

  const handleDeleteFact = useCallback(async () => {
    if (!factToDelete) return;

    const factId = factToDelete.id;
    const factContent = factToDelete.content;
    const factCategory = factToDelete.category;
    const factConfidence = factToDelete.confidence;

    setFactToDelete(null);

    try {
      await deleteMemoryFact.mutateAsync(factId);
      toast.success(factDeleteSuccess, {
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
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  }, [factToDelete, deleteMemoryFact, createMemoryFact, factDeleteSuccess]);

  const openCreateFactDialog = useCallback(() => {
    setFactToEdit(null);
    setFactForm(DEFAULT_FACT_FORM_STATE);
    setFactEditorOpen(true);
  }, []);

  const openEditFactDialog = useCallback((fact: MemoryFact) => {
    setFactToEdit(fact);
    setFactForm({
      content: fact.content,
      category: fact.category,
      confidence: String(fact.confidence),
    });
    setFactEditorOpen(true);
  }, []);

  const handleSaveFact = useCallback(async () => {
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
  }, [
    factForm,
    factToEdit,
    updateMemoryFact,
    createMemoryFact,
    editFactSuccess,
    addFactSuccess,
    factValidationContent,
    factValidationConfidence,
  ]);

  return {
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
    isFactFormPending:
      createMemoryFact.isPending || updateMemoryFact.isPending,
    handleExportMemory,
    handleImportFileSelection,
    handleConfirmImport,
    handleClearMemory,
    handleDeleteFact,
    handleSaveFact,
    openCreateFactDialog,
    openEditFactDialog,
  };
}
