"use client";

import { PenLineIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/core/i18n/hooks";
import { useDeleteMemoryFact } from "@/core/memory/hooks";
import { pathOfThread } from "@/core/threads/utils";
import { formatTimeAgo } from "@/core/utils/datetime";

import type { MemoryFact } from "./types";
import { confidenceToLevelKey, upperFirst } from "./utils";

interface FactsListProps {
  facts: MemoryFact[];
  noMatches: string;
  noFacts: string;
  normalizedQuery: string;
  onEdit: (fact: MemoryFact) => void;
  onDelete: (fact: MemoryFact) => void;
}

export function FactsList({ facts, noMatches, noFacts, normalizedQuery, onEdit, onDelete }: FactsListProps) {
  const { t } = useI18n();
  const deleteMemoryFact = useDeleteMemoryFact();

  if (facts.length === 0) {
    return (
      <div className="text-muted-foreground text-sm">
        {normalizedQuery ? noMatches : noFacts}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {facts.map((fact) => {
        const { key } = confidenceToLevelKey(fact.confidence);
        const confidenceText =
          t.settings.memory.markdown.table.confidenceLevel[key];

        return (
          <div
            key={fact.id}
            className="flex flex-col gap-3 rounded-md border p-3 sm:flex-row sm:items-start sm:justify-between"
          >
            <div className="min-w-0 space-y-2">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                <span>
                  <span className="text-muted-foreground">
                    {t.settings.memory.markdown.table.category}:
                  </span>{" "}
                  {upperFirst(fact.category)}
                </span>
                <span>
                  <span className="text-muted-foreground">
                    {t.settings.memory.markdown.table.confidence}:
                  </span>{" "}
                  {confidenceText}
                </span>
                <span>
                  <span className="text-muted-foreground">
                    {t.settings.memory.markdown.table.createdAt}:
                  </span>{" "}
                  {formatTimeAgo(fact.createdAt)}
                </span>
                <span>
                  <span className="text-muted-foreground">
                    {t.settings.memory.markdown.table.source}:
                  </span>{" "}
                  {fact.source === "manual" ? (
                    t.settings.memory.manualFactSource
                  ) : (
                    <Link
                      href={pathOfThread(fact.source)}
                      className="text-primary underline-offset-4 hover:underline"
                    >
                      {t.settings.memory.markdown.table.view}
                    </Link>
                  )}
                </span>
              </div>
              <p className="text-sm break-words">{fact.content}</p>
            </div>

            <div className="flex shrink-0 items-center gap-1 self-start sm:ml-3">
              <Button
                variant="ghost"
                size="icon"
                className="shrink-0"
                onClick={() => onEdit(fact)}
                disabled={deleteMemoryFact.isPending}
                title={t.common.edit}
                aria-label={t.common.edit}
              >
                <PenLineIcon className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                className="text-destructive hover:text-destructive shrink-0"
                onClick={() => onDelete(fact)}
                disabled={deleteMemoryFact.isPending}
                title={t.common.delete}
                aria-label={t.common.delete}
              >
                <Trash2Icon className="h-4 w-4" />
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
