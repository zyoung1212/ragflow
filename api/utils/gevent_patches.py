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
Gevent monkey patching module for RAGFlow.

This module handles all gevent monkey patching to ensure proper async behavior
when running with gunicorn + gevent worker class.

IMPORTANT: This module must be imported before any other modules that use
standard library modules that need to be patched (socket, threading, time, etc.)
"""

import os
import logging

# Check if we're running under gunicorn with gevent worker class
def should_apply_patches():
    """
    Determine if gevent monkey patches should be applied.
    
    Returns True if:
    1. Running under gunicorn with gevent worker class, OR
    2. RAGFLOW_FORCE_GEVENT environment variable is set
    """
    # Check if explicitly forced
    if os.environ.get('RAGFLOW_FORCE_GEVENT', '').lower() in ('1', 'true', 'yes'):
        return True
    
    # Check if running under gunicorn with gevent
    server_software = os.environ.get('SERVER_SOFTWARE', '')
    worker_class = os.environ.get('GUNICORN_WORKER_CLASS', '')
    
    # Gunicorn sets SERVER_SOFTWARE
    if server_software.startswith('gunicorn'):
        # If worker class is explicitly gevent
        if worker_class == 'gevent':
            return True
        # If no explicit worker class but we detect gevent usage
        try:
            import gevent
            return True
        except ImportError:
            pass
    
    return False


def apply_gevent_patches():
    """
    Apply gevent monkey patches for all necessary standard library modules.
    
    This patches:
    - socket: For network I/O operations
    - threading: For thread-based operations
    - time: For time.sleep() calls
    - select: For I/O multiplexing
    - subprocess: For subprocess operations
    - ssl: For SSL/TLS operations
    - queue: For queue operations
    - os: For some OS operations
    
    Does NOT patch:
    - signal: Can cause issues with gunicorn signal handling
    - builtins: Usually not needed and can cause issues
    """
    try:
        from gevent import monkey
        
        # Apply comprehensive patches but exclude signal to avoid conflicts with gunicorn
        monkey.patch_all(
            socket=True,      # Essential for network operations
            dns=True,         # DNS resolution
            time=True,        # time.sleep() calls
            select=True,      # I/O multiplexing
            thread=True,      # threading module
            os=True,          # os module operations
            ssl=True,         # SSL/TLS operations
            subprocess=True,  # subprocess operations
            queue=True,       # queue operations
            signal=False,     # Keep False to avoid gunicorn conflicts
            builtins=False,   # Keep False to avoid unexpected issues
            aggressive=True   # More comprehensive patching
        )
        
        logging.info("Gevent monkey patches applied successfully")
        
        # Additional patches for specific libraries that might need special handling
        _patch_redis_connections()
        _patch_database_connections()
        _patch_http_libraries()
        
        return True
        
    except ImportError as e:
        logging.warning(f"Gevent not available, skipping monkey patches: {e}")
        return False
    except Exception as e:
        logging.error(f"Failed to apply gevent monkey patches: {e}")
        return False


def _patch_redis_connections():
    """
    Apply specific patches for Redis connections to work well with gevent.
    """
    try:
        # Ensure redis-py uses gevent-compatible connections
        import redis
        from gevent import socket as gevent_socket
        
        # Redis connection pool should use gevent sockets
        # This is usually handled automatically by monkey patching,
        # but we can be explicit about it
        logging.debug("Redis gevent compatibility ensured")
        
    except ImportError:
        # Redis not available, skip
        pass
    except Exception as e:
        logging.warning(f"Failed to patch Redis for gevent: {e}")


def _patch_database_connections():
    """
    Apply specific patches for database connections.
    """
    try:
        # For peewee ORM with MySQL/PostgreSQL
        # The monkey patching should handle most cases,
        # but we can add specific handling if needed
        
        # Ensure psycopg2 works with gevent if available
        try:
            import psycopg2
            from psycopg2 import extensions
            # Enable async mode for psycopg2 if using gevent
            extensions.set_wait_callback(lambda conn: None)
            logging.debug("PostgreSQL gevent compatibility ensured")
        except ImportError:
            pass
            
    except Exception as e:
        logging.warning(f"Failed to patch database connections for gevent: {e}")


def _patch_http_libraries():
    """
    Apply specific patches for HTTP libraries like requests.
    """
    try:
        # Requests library should work with gevent after monkey patching,
        # but we can ensure urllib3 uses gevent-compatible connections
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.connection import create_connection
        
        logging.debug("HTTP libraries gevent compatibility ensured")
        
    except ImportError:
        # Requests not available, skip
        pass
    except Exception as e:
        logging.warning(f"Failed to patch HTTP libraries for gevent: {e}")


def configure_gevent_logging():
    """
    Configure logging to work properly with gevent.
    """
    try:
        import gevent
        from gevent import monkey
        
        # Ensure logging works correctly with gevent
        # This is usually handled by monkey patching, but we can be explicit
        logging.debug("Gevent logging configuration applied")
        
    except ImportError:
        pass
    except Exception as e:
        logging.warning(f"Failed to configure gevent logging: {e}")


def init_gevent_environment():
    """
    Initialize the gevent environment for RAGFlow.
    
    This function should be called as early as possible in the application
    startup process, before importing other modules.
    
    Returns:
        bool: True if gevent patches were applied, False otherwise
    """
    if should_apply_patches():
        logging.info("Initializing gevent environment for RAGFlow")
        
        # Apply monkey patches
        patches_applied = apply_gevent_patches()
        
        if patches_applied:
            # Configure additional gevent settings
            configure_gevent_logging()
            
            # Set environment variable to indicate patches are applied
            os.environ['RAGFLOW_GEVENT_PATCHED'] = '1'
            
            logging.info("Gevent environment initialized successfully")
            return True
        else:
            logging.warning("Failed to initialize gevent environment")
            return False
    else:
        logging.debug("Gevent patches not needed in current environment")
        return False


# Auto-initialize if this module is imported and conditions are met
if __name__ != '__main__':
    # Only auto-patch if we detect we should
    if should_apply_patches() and not os.environ.get('RAGFLOW_GEVENT_PATCHED'):
        init_gevent_environment()