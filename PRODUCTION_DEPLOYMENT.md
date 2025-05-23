# RAGFlow 生产模式部署指南

本文档说明如何将 RAGFlow 从开发模式（FastAPI/Werkzeug）切换到生产模式（Gunicorn WSGI）。

## 概述

RAGFlow 现在支持两种运行模式：

1. **开发模式（Development Mode）**: 使用 Werkzeug 开发服务器，适合开发和调试
2. **生产模式（Production Mode）**: 使用 Gunicorn WSGI 服务器，适合生产环境部署

## 主要变更

### 新增文件

1. `api/wsgi.py` - WSGI 应用配置文件
2. `gunicorn_config.py` - Gunicorn 配置文件
3. `docker/launch_production_service.sh` - 生产模式启动脚本

### 修改文件

1. `pyproject.toml` - 添加了 `gunicorn==21.2.0` 依赖
2. `docker/entrypoint.sh` - 添加了 `--dev-mode` 选项支持
3. `docker/launch_backend_service.sh` - 添加了开发/生产模式切换

## 使用方法

### Docker 容器部署

#### 生产模式（默认）

```bash
# 使用默认的生产模式启动
docker run -d infiniflow/ragflow:latest

# 或者使用更新的 entrypoint 脚本
docker run -d infiniflow/ragflow:latest ./entrypoint.sh
```

#### 开发模式

```bash
# 使用开发模式启动
docker run -d infiniflow/ragflow:latest ./entrypoint.sh --dev-mode
```

### 直接启动

#### 生产模式

```bash
# 方法1：使用专门的生产模式脚本
./docker/launch_production_service.sh

# 方法2：使用更新的后端服务脚本
./docker/launch_backend_service.sh --production-mode

# 方法3：直接使用 Gunicorn
gunicorn -c gunicorn_config.py api.wsgi:application
```

#### 开发模式

```bash
# 方法1：使用后端服务脚本
./docker/launch_backend_service.sh --dev-mode

# 方法2：直接运行原有的服务器
python api/ragflow_server.py --debug
```

## 配置选项

### 环境变量

- `HOST_PORT`: 服务端口（默认：9380）
- `GUNICORN_WORKERS`: Gunicorn worker 数量（默认：CPU 核数 * 2 + 1）
- `WS`: 任务执行器 worker 数量（默认：1）
- `RAGFLOW_DEBUGPY_LISTEN`: 调试端口（开发模式）

### Gunicorn 配置

主要配置项（在 `gunicorn_config.py` 中）：

```python
# Worker 配置
workers = CPU 核数 * 2 + 1  # 可通过环境变量覆盖
worker_class = "sync"        # 同步 worker，适合 CPU 密集型任务
timeout = 300               # 5分钟超时，适合处理大文档

# 性能优化
preload_app = True          # 预加载应用
max_requests = 1000         # 最大请求数，防止内存泄漏
max_requests_jitter = 50    # 请求数随机抖动
```

## 性能对比

### 开发模式 vs 生产模式

| 特性 | 开发模式 (Werkzeug) | 生产模式 (Gunicorn) |
|------|-------------------|-------------------|
| 并发处理 | 单线程 | 多进程/多线程 |
| 性能 | 较低 | 高 |
| 内存使用 | 较低 | 较高 |
| 稳定性 | 一般 | 高 |
| 调试功能 | 丰富 | 有限 |
| 热重载 | 支持 | 不支持 |
| 适用场景 | 开发/调试 | 生产环境 |

## 监控和日志

### 日志输出

生产模式下，日志会同时输出到：
- stdout（访问日志）
- stderr（错误日志）

### 日志格式

访问日志格式包含：
- 客户端 IP
- 请求时间
- 请求方法和路径
- 响应状态码
- 响应大小
- 用户代理
- 请求处理时间

### 进程监控

- Gunicorn 主进程会监控 worker 进程
- 自动重启失败的 worker
- 支持优雅重启和关闭

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口使用情况
   netstat -tlnp | grep :9380
   
   # 修改端口
   export HOST_PORT=9381
   ```

2. **Worker 进程内存不足**
   ```bash
   # 减少 worker 数量
   export GUNICORN_WORKERS=2
   ```

3. **请求超时**
   - 检查 `gunicorn_config.py` 中的 `timeout` 设置
   - 对于大文档处理，可能需要增加超时时间

### 调试技巧

1. **开启调试模式**
   ```bash
   ./docker/launch_backend_service.sh --dev-mode
   ```

2. **查看详细日志**
   ```bash
   # 设置日志级别
   export GUNICORN_LOG_LEVEL=debug
   ```

3. **性能分析**
   ```bash
   # 使用 profiling
   export RAGFLOW_DEBUGPY_LISTEN=5678
   ```

## 升级说明

从旧版本升级到支持生产模式的版本：

1. **更新依赖**
   ```bash
   uv sync --frozen --all-extras
   ```

2. **重新构建 Docker 镜像**
   ```bash
   docker build -t ragflow:production .
   ```

3. **更新启动脚本**
   - 使用新的 entrypoint.sh 选项
   - 或者使用专门的生产模式脚本

## 最佳实践

1. **生产环境部署**
   - 始终使用生产模式
   - 配置适当的 worker 数量
   - 设置资源限制
   - 配置日志轮转

2. **开发环境**
   - 使用开发模式进行调试
   - 启用热重载功能
   - 使用 debugpy 进行远程调试

3. **监控**
   - 监控 worker 进程状态
   - 观察内存和 CPU 使用情况
   - 设置告警阈值

## 支持

如果在使用过程中遇到问题，请：

1. 检查日志输出
2. 参考故障排除部分
3. 提交 issue 并附上详细的错误信息和环境配置 