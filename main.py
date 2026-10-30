#!/usr/bin/env python3
"""
中国象棋AI分析器主程序
整合棋盘检测、引擎分析和Web界面
"""

import sys
import argparse
import logging
import signal
import time
from pathlib import Path
from threading import Thread
import webbrowser

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 日志目录必须在配置日志之前创建，否则文件日志会创建失败
Path('logs').mkdir(exist_ok=True)

from src.config import (check_config, create_default_config_file, default_config,
                        load_config, merge_cli_args, save_config)
from src.tunnel_service import create_ngrok_tunnel, create_frp_tunnel
from web.app import app, socketio, init_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/xiangqi_analyzer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量
service = None


class XiangqiAnalyzerService:
    """中国象棋分析器服务类"""

    def __init__(self):
        self.config = default_config()
        self.tunnel_manager = None
        self.latest_result = None

    def load_config(self, config_file: str = 'config/config.json'):
        """加载配置文件

        Args:
            config_file: 配置文件路径
        """
        self.config = load_config(config_file)

    def save_config(self, config_file: str = 'config/config.json'):
        """保存配置文件

        Args:
            config_file: 配置文件路径
        """
        return save_config(self.config, config_file)

    def start_tunnel(self) -> bool:
        """启动内网穿透"""
        try:
            if not self.config.get('enable_tunnel', False):
                logger.info("内网穿透未启用")
                return False

            tunnel_config = self.config.get('tunnel_config', {})

            if self.config['tunnel_type'] == 'ngrok':
                self.tunnel_manager = create_ngrok_tunnel(
                    auth_token=tunnel_config.get('auth_token'),
                    region=tunnel_config.get('region', 'ap')
                )

            elif self.config['tunnel_type'] == 'frp':
                self.tunnel_manager = create_frp_tunnel(
                    server_addr=tunnel_config.get('server_addr', ''),
                    server_port=tunnel_config.get('server_port', 7000),
                    token=tunnel_config.get('token'),
                    subdomain=tunnel_config.get('subdomain')
                )

            else:
                logger.error(f"不支持的内网穿透类型: {self.config['tunnel_type']}")
                return False

            if self.tunnel_manager.start(5000):
                public_url = self.tunnel_manager.get_public_url()
                logger.info(f"✅ 内网穿透已启动 - 公网URL: {public_url}")
                return True
            else:
                logger.error("启动内网穿透失败")
                return False

        except Exception as e:
            logger.error(f"启动内网穿透失败: {e}")
            return False

    def stop_tunnel(self):
        """停止内网穿透"""
        if self.tunnel_manager:
            self.tunnel_manager.stop()
            self.tunnel_manager = None
            logger.info("✅ 内网穿透已停止")

    def get_status(self) -> dict:
        """获取服务状态"""
        status = {
            'config': self.config,
            'latest_result': self.latest_result
        }

        if self.tunnel_manager:
            status['tunnel_status'] = self.tunnel_manager.get_status()

        return status

    def cleanup(self):
        """清理资源"""
        self.stop_tunnel()
        logger.info("✅ 服务已清理")


def signal_handler(signum, frame):
    """信号处理器"""
    logger.info(f"接收到信号 {signum}，正在关闭服务...")
    if service:
        service.cleanup()
    sys.exit(0)


def setup_signal_handlers():
    """设置信号处理器"""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='中国象棋AI分析器 - 实时棋盘检测和走法推荐',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用默认配置启动
  python main.py
  
  # 指定配置文件
  python main.py --config config/my_config.json
  
  # 指定引擎路径和信号源
  python main.py --engine-path /path/to/pikafish --source-type emulator
  
  # 启用内网穿透
  python main.py --enable-tunnel --tunnel-token your_token
        """
    )
    
    parser.add_argument('--config', '-c', default='config/config.json',
                        help='配置文件路径 (默认: config/config.json)')
    
    parser.add_argument('--engine-path', '-e',
                        help='Pikafish引擎路径')
    
    parser.add_argument('--source-type', '-s', 
                        choices=['file', 'stream', 'emulator', 'screen'],
                        help='信号源类型')
    
    parser.add_argument('--source-value', '-v',
                        help='信号源值 (流地址、模拟器名称等)')
    
    parser.add_argument('--enable-tunnel', action='store_true',
                        help='启用内网穿透')
    
    parser.add_argument('--tunnel-type', choices=['ngrok', 'frp'],
                        help='内网穿透类型 (默认: ngrok)')
    
    parser.add_argument('--tunnel-token',
                        help='内网穿透认证令牌')
    
    parser.add_argument('--port', '-p', type=int, default=5000,
                        help='Web服务器端口 (默认: 5000)')
    
    parser.add_argument('--host', default='0.0.0.0',
                        help='Web服务器主机 (默认: 0.0.0.0)')
    
    parser.add_argument('--no-browser', action='store_true',
                        help='不自动打开浏览器')
    
    parser.add_argument('--debug', action='store_true',
                        help='启用调试模式')
    
    return parser.parse_args()


def main():
    """主函数"""
    global service
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建服务实例
    service = XiangqiAnalyzerService()
    
    # 加载或创建配置文件
    if not Path(args.config).exists():
        logger.info("配置文件不存在，创建默认配置")
        args.config = create_default_config_file(args.config)
    
    service.load_config(args.config)
    
    # 应用命令行参数（命令行优先级高于配置文件）
    service.config = merge_cli_args(service.config, args)
    
    # 检查配置完整性（只提示，不阻止启动）
    for problem in check_config(service.config):
        logger.warning(f"配置检查: {problem}")
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 打印配置信息
    logger.info("=" * 60)
    logger.info("中国象棋AI分析器")
    logger.info("=" * 60)
    logger.info(f"配置文件: {args.config}")
    logger.info(f"引擎路径: {service.config['engine_path'] or '未配置'}")
    logger.info(f"信号源类型: {service.config['source_type']}")
    logger.info(f"信号源值: {service.config['source_value'] or '未配置'}")
    logger.info(f"内网穿透: {'启用' if service.config['enable_tunnel'] else '禁用'}")
    logger.info("=" * 60)
    
    # 启动内网穿透（如果启用）
    if service.config['enable_tunnel']:
        service.start_tunnel()
    
    # 初始化应用，并把配置交给 Web 层统一管理
    service.config = init_app(service.config, config_file_path=args.config)
    
    # 启动Web服务器
    logger.info(f"启动Web服务器: http://{args.host}:{args.port}")
    
    # 自动打开浏览器
    if not args.no_browser:
        def open_browser():
            time.sleep(2)
            webbrowser.open(f'http://localhost:{args.port}')
        
        Thread(target=open_browser, daemon=True).start()
    
    try:
        # 运行Flask应用
        socketio.run(app, host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        logger.info("接收到中断信号")
    finally:
        # 清理资源
        service.cleanup()
        logger.info("服务已停止")


if __name__ == '__main__':
    main()
