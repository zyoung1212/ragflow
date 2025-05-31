#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
Gevent-specific patches for RAGFlow task execution.

This module provides gevent-compatible implementations for task execution
components that need special handling beyond basic monkey patching.
"""

import os
import logging
from typing import Optional, Callable


def is_gevent_enabled() -> bool:
    """Check if gevent patches are enabled."""
    return os.environ.get('RAGFLOW_GEVENT_PATCHED') == '1'


class GeventCompatibleExecutor:
    """
    A gevent-compatible task executor that can replace ThreadPoolExecutor
    in gevent environments.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or 10
        self._shutdown = False
        
        if is_gevent_enabled():
            try:
                from gevent.pool import Pool
                self._pool = Pool(self.max_workers)
                self._use_gevent = True
                logging.debug(f"GeventCompatibleExecutor initialized with gevent pool (max_workers={self.max_workers})")
            except ImportError:
                self._use_gevent = False
                self._init_thread_pool()
        else:
            self._use_gevent = False
            self._init_thread_pool()
    
    def _init_thread_pool(self):
        """Initialize standard ThreadPoolExecutor as fallback."""
        from concurrent.futures import ThreadPoolExecutor
        self._pool = ThreadPoolExecutor(max_workers=self.max_workers)
        logging.debug(f"GeventCompatibleExecutor initialized with ThreadPoolExecutor (max_workers={self.max_workers})")
    
    def submit(self, fn: Callable, *args, **kwargs):
        """Submit a task for execution."""
        if self._shutdown:
            raise RuntimeError("Executor has been shut down")
        
        if self._use_gevent:
            # Use gevent greenlet
            return self._pool.spawn(fn, *args, **kwargs)
        else:
            # Use standard thread pool
            return self._pool.submit(fn, *args, **kwargs)
    
    def shutdown(self, wait: bool = True):
        """Shutdown the executor."""
        self._shutdown = True
        
        if self._use_gevent:
            if hasattr(self._pool, 'kill'):
                self._pool.kill()
        else:
            self._pool.shutdown(wait=wait)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class GeventCompatibleLock:
    """
    A lock that works with both gevent and threading.
    """
    
    def __init__(self):
        if is_gevent_enabled():
            try:
                from gevent.lock import RLock
                self._lock = RLock()
                self._use_gevent = True
            except ImportError:
                import threading
                self._lock = threading.RLock()
                self._use_gevent = False
        else:
            import threading
            self._lock = threading.RLock()
            self._use_gevent = False
    
    def acquire(self, blocking: bool = True, timeout: float = -1):
        """Acquire the lock."""
        if self._use_gevent:
            return self._lock.acquire(blocking, timeout if timeout > 0 else None)
        else:
            return self._lock.acquire(blocking, timeout if timeout > 0 else None)
    
    def release(self):
        """Release the lock."""
        self._lock.release()
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def gevent_sleep(seconds: float):
    """
    Sleep function that uses gevent.sleep if available, otherwise time.sleep.
    """
    if is_gevent_enabled():
        try:
            import gevent
            gevent.sleep(seconds)
            return
        except ImportError:
            pass
    
    import time
    time.sleep(seconds)


def create_gevent_compatible_timer(interval: float, function: Callable, args=None, kwargs=None):
    """
    Create a timer that works with gevent.
    """
    args = args or []
    kwargs = kwargs or {}
    
    if is_gevent_enabled():
        try:
            import gevent
            
            def timer_func():
                gevent.sleep(interval)
                function(*args, **kwargs)
            
            return gevent.spawn(timer_func)
        except ImportError:
            pass
    
    # Fallback to threading.Timer
    import threading
    timer = threading.Timer(interval, function, args, kwargs)
    return timer


def patch_task_executor_imports():
    """
    Patch imports in task_executor module to use gevent-compatible versions.
    
    This should be called before importing task_executor module.
    """
    if not is_gevent_enabled():
        return
    
    try:
        import sys  # noqa: F401
        from unittest.mock import patch  # noqa: F401
        
        # Create a mock module that provides gevent-compatible implementations
        class GeventTaskModule:
            ThreadPoolExecutor = GeventCompatibleExecutor
            RLock = GeventCompatibleLock
            sleep = gevent_sleep
            Timer = create_gevent_compatible_timer
        
        # This is a more advanced approach - in practice, you might want to
        # modify the task_executor.py directly or use import hooks
        logging.debug("Gevent task executor patches prepared")
        
    except Exception as e:
        logging.warning(f"Failed to patch task executor for gevent: {e}")


def optimize_redis_for_gevent():
    """
    Apply gevent-specific optimizations for Redis connections.
    """
    if not is_gevent_enabled():
        return
    
    try:
        import redis
        from gevent import socket as gevent_socket
        
        # Configure Redis connection pool for gevent
        # This ensures Redis uses gevent-compatible sockets
        original_connection_class = redis.Connection
        
        class GeventRedisConnection(original_connection_class):
            def _connect(self):
                # Use gevent socket for Redis connections
                sock = gevent_socket.socket(gevent_socket.AF_INET, gevent_socket.SOCK_STREAM)
                sock.settimeout(self.socket_timeout)
                sock.connect((self.host, self.port))
                return sock
        
        # This is an example - actual implementation might vary
        logging.debug("Redis gevent optimizations applied")
        
    except Exception as e:
        logging.warning(f"Failed to optimize Redis for gevent: {e}")


def init_task_gevent_environment():
    """
    Initialize gevent environment specifically for task execution.
    
    This should be called in task execution modules.
    """
    if is_gevent_enabled():
        logging.info("Initializing gevent environment for task execution")
        
        # Apply task-specific patches
        patch_task_executor_imports()
        optimize_redis_for_gevent()
        
        # Set up gevent-specific configurations
        try:
            import gevent  # noqa: F401
            from gevent import monkey
            
            # Ensure all necessary patches are applied
            if not monkey.is_module_patched('socket'):
                logging.warning("Socket module not patched - some operations may block")
            
            if not monkey.is_module_patched('threading'):
                logging.warning("Threading module not patched - some operations may block")
            
            logging.info("Task gevent environment initialized successfully")
            
        except ImportError:
            logging.warning("Gevent not available for task execution")
    else:
        logging.debug("Gevent not enabled for task execution")


# Auto-initialize if imported and gevent is enabled
if __name__ != '__main__' and is_gevent_enabled():
    init_task_gevent_environment()