import type { Message } from "@langchain/langgraph-sdk";

import { describe, it, expect } from "vitest";

import type { AgentThread } from "./types";
import { pathOfThread, textOfMessage, titleOfThread } from "./utils";

describe("pathOfThread", () => {
  it("builds the canonical workspace chat path for a thread id", () => {
    expect(pathOfThread("abc-123")).toBe("/workspace/chats/abc-123");
  });
});

describe("titleOfThread", () => {
  it("returns the title stored on the thread state", () => {
    const thread = {
      thread_id: "t1",
      values: { title: "My chat", messages: [], artifacts: [] },
    } as unknown as AgentThread;
    expect(titleOfThread(thread)).toBe("My chat");
  });

  it("falls back to the default placeholder when title is missing", () => {
    const thread = {
      thread_id: "t2",
      values: { messages: [], artifacts: [] },
    } as unknown as AgentThread;
    expect(titleOfThread(thread)).toBe("新对话");
  });
});

describe("textOfMessage", () => {
  it("returns the string content directly when content is a string", () => {
    const message = { type: "human", content: "hello" } as unknown as Message;
    expect(textOfMessage(message)).toBe("hello");
  });

  it("returns the first text part when content is an array of parts", () => {
    const message = {
      type: "ai",
      content: [
        { type: "text", text: "first" },
        { type: "text", text: "second" },
      ],
    } as unknown as Message;
    expect(textOfMessage(message)).toBe("first");
  });

  it("returns null when the content array has no text part", () => {
    const message = {
      type: "ai",
      content: [{ type: "image_url", image_url: { url: "x" } }],
    } as unknown as Message;
    expect(textOfMessage(message)).toBeNull();
  });
});
