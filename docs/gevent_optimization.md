# RAGFlow Gevent 优化指南

本文档说明了 RAGFlow 项目中 Gunicorn + Gevent 的优化实现，包括猴子补丁的应用和性能优化配置。

## 概述

RAGFlow 已经集成了 Gunicorn + Gevent 的生产部署方案，通过合理的猴子补丁应用，确保了异步 I/O 操作的高效执行。

## 主要优化内容

### 1. 猴子补丁管理

#### 核心补丁模块
- **文件位置**: `api/utils/gevent_patches.py`
- **功能**: 统一管理所有 gevent 猴子补丁的应用
- **补丁范围**:
  - `socket`: 网络 I/O 操作
  - `threading`: 线程操作
  - `time`: 时间相关操作（如 `time.sleep()`）
  - `select`: I/O 多路复用
  - `subprocess`: 子进程操作
  - `ssl`: SSL/TLS 操作
  - `queue`: 队列操作
  - `os`: 部分操作系统操作

#### 任务执行优化
- **文件位置**: `rag/utils/gevent_task_patches.py`
- **功能**: 为任务执行模块提供 gevent 兼容的实现
- **特性**:
  - Gevent 兼容的线程池执行器
  - Gevent 兼容的锁机制
  - 优化的 Redis 连接处理

### 2. 应用入口优化

#### WSGI 应用 (`api/wsgi.py`)
```python
# 在所有其他模块导入之前应用 gevent 补丁
from api.utils.gevent_patches import init_gevent_environment
init_gevent_environment()
```

#### 开发服务器 (`api/ragflow_server.py`)
```python
# 确保开发和生产环境的一致性
from api.utils.gevent_patches import init_gevent_environment
init_gevent_environment()
```

#### 任务执行器 (`rag/svr/task_executor.py`)
```python
# 为任务执行应用特定的 gevent 优化
from rag.utils.gevent_task_patches import init_task_gevent_environment
init_task_gevent_environment()
```

### 3. Docker 部署优化

#### 启动脚本优化
- **文件位置**: `docker/gevent_startup.py`
- **功能**: 在 Docker 容器启动时预先配置 gevent 环境
- **特性**:
  - 环境变量设置
  - DNS 解析器优化
  - 连接池配置
  - 设置验证

#### Entrypoint 集成
- **文件位置**: `docker/entrypoint.sh`
- **修改**: 在启动 Gunicorn 前运行 gevent 初始化脚本

### 4. Gunicorn 配置优化

#### 配置文件 (`conf/gunicorn.conf.py`)
```python
# Worker 配置
worker_class = 'gevent'
worker_connections = 1000
workers = min(multiprocessing.cpu_count() * 2 + 1, 16)

# 环境变量
raw_env = [
    'PYTHONPATH=/ragflow/',
    'GUNICORN_WORKER_CLASS=gevent',
    'RAGFLOW_FORCE_GEVENT=1',
]
```

## 环境变量配置

### 核心环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `RAGFLOW_FORCE_GEVENT` | `1` | 强制启用 gevent 补丁 |
| `GUNICORN_WORKER_CLASS` | `gevent` | Gunicorn worker 类型 |
| `RAGFLOW_GEVENT_PATCHED` | `1` | 标识补丁已应用 |
| `RAGFLOW_DISABLE_GEVENT` | - | 禁用 gevent（调试用） |

### 性能调优变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GUNICORN_WORKERS` | `4` | Worker 进程数 |
| `GEVENT_WORKER_CONNECTIONS` | `1000` | 每个 worker 的连接数 |
| `GEVENT_TIMEOUT` | `300` | 请求超时时间 |
| `GEVENT_KEEPALIVE` | `10` | Keep-alive 时间 |
| `REDIS_CONNECTION_POOL_MAX_CONNECTIONS` | `50` | Redis 连接池大小 |
| `DB_POOL_SIZE` | `20` | 数据库连接池大小 |

## 使用方法

### Docker 部署（推荐）

```bash
# 使用默认配置
docker run -d ragflow:latest

# 自定义 worker 数量
docker run -d -e GUNICORN_WORKERS=8 ragflow:latest

# 禁用 gevent（调试用）
docker run -d -e RAGFLOW_DISABLE_GEVENT=1 ragflow:latest
```

### 手动部署

```bash
# 使用 Gunicorn 配置文件
gunicorn --config conf/gunicorn.conf.py api.wsgi:application

# 命令行配置
gunicorn --workers 4 --worker-class gevent --bind 0.0.0.0:9380 api.wsgi:application
```

### 开发模式

```bash
# 开发服务器也会应用 gevent 补丁以保持一致性
python api/ragflow_server.py
```

## 性能优化建议

### 1. Worker 数量调优

```bash
# CPU 密集型任务
GUNICORN_WORKERS=$(nproc)

# I/O 密集型任务（推荐）
GUNICORN_WORKERS=$(($(nproc) * 2 + 1))

# 高并发场景
GUNICORN_WORKERS=16
```

### 2. 连接池优化

```bash
# Redis 连接池
REDIS_CONNECTION_POOL_MAX_CONNECTIONS=100

# 数据库连接池
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=50
```

### 3. 超时设置

```bash
# 请求超时
GUNICORN_TIMEOUT=300

# Keep-alive
GUNICORN_KEEPALIVE=10

# Worker 连接数
GEVENT_WORKER_CONNECTIONS=2000
```

## 监控和调试

### 1. 验证 Gevent 状态

```python
import os
from gevent import monkey

# 检查补丁状态
print(f"Gevent patched: {os.environ.get('RAGFLOW_GEVENT_PATCHED')}")
print(f"Socket patched: {monkey.is_module_patched('socket')}")
print(f"Threading patched: {monkey.is_module_patched('threading')}")
```

### 2. 性能监控

```bash
# 查看 worker 状态
ps aux | grep gunicorn

# 监控连接数
netstat -an | grep :9380 | wc -l

# 查看内存使用
top -p $(pgrep -f gunicorn)
```

### 3. 日志分析

```bash
# 查看 gevent 相关日志
docker logs <container_id> | grep -i gevent

# 监控错误日志
tail -f /var/log/ragflow/error.log | grep -E "(gevent|monkey|patch)"
```

## 故障排除

### 常见问题

1. **补丁未生效**
   - 检查环境变量 `RAGFLOW_GEVENT_PATCHED`
   - 确认 gevent 模块已安装
   - 查看启动日志中的补丁应用信息

2. **性能问题**
   - 调整 worker 数量
   - 增加连接池大小
   - 检查数据库连接配置

3. **兼容性问题**
   - 某些第三方库可能与 gevent 不兼容
   - 使用 `RAGFLOW_DISABLE_GEVENT=1` 临时禁用
   - 查看具体错误日志进行针对性修复

### 调试模式

```bash
# 禁用 gevent 进行调试
export RAGFLOW_DISABLE_GEVENT=1
python api/ragflow_server.py

# 启用详细日志
export RAGFLOW_LOG_LEVEL=DEBUG
docker run -d -e RAGFLOW_LOG_LEVEL=DEBUG ragflow:latest
```

## 最佳实践

1. **生产环境**
   - 使用 Docker 部署
   - 根据负载调整 worker 数量
   - 监控内存和 CPU 使用率
   - 定期检查连接池状态

2. **开发环境**
   - 保持与生产环境的一致性
   - 使用较少的 worker 数量
   - 启用详细日志进行调试

3. **测试环境**
   - 进行压力测试验证性能
   - 测试各种配置组合
   - 验证故障恢复能力

## 版本兼容性

- **Gevent**: >= 23.9.0, < 24.0.0
- **Gunicorn**: >= 21.2.0, < 22.0.0
- **Python**: >= 3.8

## 参考资源

- [Gevent 官方文档](http://www.gevent.org/)
- [Gunicorn 配置指南](https://docs.gunicorn.org/en/stable/configure.html)
- [RAGFlow 生产部署文档](production_deployment_zh.md)