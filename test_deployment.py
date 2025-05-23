#!/usr/bin/env python3
"""
测试RAGFlow部署模式的脚本
"""

import requests
import time
import sys
import os
import subprocess
import signal

def test_server_response(url, timeout=30):
    """测试服务器是否响应"""
    print(f"Testing server at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server is responding at {url}")
                return True
        except requests.exceptions.RequestException as e:
            print(f"⏳ Waiting for server... ({e})")
            time.sleep(2)
    
    print(f"❌ Server did not respond within {timeout} seconds")
    return False

def check_wsgi_app():
    """检查WSGI应用是否可以正常导入"""
    try:
        from api.wsgi import application
        print("✅ WSGI application can be imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import WSGI application: {e}")
        return False

def test_gunicorn_config():
    """测试Gunicorn配置文件"""
    try:
        import gunicorn_config
        print("✅ Gunicorn config can be imported successfully")
        print(f"   - Workers: {getattr(gunicorn_config, 'workers', 'not set')}")
        print(f"   - Bind: {getattr(gunicorn_config, 'bind', 'not set')}")
        print(f"   - Timeout: {getattr(gunicorn_config, 'timeout', 'not set')}")
        return True
    except Exception as e:
        print(f"❌ Failed to import Gunicorn config: {e}")
        return False

def check_dependencies():
    """检查必要的依赖"""
    dependencies = ['gunicorn', 'flask', 'werkzeug']
    all_ok = True
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} is installed")
        except ImportError:
            print(f"❌ {dep} is not installed")
            all_ok = False
    
    return all_ok

def run_basic_tests():
    """运行基本测试"""
    print("="*50)
    print("RAGFlow Deployment Test")
    print("="*50)
    
    # 测试依赖
    print("\n1. Checking dependencies...")
    deps_ok = check_dependencies()
    
    # 测试WSGI应用
    print("\n2. Testing WSGI application...")
    wsgi_ok = check_wsgi_app()
    
    # 测试Gunicorn配置
    print("\n3. Testing Gunicorn configuration...")
    config_ok = test_gunicorn_config()
    
    # 总结
    print("\n" + "="*50)
    print("Test Summary:")
    print(f"Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"WSGI App: {'✅' if wsgi_ok else '❌'}")
    print(f"Gunicorn Config: {'✅' if config_ok else '❌'}")
    
    if all([deps_ok, wsgi_ok, config_ok]):
        print("\n🎉 All tests passed! Ready for production deployment.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = run_basic_tests()
    
    # 如果提供了URL参数，也测试实际的服务器
    if len(sys.argv) > 1:
        url = sys.argv[1]
        print(f"\n4. Testing live server at {url}...")
        server_ok = test_server_response(url)
        success = success and server_ok
    
    sys.exit(0 if success else 1) 