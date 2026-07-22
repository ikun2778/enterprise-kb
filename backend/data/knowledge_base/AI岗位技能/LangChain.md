# LangChain开发指南

## LangChain简介

LangChain是目前最流行的LLM应用开发框架，提供了构建AI应用所需的全套组件。它抽象了LLM调用、提示管理、链式调用、工具集成等核心功能。

核心优势：
- 统一的LLM接口：支持OpenAI、Claude、Moonshot等多种模型
- 丰富的组件生态：文档加载、向量存储、工具集成
- 灵活的编排方式：Chain、Agent、Runnable等多种模式
- 活跃的社区支持：持续更新，文档完善

## 核心组件

### Prompt模板

PromptTemplate用于管理提示词：

```python
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}"),
    ("human", "{question}")
])
```

### 输出解析器

将LLM输出转换为结构化数据：

- StrOutputParser：输出纯字符串
- JsonOutputParser：输出JSON对象
- PydanticOutputParser：输出Pydantic模型

### 文档加载器

支持多种数据源：

- TextLoader：加载文本文件
- PDFPlumberLoader：加载PDF文件
- WebBaseLoader：加载网页内容
- CSVLoader：加载CSV数据

### 文本分割器

将长文档切分为小块：

- RecursiveCharacterTextSplitter：递归分割，推荐使用
- MarkdownHeaderTextSplitter：按Markdown标题分割
- TokenTextSplitter：按Token数分割

### 向量存储

FAISS的LangChain集成：

```python
from langchain_community.vectorstores import FAISS

vectorstore = FAISS.from_documents(docs, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
```

## Runnable接口

LangChain的Runnable接口是其核心抽象，所有组件都实现了这个接口。

### 基本操作

- invoke：单次调用
- batch：批量调用
- stream：流式调用

### 链式组合

使用管道操作符组合组件：

```python
chain = prompt | llm | StrOutputParser()
result = chain.invoke({"question": "什么是RAG"})
```

### 并行执行

使用RunnableParallel并行执行多个操作：

```python
from langchain_core.runnables import RunnableParallel

parallel = RunnableParallel(
    summary=summary_chain,
    keywords=keywords_chain
)
```

## 实用开发模式

### RAG Chain

构建检索增强生成链：

```python
def build_rag_chain(retriever, llm):
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain
```

### 多轮对话

使用消息历史管理对话：

```python
from langchain_core.messages import HumanMessage, AIMessage

history = [
    HumanMessage(content="你好"),
    AIMessage(content="你好！有什么可以帮助你的？")
]
```

### 流式输出

```python
for chunk in chain.stream({"question": "什么是RAG"}):
    print(chunk, end="", flush=True)
```

## 常见问题

### 中文支持

- 选择支持中文的Embedding模型（如BGE）
- 分割器使用中文标点作为分隔符
- Prompt中明确要求使用中文回答

### 性能优化

- 使用Prompt Caching减少重复计算
- 批量处理多个查询
- 异步调用提高并发性能
- 合理设置top_k避免过多检索

### 错误处理

- 捕获API调用异常
- 设置合理的超时时间
- 实现重试机制
- 记录详细的错误日志
