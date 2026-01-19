"""
内网穿透服务
支持通过ngrok或frp实现内网穿透
"""

import subprocess
import time
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import requests
import json
import threading
import queue

logger = logging.getLogger(__name__)


class TunnelService:
    """内网穿透服务基类"""
    
    def __init__(self):
        self.process = None
        self.running = False
        self.public_url = None
    
    def start(self) -> bool:
        """启动内网穿透服务"""
        raise NotImplementedError
    
    def stop(self):
        """停止内网穿透服务"""
        raise NotImplementedError
    
    def get_public_url(self) -> Optional[str]:
        """获取公网URL"""
        return self.public_url
    
    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        return self.running and self.process is not None


class NgrokTunnel(TunnelService):
    """ngrok内网穿透服务"""
    
    def __init__(self, auth_token: str = None, region: str = 'ap'):
        """
        初始化ngrok服务
        
        Args:
            auth_token: ngrok认证令牌
            region: 区域 (us, eu, ap, au, sa, jp, in)
        """
        super().__init__()
        self.auth_token = auth_token
        self.region = region
        self.port = 5000
        self.tunnel_info = None
    
    def start(self, port: int = 5000) -> bool:
        """启动ngrok服务"""
        try:
            self.port = port
            
            # 检查ngrok是否已安装
            result = subprocess.run(['ngrok', 'version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("ngrok未安装或未添加到PATH")
                return False
            
            # 如果有认证令牌，先进行认证
            if self.auth_token:
                subprocess.run(['ngrok', 'authtoken', self.auth_token], 
                             capture_output=True)
            
            # 启动ngrok
            self.process = subprocess.Popen(
                ['ngrok', 'http', str(port), '--region', self.region],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待ngrok启动
            time.sleep(3)
            
            # 获取隧道信息
            if self._get_tunnel_info():
                self.running = True
                logger.info(f"✅ ngrok已启动 - 公网URL: {self.public_url}")
                return True
            else:
                logger.error("无法获取ngrok隧道信息")
                self.stop()
                return False
                
        except FileNotFoundError:
            logger.error("ngrok命令未找到，请先安装ngrok")
            return False
        except Exception as e:
            logger.error(f"启动ngrok失败: {e}")
            return False
    
    def _get_tunnel_info(self) -> bool:
        """从ngrok API获取隧道信息"""
        try:
            # ngrok的本地API
            response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                
                if tunnels:
                    # 获取第一个HTTP隧道的公网URL
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'https':
                            self.public_url = tunnel.get('public_url')
                            self.tunnel_info = tunnel
                            return True
                    
                    # 如果没有HTTPS隧道，使用HTTP
                    for tunnel in tunnels:
                        if tunnel.get('proto') == 'http':
                            self.public_url = tunnel.get('public_url')
                            self.tunnel_info = tunnel
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"获取ngrok隧道信息失败: {e}")
            return False
    
    def stop(self):
        """停止ngrok服务"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("ngrok已停止")
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"停止ngrok失败: {e}")
            finally:
                self.process = None
                self.running = False
                self.public_url = None
                self.tunnel_info = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            'running': self.running,
            'public_url': self.public_url,
            'region': self.region,
            'port': self.port
        }
        
        if self.tunnel_info:
            status['tunnel_info'] = self.tunnel_info
        
        return status


class FrpTunnel(TunnelService):
    """frp内网穿透服务"""
    
    def __init__(self, server_addr: str, server_port: int = 7000, 
                 token: str = None, subdomain: str = None):
        """
        初始化frp服务
        
        Args:
            server_addr: frp服务器地址
            server_port: frp服务器端口
            token: 访问令牌
            subdomain: 子域名
        """
        super().__init__()
        self.server_addr = server_addr
        self.server_port = server_port
        self.token = token
        self.subdomain = subdomain
        self.port = 5000
        self.config_file = None
    
    def start(self, port: int = 5000) -> bool:
        """启动frp服务"""
        try:
            self.port = port
            
            # 检查frpc是否已安装
            result = subprocess.run(['frpc', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.error("frpc未安装或未添加到PATH")
                return False
            
            # 创建frp配置文件
            self.config_file = self._create_config_file()
            
            if not self.config_file:
                logger.error("创建frp配置文件失败")
                return False
            
            # 启动frpc
            self.process = subprocess.Popen(
                ['frpc', '-c', str(self.config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待frp启动
            time.sleep(5)
            
            # 检查进程是否还在运行
            if self.process.poll() is None:
                self.running = True
                self.public_url = f"http://{self.subdomain}.{self.server_addr}"
                logger.info(f"✅ frp已启动 - 公网URL: {self.public_url}")
                return True
            else:
                logger.error("frp启动失败")
                return False
                
        except FileNotFoundError:
            logger.error("frpc命令未找到，请先安装frp")
            return False
        except Exception as e:
            logger.error(f"启动frp失败: {e}")
            return False
    
    def _create_config_file(self) -> Optional[Path]:
        """创建frp配置文件"""
        try:
            config_dir = Path.home() / '.xiangqi_analyzer' / 'frp'
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / 'frpc.ini'
            
            config_content = f"""[common]
server_addr = {self.server_addr}
server_port = {self.server_port}
"""
            
            if self.token:
                config_content += f"token = {self.token}\n"
            
            config_content += f"""
[web]
type = http
local_port = {self.port}
local_ip = 127.0.0.1
"""
            
            if self.subdomain:
                config_content += f"subdomain = {self.subdomain}\n"
            else:
                config_content += f"remote_port = {self.port + 10000}\n"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            return config_file
            
        except Exception as e:
            logger.error(f"创建frp配置文件失败: {e}")
            return None
    
    def stop(self):
        """停止frp服务"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                logger.info("frp已停止")
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                logger.error(f"停止frp失败: {e}")
            finally:
                self.process = None
                self.running = False
                self.public_url = None
                
                # 清理配置文件
                if self.config_file and self.config_file.exists():
                    try:
                        self.config_file.unlink()
                    except:
                        pass
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'running': self.running,
            'public_url': self.public_url,
            'server_addr': self.server_addr,
            'server_port': self.server_port,
            'subdomain': self.subdomain,
            'port': self.port
        }


class TunnelManager:
    """内网穿透管理器"""
    
    def __init__(self):
        self.tunnel = None
        self.tunnel_type = None
        self.config = {}
    
    def setup_ngrok(self, auth_token: str = None, region: str = 'ap'):
        """设置ngrok"""
        self.tunnel_type = 'ngrok'
        self.config = {
            'auth_token': auth_token,
            'region': region
        }
    
    def setup_frp(self, server_addr: str, server_port: int = 7000, 
                  token: str = None, subdomain: str = None):
        """设置frp"""
        self.tunnel_type = 'frp'
        self.config = {
            'server_addr': server_addr,
            'server_port': server_port,
            'token': token,
            'subdomain': subdomain
        }
    
    def start(self, port: int = 5000) -> bool:
        """启动内网穿透"""
        try:
            if self.tunnel_type == 'ngrok':
                self.tunnel = NgrokTunnel(
                    auth_token=self.config.get('auth_token'),
                    region=self.config.get('region', 'ap')
                )
            elif self.tunnel_type == 'frp':
                self.tunnel = FrpTunnel(
                    server_addr=self.config.get('server_addr'),
                    server_port=self.config.get('server_port', 7000),
                    token=self.config.get('token'),
                    subdomain=self.config.get('subdomain')
                )
            else:
                logger.error("未设置内网穿透类型")
                return False
            
            return self.tunnel.start(port)
            
        except Exception as e:
            logger.error(f"启动内网穿透失败: {e}")
            return False
    
    def stop(self):
        """停止内网穿透"""
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None
    
    def get_public_url(self) -> Optional[str]:
        """获取公网URL"""
        if self.tunnel:
            return self.tunnel.get_public_url()
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        if self.tunnel:
            status = self.tunnel.get_status()
            status['type'] = self.tunnel_type
            return status
        
        return {
            'running': False,
            'type': self.tunnel_type,
            'config': self.config
        }
    
    def is_running(self) -> bool:
        """检查服务是否正在运行"""
        if self.tunnel:
            return self.tunnel.is_running()
        return False


# 便捷函数
def create_ngrok_tunnel(auth_token: str = None, region: str = 'ap') -> TunnelManager:
    """创建ngrok隧道管理器"""
    manager = TunnelManager()
    manager.setup_ngrok(auth_token, region)
    return manager


def create_frp_tunnel(server_addr: str, server_port: int = 7000, 
                     token: str = None, subdomain: str = None) -> TunnelManager:
    """创建frp隧道管理器"""
    manager = TunnelManager()
    manager.setup_frp(server_addr, server_port, token, subdomain)
    return manager


# 测试代码
if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建ngrok隧道（需要安装ngrok）
    # manager = create_ngrok_tunnel(auth_token='your_token_here')
    
    # 创建frp隧道（需要安装frp）
    # manager = create_frp_tunnel('your_server.com', 7000, 'token', 'subdomain')
    
    # 示例：启动隧道
    # if manager.start(5000):
    #     print(f"公网URL: {manager.get_public_url()}")
    #     time.sleep(60)  # 运行1分钟
    #     manager.stop()
    
    pass