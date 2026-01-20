#!/usr/bin/env python3
"""
中国象棋AI分析器主程序
整合棋盘检测、引擎分析和Web界面
"""

import os
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

from src.chess_analyzer import XiangqiAnalyzer
from src.stream_processor import RTMPStreamProcessor, EmulatorCapture, create_screen_capture
from src.tunnel_service import TunnelManager, create_ngrok_tunnel, create_frp_tunnel
from web.app import app, socketio, init_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/xiangqi_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量
analyzer = None
stream_processor = None
emulator_capture = None
tunnel_manager = None
running = False
config = {}


class XiangqiAnalyzerService:
    """中国象棋分析器服务类"""
    
    def __init__(self):
        self.analyzer = None
        self.stream_processor = None
        self.emulator_capture = None
        self.capture_thread = None
        self.analysis_thread = None
        self.running = False
        self.latest_result = None
        
        # 默认配置
        self.config = {
            'engine_path': '',
            'pose_model_path': 'onnx/pose/4_v6-0301.onnx',
            'classifier_model_path': 'onnx/layout_recognition/nano_v3-0319.onnx',
            'source_type': 'file',
            'source_value': '',
            'think_time': 2000,
            'analysis_interval': 3,
            'enable_tunnel': False,
            'tunnel_type': 'ngrok',
            'tunnel_config': {}
        }
    
    def load_config(self, config_file: str = 'config/config.json'):
        """加载配置文件"""
        try:
            import json
            config_path = Path(config_file)
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    logger.info(f"配置文件已加载: {config_file}")
            else:
                logger.warning(f"配置文件不存在: {config_file}")
                
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def save_config(self, config_file: str = 'config/config.json'):
        """保存配置文件"""
        try:
            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                logger.info(f"配置文件已保存: {config_file}")
                
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def initialize_analyzer(self) -> bool:
        """初始化分析器"""
        try:
            if not self.config['engine_path']:
                logger.error("未配置Pikafish引擎路径")
                return False
            
            if not Path(self.config['engine_path']).exists():
                logger.error(f"Pikafish引擎不存在: {self.config['engine_path']}")
                return False
            
            self.analyzer = XiangqiAnalyzer(
                engine_path=self.config['engine_path'],
                pose_model_path=self.config['pose_model_path'],
                classifier_model_path=self.config['classifier_model_path']
            )
            
            logger.info("✅ 分析器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"初始化分析器失败: {e}")
            return False
    
    def start_capture(self) -> bool:
        """启动捕获"""
        try:
            if self.config['source_type'] == 'stream':
                if not self.config['source_value']:
                    logger.error("未配置流地址")
                    return False
                
                self.stream_processor = RTMPStreamProcessor(self.config['source_value'])
                if not self.stream_processor.start():
                    return False
            
            elif self.config['source_type'] == 'emulator':
                from core.stream_processor import EmulatorCapture
                emulator_name = self.config.get('source_value', 'MuMu')
                self.emulator_capture = EmulatorCapture(emulator_name)
            
            elif self.config['source_type'] == 'screen':
                self.screen_capture = create_screen_capture()
            
            self.running = True
            
            # 启动捕获线程
            self.capture_thread = Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            # 启动分析线程
            self.analysis_thread = Thread(target=self._analysis_loop, daemon=True)
            self.analysis_thread.start()
            
            logger.info("✅ 捕获已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动捕获失败: {e}")
            return False
    
    def stop_capture(self):
        """停止捕获"""
        self.running = False
        
        if self.stream_processor:
            self.stream_processor.stop()
            self.stream_processor = None
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
        
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        
        logger.info("✅ 捕获已停止")
    
    def _capture_loop(self):
        """捕获循环"""
        while self.running:
            try:
                frame = None
                
                if self.config['source_type'] == 'stream' and self.stream_processor:
                    frame = self.stream_processor.get_latest_frame()
                
                elif self.config['source_type'] == 'emulator' and self.emulator_capture:
                    frame = self.emulator_capture.capture()
                
                elif self.config['source_type'] == 'screen':
                    region = self.config.get('screen_region')
                    if region:
                        # 解析区域
                        try:
                            region_parts = region.split(',')
                            region_tuple = tuple(map(int, region_parts))
                            frame = self.screen_capture.capture_window(region=region_tuple)
                        except:
                            frame = self.screen_capture.capture_window()
                    else:
                        frame = self.screen_capture.capture_window()
                
                # 处理捕获的帧
                if frame is not None and self.analyzer:
                    result = self.analyzer.analyze_image(frame, self.config['think_time'])
                    
                    if result:
                        self.latest_result = result
                        logger.info(f"分析完成 - 最佳走法: {result['best_move']}")
                
                time.sleep(self.config['analysis_interval'])
                
            except Exception as e:
                logger.error(f"捕获循环出错: {e}")
                time.sleep(1)
    
    def _analysis_loop(self):
        """分析循环"""
        # 这个循环可以与捕获循环合并
        # 这里保留用于扩展功能
        pass
    
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
            'running': self.running,
            'config': self.config,
            'latest_result': self.latest_result
        }
        
        if self.tunnel_manager:
            status['tunnel_status'] = self.tunnel_manager.get_status()
        
        return status
    
    def cleanup(self):
        """清理资源"""
        self.stop_capture()
        self.stop_tunnel()
        
        if self.analyzer:
            self.analyzer.quit()
        
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
                        default='ngrok', help='内网穿透类型 (默认: ngrok)')
    
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


def create_default_config():
    """创建默认配置文件"""
    default_config = {
        'engine_path': '',
        'pose_model_path': 'onnx/pose/4_v6-0301.onnx',
        'classifier_model_path': 'onnx/layout_recognition/nano_v3-0319.onnx',
        'source_type': 'file',
        'source_value': '',
        'think_time': 2000,
        'analysis_interval': 3,
        'enable_tunnel': False,
        'tunnel_type': 'ngrok',
        'tunnel_config': {
            'auth_token': '',
            'region': 'ap'
        }
    }
    
    config_dir = Path('config')
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / 'config.json'
    
    import json
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"默认配置文件已创建: {config_file}")
    return str(config_file)


def main():
    """主函数"""
    global service
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建日志目录
    Path('logs').mkdir(exist_ok=True)
    
    # 创建服务实例
    service = XiangqiAnalyzerService()
    
    # 加载或创建配置文件
    if not Path(args.config).exists():
        logger.info(f"配置文件不存在，创建默认配置")
        args.config = create_default_config()
    
    service.load_config(args.config)
    
    # 应用命令行参数
    if args.engine_path:
        service.config['engine_path'] = args.engine_path
    
    if args.source_type:
        service.config['source_type'] = args.source_type
    
    if args.source_value:
        service.config['source_value'] = args.source_value
    
    if args.enable_tunnel:
        service.config['enable_tunnel'] = True
        if args.tunnel_token:
            service.config['tunnel_config']['auth_token'] = args.tunnel_token
    
    if args.tunnel_type:
        service.config['tunnel_type'] = args.tunnel_type
    
    # 设置信号处理器
    setup_signal_handlers()
    
    # 打印配置信息
    logger.info("=" * 60)
    logger.info("中国象棋AI分析器")
    logger.info("=" * 60)
    logger.info(f"配置文件: {args.config}")
    logger.info(f"信号源类型: {service.config['source_type']}")
    logger.info(f"信号源值: {service.config['source_value'] or '未配置'}")
    logger.info(f"内网穿透: {'启用' if service.config['enable_tunnel'] else '禁用'}")
    logger.info("=" * 60)
    
    # 启动内网穿透（如果启用）
    if service.config['enable_tunnel']:
        service.start_tunnel()
    
    # 初始化应用
    init_app()
    
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