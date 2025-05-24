#!/usr/bin/env python3
"""
测试脚本：验证RAGFlow生产模式配置
"""

import os
import sys
import subprocess
import tempfile
import time

def test_wsgi_import():
    """测试WSGI模块能否正常导入"""
    print("Testing WSGI module import...")
    try:
        # 添加项目路径到Python路径
        sys.path.insert(0, '/ragflow')
        
        # 测试导入WSGI应用
        from api.wsgi import application
        print("✅ WSGI application imported successfully")
        print(f"   Application type: {type(application)}")
        return True
    except Exception as e:
        print(f"❌ WSGI import failed: {e}")
        return False

def test_gunicorn_config():
    """测试Gunicorn配置文件"""
    print("\nTesting Gunicorn configuration...")
    config_path = "/ragflow/conf/gunicorn.conf.py"
    
    if not os.path.exists(config_path):
        print(f"❌ Gunicorn config file not found: {config_path}")
        return False
    
    try:
        # 尝试加载配置文件
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # 检查关键配置项
        required_configs = ['bind', 'workers', 'worker_class', 'timeout', 'preload_app']
        for config in required_configs:
            if config in config_content:
                print(f"   ✅ Found config: {config}")
            else:
                print(f"   ❌ Missing config: {config}")
                return False
        
        print("✅ Gunicorn configuration file is valid")
        return True
    except Exception as e:
        print(f"❌ Failed to read gunicorn config: {e}")
        return False

def test_entrypoint_script():
    """测试entrypoint.sh脚本"""
    print("\nTesting entrypoint script...")
    script_path = "/ragflow/docker/entrypoint.sh"
    
    if not os.path.exists(script_path):
        print(f"❌ Entrypoint script not found: {script_path}")
        return False
    
    try:
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # 检查关键内容
        if 'gunicorn' in script_content and 'api.wsgi:application' in script_content:
            print("✅ Entrypoint script contains Gunicorn WSGI setup")
        else:
            print("❌ Entrypoint script missing Gunicorn WSGI setup")
            return False
        
        if 'Production Mode' in script_content:
            print("✅ Entrypoint script indicates production mode")
        else:
            print("❌ Entrypoint script missing production mode indication")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Failed to read entrypoint script: {e}")
        return False

def test_gunicorn_command():
    """测试Gunicorn命令是否可用"""
    print("\nTesting Gunicorn installation...")
    try:
        result = subprocess.run(['gunicorn', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ Gunicorn installed: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Gunicorn version check failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Gunicorn not found in PATH")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Gunicorn version check timed out")
        return False
    except Exception as e:
        print(f"❌ Gunicorn test failed: {e}")
        return False

def test_production_warning():
    """测试开发模式警告"""
    print("\nTesting development mode warning...")
    try:
        with open('/ragflow/api/ragflow_server.py', 'r') as f:
            server_content = f.read()
        
        if 'DEVELOPMENT MODE WARNING' in server_content:
            print("✅ Development mode warning found")
            return True
        else:
            print("❌ Development mode warning not found")
            return False
    except Exception as e:
        print(f"❌ Failed to check development warning: {e}")
        return False

def main():
    """运行所有测试"""
    print("RAGFlow Production Mode Configuration Test")
    print("=" * 50)
    
    tests = [
        test_wsgi_import,
        test_gunicorn_config,
        test_entrypoint_script,
        test_gunicorn_command,
        test_production_warning
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Production mode is ready.")
        print("\n💡 To start in production mode:")
        print("   docker run -d ragflow:latest")
        print("   # or manually:")
        print("   gunicorn --config conf/gunicorn.conf.py api.wsgi:application")
        return True
    else:
        print("❌ Some tests failed. Please check the configuration.")
        return False

if __name__ == '__main__':
    sys.exit(0 if main() else 1) 