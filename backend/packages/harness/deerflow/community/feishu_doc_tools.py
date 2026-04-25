"""
Feishu Doc Tools - Read and search Feishu cloud documents.
"""

import logging

from langchain.tools import tool

from .feishu_utils import _error_response, _get_feishu_client, _ok_response

logger = logging.getLogger(__name__)


@tool("feishu_doc_read", parse_docstring=True)
def feishu_doc_read(document_id: str) -> str:
    """Read content from a Feishu cloud document.

    Args:
        document_id: The document ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        from lark_oapi.api.docx.v1.model.raw_content_document_request import RawContentDocumentRequest

        resp = client.docx.v1.document.raw_content(RawContentDocumentRequest.builder().document_id(document_id).build())
        if not resp.success():
            return _error_response(f"Failed to read doc: code={resp.code}, msg={resp.msg}")

        content = getattr(resp.data, "content", "") if resp.data else ""
        return _ok_response(
            {
                "document_id": document_id,
                "content": content,
            }
        )
    except Exception as e:
        logger.error("[feishu_doc_read] error: %s", e)
        return _error_response(str(e))


@tool("feishu_doc_search", parse_docstring=True)
def feishu_doc_search(query: str, count: int = 10) -> str:
    """Search Feishu cloud documents.

    Args:
        query: Search keyword (required).
        count: Number of results (1-50, default 10).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    count = max(1, min(count, 50))

    try:
        from lark_oapi.api.search.v2.model.search_doc_wiki_request import SearchDocWikiRequest
        from lark_oapi.api.search.v2.model.search_doc_wiki_request_body import SearchDocWikiRequestBody

        body = SearchDocWikiRequestBody.builder().query(query).page_size(count).build()
        resp = client.search.v2.doc_wiki.search(SearchDocWikiRequest.builder().request_body(body).build())
        if not resp.success():
            return _error_response(f"Failed to search docs: code={resp.code}, msg={resp.msg}")

        data = resp.data
        items = getattr(data, "items", []) if data else []
        documents = [
            {
                "document_id": getattr(item, "document_id", ""),
                "title": getattr(item, "title", ""),
            }
            for item in items
        ]
        return _ok_response(
            {
                "query": query,
                "count": len(documents),
                "documents": documents,
            }
        )
    except Exception as e:
        logger.error("[feishu_doc_search] error: %s", e)
        return _error_response(str(e))


@tool("feishu_doc_meta", parse_docstring=True)
def feishu_doc_meta(document_id: str) -> str:
    """Get metadata of a Feishu cloud document.

    Args:
        document_id: The document ID (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    try:
        from lark_oapi.api.docx.v1.model.get_document_request import GetDocumentRequest

        resp = client.docx.v1.document.get(GetDocumentRequest.builder().document_id(document_id).build())
        if not resp.success():
            return _error_response(f"Failed to get doc metadata: code={resp.code}, msg={resp.msg}")

        doc = getattr(resp.data, "document", None) if resp.data else None
        return _ok_response(
            {
                "document_id": document_id,
                "title": getattr(doc, "title", "") if doc else "",
                "owner": getattr(doc, "owner", "") if doc else "",
                "created_time": getattr(doc, "created_time", "") if doc else "",
                "updated_time": getattr(doc, "updated_time", "") if doc else "",
            }
        )
    except Exception as e:
        logger.error("[feishu_doc_meta] error: %s", e)
        return _error_response(str(e))


@tool("feishu_doc_create", parse_docstring=True)
def feishu_doc_create(folder_token: str, title: str) -> str:
    """Create a new Feishu cloud document.

    Args:
        folder_token: The folder token to create document in (required).
        title: Document title (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not folder_token.strip():
        return _error_response("folder_token is required")
    if not title.strip():
        return _error_response("title is required")

    try:
        from lark_oapi.api.docx.v1.model.create_document_request import CreateDocumentRequest
        from lark_oapi.api.docx.v1.model.create_document_request_body import CreateDocumentRequestBody

        body = CreateDocumentRequestBody.builder().folder_token(folder_token).title(title).build()
        request = CreateDocumentRequest.builder().request_body(body).build()
        resp = client.docx.v1.document.create(request)
        if not resp.success():
            return _error_response(f"Failed to create doc: code={resp.code}, msg={resp.msg}")

        doc = getattr(resp.data, "document", None) if resp.data else None
        return _ok_response(
            {
                "document_id": getattr(doc, "document_id", "") if doc else "",
                "title": getattr(doc, "title", "") if doc else "",
            }
        )
    except Exception as e:
        logger.error("[feishu_doc_create] error: %s", e)
        return _error_response(str(e))


@tool("feishu_doc_write", parse_docstring=True)
def feishu_doc_write(document_id: str, content: str) -> str:
    """Write text content to a Feishu cloud document.

    Args:
        document_id: The document ID to write to (required).
        content: Text content to write (required).
    """
    client = _get_feishu_client()
    if client is None:
        return _error_response("Feishu client not available")

    if not document_id.strip():
        return _error_response("document_id is required")
    if not content.strip():
        return _error_response("content is required")

    try:
        from lark_oapi.api.docx.v1.model.block import Block
        from lark_oapi.api.docx.v1.model.create_document_block_children_request import CreateDocumentBlockChildrenRequest
        from lark_oapi.api.docx.v1.model.create_document_block_children_request_body import CreateDocumentBlockChildrenRequestBody
        from lark_oapi.api.docx.v1.model.text import Text
        from lark_oapi.api.docx.v1.model.text_element import TextElement
        from lark_oapi.api.docx.v1.model.text_run import TextRun

        text_run = TextRun.builder().content(content).build()
        text_element = TextElement.builder().text_run(text_run).build()
        text = Text.builder().elements([text_element]).build()
        block = Block.builder().block_type(2).text(text).build()

        body = CreateDocumentBlockChildrenRequestBody.builder().children([block]).index(-1).build()
        request = CreateDocumentBlockChildrenRequest.builder().document_id(document_id).block_id(document_id).request_body(body).build()
        resp = client.docx.v1.document_block_children.create(request)
        if not resp.success():
            return _error_response(f"Failed to write doc: code={resp.code}, msg={resp.msg}")

        return _ok_response(
            {
                "document_id": document_id,
                "blocks_created": len(getattr(resp.data, "children", [])),
            }
        )
    except Exception as e:
        logger.error("[feishu_doc_write] error: %s", e)
        return _error_response(str(e))
