# Milvus向量数据库指南

## Milvus简介

Milvus是一个开源的分布式向量数据库，专为大规模向量相似性搜索而设计。相比FAISS，Milvus更适合生产环境。

核心优势：
- 分布式架构：支持水平扩展
- 高可用性：支持故障恢复
- 丰富功能：支持多种索引和距离度量
- 云原生：支持Kubernetes部署

## 基本使用

### 安装

```bash
pip install pymilvus
```

### 连接

```python
from pymilvus import connections

connections.connect("default", host="localhost", port="19530")
```

### 创建集合

```python
from pymilvus import CollectionSchema, FieldSchema, DataType

# 定义字段
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768)
]

schema = CollectionSchema(fields)
collection = Collection("documents", schema)
```

### 插入数据

```python
import numpy as np

data = [
    ["文档1", "文档2", "文档3"],
    np.random.random((3, 768)).tolist()
]

collection.insert(data)
```

### 创建索引

```python
index_params = {
    "index_type": "IVF_FLAT",
    "metric_type": "L2",
    "params": {"nlist": 1024}
}

collection.create_index("embedding", index_params)
```

### 搜索

```python
collection.load()

search_params = {"metric_type": "L2", "params": {"nprobe": 16}}
query_vector = np.random.random((1, 768)).tolist()

results = collection.search(
    data=query_vector,
    anns_field="embedding",
    param=search_params,
    limit=10,
    output_fields=["text"]
)
```

## 索引类型

### FLAT

精确搜索，适合小规模数据。

### IVF_FLAT

倒排索引，平衡精度和速度。

### IVF_SQ8

标量量化，减少内存占用。

### IVF_PQ

乘积量化，进一步压缩。

### HNSW

图索引，查询速度快，适合高维数据。

## 与LangChain集成

```python
from langchain_community.vectorstores import Milvus

vectorstore = Milvus.from_documents(
    docs,
    embeddings,
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="documents"
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

## 部署方式

### Docker Compose

```yaml
version: '3.5'

services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.0
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296

  minio:
    image: minio/minio:RELEASE.2020-12-03T00-03-10Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin

  standalone:
    image: milvusdb/milvus:latest
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    ports:
      - "19530:19530"
```

### Kubernetes

使用Helm Chart部署：

```bash
helm repo add milvus https://milvus-io/milvus-helm
helm install my-milvus milvus/milvus
```

## 性能优化

### 批量操作

- 批量插入数据
- 批量查询
- 使用分区管理数据

### 索引选择

- 小规模数据：FLAT
- 中等规模：IVF_FLAT
- 大规模高维：HNSW
- 内存受限：IVF_PQ

### 查询优化

- 合理设置nprobe
- 使用过滤条件缩小范围
- 调整搜索参数

## 常见问题

### 连接问题

- 检查Milvus服务状态
- 验证网络配置
- 检查防火墙设置

### 性能问题

- 选择合适的索引类型
- 优化查询参数
- 增加资源分配

### 数据一致性

- 使用事务保证一致性
- 合理设置副本数
- 监控数据同步状态
