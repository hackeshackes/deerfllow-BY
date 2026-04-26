"""Document processor for parsing and chunking files for RAG."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk_text_content = text[start:end]
        chunks.append({
            "content": chunk_text_content,
            "start": start,
            "end": end,
            "index": len(chunks)
        })
        if end >= text_len:
            break
        start = end - overlap
    return chunks


async def process_pdf(file_path: str) -> list[dict]:
    try:
        import fitz
        doc = fitz.open(file_path)
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            full_text += f"\n--- Page {page_num + 1} ---\n{text}"
        doc.close()
        chunks = chunk_text(full_text)
        for chunk in chunks:
            chunk["metadata"] = {"source": file_path, "type": "pdf"}
        return chunks
    except ImportError:
        logger.warning("PyMuPDF not installed, cannot process PDF")
        return [{"content": "[PDF content unavailable - PyMuPDF not installed]", "metadata": {"source": file_path, "type": "pdf"}}]
    except Exception as e:
        logger.error(f"Failed to process PDF {file_path}: {e}")
        return []


async def process_docx(file_path: str) -> list[dict]:
    try:
        from docx import Document
        doc = Document(file_path)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        chunks = chunk_text(full_text)
        for chunk in chunks:
            chunk["metadata"] = {"source": file_path, "type": "docx"}
        return chunks
    except ImportError:
        logger.warning("python-docx not installed, cannot process DOCX")
        return [{"content": "[DOCX content unavailable - python-docx not installed]", "metadata": {"source": file_path, "type": "docx"}}]
    except Exception as e:
        logger.error(f"Failed to process DOCX {file_path}: {e}")
        return []


async def process_txt(file_path: str) -> list[dict]:
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_text(content)
        for chunk in chunks:
            chunk["metadata"] = {"source": file_path, "type": "txt"}
        return chunks
    except Exception as e:
        logger.error(f"Failed to process TXT {file_path}: {e}")
        return []


async def process_csv(file_path: str) -> list[dict]:
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        content = df.to_string()
        chunks = chunk_text(content)
        for chunk in chunks:
            chunk["metadata"] = {"source": file_path, "type": "csv", "rows": len(df)}
        return chunks
    except ImportError:
        logger.warning("pandas not installed, cannot process CSV")
        return [{"content": "[CSV content unavailable - pandas not installed]", "metadata": {"source": file_path, "type": "csv"}}]
    except Exception as e:
        logger.error(f"Failed to process CSV {file_path}: {e}")
        return []


async def process_markdown(file_path: str) -> list[dict]:
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        chunks = chunk_text(content)
        for chunk in chunks:
            chunk["metadata"] = {"source": file_path, "type": "md"}
        return chunks
    except Exception as e:
        logger.error(f"Failed to process MD {file_path}: {e}")
        return []


async def process_document(
    file_path: str,
    file_type: str,
) -> list[dict]:
    if file_type == "pdf":
        return await process_pdf(file_path)
    elif file_type == "docx":
        return await process_docx(file_path)
    elif file_type == "txt":
        return await process_txt(file_path)
    elif file_type == "md":
        return await process_markdown(file_path)
    elif file_type == "csv":
        return await process_csv(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_type}")
        return []


def estimate_tokens(text: str) -> int:
    return len(text) // 4


class DocumentProcessor:
    def __init__(self, kb_id: str, doc_id: str):
        self.kb_id = kb_id
        self.doc_id = doc_id
        self.chunks: list[dict] = []
        self.total_tokens = 0

    async def process_file(self, file_path: str, file_type: str) -> bool:
        try:
            self.chunks = await process_document(file_path, file_type)
            self.total_tokens = sum(estimate_tokens(c["content"]) for c in self.chunks)
            logger.info(f"Processed document {self.doc_id}: {len(self.chunks)} chunks, ~{self.total_tokens} tokens")
            return True
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            return False

    def get_chunks(self) -> list[dict]:
        return self.chunks

    def get_chunk_with_id(self, index: int) -> dict | None:
        if 0 <= index < len(self.chunks):
            chunk = self.chunks[index]
            return {
                "id": f"{self.doc_id}_chunk_{index}",
                "content": chunk["content"],
                "metadata": chunk.get("metadata", {}),
                "token_count": estimate_tokens(chunk["content"])
            }
        return None
