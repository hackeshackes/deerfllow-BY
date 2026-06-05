import type { ToolCall } from "@langchain/core/messages";
import type { AIMessage } from "@langchain/langgraph-sdk";
import { describe, it, expect } from "vitest";

import { enUS } from "../i18n/locales/en-US";

import { explainLastToolCall, explainToolCall } from "./utils";

const t = enUS;

function toolCall(
  name: string,
  args: Record<string, unknown> = {},
): ToolCall {
  return { name, args, id: "call_1", type: "tool_call" };
}

function aiMessage(toolCalls: ToolCall[]): AIMessage {
  return {
    type: "ai",
    id: "m1",
    content: "",
    tool_calls: toolCalls,
  } as unknown as AIMessage;
}

describe("explainToolCall", () => {
  it("returns the localized search label for web_search", () => {
    expect(explainToolCall(toolCall("web_search", { query: "vitest" }), t)).toBe(
      'Search for "vitest"',
    );
  });

  it("returns the localized search label for image_search", () => {
    expect(
      explainToolCall(toolCall("image_search", { query: "logo" }), t),
    ).toBe('Search for "logo"');
  });

  it("returns the localized view-web-page label for web_fetch", () => {
    expect(explainToolCall(toolCall("web_fetch"), t)).toBe("View web page");
  });

  it("returns the localized present-files label", () => {
    expect(explainToolCall(toolCall("present_files"), t)).toBe("Present files");
  });

  it("returns the localized write-todos label", () => {
    expect(explainToolCall(toolCall("write_todos"), t)).toBe(
      "Update to-do list",
    );
  });

  it("falls back to the description argument when present", () => {
    expect(
      explainToolCall(
        toolCall("some_tool", { description: "Read the file" }),
        t,
      ),
    ).toBe("Read the file");
  });

  it("falls back to the generic useTool label when no description", () => {
    expect(explainToolCall(toolCall("random_tool"), t)).toBe(
      'Use "random_tool" tool',
    );
  });
});

describe("explainLastToolCall", () => {
  it("explains the most recent tool call on a message", () => {
    const message = aiMessage([
      toolCall("web_search", { query: "first" }),
      toolCall("web_fetch"),
    ]);
    expect(explainLastToolCall(message, t)).toBe("View web page");
  });

  it("falls back to the thinking label when no tool calls are present", () => {
    const message = aiMessage([]);
    expect(explainLastToolCall(message, t)).toBe(t.common.thinking);
  });
});
