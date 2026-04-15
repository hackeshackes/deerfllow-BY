from pydantic import BaseModel, Field


class UploadConfig(BaseModel):
    pdf_converter: str = Field(
        default="auto",
        description="PDF-to-Markdown converter: auto/pymupdf4llm/markitdown",
    )
