# FAISS向量检索指南

## FAISS简介

FAISS（Facebook AI Similarity Search）是Facebook开源的高效向量检索库，专门用于大规模向量的相似性搜索和聚类。

核心优势：
- 高性能：经过高度优化的C++实现
- GPU支持：可利用GPU加速检索
- 灵活性：支持多种索引类型
- 易用性：Python接口友好

## 基本使用

### 安装

```bash
pip install faiss-cpu  # CPU版本
pip install faiss-gpu  # GPU版本
```

### 创建索引

```python
import faiss
import numpy as np

# 维度
d = 64
# 向量数量
nb = 100000

# 随机生成向量
vectors = np.random.random((nb, d)).astype('float32')

# 创建索引
index = faiss.IndexFlatL2(d)  # L2距离
index.add(vectors)
```

### 搜索

```python
# 查询向量
k = 5  # 返回最近的5个
query = np.random.random((1, d)).astype('float32')

# 搜索
distances, indices = index.search(query, k)
```

## 索引类型

### IndexFlatL2

精确搜索，使用L2距离。适合小规模数据。

```python
index = faiss.IndexFlatL2(d)
```

### IndexFlatIP

精确搜索，使用内积（余弦相似度）。

```python
index = faiss.IndexFlatIP(d)
```

### IndexIVFFlat

倒排索引，适合大规模数据。

```python
nlist = 100  # 聚类中心数量
quantizer = faiss.IndexFlatL2(d)
index = faiss.IndexIVFFlat(quantizer, d, nlist)
index.train(vectors)
index.add(vectors)
```

### IndexIVFPQ

乘积量化，进一步压缩存储。

```python
m = 8  # 子向量数量
nbits = 8  # 每个子向量的位数
index = faiss.IndexIVFPQ(quantizer, d, nlist, m, nbits)
```

## 与LangChain集成

```python
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5")

# 从文档创建
vectorstore = FAISS.from_documents(docs, embeddings)

# 保存
vectorstore.save_local("vector_store")

# 加载
vectorstore = FAISS.load_local("vector_store", embeddings)

# 检索
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
results = retriever.invoke("查询文本")
```

## 性能优化

### 批量处理

```python
# 批量添加
batch_size = 10000
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i+batch_size]
    index.add(batch)
```

### GPU加速

```python
# 将索引移到GPU
res = faiss.StandardGpuResources()
gpu_index = faiss.index_cpu_to_gpu(res, 0, index)
```

### 预训练

对于IVF索引，需要先训练：

```python
index.train(training_vectors)
index.add(vectors)
```

## 持久化

### 保存索引

```python
faiss.write_index(index, "index.faiss")
```

### 加载索引

```python
index = faiss.read_index("index.faiss")
```

### 安全注意事项

加载外部索引时需要设置`allow_dangerous_deserialization=True`，因为FAISS索引使用pickle序列化，可能存在安全风险。

## 常见问题

### 内存不足

- 使用PQ量化减少内存占用
- 使用IVF索引减少搜索范围
- 分片存储大规模数据

### 检索质量

- 选择合适的索引类型
- 调整nlist和nprobe参数
- 使用合适的距离度量

### 性能瓶颈

- 使用GPU加速
- 批量处理查询
- 合理设置搜索参数
