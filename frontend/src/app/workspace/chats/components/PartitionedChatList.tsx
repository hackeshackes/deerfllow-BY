"use client";

import type { ReactNode } from "react";
import { useState } from "react";

import type { ThreadSource } from "@/core/threads/source";

export interface ChatItem {
  id: string;
  title: string;
  source: ThreadSource;
  updatedAt: string;
}

type Tab = "all" | ThreadSource;

const TABS: ReadonlyArray<Tab> = ["all", "manual", "automation", "channel"];

export interface PartitionedChatListProps {
  chats: ChatItem[];
  /**
   * Optional per-item renderer. When provided, the list item is wrapped in
   * a click target supplied by the caller (typically a Next `<Link>`).
   * When omitted, the default `<li>` body is rendered.
   */
  renderItem?: (item: ChatItem) => ReactNode;
}

/** Chat list partitioned by `source`. Defaults to showing all threads. */
export function PartitionedChatList({ chats, renderItem }: PartitionedChatListProps) {
  const [activeTab, setActiveTab] = useState<Tab>("all");

  const visible: ChatItem[] = activeTab === "all"
    ? chats
    : chats.filter((c) => c.source === activeTab);

  return (
    <div data-testid="partitioned-chat-list">
      <div className="flex gap-2 border-b" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            role="tab"
            data-testid={`tab-${tab}`}
            aria-selected={activeTab === tab}
            className={`px-3 py-2 ${
              activeTab === tab ? "border-b-2 border-blue-500" : ""
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === "all" ? "All" : tab}
          </button>
        ))}
      </div>
      <ul className="mt-2" data-testid="chat-list">
        {visible.length === 0 && (
          <li data-testid="empty-state" className="p-2 text-sm text-gray-500">
            No threads in this partition.
          </li>
        )}
        {visible.map((c) => (
          <li
            key={c.id}
            data-testid={`chat-${c.id}`}
            className="border-b p-2"
          >
            {renderItem ? (
              renderItem(c)
            ) : (
              <>
                <span className="font-medium">{c.title}</span>
                <span className="ml-2 text-xs text-gray-500">[{c.source}]</span>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
