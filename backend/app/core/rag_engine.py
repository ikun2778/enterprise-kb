"""
RAG引擎 - 文档解析、向量化、检索、重排序
完整实现C8的所有核心功能
"""

import os
import hashlib
import logging
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# 禁用HuggingFace警告
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# 禁用FAISS的OpenMP警告
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers.bm25 import BM25Retriever

logger = logging.getLogger(__name__)

# 降低第三方库的日志级别
logging.getLogger("langchain_huggingface").setLevel(logging.WARNING)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("faiss").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


class RAGEngine:
    """RAG引擎核心类"""

    # 分类映射（适配CareerCopilot知识库目录结构）
    CATEGORY_MAPPING = {
        'AI岗位技能': 'AI岗位技能',
        '面试题库': '面试题库',
        '项目案例': '项目案例',
        '岗位JD': '岗位JD',
    }
    CATEGORY_LABELS = list(dict.fromkeys(CATEGORY_MAPPING.values()))

    def __init__(self, config):
        """
        初始化RAG引擎

        Args:
            config: 应用配置对象
        """
        self.config = config
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.vector_store: Optional[FAISS] = None
        self.bm25_retriever: Optional[BM25Retriever] = None
        self.documents: List[Document] = []  # 父文档（完整文档）
        self.chunks: List[Document] = []     # 子文档（分块后的文档）
        self.parent_child_map: Dict[str, str] = {}  # 子块ID -> 父文档ID

        # 初始化
        self._init_embeddings()

    def _init_embeddings(self):
        """初始化Embedding模型"""
        logger.info(f"初始化Embedding模型: {self.config.embedding.model_name}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embedding.model_name,
            model_kwargs={'device': self.config.embedding.device},
            encode_kwargs={'normalize_embeddings': self.config.embedding.normalize}
        )
        logger.info("Embedding模型初始化完成")

    def load_documents(self, data_path: str) -> List[Document]:
        """
        加载文档

        Args:
            data_path: 数据目录路径

        Returns:
            加载的文档列表
        """
        logger.info(f"加载文档: {data_path}")
        documents = []
        data_path_obj = Path(data_path)

        if not data_path_obj.exists():
            logger.warning(f"数据路径不存在: {data_path}")
            return []

        for md_file in data_path_obj.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 生成确定性的父文档ID（基于相对路径）
                try:
                    relative_path = md_file.relative_to(data_path_obj).as_posix()
                except Exception:
                    relative_path = md_file.as_posix()
                parent_id = hashlib.md5(relative_path.encode("utf-8")).hexdigest()

                # 创建父文档对象
                metadata = {
                    "source": str(md_file),
                    "parent_id": parent_id,
                    "doc_type": "parent",
                    "relative_path": relative_path,
                    "filename": md_file.name,
                }

                doc = Document(page_content=content, metadata=metadata)
                documents.append(doc)

            except Exception as e:
                logger.warning(f"加载文件失败 {md_file}: {e}")

        # 增强元数据
        for doc in documents:
            self._enhance_metadata(doc, data_path_obj)

        self.documents = documents
        logger.info(f"成功加载 {len(documents)} 个文档")
        return documents

    def _enhance_metadata(self, doc: Document, data_root: Path):
        """
        增强文档元数据

        Args:
            doc: 文档对象
            data_root: 数据根目录
        """
        file_path = Path(doc.metadata.get('source', ''))
        relative_path = doc.metadata.get('relative_path', '')

        # 提取分类
        path_parts = Path(relative_path).parts
        doc.metadata['category'] = '其他'
        for key, value in self.CATEGORY_MAPPING.items():
            if key in path_parts:
                doc.metadata['category'] = value
                break

        # 提取文档名称（从文件名）
        doc.metadata['document_name'] = file_path.stem

        # 尝试从内容中提取标题
        content = doc.page_content
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            doc.metadata['title'] = title_match.group(1).strip()
        else:
            doc.metadata['title'] = file_path.stem

    @classmethod
    def get_supported_categories(cls) -> List[str]:
        """获取支持的分类列表"""
        return cls.CATEGORY_LABELS

    def chunk_documents(self, documents: Optional[List[Document]] = None) -> List[Document]:
        """
        Markdown结构感知分块

        Args:
            documents: 待分块文档列表

        Returns:
            分块后的文档列表
        """
        docs = documents or self.documents
        if not docs:
            logger.warning("没有文档需要分块")
            return []

        logger.info("开始Markdown结构感知分块...")

        # Markdown标题分割器
        headers_to_split_on = [
            ("#", "主标题"),
            ("##", "二级标题"),
            ("###", "三级标题"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False  # 保留标题
        )

        # 备用分割器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.rag.chunk_size,
            chunk_overlap=self.config.rag.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]
        )

        all_chunks = []

        for doc in docs:
            try:
                # 对每个文档进行Markdown分割
                md_chunks = markdown_splitter.split_text(doc.page_content)

                # 如果没有分割成功，说明文档可能没有标题结构
                if len(md_chunks) <= 1:
                    logger.warning(f"文档 {doc.metadata.get('document_name', '未知')} 未能按标题分割")

                # 为每个子块建立与父文档的关系
                parent_id = doc.metadata["parent_id"]

                for i, chunk in enumerate(md_chunks):
                    # 为子块分配唯一ID
                    child_id = str(uuid.uuid4())

                    # 合并原文档元数据和新的标题元数据
                    chunk.metadata.update(doc.metadata)
                    chunk.metadata.update({
                        "chunk_id": child_id,
                        "parent_id": parent_id,
                        "doc_type": "child",
                        "chunk_index": i
                    })

                    # 建立父子映射关系
                    self.parent_child_map[child_id] = parent_id

                all_chunks.extend(md_chunks)

            except Exception as e:
                logger.warning(f"文档 {doc.metadata.get('source', '未知')} Markdown分割失败: {e}")
                # 如果Markdown分割失败，使用备用分割器
                fallback_chunks = text_splitter.split_documents([doc])
                for chunk in fallback_chunks:
                    chunk.metadata["chunk_id"] = str(uuid.uuid4())
                    chunk.metadata["parent_id"] = doc.metadata["parent_id"]
                    chunk.metadata["doc_type"] = "child"
                all_chunks.extend(fallback_chunks)

        # 为每个chunk添加基础元数据
        for i, chunk in enumerate(all_chunks):
            if 'chunk_id' not in chunk.metadata:
                chunk.metadata['chunk_id'] = str(uuid.uuid4())
            chunk.metadata['batch_index'] = i
            chunk.metadata['chunk_size'] = len(chunk.page_content)

        self.chunks = all_chunks
        logger.info(f"Markdown分块完成，共生成 {len(all_chunks)} 个chunk")
        return all_chunks

    def get_parent_documents(self, child_chunks: List[Document]) -> List[Document]:
        """
        根据子块获取对应的父文档（智能去重）

        Args:
            child_chunks: 检索到的子块列表

        Returns:
            对应的父文档列表（去重，按相关性排序）
        """
        # 统计每个父文档被匹配的次数（相关性指标）
        parent_relevance: Dict[str, int] = {}
        parent_docs_map: Dict[str, Document] = {}

        # 收集所有相关的父文档ID和相关性分数
        for chunk in child_chunks:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id:
                # 增加相关性计数
                parent_relevance[parent_id] = parent_relevance.get(parent_id, 0) + 1

                # 缓存父文档
                if parent_id not in parent_docs_map:
                    for doc in self.documents:
                        if doc.metadata.get("parent_id") == parent_id:
                            parent_docs_map[parent_id] = doc
                            break

        # 按相关性排序（匹配次数多的排在前面）
        sorted_parent_ids = sorted(
            parent_relevance.keys(),
            key=lambda x: parent_relevance[x],
            reverse=True
        )

        # 构建去重后的父文档列表
        parent_docs = []
        for parent_id in sorted_parent_ids:
            if parent_id in parent_docs_map:
                parent_docs.append(parent_docs_map[parent_id])

        # 收集父文档名称和相关性信息用于日志
        parent_info = []
        for doc in parent_docs:
            doc_name = doc.metadata.get('document_name', '未知文档')
            parent_id = doc.metadata.get('parent_id')
            relevance_count = parent_relevance.get(parent_id, 0)
            parent_info.append(f"{doc_name}({relevance_count}块)")

        logger.info(f"从 {len(child_chunks)} 个子块中找到 {len(parent_docs)} 个去重父文档: {', '.join(parent_info)}")
        return parent_docs

    def build_vector_store(self, chunks: Optional[List[Document]] = None) -> FAISS:
        """
        构建向量索引

        Args:
            chunks: 文档块列表

        Returns:
            FAISS向量存储
        """
        docs = chunks or self.chunks
        if not docs:
            raise ValueError("没有文档块可以索引")

        logger.info(f"构建向量索引，共 {len(docs)} 个文档块...")
        self.vector_store = FAISS.from_documents(
            documents=docs,
            embedding=self.embeddings
        )
        logger.info("向量索引构建完成")
        return self.vector_store

    def build_bm25_retriever(self, chunks: Optional[List[Document]] = None):
        """
        构建BM25检索器

        Args:
            chunks: 文档块列表
        """
        docs = chunks or self.chunks
        if not docs:
            raise ValueError("没有文档块可以索引")

        logger.info("构建BM25检索器...")
        self.bm25_retriever = BM25Retriever.from_documents(docs, k=self.config.rag.top_k)
        logger.info("BM25检索器构建完成")

    def save_vector_store(self, path: Optional[str] = None):
        """保存向量索引"""
        save_path = path or self.config.vector_store.persist_dir
        if not self.vector_store:
            raise ValueError("向量索引未构建")

        Path(save_path).mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(save_path)
        logger.info(f"向量索引已保存到: {save_path}")

    def load_vector_store(self, path: Optional[str] = None) -> bool:
        """
        加载向量索引

        Returns:
            是否加载成功
        """
        load_path = path or self.config.vector_store.persist_dir
        index_path = Path(load_path)
        index_file = index_path / "index.faiss"

        # 先检查索引文件是否存在，避免不必要的错误日志
        if not index_file.exists():
            logger.info("向量索引文件不存在，需要重新构建")
            return False

        try:
            self.vector_store = FAISS.load_local(
                load_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info(f"向量索引已从 {load_path} 加载")
            return True
        except Exception as e:
            logger.warning(f"加载向量索引失败: {e}，将构建新索引")
            return False

    def hybrid_search(self, query: str, top_k: Optional[int] = None) -> List[Document]:
        """
        混合检索 - 向量检索 + BM25 + RRF重排序

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            检索到的文档列表
        """
        k = top_k or self.config.rag.top_k

        if not self.vector_store:
            raise ValueError("向量索引未构建")

        # 向量检索
        vector_retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k * 2}
        )
        vector_docs = vector_retriever.invoke(query)

        # BM25检索
        bm25_docs = []
        if self.bm25_retriever:
            bm25_docs = self.bm25_retriever.invoke(query)

        # RRF重排序
        reranked_docs = self._rrf_rerank(vector_docs, bm25_docs)

        return reranked_docs[:k]

    def metadata_filtered_search(
        self,
        query: str,
        filters: Dict[str, Any],
        top_k: Optional[int] = None
    ) -> List[Document]:
        """
        带元数据过滤的检索

        Args:
            query: 查询文本
            filters: 元数据过滤条件
            top_k: 返回结果数量

        Returns:
            过滤后的文档列表
        """
        k = top_k or self.config.rag.top_k

        # 先进行混合检索，获取更多候选
        docs = self.hybrid_search(query, k * 3)

        # 应用元数据过滤
        filtered_docs = []
        for doc in docs:
            match = True
            for key, value in filters.items():
                if key in doc.metadata:
                    if isinstance(value, list):
                        if doc.metadata[key] not in value:
                            match = False
                            break
                    else:
                        if doc.metadata[key] != value:
                            match = False
                            break
                else:
                    match = False
                    break

            if match:
                filtered_docs.append(doc)
                if len(filtered_docs) >= k:
                    break

        return filtered_docs

    def _rrf_rerank(
        self,
        vector_docs: List[Document],
        bm25_docs: List[Document],
        k: int = 60
    ) -> List[Document]:
        """
        RRF重排序算法

        Args:
            vector_docs: 向量检索结果
            bm25_docs: BM25检索结果
            k: RRF参数

        Returns:
            重排序后的文档列表
        """
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}

        # 处理向量检索结果
        for rank, doc in enumerate(vector_docs):
            doc_id = self._get_doc_id(doc)
            doc_map[doc_id] = doc
            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        # 处理BM25检索结果
        for rank, doc in enumerate(bm25_docs):
            doc_id = self._get_doc_id(doc)
            doc_map[doc_id] = doc
            rrf_score = 1.0 / (k + rank + 1)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score

        # 按分数排序
        sorted_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        result = []
        for doc_id in sorted_ids:
            if doc_id in doc_map:
                doc = doc_map[doc_id]
                doc.metadata['rrf_score'] = doc_scores[doc_id]
                result.append(doc)

        return result

    def _get_doc_id(self, doc: Document) -> str:
        """生成文档唯一标识"""
        content_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
        return content_hash

    def filter_documents_by_category(self, category: str) -> List[Document]:
        """
        按分类过滤文档

        Args:
            category: 分类名称

        Returns:
            过滤后的文档列表
        """
        return [doc for doc in self.documents if doc.metadata.get('category') == category]

    def initialize(self, data_path: str, force_rebuild: bool = False):
        """
        初始化RAG引擎

        Args:
            data_path: 数据目录路径
            force_rebuild: 是否强制重建索引
        """
        logger.info("初始化RAG引擎...")

        # 尝试加载已有索引
        if not force_rebuild and self.load_vector_store():
            logger.info("使用已有向量索引")
            # 仍需加载文档用于BM25和父文档查询
            self.load_documents(data_path)
            self.chunk_documents()
            self.build_bm25_retriever()
        else:
            # 重新构建索引
            self.load_documents(data_path)
            self.chunk_documents()
            self.build_vector_store()
            self.build_bm25_retriever()
            self.save_vector_store()

        logger.info("RAG引擎初始化完成")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 统计分类分布
        categories = {}
        for doc in self.documents:
            category = doc.metadata.get('category', '未知')
            categories[category] = categories.get(category, 0) + 1

        return {
            "document_count": len(self.documents),
            "chunk_count": len(self.chunks),
            "vector_store_ready": self.vector_store is not None,
            "bm25_ready": self.bm25_retriever is not None,
            "categories": categories,
        }
