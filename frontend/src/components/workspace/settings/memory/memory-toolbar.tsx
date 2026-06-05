"use client";

import {
  DownloadIcon,
  PlusIcon,
  UploadIcon,
} from "lucide-react";
import type { RefObject } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useI18n } from "@/core/i18n/hooks";

import type { MemoryViewFilter } from "./types";

interface MemoryToolbarProps {
  query: string;
  onQueryChange: (value: string) => void;
  filter: MemoryViewFilter;
  onFilterChange: (value: MemoryViewFilter) => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
  onImportFile: (event: { target: HTMLInputElement }) => void;
  isImporting: boolean;
  isExporting: boolean;
  onExport: () => void;
  onAddFact: () => void;
  isClearing: boolean;
  onClear: () => void;
}

export function MemoryToolbar({
  query,
  onQueryChange,
  filter,
  onFilterChange,
  fileInputRef,
  onImportFile,
  isImporting,
  isExporting,
  onExport,
  onAddFact,
  isClearing,
  onClear,
}: MemoryToolbarProps) {
  const { t } = useI18n();
  const searchPlaceholder =
    t.settings.memory.searchPlaceholder ?? "Search memory";
  const filterAll = t.settings.memory.filterAll ?? "All";
  const filterFacts = t.settings.memory.filterFacts ?? "Facts";
  const filterSummaries = t.settings.memory.filterSummaries ?? "Summaries";
  const importButton = t.settings.memory.importButton ?? t.common.import;
  const exportButton = t.settings.memory.exportButton ?? t.common.export;
  const addFactLabel = t.settings.memory.addFact;
  const clearAllLabel = t.settings.memory.clearAll ?? "Clear all memory";

  return (
    <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={searchPlaceholder}
          className="sm:max-w-xs"
        />
        <ToggleGroup
          type="single"
          value={filter}
          onValueChange={(value) => {
            if (value) onFilterChange(value as MemoryViewFilter);
          }}
          variant="outline"
        >
          <ToggleGroupItem value="all">{filterAll}</ToggleGroupItem>
          <ToggleGroupItem value="facts">{filterFacts}</ToggleGroupItem>
          <ToggleGroupItem value="summaries">
            {filterSummaries}
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          className="hidden"
          onChange={(event) => void onImportFile(event)}
        />
        <Button
          variant="outline"
          onClick={() => fileInputRef.current?.click()}
          disabled={isImporting}
        >
          <UploadIcon className="mr-2 h-4 w-4" />
          {importButton}
        </Button>
        <Button
          variant="outline"
          onClick={onExport}
          disabled={isExporting}
        >
          <DownloadIcon className="mr-2 h-4 w-4" />
          {isExporting ? t.common.loading : exportButton}
        </Button>
        <Button variant="outline" onClick={onAddFact}>
          <PlusIcon className="mr-2 h-4 w-4" />
          {addFactLabel}
        </Button>
        <Button
          variant="destructive"
          onClick={onClear}
          disabled={isClearing}
        >
          {isClearing ? t.common.loading : clearAllLabel}
        </Button>
      </div>
    </div>
  );
}
