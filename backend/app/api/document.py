"""
文档管理API接口
"""

import uuid
import logging
import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File

from ..models.schemas import ApiResponse
from ..config import UPLOAD_DIR, KNOWLEDGE_BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["文档"])

# 全局RAG引擎实例
rag_engine = None

# 文档存储（简单实现，生产环境应使用数据库）
documents_store = {}


def init_document_router(rag_engine_instance):
    """初始化文档路由"""
    global rag_engine
    rag_engine = rag_engine_instance


@router.get("/supported-types")
async def get_supported_types():
    """获取支持的文件类型"""
    return ApiResponse(data={
        "extensions": [".md", ".txt", ".pdf", ".docx"],
        "descriptions": {
            ".md": "Markdown文档",
            ".txt": "纯文本文件",
            ".pdf": "PDF文档",
            ".docx": "Word文档"
        }
    })


@router.post("/upload", response_model=ApiResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档到知识库

    Args:
        file: 上传的文件

    Returns:
        上传结果
    """
    # 检查文件类型
    allowed_extensions = {".md", ".txt"}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，支持: {', '.join(allowed_extensions)}"
        )

    try:
        # 生成文档ID
        doc_id = str(uuid.uuid4())

        # 保存文件到知识库目录（直接放入knowledge_base）
        target_dir = KNOWLEDGE_BASE_DIR / "uploads"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / file.filename

        content = await file.read()

        with open(file_path, "wb") as f:
            f.write(content)

        # 记录文档信息
        doc_info = {
            "id": doc_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "status": "uploaded"
        }
        documents_store[doc_id] = doc_info

        logger.info(f"文档上传成功: {file.filename}")

        return ApiResponse(
            message="文档上传成功，如需立即生效请重建索引",
            data=doc_info
        )

    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/list")
async def list_documents():
    """获取文档列表"""
    docs = list(documents_store.values())
    return ApiResponse(data=docs)


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """获取文档详情"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="文档不存在")

    return ApiResponse(data=documents_store[doc_id])


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    if doc_id not in documents_store:
        raise HTTPException(status_code=404, detail="文档不存在")

    doc_info = documents_store[doc_id]

    # 删除文件
    file_path = Path(doc_info["file_path"])
    if file_path.exists():
        file_path.unlink()

    # 从存储中删除
    del documents_store[doc_id]

    logger.info(f"文档已删除: {doc_info['filename']}")
    return ApiResponse(message="文档已删除")
