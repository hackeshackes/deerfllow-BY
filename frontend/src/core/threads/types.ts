import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { ThreadSource } from "./source";
import type { Todo } from "../todos";

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
  todos?: Todo[];
  /**
   * v1.5.5 — space the thread lives in. Defaults to `personal` when
   * unset (older threads persisted before the v1.5.5 cutover).
   */
  space_type?: "personal" | "workspace";
  /**
   * v1.5.5 — how the thread originated. Drives the partition in
   * `PartitionedChatList`.
   */
  source?: ThreadSource;
  /**
   * v1.5.5 — for workspace-scope threads that were promoted from a
   * personal thread, the original thread id.
   */
  published_from_thread_id?: string | null;
}

export interface AgentThread extends Thread<AgentThreadState> {}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  reasoning_effort?: "minimal" | "low" | "medium" | "high";
  agent_name?: string;
}
