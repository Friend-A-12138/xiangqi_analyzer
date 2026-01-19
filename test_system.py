#!/usr/bin/env python3
"""
系统测试脚本
验证各个模块是否正常工作
"""

import sys
import os
from pathlib import Path
import logging

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n")


def print_result(test_name, success, message=""):
    """打印测试结果"""
    status = f"{Colors.GREEN}✓ 通过" if success else f"{Colors.RED}✗ 失败"
    print(f"{test_name}: {status}{Colors.RESET}")
    if message:
        print(f"  {message}")


def test_imports():
    """测试模块导入"""
    print_header("测试模块导入")
    
    tests = [
        ("OpenCV", "import cv2"),
        ("NumPy", "import numpy as np"),
        ("Flask", "from flask import Flask"),
        ("Pillow", "from PIL import Image"),
        ("核心模块", "from src.chess_analyzer import XiangqiAnalyzer"),
        ("流处理模块", "from src.stream_processor import RTMPStreamProcessor"),
    ]
    
    all_passed = True
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print_result(name, True)
        except ImportError as e:
            print_result(name, False, str(e))
            all_passed = False
    
    return all_passed


def test_directory_structure():
    """测试目录结构"""
    print_header("测试目录结构")
    
    required_dirs = [
        "core",
        "web",
        "web/templates",
        "config",
        "logs"
    ]
    
    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "src/chess_analyzer.py",
        "src/stream_processor.py",
        "web/app.py",
        "web/templates/index.html"
    ]
    
    all_passed = True
    
    # 检查目录
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print_result(f"目录: {dir_path}", True)
        else:
            print_result(f"目录: {dir_path}", False, "目录不存在")
            all_passed = False
    
    # 检查文件
    for file_path in required_files:
        if Path(file_path).exists():
            print_result(f"文件: {file_path}", True)
        else:
            print_result(f"文件: {file_path}", False, "文件不存在")
            all_passed = False
    
    return all_passed


def test_chess_analyzer():
    """测试象棋分析器"""
    print_header("测试象棋分析器")
    
    try:
        from src.chess_analyzer import XiangqiAnalyzer
        
        # 测试创建分析器（不初始化引擎）
        logger.info("测试分析器类结构...")
        
        # 检查必要的类和方法
        analyzer_methods = [
            '__init__',
            'analyze_image',
            'format_analysis_result',
            'quit'
        ]
        
        for method in analyzer_methods:
            if hasattr(XiangqiAnalyzer, method):
                print_result(f"方法: {method}", True)
            else:
                print_result(f"方法: {method}", False, "方法不存在")
        
        # 测试常量
        from src.chess_analyzer import CATEGORY_MAP, CATEGORY_MAP_REVERSE
        print_result("棋子映射表", True)
        
        return True
        
    except Exception as e:
        print_result("象棋分析器", False, str(e))
        return False


def test_stream_processor():
    """测试流处理器"""
    print_header("测试流处理器")
    
    try:
        from src.stream_processor import RTMPStreamProcessor, ScreenCapture, EmulatorCapture
        
        # 测试类
        classes = [
            ("RTMPStreamProcessor", RTMPStreamProcessor),
            ("ScreenCapture", ScreenCapture),
            ("EmulatorCapture", EmulatorCapture)
        ]
        
        for name, cls in classes:
            print_result(f"类: {name}", True)
        
        # 测试便捷函数
        from src.stream_processor import create_stream_processor, create_emulator_capture, create_screen_capture
        
        funcs = [
            ("create_stream_processor", create_stream_processor),
            ("create_emulator_capture", create_emulator_capture),
            ("create_screen_capture", create_screen_capture)
        ]
        
        for name, func in funcs:
            if callable(func):
                print_result(f"函数: {name}", True)
            else:
                print_result(f"函数: {name}", False, "不可调用")
        
        return True
        
    except Exception as e:
        print_result("流处理器", False, str(e))
        return False


def test_tunnel_service():
    """测试内网穿透服务"""
    print_header("测试内网穿透服务")
    
    try:
        from src.tunnel_service import TunnelManager, NgrokTunnel, FrpTunnel
        
        # 测试类
        classes = [
            ("TunnelManager", TunnelManager),
            ("NgrokTunnel", NgrokTunnel),
            ("FrpTunnel", FrpTunnel)
        ]
        
        for name, cls in classes:
            print_result(f"类: {name}", True)
        
        # 测试便捷函数
        from src.tunnel_service import create_ngrok_tunnel, create_frp_tunnel
        
        if callable(create_ngrok_tunnel):
            print_result("函数: create_ngrok_tunnel", True)
        else:
            print_result("函数: create_ngrok_tunnel", False)
        
        if callable(create_frp_tunnel):
            print_result("函数: create_frp_tunnel", True)
        else:
            print_result("函数: create_frp_tunnel", False)
        
        return True
        
    except Exception as e:
        print_result("内网穿透服务", False, str(e))
        return False


def test_web_app():
    """测试Web应用"""
    print_header("测试Web应用")
    
    try:
        from web.app import app, socketio
        
        # 测试Flask应用
        if isinstance(app, type(type)) and hasattr(app, 'run'):
            print_result("Flask应用", True)
        else:
            print_result("Flask应用", False, "Flask应用创建失败")
        
        # 测试SocketIO
        if socketio is not None:
            print_result("SocketIO", True)
        else:
            print_result("SocketIO", False, "SocketIO未初始化")
        
        # 测试路由
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ['/', '/login', '/settings', '/logout']
        
        for route in expected_routes:
            if route in rules:
                print_result(f"路由: {route}", True)
            else:
                print_result(f"路由: {route}", False, "路由不存在")
        
        return True
        
    except Exception as e:
        print_result("Web应用", False, str(e))
        return False


def test_dependencies():
    """测试依赖版本"""
    print_header("测试依赖版本")
    
    import sys
    import cv2
    import numpy as np
    
    # Python版本
    python_version = sys.version
    version_ok = sys.version_info >= (3, 7)
    print_result(f"Python版本: {python_version}", version_ok)
    
    # OpenCV版本
    opencv_version = cv2.__version__
    opencv_ok = cv2.__version__ >= "4.5.0"
    print_result(f"OpenCV版本: {opencv_version}", opencv_ok)
    
    # NumPy版本
    numpy_version = np.__version__
    numpy_ok = np.__version__ >= "1.21.0"
    print_result(f"NumPy版本: {numpy_version}", numpy_ok)
    
    return version_ok and opencv_ok and numpy_ok


def test_main_program():
    """测试主程序"""
    print_header("测试主程序")
    
    try:
        # 测试main.py是否存在
        if Path("main.py").exists():
            print_result("main.py文件", True)
        else:
            print_result("main.py文件", False, "文件不存在")
            return False
        
        # 测试XiangqiAnalyzerService类
        exec(open("main.py").read().split("if __name__ == '__main__':")[0])
        
        # 检查必要的类
        if 'XiangqiAnalyzerService' in locals():
            print_result("XiangqiAnalyzerService类", True)
        else:
            print_result("XiangqiAnalyzerService类", False, "类未定义")
        
        return True
        
    except Exception as e:
        print_result("主程序", False, str(e))
        return False


def generate_summary(results):
    """生成测试摘要"""
    print_header("测试摘要")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r)
    failed_tests = total_tests - passed_tests
    
    print(f"总测试数: {total_tests}")
    print(f"通过: {Colors.GREEN}{passed_tests}{Colors.RESET}")
    print(f"失败: {Colors.RED}{failed_tests}{Colors.RESET}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！系统已准备好运行。{Colors.RESET}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败，请检查上面的错误信息。{Colors.RESET}")
        print(f"\n{Colors.YELLOW}提示: 如果某些模块失败，系统可能仍然可以运行，但功能会受到限制。{Colors.RESET}")
        return False


def main():
    """主函数"""
    print_header("中国象棋AI分析器 - 系统测试")
    
    # 运行所有测试
    test_results = []
    
    test_results.append(test_imports())
    test_results.append(test_directory_structure())
    test_results.append(test_chess_analyzer())
    test_results.append(test_stream_processor())
    test_results.append(test_tunnel_service())
    test_results.append(test_web_app())
    test_results.append(test_dependencies())
    test_results.append(test_main_program())
    
    # 生成摘要
    success = generate_summary(test_results)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()