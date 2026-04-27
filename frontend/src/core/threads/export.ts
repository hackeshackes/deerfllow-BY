import type { Message } from "@langchain/langgraph-sdk";

import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  hasContent,
  hasToolCalls,
  stripUploadedFilesTag,
} from "../messages/utils";

import type { AgentThread } from "./types";
import { titleOfThread } from "./utils";

function formatMessageContent(message: Message): string {
  const text = extractContentFromMessage(message);
  if (!text) return "";
  return stripUploadedFilesTag(text);
}

function formatToolCalls(message: Message): string {
  if (message.type !== "ai" || !hasToolCalls(message)) return "";
  const calls = message.tool_calls ?? [];
  return calls.map((call) => `- **Tool:** \`${call.name}\``).join("\n");
}

export function formatThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
): string {
  const title = titleOfThread(thread);
  const createdAt = thread.created_at
    ? new Date(thread.created_at).toLocaleString()
    : "Unknown";

  const lines: string[] = [
    `# ${title}`,
    "",
    `*Exported on ${new Date().toLocaleString()} · Created ${createdAt}*`,
    "",
    "---",
    "",
  ];

  for (const message of messages) {
    if (message.type === "human") {
      const content = formatMessageContent(message);
      if (content) {
        lines.push(`## User`, "", content, "", "---", "");
      }
    } else if (message.type === "ai") {
      const reasoning = extractReasoningContentFromMessage(message);
      const content = formatMessageContent(message);
      const toolCalls = formatToolCalls(message);

      if (!content && !toolCalls && !reasoning) continue;

      lines.push(`## Assistant`);

      if (reasoning) {
        lines.push("", `[Thinking] ${reasoning}`, "");
      }

      if (toolCalls) {
        lines.push("", toolCalls);
      }

      if (content && hasContent(message)) {
        lines.push("", content);
      }

      lines.push("", "---", "");
    }
  }

  return lines.join("\n").trimEnd() + "\n";
}

export function formatThreadAsJSON(
  thread: AgentThread,
  messages: Message[],
): string {
  const exportData = {
    title: titleOfThread(thread),
    thread_id: thread.thread_id,
    created_at: thread.created_at,
    exported_at: new Date().toISOString(),
    messages: messages.map((msg) => ({
      type: msg.type,
      id: msg.id,
      content: typeof msg.content === "string" ? msg.content : msg.content,
      ...(msg.type === "ai" && msg.tool_calls?.length
        ? { tool_calls: msg.tool_calls }
        : {}),
    })),
  };
  return JSON.stringify(exportData, null, 2);
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^\p{L}\p{N}_\- ]/gu, "").trim() || "conversation";
}

export function downloadAsFile(
  content: string,
  filename: string,
  mimeType: string,
) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
) {
  const markdown = formatThreadAsMarkdown(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.md`;
  downloadAsFile(markdown, filename, "text/markdown;charset=utf-8");
}

export function exportThreadAsJSON(thread: AgentThread, messages: Message[]) {
  const json = formatThreadAsJSON(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.json`;
  downloadAsFile(json, filename, "application/json;charset=utf-8");
}

export function exportThreadAsWord(thread: AgentThread, messages: Message[]) {
  const title = titleOfThread(thread);
  const createdAt = thread.created_at
    ? new Date(thread.created_at).toLocaleString()
    : "Unknown";

  const htmlParts: string[] = [
    `<!DOCTYPE html>`,
    `<html>`,
    `<head>`,
    `<meta charset="utf-8">`,
    `<title>${title}</title>`,
    `<style>`,
    `body { font-family: Arial, sans-serif; margin: 20px; }`,
    `h1 { color: #333; }`,
    `h2 { color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }`,
    `.meta { color: #888; font-size: 12px; }`,
    `.thinking { background: #f5f5f5; padding: 10px; margin: 10px 0; border-left: 3px solid #666; }`,
    `.tool { color: #0066cc; }`,
    `</style>`,
    `</head>`,
    `<body>`,
    `<h1>${title}</h1>`,
    `<p class="meta">Exported on ${new Date().toLocaleString()} · Created ${createdAt}</p>`,
  ];

  for (const message of messages) {
    if (message.type === "human") {
      const content = formatMessageContent(message);
      if (content) {
        htmlParts.push(`<h2>User</h2>`, `<p>${content.replace(/\n/g, "<br>")}</p>`);
      }
    } else if (message.type === "ai") {
      const reasoning = extractReasoningContentFromMessage(message);
      const content = formatMessageContent(message);
      const toolCalls = formatToolCalls(message);

      if (!content && !toolCalls && !reasoning) continue;

      htmlParts.push(`<h2>Assistant</h2>`);

      if (reasoning) {
        htmlParts.push(`<div class="thinking"><strong>[Thinking]</strong><br>${reasoning.replace(/\n/g, "<br>")}</div>`);
      }

      if (toolCalls) {
        htmlParts.push(`<p class="tool">${toolCalls.replace(/\n/g, "<br>")}</p>`);
      }

      if (content && hasContent(message)) {
        htmlParts.push(`<p>${content.replace(/\n/g, "<br>")}</p>`);
      }
    }
  }

  htmlParts.push(`</body>`, `</html>`);

  const html = htmlParts.join("\n");
  const filename = `${sanitizeFilename(title)}.doc`;
  downloadAsFile(html, filename, "application/msword;charset=utf-8");
}

export function exportThreadAsExcel(thread: AgentThread, messages: Message[]) {
  const title = titleOfThread(thread);

  const rows: string[][] = [
    ["Role", "Content", "Tool Calls", "Thinking", "Timestamp"],
  ];

  for (const message of messages) {
    if (message.type === "human") {
      const content = formatMessageContent(message);
      if (content) {
        rows.push(["User", content, "", "", new Date().toISOString()]);
      }
    } else if (message.type === "ai") {
      const reasoning = extractReasoningContentFromMessage(message);
      const content = formatMessageContent(message);
      const toolCalls = message.tool_calls
        ?.map((call) => `${call.name}(${JSON.stringify(call.args)})`)
        .join("; ") ?? "";

      if (!content && !toolCalls && !reasoning) continue;

      rows.push(["Assistant", content ?? "", toolCalls, reasoning ?? "", new Date().toISOString()]);
    }
  }

  const csv = rows
    .map((row) =>
      row
        .map((cell) => {
          const escaped = cell.replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",")
    )
    .join("\n");

  const filename = `${sanitizeFilename(title)}.csv`;
  downloadAsFile(csv, filename, "text/csv;charset=utf-8");
}

export function exportThreadAsPDF(thread: AgentThread, messages: Message[]) {
  const title = titleOfThread(thread);

  const printContent = formatThreadAsMarkdown(thread, messages);
  const printWindow = window.open("", "_blank");
  if (!printWindow) {
    alert("Unable to open print window. Please allow popups for this site.");
    return;
  }

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>${title}</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        .meta { color: #888; font-size: 12px; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      <p class="meta">Exported on ${new Date().toLocaleString()}</p>
      <pre>${printContent.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
      <script>window.onload = function() { window.print(); window.close(); }</script>
    </body>
    </html>
  `);
  printWindow.document.close();
}
