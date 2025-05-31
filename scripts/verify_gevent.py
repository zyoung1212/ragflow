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
RAGFlow Gevent 验证脚本

用于验证 gevent 猴子补丁是否正确应用，以及相关配置是否正常。
"""

import os
import sys
import time
import logging
from typing import Dict, List, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ragflow.gevent_verify')


def check_environment_variables() -> Dict[str, str]:
    """
    检查 gevent 相关的环境变量。
    """
    logger.info("检查环境变量...")
    
    env_vars = {
        'RAGFLOW_GEVENT_PATCHED': os.environ.get('RAGFLOW_GEVENT_PATCHED', 'Not Set'),
        'RAGFLOW_FORCE_GEVENT': os.environ.get('RAGFLOW_FORCE_GEVENT', 'Not Set'),
        'GUNICORN_WORKER_CLASS': os.environ.get('GUNICORN_WORKER_CLASS', 'Not Set'),
        'RAGFLOW_DISABLE_GEVENT': os.environ.get('RAGFLOW_DISABLE_GEVENT', 'Not Set'),
        'GUNICORN_WORKERS': os.environ.get('GUNICORN_WORKERS', 'Not Set'),
        'SERVER_SOFTWARE': os.environ.get('SERVER_SOFTWARE', 'Not Set'),
    }
    
    for key, value in env_vars.items():
        logger.info(f"  {key}: {value}")
    
    return env_vars


def check_gevent_availability() -> bool:
    """
    检查 gevent 是否可用。
    """
    logger.info("检查 gevent 可用性...")
    
    try:
        import gevent
        logger.info(f"  Gevent 版本: {gevent.__version__}")
        return True
    except ImportError as e:
        logger.error(f"  Gevent 不可用: {e}")
        return False


def check_monkey_patches() -> Dict[str, bool]:
    """
    检查猴子补丁状态。
    """
    logger.info("检查猴子补丁状态...")
    
    patch_status = {}
    
    try:
        from gevent import monkey
        
        modules_to_check = [
            'socket', 'dns', 'time', 'select', 'thread', 
            'os', 'ssl', 'subprocess', 'queue', 'signal', 'builtins'
        ]
        
        for module in modules_to_check:
            is_patched = monkey.is_module_patched(module)
            patch_status[module] = is_patched
            status = "✓" if is_patched else "✗"
            logger.info(f"  {module}: {status}")
        
    except ImportError:
        logger.error("  无法导入 gevent.monkey")
    
    return patch_status


def test_gevent_functionality() -> List[Tuple[str, bool, str]]:
    """
    测试 gevent 基本功能。
    """
    logger.info("测试 gevent 基本功能...")
    
    test_results = []
    
    # 测试 gevent.sleep
    try:
        import gevent
        start_time = time.time()
        gevent.sleep(0.1)
        elapsed = time.time() - start_time
        success = 0.05 <= elapsed <= 0.2  # 允许一定误差
        test_results.append(("gevent.sleep", success, f"耗时: {elapsed:.3f}s"))
        logger.info(f"  gevent.sleep: {'✓' if success else '✗'} (耗时: {elapsed:.3f}s)")
    except Exception as e:
        test_results.append(("gevent.sleep", False, str(e)))
        logger.error(f"  gevent.sleep: ✗ ({e})")
    
    # 测试 gevent.socket
    try:
        import gevent.socket
        sock = gevent.socket.socket(gevent.socket.AF_INET, gevent.socket.SOCK_STREAM)
        sock.close()
        test_results.append(("gevent.socket", True, "创建和关闭成功"))
        logger.info("  gevent.socket: ✓")
    except Exception as e:
        test_results.append(("gevent.socket", False, str(e)))
        logger.error(f"  gevent.socket: ✗ ({e})")
    
    # 测试 gevent.pool
    try:
        from gevent.pool import Pool
        pool = Pool(2)
        
        def test_func(x):
            gevent.sleep(0.01)
            return x * 2
        
        results = list(pool.map(test_func, [1, 2, 3]))
        expected = [2, 4, 6]
        success = results == expected
        test_results.append(("gevent.pool", success, f"结果: {results}"))
        logger.info(f"  gevent.pool: {'✓' if success else '✗'} (结果: {results})")
    except Exception as e:
        test_results.append(("gevent.pool", False, str(e)))
        logger.error(f"  gevent.pool: ✗ ({e})")
    
    return test_results


def test_ragflow_integration() -> List[Tuple[str, bool, str]]:
    """
    测试 RAGFlow 集成。
    """
    logger.info("测试 RAGFlow 集成...")
    
    test_results = []
    
    # 测试 gevent_patches 模块
    try:
        from api.utils.gevent_patches import should_apply_patches, init_gevent_environment  # noqa: F401
        should_patch = should_apply_patches()
        test_results.append(("gevent_patches 模块", True, f"should_apply_patches: {should_patch}"))
        logger.info(f"  gevent_patches 模块: ✓ (should_apply_patches: {should_patch})")
    except Exception as e:
        test_results.append(("gevent_patches 模块", False, str(e)))
        logger.error(f"  gevent_patches 模块: ✗ ({e})")
    
    # 测试 gevent_task_patches 模块
    try:
        from rag.utils.gevent_task_patches import is_gevent_enabled, GeventCompatibleExecutor
        gevent_enabled = is_gevent_enabled()
        test_results.append(("gevent_task_patches 模块", True, f"is_gevent_enabled: {gevent_enabled}"))
        logger.info(f"  gevent_task_patches 模块: ✓ (is_gevent_enabled: {gevent_enabled})")
        
        # 测试 GeventCompatibleExecutor
        executor = GeventCompatibleExecutor(max_workers=2)
        future = executor.submit(lambda: "test")
        if hasattr(future, 'get'):
            result = future.get(timeout=1)
        else:
            result = future.result(timeout=1)
        success = result == "test"
        test_results.append(("GeventCompatibleExecutor", success, f"结果: {result}"))
        logger.info(f"  GeventCompatibleExecutor: {'✓' if success else '✗'} (结果: {result})")
        executor.shutdown()
        
    except Exception as e:
        test_results.append(("gevent_task_patches 模块", False, str(e)))
        logger.error(f"  gevent_task_patches 模块: ✗ ({e})")
    
    return test_results


def generate_report(env_vars: Dict[str, str], 
                   patch_status: Dict[str, bool], 
                   gevent_tests: List[Tuple[str, bool, str]], 
                   ragflow_tests: List[Tuple[str, bool, str]]) -> str:
    """
    生成验证报告。
    """
    report = []
    report.append("=" * 60)
    report.append("RAGFlow Gevent 验证报告")
    report.append("=" * 60)
    report.append("")
    
    # 环境变量
    report.append("环境变量:")
    for key, value in env_vars.items():
        report.append(f"  {key}: {value}")
    report.append("")
    
    # 补丁状态
    report.append("猴子补丁状态:")
    for module, is_patched in patch_status.items():
        status = "✓" if is_patched else "✗"
        report.append(f"  {module}: {status}")
    report.append("")
    
    # Gevent 功能测试
    report.append("Gevent 功能测试:")
    for test_name, success, details in gevent_tests:
        status = "✓" if success else "✗"
        report.append(f"  {test_name}: {status} ({details})")
    report.append("")
    
    # RAGFlow 集成测试
    report.append("RAGFlow 集成测试:")
    for test_name, success, details in ragflow_tests:
        status = "✓" if success else "✗"
        report.append(f"  {test_name}: {status} ({details})")
    report.append("")
    
    # 总结
    total_tests = len(gevent_tests) + len(ragflow_tests)
    passed_tests = sum(1 for _, success, _ in gevent_tests + ragflow_tests if success)
    
    report.append("总结:")
    report.append(f"  总测试数: {total_tests}")
    report.append(f"  通过测试: {passed_tests}")
    report.append(f"  失败测试: {total_tests - passed_tests}")
    report.append(f"  成功率: {passed_tests/total_tests*100:.1f}%")
    
    if passed_tests == total_tests:
        report.append("  状态: ✓ 所有测试通过")
    else:
        report.append("  状态: ✗ 存在失败的测试")
    
    report.append("")
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    """
    主函数。
    """
    logger.info("开始 RAGFlow Gevent 验证")
    
    # 检查环境变量
    env_vars = check_environment_variables()
    
    # 检查 gevent 可用性
    if not check_gevent_availability():
        logger.error("Gevent 不可用，无法继续验证")
        return False
    
    # 检查猴子补丁
    patch_status = check_monkey_patches()
    
    # 测试 gevent 功能
    gevent_tests = test_gevent_functionality()
    
    # 测试 RAGFlow 集成
    ragflow_tests = test_ragflow_integration()
    
    # 生成报告
    report = generate_report(env_vars, patch_status, gevent_tests, ragflow_tests)
    print("\n" + report)
    
    # 判断是否成功
    all_tests = gevent_tests + ragflow_tests
    success = all(success for _, success, _ in all_tests)
    
    if success:
        logger.info("✓ 所有验证通过")
        return True
    else:
        logger.error("✗ 存在验证失败")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)