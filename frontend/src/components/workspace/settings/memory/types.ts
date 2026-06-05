import type { UserMemory } from "@/core/memory/types";

export type {
  MemoryFact,
  MemoryFactInput,
  MemoryFactPatchInput,
  UserMemory,
} from "@/core/memory/types";

export type MemoryViewFilter = "all" | "facts" | "summaries";

export type MemorySection = {
  title: string;
  summary: string;
  updatedAt?: string;
};

export type MemorySectionGroup = {
  title: string;
  sections: MemorySection[];
};

export type PendingImport = {
  fileName: string;
  memory: UserMemory;
};

export type FactFormState = {
  content: string;
  category: string;
  confidence: string;
};

export const DEFAULT_FACT_FORM_STATE: FactFormState = {
  content: "",
  category: "context",
  confidence: "0.8",
};
