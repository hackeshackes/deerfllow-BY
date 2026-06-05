"use client";

import { Streamdown } from "streamdown";

import { useI18n } from "@/core/i18n/hooks";
import type { UserMemory } from "@/core/memory/types";
import { streamdownPlugins } from "@/core/streamdown/plugins";

import type { MemorySectionGroup } from "./types";
import { summariesToMarkdown } from "./utils";

interface MemorySummaryViewProps {
  memory: UserMemory;
  filteredSectionGroups: MemorySectionGroup[];
}

export function MemorySummaryView({
  memory,
  filteredSectionGroups,
}: MemorySummaryViewProps) {
  const { t } = useI18n();
  const summaryReadOnly = t.settings.memory.summaryReadOnly;

  return (
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
  );
}
