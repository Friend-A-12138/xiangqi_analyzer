#!/usr/bin/env python3
"""
Pikafish引擎测试脚本
用于测试引擎是否正常工作和权限问题
"""

import os
import sys
import subprocess
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


def test_engine_permissions(engine_path):
    """测试引擎权限"""
    print_header("测试引擎权限")
    
    engine_path = Path(engine_path)
    
    # 检查文件是否存在
    if not engine_path.exists():
        print_result("文件存在性", False, f"文件不存在: {engine_path}")
        return False
    
    print_result("文件存在性", True, f"文件存在: {engine_path}")
    
    # 检查是否为文件
    if not engine_path.is_file():
        print_result("文件类型", False, "这不是一个文件")
        return False
    
    print_result("文件类型", True, "这是一个文件")
    
    # 检查执行权限 (Unix/Linux/macOS)
    if os.name != 'nt':  # 非Windows
        if not os.access(engine_path, os.X_OK):
            print_result("执行权限", False, "没有执行权限")
            print(f"  {Colors.YELLOW}解决方法: chmod +x {engine_path}{Colors.RESET}")
            return False
        else:
            print_result("执行权限", True, "有执行权限")
    else:
        print_result("执行权限", True, "Windows系统，跳过权限检查")
    
    # 检查文件大小
    file_size = engine_path.stat().st_size
    if file_size < 1000:  # 小于1KB，可能是空文件或链接
        print_result("文件大小", False, f"文件太小: {file_size} bytes")
        return False
    
    print_result("文件大小", True, f"文件大小: {file_size:,} bytes")
    
    return True


def test_engine_execution(engine_path):
    """测试引擎执行"""
    print_header("测试引擎执行")
    
    try:
        # 尝试启动引擎
        logger.info(f"尝试启动引擎: {engine_path}")
        
        # Windows下需要设置creationflags
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        
        process = subprocess.Popen(
            [str(engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=creation_flags
        )
        
        # 发送UCI命令
        logger.info("发送UCI命令...")
        process.stdin.write("uci\n")
        process.stdin.flush()
        
        # 等待响应
        logger.info("等待引擎响应...")
        start_time = time.time()
        while time.time() - start_time < 5:  # 5秒超时
            line = process.stdout.readline().strip()
            if line:
                logger.info(f"引擎输出: {line}")
                if "uciok" in line.lower():
                    print_result("UCI协议", True, "引擎响应正常")
                    break
        else:
            print_result("UCI协议", False, "引擎响应超时")
            process.kill()
            return False
        
        # 测试象棋变体设置
        logger.info("设置象棋变体...")
        process.stdin.write("setoption name UCI_Variant value xiangqi\n")
        process.stdin.flush()
        
        # 发送isready命令
        process.stdin.write("isready\n")
        process.stdin.flush()
        
        start_time = time.time()
        while time.time() - start_time < 5:
            line = process.stdout.readline().strip()
            if line:
                logger.info(f"引擎输出: {line}")
                if "readyok" in line.lower():
                    print_result("准备状态", True, "引擎准备就绪")
                    break
        else:
            print_result("准备状态", False, "引擎准备超时")
            process.kill()
            return False
        
        # 退出引擎
        process.stdin.write("quit\n")
        process.stdin.flush()
        process.wait(timeout=2)
        
        print_result("引擎退出", True, "引擎正常退出")
        return True
        
    except FileNotFoundError:
        print_result("引擎执行", False, "找不到引擎文件")
        return False
    except PermissionError:
        print_result("引擎执行", False, "没有执行权限（PermissionError）")
        if os.name != 'nt':
            print(f"  {Colors.YELLOW}解决方法: chmod +x {engine_path}{Colors.RESET}")
        return False
    except Exception as e:
        print_result("引擎执行", False, f"发生错误: {e}")
        return False


def test_engine_path_resolution(engine_path):
    """测试引擎路径解析"""
    print_header("测试路径解析")
    
    # 测试绝对路径
    abs_path = Path(engine_path).resolve()
    print(f"绝对路径: {abs_path}")
    
    # 测试相对路径
    if not Path(engine_path).is_absolute():
        rel_path = Path.cwd() / engine_path
        print(f"相对路径解析: {rel_path}")
        if rel_path.exists():
            print_result("相对路径", True, f"找到文件: {rel_path}")
        else:
            print_result("相对路径", False, "文件不存在")
    
    # 测试PATH环境变量
    if os.name != 'nt':
        which_result = subprocess.run(['which', 'pikafish'], 
                                    capture_output=True, text=True)
        if which_result.returncode == 0:
            print_result("PATH查找", True, f"找到: {which_result.stdout.strip()}")
        else:
            print_result("PATH查找", True, "未在PATH中找到（正常）")
    
    return True


def test_common_paths():
    """测试常见路径"""
    print_header("测试常见路径")
    
    common_paths = []
    
    if os.name == 'nt':  # Windows
        common_paths = [
            "pikafish.exe",
            "pikafish-windows-x86_64.exe",
            "C:/Program Files/Pikafish/pikafish.exe",
            "C:/Users/Public/Pikafish/pikafish.exe",
            "./pikafish.exe",
            "../pikafish.exe"
        ]
    else:  # Linux/macOS
        common_paths = [
            "pikafish",
            "pikafish-linux-x86_64",
            "pikafish-osx-x86_64",
            "/usr/local/bin/pikafish",
            "/usr/bin/pikafish",
            "./pikafish",
            "../pikafish"
        ]
    
    found_paths = []
    for path in common_paths:
        if Path(path).exists():
            print_result(f"路径测试: {path}", True, "文件存在")
            found_paths.append(path)
        else:
            print_result(f"路径测试: {path}", False, "文件不存在")
    
    if found_paths:
        print(f"\n{Colors.GREEN}找到以下路径:{Colors.RESET}")
        for path in found_paths:
            print(f"  - {path}")
    
    return len(found_paths) > 0


def generate_diagnosis_report(engine_path, test_results):
    """生成诊断报告"""
    print_header("诊断报告")
    
    print(f"引擎路径: {engine_path}")
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"操作系统: {sys.platform}")
    print(f"Python版本: {sys.version}")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n测试结果: {passed}/{total}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ 引擎测试通过！可以正常使用。{Colors.RESET}")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ 引擎测试未通过，请查看上面的错误信息。{Colors.RESET}")
        
        print(f"\n{Colors.YELLOW}常见问题解决:{Colors.RESET}")
        print("1. 权限问题:")
        if os.name != 'nt':
            print("   chmod +x /path/to/pikafish")
        else:
            print("   右键属性 → 安全 → 完全控制")
        
        print("2. 路径问题:")
        print("   使用绝对路径: /full/path/to/pikafish")
        print("   或确保相对路径正确")
        
        print("3. 文件完整性:")
        print("   重新下载引擎文件")
        print("   确保文件没有被损坏")
        
        return False


def main():
    """主函数"""
    print_header("Pikafish引擎测试工具")
    
    # 从命令行获取引擎路径，或使用默认路径
    if len(sys.argv) > 1:
        engine_path = sys.argv[1]
    else:
        # 默认路径
        if os.name == 'nt':  # Windows
            engine_path = "pikafish.exe"
        else:
            engine_path = "pikafish"
    
    print(f"测试引擎: {engine_path}")
    
    # 运行测试
    test_results = []
    
    test_results.append(test_engine_permissions(engine_path))
    test_results.append(test_engine_path_resolution(engine_path))
    test_results.append(test_common_paths())
    test_results.append(test_engine_execution(engine_path))
    
    # 生成诊断报告
    success = generate_diagnosis_report(engine_path, test_results)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()