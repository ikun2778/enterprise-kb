# FastAPI开发指南

## FastAPI简介

FastAPI是Python中最流行的高性能Web框架之一，专为构建API而设计。它基于Python类型注解，自动生成API文档，性能接近Node.js和Go。

核心优势：
- 高性能：基于Starlette和Pydantic，性能优秀
- 自动文档：自动生成Swagger UI和ReDoc文档
- 类型安全：使用Python类型注解，IDE支持好
- 异步支持：原生支持async/await

## 基础使用

### 创建应用

```python
from fastapi import FastAPI

app = FastAPI(title="CareerCopilot", version="2.0.0")
```

### 定义路由

```python
@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    # 处理逻辑
    return result
```

### 请求模型

使用Pydantic定义请求体：

```python
from pydantic import BaseModel, Field

class AnalyzeRequest(BaseModel):
    jd_text: str = Field(..., description="岗位JD文本")
    resume_text: str = Field(..., description="简历文本")
```

## 依赖注入

FastAPI的依赖注入系统非常强大：

```python
from fastapi import Depends

async def get_db():
    db = Database()
    try:
        yield db
    finally:
        await db.close()

@app.get("/items")
async def get_items(db = Depends(get_db)):
    return await db.get_items()
```

## 文件上传

处理文件上传：

```python
from fastapi import UploadFile, File

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}
```

## 中间件

### CORS中间件

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 生命周期管理

使用lifespan管理应用启动和关闭：

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    initialize_resources()
    yield
    # 关闭时执行
    cleanup_resources()

app = FastAPI(lifespan=lifespan)
```

## 异常处理

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]
```

## 流式响应

支持Server-Sent Events：

```python
from fastapi.responses import StreamingResponse

async def generate():
    for i in range(10):
        yield f"data: {i}\n\n"

@app.get("/stream")
async def stream():
    return StreamingResponse(generate(), media_type="text/event-stream")
```

## 最佳实践

### 项目结构

```
app/
├── main.py          # 应用入口
├── config.py        # 配置管理
├── api/             # API路由
├── core/            # 核心业务逻辑
├── models/          # 数据模型
├── services/        # 服务层
└── utils/           # 工具函数
```

### 配置管理

使用Pydantic Settings管理配置：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MyApp"
    debug: bool = False
    database_url: str

    class Config:
        env_file = ".env"
```

### 错误处理

- 使用HTTPException返回标准错误
- 定义统一的错误响应格式
- 记录详细的错误日志
- 区分客户端错误和服务器错误

### 安全性

- 使用HTTPS
- 实现请求验证
- 设置速率限制
- 使用CORS保护
- 输入数据清洗
