"use client";

import { Download, FileJson, FileSpreadsheet, FileText, FileType } from "lucide-react";
import { useCallback } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import {
  exportThreadAsExcel,
  exportThreadAsJSON,
  exportThreadAsMarkdown,
  exportThreadAsPDF,
  exportThreadAsWord,
} from "@/core/threads/export";
import type { AgentThread } from "@/core/threads/types";

import { useThread } from "./messages/context";
import { Tooltip } from "./tooltip";

export function ExportTrigger({ threadId }: { threadId: string }) {
  const { t } = useI18n();
  const { thread } = useThread();

  const messages = thread.messages;

  const handleExport = useCallback(
    (format: "markdown" | "json" | "word" | "excel" | "pdf") => {
      if (messages.length === 0) {
        toast.error(t.conversation.noMessages);
        return;
      }
      const agentThread = {
        thread_id: threadId,
        updated_at: new Date().toISOString(),
        values: thread.values,
      } as AgentThread;

      switch (format) {
        case "markdown":
          exportThreadAsMarkdown(agentThread, messages);
          break;
        case "json":
          exportThreadAsJSON(agentThread, messages);
          break;
        case "word":
          exportThreadAsWord(agentThread, messages);
          break;
        case "excel":
          exportThreadAsExcel(agentThread, messages);
          break;
        case "pdf":
          exportThreadAsPDF(agentThread, messages);
          break;
      }
      toast.success(t.common.exportSuccess);
    },
    [messages, thread.values, threadId, t],
  );

  if (messages.length === 0) {
    return null;
  }

  return (
    <DropdownMenu>
      <Tooltip content={t.common.export}>
        <DropdownMenuTrigger asChild>
          <Button
            className="text-muted-foreground hover:text-foreground"
            variant="ghost"
          >
            <Download />
            {t.common.export}
          </Button>
        </DropdownMenuTrigger>
      </Tooltip>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => handleExport("markdown")}>
          <FileText className="text-muted-foreground" />
          <span>{t.common.exportAsMarkdown}</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleExport("json")}>
          <FileJson className="text-muted-foreground" />
          <span>{t.common.exportAsJSON}</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => handleExport("word")}>
          <FileType className="text-muted-foreground" />
          <span>{t.common.exportAsWord}</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleExport("excel")}>
          <FileSpreadsheet className="text-muted-foreground" />
          <span>{t.common.exportAsExcel}</span>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => handleExport("pdf")}>
          <FileType className="text-muted-foreground" />
          <span>{t.common.exportAsPDF}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
