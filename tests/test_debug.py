#!/usr/bin/env python3
"""
通用调试脚本
用于测试各个模块的功能
"""

import os
import sys
from pathlib import Path
import logging
import traceback

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 颜色输出
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
    
    modules = [
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("flask", "Flask"),
        ("src.chess_analyzer", "象棋分析器"),
        ("src.stream_processor", "流处理器"),
        ("src.tunnel_service", "内网穿透"),
        ("src.web.app", "Web应用"),
    ]
    
    results = []
    for module_name, display_name in modules:
        try:
            if '.' in module_name:
                exec(f"import {module_name}")
            else:
                __import__(module_name)
            print_result(f"导入: {display_name}", True)
            results.append(True)
        except ImportError as e:
            print_result(f"导入: {display_name}", False, str(e))
            results.append(False)
    
    return all(results)


def test_paths():
    """测试路径"""
    print_header("测试路径")
    
    paths = [
        "src",
        "src/chess_analyzer.py",
        "src/stream_processor.py", 
        "src/tunnel_service.py",
        "web/app.py",
        "web/templates",
        "config",
        "tests",
        "logs",
    ]
    
    results = []
    for path in paths:
        if Path(path).exists():
            print_result(f"路径: {path}", True)
            results.append(True)
        else:
            print_result(f"路径: {path}", False, "路径不存在")
            results.append(False)
    
    return all(results)


def test_chess_analyzer():
    """测试象棋分析器"""
    print_header("测试象棋分析器")
    
    try:
        from src.chess_analyzer import XiangqiAnalyzer, PikafishEngine
        
        # 测试PikafishEngine类
        print_result("PikafishEngine类", True)
        
        # 测试XiangqiAnalyzer类
        print_result("XiangqiAnalyzer类", True)
        
        # 检查必需的方法
        methods = ['analyze_image', 'format_analysis_result', 'quit']
        for method in methods:
            if hasattr(XiangqiAnalyzer, method):
                print_result(f"方法: {method}", True)
            else:
                print_result(f"方法: {method}", False, "方法不存在")
        
        return True
        
    except Exception as e:
        print_result("象棋分析器", False, str(e))
        logger.error(traceback.format_exc())
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
        logger.error(traceback.format_exc())
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
        logger.error(traceback.format_exc())
        return False


def test_web_app():
    """测试Web应用"""
    print_header("测试Web应用")
    
    try:
        from src.web.app import app, socketio
        
        # 测试Flask应用
        if hasattr(app, 'run'):
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
        logger.error(traceback.format_exc())
        return False


def test_config():
    """测试配置"""
    print_header("测试配置")
    
    config_file = "config/config.json"
    example_file = "config/config.example.json"
    
    # 检查配置文件
    if Path(config_file).exists():
        print_result(f"配置文件: {config_file}", True)
    else:
        print_result(f"配置文件: {config_file}", False, "使用默认配置")
    
    # 检查示例文件
    if Path(example_file).exists():
        print_result(f"示例文件: {example_file}", True)
    else:
        print_result(f"示例文件: {example_file}", False, "示例文件不存在")
    
    return True


def test_logging():
    """测试日志系统"""
    print_header("测试日志系统")
    
    try:
        # 测试日志目录
        log_dir = Path("logs")
        if not log_dir.exists():
            log_dir.mkdir(exist_ok=True)
            print_result("日志目录", True, "已创建")
        else:
            print_result("日志目录", True, "已存在")
        
        # 测试日志文件
        log_file = log_dir / "test.log"
        
        # 配置测试日志
        test_logger = logging.getLogger("test")
        test_logger.setLevel(logging.DEBUG)
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
        
        # 测试写入日志
        test_logger.info("测试日志信息")
        test_logger.debug("测试日志调试")
        test_logger.warning("测试日志警告")
        test_logger.error("测试日志错误")
        
        # 检查日志文件
        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
                if "测试日志" in content:
                    print_result("日志写入", True, "日志正常写入")
                else:
                    print_result("日志写入", False, "日志内容不正确")
        else:
            print_result("日志写入", False, "日志文件未创建")
        
        # 清理测试日志
        log_file.unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        print_result("日志系统", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    print_header("运行所有测试")
    
    tests = [
        ("模块导入", test_imports),
        ("路径检查", test_paths),
        ("象棋分析器", test_chess_analyzer),
        ("流处理器", test_stream_processor),
        ("内网穿透", test_tunnel_service),
        ("Web应用", test_web_app),
        ("配置检查", test_config),
        ("日志系统", test_logging),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print_result(test_name, False, f"测试异常: {e}")
            logger.error(traceback.format_exc())
            results.append(False)
    
    # 总结
    print_header("测试总结")
    
    passed = sum(results)
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过: {Colors.GREEN}{passed}{Colors.RESET}")
    print(f"失败: {Colors.RED}{total - passed}{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ 所有测试通过！系统运行正常。{Colors.RESET}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ 部分测试失败，请查看上面的错误信息。{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}调试建议:{Colors.RESET}")
        print("1. 查看详细日志: tail -f logs/xiangqi_analyzer.log")
        print("2. 运行特定测试: python tests/test_debug.py")
        print("3. 启用调试模式: python main.py --debug")
        print("4. 检查配置文件: config/config.json")
        
        return False


def interactive_debug():
    """交互式调试"""
    print_header("交互式调试")
    
    print("选择要调试的模块:")
    print("1. Pikafish引擎")
    print("2. 棋盘检测器")
    print("3. 流处理器")
    print("4. Web应用")
    print("5. 退出")
    
    choice = input("\n请输入选项 (1-5): ").strip()
    
    if choice == "1":
        engine_path = input("请输入引擎路径: ").strip()
        if engine_path:
            os.system(f"python tests/test_pikafish.py {engine_path}")
    elif choice == "2":
        print("棋盘检测器测试...")
        # TODO: 添加检测器测试
    elif choice == "3":
        print("流处理器测试...")
        # TODO: 添加流处理器测试
    elif choice == "4":
        print("Web应用测试...")
        # TODO: 添加Web应用测试
    elif choice == "5":
        print("退出调试")
    else:
        print("无效选项")


def main():
    """主函数"""
    print_header("通用调试工具")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--interactive":
            interactive_debug()
        elif sys.argv[1] == "--all":
            run_all_tests()
        else:
            print(f"未知选项: {sys.argv[1]}")
            print("使用 --interactive 进行交互式调试")
            print("使用 --all 运行所有测试")
    else:
        # 默认运行所有测试
        success = run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()