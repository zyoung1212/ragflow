#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
WSGI configuration for RAGFlow production deployment with Gunicorn.
"""

import os
import logging
import signal
import sys
import time
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

# 初始化日志和插件（必须在导入其他模块之前）
from api.utils.log_utils import initRootLogger
from plugin import GlobalPluginManager
initRootLogger("ragflow_server")

from api import settings
from api.apps import app
from api.db.runtime_config import RuntimeConfig
from api.db.services.document_service import DocumentService
from api import utils
from api.db.db_models import init_database_tables as init_web_db
from api.db.init_data import init_web_data
from api.versions import get_ragflow_version
from api.utils import show_configs
from rag.settings import print_rag_settings
from rag.utils.redis_conn import RedisDistributedLock

# 全局停止事件
stop_event = threading.Event()

def update_progress():
    """后台进度更新任务"""
    lock_value = str(uuid.uuid4())
    redis_lock = RedisDistributedLock("update_progress", lock_value=lock_value, timeout=60)
    logging.info(f"update_progress lock_value: {lock_value}")
    while not stop_event.is_set():
        try:
            if redis_lock.acquire():
                DocumentService.update_progress()
                redis_lock.release()
            stop_event.wait(6)
        except Exception:
            logging.exception("update_progress exception")
        finally:
            redis_lock.release()

def signal_handler(sig, frame):
    """信号处理器"""
    logging.info("Received interrupt signal, shutting down...")
    stop_event.set()
    time.sleep(1)
    sys.exit(0)

def initialize_ragflow():
    """初始化RAGFlow应用"""
    logging.info(r"""
        ____   ___    ______ ______ __               
       / __ \ /   |  / ____// ____// /____  _      __
      / /_/ // /| | / / __ / /_   / // __ \| | /| / /
     / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ / 
    /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/                             

    """)
    logging.info(f'RAGFlow version: {get_ragflow_version()}')
    logging.info(f'project base: {utils.file_utils.get_project_base_directory()}')
    
    # 显示配置
    show_configs()
    settings.init_settings()
    print_rag_settings()

    # 调试模式配置
    RAGFLOW_DEBUGPY_LISTEN = int(os.environ.get('RAGFLOW_DEBUGPY_LISTEN', "0"))
    if RAGFLOW_DEBUGPY_LISTEN > 0:
        logging.info(f"debugpy listen on {RAGFLOW_DEBUGPY_LISTEN}")
        import debugpy
        debugpy.listen(("0.0.0.0", RAGFLOW_DEBUGPY_LISTEN))

    # 初始化数据库
    init_web_db()
    init_web_data()

    # 初始化运行时配置
    RuntimeConfig.DEBUG = False  # 在生产模式中禁用调试
    logging.info("Running in production mode with WSGI")
    
    RuntimeConfig.init_env()
    RuntimeConfig.init_config(JOB_SERVER_HOST=settings.HOST_IP, HTTP_PORT=settings.HOST_PORT)

    # 加载插件
    GlobalPluginManager.load_plugins()

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动后台任务
    thread = ThreadPoolExecutor(max_workers=1)
    thread.submit(update_progress)
    
    logging.info("RAGFlow WSGI application initialized successfully")

# 初始化应用（在导入时执行）
initialize_ragflow()

# 导出WSGI应用
application = app

if __name__ == "__main__":
    # 用于调试目的
    from werkzeug.serving import run_simple
    run_simple(
        hostname=settings.HOST_IP,
        port=settings.HOST_PORT,
        application=app,
        threaded=True,
        use_reloader=False,
        use_debugger=False,
    ) 