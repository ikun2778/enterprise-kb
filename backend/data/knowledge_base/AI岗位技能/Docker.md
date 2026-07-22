# Docker开发指南

## Docker简介

Docker是一个开源的容器化平台，用于自动化应用程序的部署、扩展和管理。它将应用及其依赖打包到一个轻量级、可移植的容器中。

核心概念：
- 镜像（Image）：应用的只读模板
- 容器（Container）：镜像的运行实例
- 仓库（Registry）：存储和分发镜像的服务

## 基础命令

### 镜像操作

```bash
# 拉取镜像
docker pull python:3.11-slim

# 构建镜像
docker build -t myapp:latest .

# 查看镜像
docker images

# 删除镜像
docker rmi myapp:latest
```

### 容器操作

```bash
# 运行容器
docker run -d -p 8000:8000 --name myapp myapp:latest

# 查看容器
docker ps

# 停止容器
docker stop myapp

# 删除容器
docker rm myapp

# 查看日志
docker logs myapp
```

## Dockerfile编写

### Python应用示例

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 多阶段构建

```dockerfile
# 构建阶段
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# 运行阶段
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "app.main:app"]
```

## Docker Compose

用于定义和运行多容器应用：

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - MOONSHOT_API_KEY=${MOONSHOT_API_KEY}
    restart: unless-stopped
```

### 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 数据持久化

### Volume

```bash
# 创建Volume
docker volume create mydata

# 使用Volume
docker run -v mydata:/app/data myapp:latest
```

### Bind Mount

```bash
# 挂载主机目录
docker run -v /host/path:/container/path myapp:latest
```

## 网络配置

### 创建网络

```bash
docker network create mynet
```

### 连接网络

```bash
docker run --network mynet --name app1 myapp:latest
```

## 最佳实践

### 镜像优化

- 使用slim基础镜像
- 合并RUN指令减少层数
- 使用.dockerignore排除不需要的文件
- 多阶段构建减小最终镜像大小

### 安全性

- 不要以root用户运行
- 定期更新基础镜像
- 扫描镜像漏洞
- 使用secrets管理敏感信息

### 性能

- 合理使用缓存
- 限制容器资源
- 使用健康检查
- 配置合理的重启策略
