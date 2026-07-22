"""
统一文件解析器 - 支持 PDF / Markdown / TXT
"""

import logging
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class FileParser:
    """统一文件解析器，将 PDF/MD/TXT 转换为 LangChain Document"""

    SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def parse(cls, file_path: str, encoding: str = "utf-8") -> Document:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            content = cls._parse_pdf(path)
        elif suffix in (".md", ".markdown"):
            content = cls._parse_text(path, encoding)
        elif suffix == ".txt":
            content = cls._parse_text(path, encoding)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

        return Document(
            page_content=content,
            metadata={
                "source": str(path),
                "filename": path.name,
                "file_type": suffix.lstrip("."),
                "file_size": path.stat().st_size,
            },
        )

    @classmethod
    def parse_bytes(
        cls, content: bytes, filename: str, encoding: str = "utf-8"
    ) -> Document:
        suffix = Path(filename).suffix.lower()
        if suffix == ".pdf":
            text = cls._parse_pdf_bytes(content)
        elif suffix in (".md", ".markdown", ".txt"):
            text = content.decode(encoding)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

        return Document(
            page_content=text,
            metadata={
                "filename": filename,
                "file_type": suffix.lstrip("."),
                "file_size": len(content),
            },
        )

    @staticmethod
    def _parse_pdf(path: Path) -> str:
        doc = fitz.open(str(path))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)

    @staticmethod
    def _parse_pdf_bytes(content: bytes) -> str:
        doc = fitz.open(stream=content, filetype="pdf")
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)

    @staticmethod
    def _parse_text(path: Path, encoding: str = "utf-8") -> str:
        return path.read_text(encoding=encoding)
