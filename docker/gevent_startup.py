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
Gevent startup optimization script for RAGFlow Docker deployment.

This script ensures proper gevent monkey patching is applied before
starting the RAGFlow application in Docker containers.
"""

import os
import sys
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ragflow.gevent_startup')


def setup_gevent_environment():
    """
    Set up the gevent environment for optimal performance.
    """
    logger.info("Setting up gevent environment for RAGFlow")
    
    # Set environment variables to ensure gevent is used
    os.environ['RAGFLOW_FORCE_GEVENT'] = '1'
    os.environ['GUNICORN_WORKER_CLASS'] = 'gevent'
    
    # Apply gevent monkey patches as early as possible
    try:
        from gevent import monkey
        
        # Apply comprehensive monkey patches
        monkey.patch_all(
            socket=True,
            dns=True,
            time=True,
            select=True,
            thread=True,
            os=True,
            ssl=True,
            subprocess=True,
            queue=True,
            signal=False,  # Don't patch signal to avoid gunicorn conflicts
            builtins=False,
            aggressive=True
        )
        
        logger.info("Gevent monkey patches applied successfully")
        
        # Set environment variable to indicate patches are applied
        os.environ['RAGFLOW_GEVENT_PATCHED'] = '1'
        
        # Configure gevent-specific settings
        configure_gevent_settings()
        
        return True
        
    except ImportError as e:
        logger.error(f"Gevent not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to apply gevent patches: {e}")
        return False


def configure_gevent_settings():
    """
    Configure gevent-specific settings for optimal performance.
    """
    try:
        import gevent
        from gevent import config
        
        # Configure gevent resolver
        # Use c-ares for better DNS performance if available
        try:
            from gevent.resolver.cares import Resolver
            gevent.get_hub().resolver = Resolver()
            logger.info("Using c-ares resolver for DNS")
        except ImportError:
            logger.info("Using default gevent resolver")
        
        # Configure gevent hub
        hub = gevent.get_hub()
        
        # Set reasonable defaults for connection pooling
        os.environ.setdefault('GEVENT_RESOLVER_TIMEOUT', '10')
        os.environ.setdefault('GEVENT_RESOLVER_RETRIES', '3')
        
        logger.info("Gevent settings configured")
        
    except Exception as e:
        logger.warning(f"Failed to configure gevent settings: {e}")


def optimize_for_ragflow():
    """
    Apply RAGFlow-specific optimizations for gevent.
    """
    logger.info("Applying RAGFlow-specific gevent optimizations")
    
    # Set optimal worker connections for RAGFlow workload
    os.environ.setdefault('GEVENT_WORKER_CONNECTIONS', '1000')
    
    # Configure Redis connection pooling for gevent
    os.environ.setdefault('REDIS_CONNECTION_POOL_MAX_CONNECTIONS', '50')
    
    # Configure database connection pooling
    os.environ.setdefault('DB_POOL_SIZE', '20')
    os.environ.setdefault('DB_MAX_OVERFLOW', '30')
    
    # Set timeouts for better resource management
    os.environ.setdefault('GEVENT_TIMEOUT', '300')
    os.environ.setdefault('GEVENT_KEEPALIVE', '10')
    
    logger.info("RAGFlow gevent optimizations applied")


def validate_gevent_setup():
    """
    Validate that gevent is properly set up.
    """
    try:
        import gevent
        from gevent import monkey
        
        # Check that critical modules are patched
        critical_modules = ['socket', 'threading', 'time', 'select']
        patched_modules = []
        unpatched_modules = []
        
        for module in critical_modules:
            if monkey.is_module_patched(module):
                patched_modules.append(module)
            else:
                unpatched_modules.append(module)
        
        logger.info(f"Patched modules: {patched_modules}")
        
        if unpatched_modules:
            logger.warning(f"Unpatched modules: {unpatched_modules}")
            return False
        
        # Test basic gevent functionality
        import gevent.socket
        logger.info("Gevent socket module available")
        
        logger.info("Gevent setup validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Gevent setup validation failed: {e}")
        return False


def main():
    """
    Main function to set up gevent environment.
    """
    logger.info("Starting RAGFlow gevent initialization")
    
    # Check if we should apply gevent patches
    if os.environ.get('RAGFLOW_DISABLE_GEVENT', '').lower() in ('1', 'true', 'yes'):
        logger.info("Gevent disabled by environment variable")
        return True
    
    # Set up gevent environment
    if not setup_gevent_environment():
        logger.error("Failed to set up gevent environment")
        return False
    
    # Apply RAGFlow-specific optimizations
    optimize_for_ragflow()
    
    # Validate setup
    if not validate_gevent_setup():
        logger.error("Gevent setup validation failed")
        return False
    
    logger.info("RAGFlow gevent initialization completed successfully")
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
else:
    # Auto-initialize when imported
    main()