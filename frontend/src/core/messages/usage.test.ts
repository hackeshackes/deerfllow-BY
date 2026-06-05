import type { Message } from "@langchain/langgraph-sdk";
import { describe, it, expect } from "vitest";

import { accumulateUsage, formatTokenCount } from "./usage";

function aiMessage(usage?: {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
}): Message {
  const message: Record<string, unknown> = { type: "ai", content: "" };
  if (usage) {
    message.usage_metadata = usage;
  }
  return message as unknown as Message;
}

describe("accumulateUsage", () => {
  it("returns null when no message has usage metadata", () => {
    expect(accumulateUsage([aiMessage(), aiMessage()])).toBeNull();
  });

  it("returns null for an empty message list", () => {
    expect(accumulateUsage([])).toBeNull();
  });

  it("skips messages without usage metadata and aggregates the rest", () => {
    const messages = [
      aiMessage({ input_tokens: 10, output_tokens: 5, total_tokens: 15 }),
      aiMessage(),
      aiMessage({ input_tokens: 3, output_tokens: 2, total_tokens: 5 }),
    ];
    expect(accumulateUsage(messages)).toEqual({
      inputTokens: 13,
      outputTokens: 7,
      totalTokens: 20,
    });
  });

  it("ignores non-ai messages even if they have usage metadata", () => {
    const ai = aiMessage({ input_tokens: 1, output_tokens: 1, total_tokens: 2 });
    const human: Message = {
      type: "human",
      content: "",
    } as unknown as Message;
    expect(accumulateUsage([ai, human])).toEqual({
      inputTokens: 1,
      outputTokens: 1,
      totalTokens: 2,
    });
  });
});

describe("formatTokenCount", () => {
  it("formats numbers under 10,000 with locale grouping", () => {
    expect(formatTokenCount(0)).toBe("0");
    expect(formatTokenCount(1234)).toBe("1,234");
    expect(formatTokenCount(9999)).toBe("9,999");
  });

  it("formats numbers at or above 10,000 as a K-suffixed value", () => {
    expect(formatTokenCount(10_000)).toBe("10.0K");
    expect(formatTokenCount(12_345)).toBe("12.3K");
    expect(formatTokenCount(150_000)).toBe("150.0K");
  });
});
