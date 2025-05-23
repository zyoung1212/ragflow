# RAGFlow 生产模式部署 - 修改总结

## 🎯 问题解决

✅ **已完成**: 将RAGFlow从FastAPI开发模式（Werkzeug）切换到生产模式（Gunicorn WSGI）

## 📋 文件修改清单

### 新增文件
- `api/wsgi.py` - WSGI应用配置，包含所有初始化逻辑
- `gunicorn_config.py` - Gunicorn生产环境配置
- `docker/launch_production_service.sh` - 专用生产模式启动脚本
- `test_deployment.py` - 部署测试脚本
- `PRODUCTION_DEPLOYMENT.md` - 详细部署指南
- `DEPLOYMENT_SUMMARY.md` - 本文件

### 修改文件
- `pyproject.toml` - 添加 `gunicorn==21.2.0` 依赖
- `docker/entrypoint.sh` - 支持 `--dev-mode` 开发模式选项
- `docker/launch_backend_service.sh` - 支持开发/生产模式切换
- `Dockerfile` - 复制Gunicorn配置和新脚本

## 🚀 快速使用

### 生产模式启动 (默认，推荐)

```bash
# Docker容器方式
docker run -d ragflow:latest

# 直接启动方式
./docker/launch_production_service.sh

# 或使用Gunicorn直接启动
gunicorn -c gunicorn_config.py api.wsgi:application
```

### 开发模式启动

```bash
# Docker容器方式  
docker run -d ragflow:latest ./entrypoint.sh --dev-mode

# 直接启动方式
./docker/launch_backend_service.sh --dev-mode

# 或直接运行原服务器
python api/ragflow_server.py --debug
```

## ⚙️ 关键特性

1. **保留所有初始化操作**: 数据库初始化、插件加载、后台任务等
2. **无缝切换**: 支持开发模式和生产模式一键切换
3. **完整的Gunicorn配置**: 优化的worker数量、超时设置、日志配置
4. **Docker兼容**: 所有修改都兼容现有Docker镜像构建
5. **向后兼容**: 原有的启动方式仍然有效

## 🔧 配置项

### 环境变量
- `HOST_PORT`: 服务端口 (默认: 9380)
- `GUNICORN_WORKERS`: Worker数量 (默认: CPU核数*2+1)
- `WS`: 任务执行器数量 (默认: 1)

### 性能提升
- **多进程**: Gunicorn多worker并发处理请求
- **预加载**: preload_app提高启动速度
- **内存管理**: max_requests防止内存泄漏
- **优雅重启**: 支持零停机时间重启

## 📊 模式对比

| 特性 | 开发模式 | 生产模式 |
|------|---------|---------|
| 服务器 | Werkzeug | Gunicorn |
| 并发性 | 单线程 | 多进程 |
| 性能 | 较低 | 高 |
| 调试 | 完整支持 | 有限支持 |
| 热重载 | ✅ | ❌ |
| 生产就绪 | ❌ | ✅ |

## 🧪 测试

```bash
# 运行部署测试
python test_deployment.py

# 测试实际服务器
python test_deployment.py http://localhost:9380
```

## 📈 预期改进

1. **性能提升**: 2-3倍的请求处理能力
2. **稳定性**: 进程隔离，单个请求错误不影响其他请求
3. **可扩展性**: 可根据负载调整worker数量
4. **生产就绪**: 符合生产环境部署标准

## ⚠️ 注意事项

1. **内存使用**: 生产模式会使用更多内存（多进程）
2. **启动时间**: 首次启动可能稍慢（预加载应用）
3. **调试**: 生产模式下调试功能有限，开发时请使用开发模式

## 📞 问题排查

如遇到问题，请：
1. 查看 `PRODUCTION_DEPLOYMENT.md` 详细指南
2. 检查日志输出中的错误信息
3. 确认环境变量设置
4. 运行测试脚本验证配置

---

✨ **总结**: 现在您可以在生产环境中安全部署RAGFlow，享受更好的性能和稳定性！ 