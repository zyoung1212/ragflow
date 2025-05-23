"""
Gunicorn configuration for RAGFlow production deployment.
"""

import os
import multiprocessing

# 绑定地址和端口
bind = f"0.0.0.0:{os.getenv('HOST_PORT', '9380')}"

# Worker 配置
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"  # 使用同步worker，适合CPU密集型任务
worker_connections = 1000
timeout = 300  # 5分钟超时，适合处理大文档
keepalive = 30

# 最大请求数，防止内存泄漏
max_requests = 1000
max_requests_jitter = 50

# 进程重启配置
preload_app = True  # 预加载应用，提高性能
reload = False  # 生产环境不启用自动重载

# 日志配置
loglevel = "info"
accesslog = "-"  # 输出到stdout
errorlog = "-"   # 输出到stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程名
proc_name = "ragflow_gunicorn"

# 临时目录
tmp_upload_dir = "/tmp"

# 信号处理
graceful_timeout = 120

# 安全配置
limit_request_line = 8192
limit_request_fields = 200
limit_request_field_size = 8192

def when_ready(server):
    """服务器就绪时的回调"""
    server.log.info("RAGFlow server is ready. Listening on %s", server.address)

def worker_int(worker):
    """Worker中断时的回调"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Worker fork前的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Worker fork后的回调"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    """Worker异常终止时的回调"""
    worker.log.info("Worker received SIGABRT signal") 