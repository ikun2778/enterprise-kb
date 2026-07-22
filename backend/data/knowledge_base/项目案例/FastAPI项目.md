# FastAPI项目实战案例

## 高性能API网关

### 项目背景

微服务架构下，需要一个统一的API网关处理请求路由、认证鉴权、限流熔断等横切关注点。需要构建一个高性能、可扩展的API网关。

### 技术架构

```
客户端请求
    ↓
FastAPI网关
├── 认证中间件
├── 限流中间件
├── 日志中间件
    ↓
路由分发
    ↓
后端服务
    ↓
响应处理
    ↓
返回客户端
```

### 核心实现

#### 中间件设计

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # 认证逻辑
    token = request.headers.get("Authorization")
    if not validate_token(token):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    response = await call_next(request)
    return response
```

#### 路由配置

使用配置文件定义路由规则：

```python
routes = [
    {"path": "/api/users", "target": "http://user-service:8001"},
    {"path": "/api/orders", "target": "http://order-service:8002"},
]
```

#### 限流实现

使用令牌桶算法实现限流：

```python
class RateLimiter:
    def __init__(self, rate: int, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_time = time.time()

    async def acquire(self):
        now = time.time()
        self.tokens = min(self.capacity, self.tokens + (now - self.last_time) * self.rate)
        self.last_time = now
        if self.tokens < 1:
            raise HTTPException(status_code=429)
        self.tokens -= 1
```

### 优化经验

#### 性能优化

- 异步处理：全链路异步
- 连接池：复用HTTP连接
- 缓存机制：缓存路由配置
- 批量处理：合并多个请求

#### 可靠性

- 熔断机制：后端服务故障时快速失败
- 重试策略：对临时失败进行重试
- 超时控制：设置合理的超时时间
- 降级方案：提供默认响应

## 实时数据处理平台

### 项目背景

需要构建一个实时数据处理平台，能够接收、处理和分析实时数据流，提供实时的监控和告警功能。

### 技术架构

```
数据源
    ↓
FastAPI接收接口
    ↓
消息队列（Redis/Kafka）
    ↓
处理引擎
    ↓
存储层
    ↓
查询接口
    ↓
前端展示
```

### 核心实现

#### 数据接收

```python
@app.post("/api/data/ingest")
async def ingest_data(data: DataModel):
    # 验证数据
    validate(data)
    # 发送到消息队列
    await redis.lpush("data_queue", json.dumps(data.dict()))
    return {"status": "accepted"}
```

#### 实时查询

使用WebSocket实现实时数据推送：

```python
@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await get_realtime_data()
        await websocket.send_json(data)
        await asyncio.sleep(1)
```

#### 告警系统

```python
async def check_alerts(data):
    if data["value"] > threshold:
        await send_alert(
            channel="email",
            to="admin@example.com",
            subject="数据告警",
            body=f"数据超过阈值: {data['value']}"
        )
```

### 优化经验

#### 性能优化

- 异步IO：全链路异步处理
- 批量写入：减少数据库写入次数
- 缓存机制：缓存热点数据
- 索引优化：优化查询索引

#### 可扩展性

- 水平扩展：支持多实例部署
- 分片处理：数据分片并行处理
- 消息队列：解耦数据接收和处理

## 微服务通信框架

### 项目背景

微服务架构下，服务间通信复杂，需要一个统一的通信框架处理服务发现、负载均衡、故障恢复等问题。

### 技术架构

```
服务A
    ↓
通信客户端
    ↓
服务发现
    ↓
负载均衡
    ↓
服务B
```

### 核心实现

#### 服务发现

```python
class ServiceRegistry:
    def __init__(self):
        self.services = {}

    async def register(self, name: str, host: str, port: int):
        if name not in self.services:
            self.services[name] = []
        self.services[name].append({"host": host, "port": port})

    async def discover(self, name: str) -> dict:
        if name not in self.services:
            raise ValueError(f"Service {name} not found")
        return random.choice(self.services[name])
```

#### 负载均衡

```python
class LoadBalancer:
    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.index = 0

    def select(self, instances: list) -> dict:
        if self.strategy == "round_robin":
            instance = instances[self.index % len(instances)]
            self.index += 1
            return instance
        elif self.strategy == "random":
            return random.choice(instances)
```

#### 故障恢复

```python
async def call_with_retry(func, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(delay * (2 ** attempt))
```

### 优化经验

#### 性能优化

- 连接池：复用HTTP连接
- 批量请求：合并多个请求
- 缓存机制：缓存服务地址
- 异步调用：并行处理多个请求

#### 可靠性

- 健康检查：定期检查服务状态
- 熔断机制：快速失败保护
- 重试策略：智能重试
- 降级方案：提供默认响应

#### 可观测性

- 链路追踪：跟踪请求链路
- 指标收集：收集性能指标
- 日志聚合：统一日志管理
- 告警机制：异常情况告警
