import { getBackendBaseURL } from "@/core/config";

export interface KnowledgeBase {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  embedding_model: string;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  knowledge_base_id: string;
  original_name: string;
  file_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  token_count: number;
  uploaded_at: string;
  processed_at?: string;
}

export interface SearchResult {
  document_id: string;
  document_name: string;
  chunk_content: string;
  similarity_score: number;
  metadata: Record<string, unknown>;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  knowledge_base_id: string;
}

export async function loadKnowledgeBases(): Promise<KnowledgeBase[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge`);
  return response.json();
}

export async function getKnowledgeBase(kbId: string): Promise<KnowledgeBase> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}`);
  return response.json();
}

export async function createKnowledgeBase(
  name: string,
  description?: string
): Promise<KnowledgeBase> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}`);
  }
  return response.json();
}

export async function updateKnowledgeBase(
  kbId: string,
  name?: string,
  description?: string
): Promise<KnowledgeBase> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  return response.json();
}

export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}`, {
    method: "DELETE",
  });
}

export async function listDocuments(kbId: string): Promise<Document[]> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}/documents`);
  return response.json();
}

export async function uploadDocument(
  kbId: string,
  file: File
): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail ?? `HTTP ${response.status}`);
  }
  return response.json();
}

export async function deleteDocument(
  kbId: string,
  docId: string
): Promise<void> {
  await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}/documents/${docId}`, {
    method: "DELETE",
  });
}

export async function reindexDocument(
  kbId: string,
  docId: string
): Promise<Document> {
  const response = await fetch(
    `${getBackendBaseURL()}/api/knowledge/${kbId}/documents/${docId}/reindex`,
    { method: "POST" }
  );
  return response.json();
}

export async function searchKnowledgeBase(
  kbId: string,
  query: string,
  topK = 5,
  similarityThreshold = 0.7
): Promise<SearchResponse> {
  const response = await fetch(`${getBackendBaseURL()}/api/knowledge/${kbId}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, similarity_threshold: similarityThreshold }),
  });
  return response.json();
}
