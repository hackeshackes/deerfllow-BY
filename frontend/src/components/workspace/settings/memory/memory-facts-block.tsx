"use client";

import { useI18n } from "@/core/i18n/hooks";

import { FactsList } from "./facts-list";
import type { MemoryFact } from "./types";

interface MemoryFactsBlockProps {
  facts: MemoryFact[];
  noMatches: string;
  noFacts: string;
  normalizedQuery: string;
  onEdit: (fact: MemoryFact) => void;
  onDelete: (fact: MemoryFact) => void;
}

export function MemoryFactsBlock({
  facts,
  noMatches,
  noFacts,
  normalizedQuery,
  onEdit,
  onDelete,
}: MemoryFactsBlockProps) {
  const { t } = useI18n();
  return (
    <div className="rounded-lg border p-4">
      <div className="mb-4">
        <h3 className="text-base font-medium">
          {t.settings.memory.markdown.facts}
        </h3>
      </div>
      <FactsList
        facts={facts}
        noMatches={noMatches}
        noFacts={noFacts}
        normalizedQuery={normalizedQuery}
        onEdit={onEdit}
        onDelete={onDelete}
      />
    </div>
  );
}
