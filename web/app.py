"""
Web界面主程序
提供实时棋盘分析和推荐走法展示
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
import threading
import time
import json
import os
import sys
import re
import hashlib
import hmac
from pathlib import Path
from datetime import datetime, timedelta
import logging
import cv2
import numpy as np
import base64
from io import BytesIO

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chess_analyzer import XiangqiAnalyzer, analyze_image_file
from src.board_render import draw_on_original
from src.frame_diff import frame_signature, is_frame_changed
from src.config import (check_config, default_config, load_config,
                        normalize_config, save_config)
from src.stream_processor import (RTMPStreamProcessor, EmulatorCapture,
                                  create_screen_capture, parse_region)
from src.tunnel_service import create_frp_tunnel, create_ngrok_tunnel

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'xiangqi_analyzer_secret_key_2024'
app.config['SESSION_TYPE'] = 'filesystem'

# 创建SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 密码哈希迭代次数
PASSWORD_ITERATIONS = 100000

# 全局变量
analyzer = None
stream_processor = None
emulator_capture = None
screen_capture = None
capture_thread = None
analysis_thread = None
running = False
latest_result = None
latest_arrow = None
last_analyzed_signature = None   # 上次真正做分析的帧签名
last_preview_signature = None    # 上次推送预览的帧签名
last_analyzer_error = None       # 上次分析器重建失败信息（用于去重日志）
analysis_config = default_config()

# 内网穿透管理器与实际监听端口（用于 ngrok/frp 转发）
tunnel_manager = None
web_port = 5000

# 当前使用的配置文件路径（由 main.py 传入，Web 保存设置时写回同一个文件）
config_file = None

def safe_float(value, default=0.0):
    """确保值是浮点数"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r'(\d+\.?\d*)', value)
        return float(match.group(1)) if match else default
    if isinstance(value, (list, tuple)) and len(value) == 1:  # 可能是单元素数组
        return safe_float(value[0], default)
    return default

def make_json_serializable(obj):
    """转换所有 numpy 类型为 JSON 可序列化"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()  # 转换为嵌套列表
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    return obj

def encode_image(image, quality: int = 85):
    """把 OpenCV 图像编码为 base64 data URI

    Args:
        image: BGR 图像（numpy数组）
        quality: JPEG 质量

    Returns:
        str: data URI，图像无效时返回 None
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        return None

    try:
        ok, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            return None
        return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
    except Exception as e:
        logger.error(f"图像编码失败: {e}")
        return None

def serialize_result(result: dict, include_images: bool = False) -> dict:
    """把分析结果转换为可 JSON 序列化的字典

    Args:
        result: 分析器返回的原始结果
        include_images: 是否附带调试图（WebSocket 推送时不附带）

    Returns:
        dict: 可直接 jsonify 的结果
    """
    if not result:
        return {}

    image_keys = ('original_with_keypoints', 'transformed_board')

    # 图像单独处理，其余字段递归转换为原生类型
    data = make_json_serializable(
        {key: value for key, value in result.items() if key not in image_keys})

    # 关键数值字段做容错，前端会直接调用 toFixed
    data['detect_time'] = safe_float(data.get('detect_time'), 0.0)
    data['confidence'] = safe_float(data.get('confidence'), 0.0)

    if include_images:
        for key in image_keys:
            data[key] = encode_image(result.get(key))

    return data

def apply_config_update(data: dict) -> dict:
    """把接口提交的配置合并进当前配置并写回文件
    
    Args:
        data: 需要覆盖的配置项（可只提交部分字段）
        
    Returns:
        dict: 规范化后的完整配置
    """
    merged = {**analysis_config, **data}
    
    # tunnel_config 需要深合并，避免只提交部分字段时丢失其他配置
    if isinstance(data.get('tunnel_config'), dict):
        merged['tunnel_config'] = {**analysis_config.get('tunnel_config', {}),
                                   **data['tunnel_config']}
    
    updated = normalize_config(merged)
    analysis_config.update(updated)
    save_config(analysis_config, config_file)
    return analysis_config

def get_analyzer():
    """获取分析器实例，未初始化时按当前配置创建

    Returns:
        tuple: (分析器, 错误信息)，失败时分析器为 None
    """
    global analyzer

    if analyzer is not None:
        return analyzer, None

    engine_path = analysis_config.get('engine_path')
    if not engine_path:
        return None, '请先在设置页配置Pikafish引擎路径'

    if not Path(engine_path).exists():
        return None, f'Pikafish引擎不存在: {engine_path}'

    try:
        analyzer = XiangqiAnalyzer(
            engine_path=engine_path,
            pose_model_path=analysis_config.get('pose_model_path', ''),
            classifier_model_path=analysis_config.get('classifier_model_path', ''),
            player_side=analysis_config.get('player_side', 'red'),
            uci_options=analysis_config.get('uci_options'),
            onnx_providers=analysis_config.get('onnx_providers')
        )
        logger.info("✅ 分析器已按需初始化")
        return analyzer, None

    except Exception as e:
        logger.error(f"初始化分析器失败: {e}")
        return None, f'初始化分析器失败: {e}'

# 用户管理
class UserManager:
    """用户管理器

    密码使用 PBKDF2-SHA256 加盐存储，用户信息可持久化到 JSON 文件。
    """
    
    def __init__(self, users_file=None):
        self.users = {}
        self.active_sessions = {}
        self.max_users = 5  # 最大用户数
        self.users_file = Path(users_file) if users_file else None
    
    @staticmethod
    def _hash_password(password: str, salt: str = None) -> str:
        """生成密码哈希
        
        Args:
            password: 明文密码
            salt: 盐值（十六进制），为空时随机生成
            
        Returns:
            str: pbkdf2_sha256$迭代次数$盐$哈希
        """
        salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), bytes.fromhex(salt), PASSWORD_ITERATIONS)
        return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"
    
    @staticmethod
    def _verify_password(password: str, stored: str) -> bool:
        """校验密码哈希"""
        try:
            algorithm, iterations, salt, digest = stored.split('$')
            if algorithm != 'pbkdf2_sha256':
                return False
            computed = hashlib.pbkdf2_hmac(
                'sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations))
            return hmac.compare_digest(computed.hex(), digest)
        except (ValueError, AttributeError):
            return False
    
    def add_user(self, username: str, password: str) -> bool:
        """添加用户
        
        Args:
            username: 用户名
            password: 明文密码（内部会哈希保存）
            
        Returns:
            bool: 是否添加成功
        """
        if len(self.users) >= self.max_users:
            logger.warning(f"用户数量已达上限: {self.max_users}")
            return False
        
        if username in self.users:
            return False
        
        self.users[username] = {
            'password': self._hash_password(password),
            'created_at': datetime.now(),
            'last_login': None
        }
        self.save()
        return True
    
    def remove_user(self, username: str) -> bool:
        """删除用户，并清理其会话
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否删除成功
        """
        if username not in self.users:
            return False
        
        del self.users[username]
        
        for session_id in [sid for sid, info in self.active_sessions.items()
                           if info['username'] == username]:
            del self.active_sessions[session_id]
        
        self.save()
        return True
    
    def list_users(self) -> list:
        """列出所有用户（不含密码）"""
        online_names = {info['username'] for info in self.active_sessions.values()}
        
        return [{
            'username': name,
            'created_at': info['created_at'].isoformat(timespec='seconds'),
            'last_login': info['last_login'].isoformat(timespec='seconds')
                          if info['last_login'] else None,
            'online': name in online_names
        } for name, info in sorted(self.users.items())]
    
    def set_max_users(self, count: int):
        """设置用户数量上限"""
        try:
            self.max_users = max(1, int(count))
        except (TypeError, ValueError):
            self.max_users = 5
    
    def authenticate(self, username: str, password: str) -> bool:
        """验证用户
        
        兼容旧版本保存的明文密码，校验通过后自动升级为哈希存储。
        """
        user = self.users.get(username)
        if not user:
            return False
        
        stored = str(user.get('password', ''))
        if stored.startswith('pbkdf2_sha256$'):
            return self._verify_password(password, stored)
        
        if hmac.compare_digest(stored, str(password)):
            user['password'] = self._hash_password(password)
            self.save()
            return True
        
        return False
    
    def login(self, username: str, session_id: str):
        """用户登录
        
        Args:
            username: 用户名
            session_id: 会话ID
        """
        # 登录时顺便清理过期会话，避免长期占用在线名额
        self.cleanup_expired_sessions()
        
        self.active_sessions[session_id] = {
            'username': username,
            'login_time': datetime.now()
        }
        if username in self.users:
            self.users[username]['last_login'] = datetime.now()
    
    def logout(self, session_id: str):
        """用户登出"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    def is_logged_in(self, session_id: str) -> bool:
        """检查用户是否已登录"""
        return session_id in self.active_sessions
    
    def get_active_user_count(self) -> int:
        """获取在线用户数"""
        return len(self.active_sessions)
    
    def save(self) -> bool:
        """把用户信息写入文件
        
        Returns:
            bool: 是否保存成功（未配置文件路径时返回 False）
        """
        if not self.users_file:
            return False
        
        try:
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                name: {
                    'password': info['password'],
                    'created_at': info['created_at'].isoformat(),
                    'last_login': info['last_login'].isoformat()
                                  if info['last_login'] else None
                }
                for name, info in self.users.items()
            }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            logger.error(f"保存用户信息失败: {e}")
            return False
    
    def load(self) -> bool:
        """从文件读取用户信息
        
        Returns:
            bool: 是否读取成功
        """
        if not self.users_file or not self.users_file.exists():
            return False
        
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                logger.error(f"用户文件格式错误: {self.users_file}")
                return False
            
            for name, info in data.items():
                self.users[name] = {
                    'password': str(info.get('password', '')),
                    'created_at': datetime.fromisoformat(info['created_at'])
                                  if info.get('created_at') else datetime.now(),
                    'last_login': datetime.fromisoformat(info['last_login'])
                                  if info.get('last_login') else None
                }
            
            logger.info(f"已加载 {len(self.users)} 个用户: {self.users_file}")
            return True
            
        except Exception as e:
            logger.error(f"加载用户信息失败: {e}")
            return False
    
    def cleanup_expired_sessions(self, timeout_hours: int = 24):
        """清理过期会话"""
        cutoff_time = datetime.now() - timedelta(hours=timeout_hours)
        expired_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if session_info['login_time'] < cutoff_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]

user_manager = UserManager()

# 路由定义
@app.route('/')
def index():
    """主页"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return redirect(url_for('login'))
    
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if user_manager.authenticate(username, password):
            session['session_id'] = os.urandom(16).hex()
            session['username'] = username
            user_manager.login(username, session['session_id'])
            logger.info(f"用户登录成功: {username}")
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """登出"""
    session_id = session.get('session_id')
    if session_id:
        user_manager.logout(session_id)
    
    session.clear()
    return redirect(url_for('login'))

@app.route('/settings')
def settings():
    """设置页面"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return redirect(url_for('login'))
    
    return render_template('settings.html', config=analysis_config)

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    return jsonify({
        'running': running,
        'source_type': analysis_config['source_type'],
        'source_value': analysis_config['source_value'],
        'active_users': user_manager.get_active_user_count(),
        'max_users': user_manager.max_users,
        'tunnel': {
            'enabled': analysis_config['enable_tunnel'],
            'type': analysis_config['tunnel_type'],
            'status': tunnel_manager.get_status() if tunnel_manager else {'running': False}
        }
    })

@app.route('/api/windows')
def list_windows():
    """列出当前可截图的窗口标题，供模拟器选择"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        capture = create_screen_capture()
        return jsonify({'windows': capture.list_windows()})
        
    except Exception as e:
        logger.error(f"获取窗口列表失败: {e}")
        return jsonify({'windows': [], 'error': str(e)})

@app.route('/api/users', methods=['GET', 'POST'])
def manage_users():
    """用户管理：查询用户列表或添加用户"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    if request.method == 'GET':
        return jsonify({
            'users': user_manager.list_users(),
            'active_users': user_manager.get_active_user_count(),
            'max_users': user_manager.max_users
        })
    
    try:
        data = request.get_json(silent=True) or {}
        username = str(data.get('username', '')).strip()
        password = str(data.get('password', ''))
        
        if not username or not password:
            return jsonify({'error': '用户名和密码不能为空'}), 400
        
        if len(password) < 6:
            return jsonify({'error': '密码长度不能少于6位'}), 400
        
        if username in user_manager.users:
            return jsonify({'error': f'用户已存在: {username}'}), 400
        
        if not user_manager.add_user(username, password):
            return jsonify({'error': f'用户数量已达上限（{user_manager.max_users}人）'}), 400
        
        logger.info(f"已添加用户: {username}")
        return jsonify({'success': True, 'users': user_manager.list_users()})
        
    except Exception as e:
        logger.error(f"添加用户失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<username>', methods=['DELETE'])
def delete_user(username):
    """删除用户"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    if username == session.get('username'):
        return jsonify({'error': '不能删除当前登录的用户'}), 400
    
    if len(user_manager.users) <= 1:
        return jsonify({'error': '至少需要保留一个用户'}), 400
    
    if not user_manager.remove_user(username):
        return jsonify({'error': f'用户不存在: {username}'}), 404
    
    logger.info(f"已删除用户: {username}")
    return jsonify({'success': True, 'users': user_manager.list_users()})

@app.route('/api/tunnel', methods=['GET', 'POST', 'DELETE'])
def manage_tunnel():
    """内网穿透：查询状态 / 启动 / 停止"""
    global tunnel_manager
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    if request.method == 'GET':
        return jsonify({
            'enabled': analysis_config['enable_tunnel'],
            'type': analysis_config['tunnel_type'],
            'port': web_port,
            'status': tunnel_manager.get_status() if tunnel_manager else {'running': False}
        })
    
    if request.method == 'DELETE':
        if tunnel_manager:
            tunnel_manager.stop()
            tunnel_manager = None
        
        analysis_config['enable_tunnel'] = False
        save_config(analysis_config, config_file)
        return jsonify({'success': True, 'status': {'running': False}})
    
    # POST：启动内网穿透（可同时提交最新配置）
    if tunnel_manager and tunnel_manager.is_running():
        return jsonify({'error': '内网穿透已在运行'}), 400
    
    data = request.get_json(silent=True) or {}
    if data:
        apply_config_update(data)
    
    tunnel_config = analysis_config.get('tunnel_config', {})
    
    if analysis_config['tunnel_type'] == 'ngrok':
        manager = create_ngrok_tunnel(
            auth_token=tunnel_config.get('auth_token'),
            region=tunnel_config.get('region', 'ap'))
    else:
        if not tunnel_config.get('server_addr'):
            return jsonify({'error': 'frp 模式需要先填写服务器地址'}), 400
        manager = create_frp_tunnel(
            server_addr=tunnel_config['server_addr'],
            server_port=int(tunnel_config.get('server_port', 7000)),
            token=tunnel_config.get('token'),
            subdomain=tunnel_config.get('subdomain'))
    
    logger.info(f"正在启动内网穿透: {analysis_config['tunnel_type']} -> 端口 {web_port}")
    
    if not manager.start(web_port):
        return jsonify({
            'error': '内网穿透启动失败，请确认已安装 ngrok/frpc，并检查令牌或服务器配置'
        }), 500
    
    tunnel_manager = manager
    analysis_config['enable_tunnel'] = True
    save_config(analysis_config, config_file)
    
    logger.info(f"✅ 内网穿透已启动: {manager.get_public_url()}")
    return jsonify({'success': True, 'public_url': manager.get_public_url(),
                    'status': manager.get_status()})

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    global analyzer, latest_arrow, last_analyzed_signature
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        
        # 校验、合并并写回配置文件
        updated = apply_config_update(data)
        warnings = check_config(updated)
        for problem in warnings:
            logger.warning(f"配置检查: {problem}")
        
        # 配置变化后释放旧分析器（含引擎进程），并强制下一轮重新分析：
        # 即使画面没变，也要用新的执子/朝向重新出结果
        if analyzer is not None:
            try:
                analyzer.quit()
            except Exception as e:
                logger.warning(f"关闭旧分析器失败: {e}")
        analyzer = None
        latest_arrow = None
        last_analyzed_signature = None
        
        logger.info(f"配置已更新: {analysis_config}")
        return jsonify({'success': True, 'config': analysis_config, 'warnings': warnings})
        
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_analysis():
    """开始分析"""
    global running, analyzer, capture_thread, analysis_thread, latest_arrow
    global last_analyzed_signature, last_preview_signature
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    if running:
        return jsonify({'error': '分析已在运行中'})
    
    try:
        # 按需创建分析器，无需先点击"开始分析"
        engine, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 400
        
        running = True
        latest_arrow = None  # 新一轮分析前清掉旧箭头，避免叠加到新画面上
        last_analyzed_signature = None
        last_preview_signature = None
        
        # 启动捕获线程
        capture_thread = threading.Thread(target=capture_loop, daemon=True)
        capture_thread.start()
        
        # 启动分析线程
        analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        analysis_thread.start()
        
        logger.info("分析已启动")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"启动分析失败: {e}")
        running = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_analysis():
    """停止分析"""
    global running, latest_arrow, last_analyzed_signature, last_preview_signature
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    running = False
    latest_arrow = None
    last_analyzed_signature = None
    last_preview_signature = None
    logger.info("分析已停止")
    return jsonify({'success': True})

@app.route('/api/result')
def get_latest_result():
    """获取最新分析结果"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    if latest_result:
        return jsonify(serialize_result(latest_result, include_images=True))
    else:
        return jsonify({'error': '暂无分析结果'}), 404

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """上传图片进行分析"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        if 'image' not in request.files:
            return jsonify({'error': '未上传图片'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '未选择图片'}), 400
        
        # 读取图片
        image_data = file.read()
        if not image_data:
            return jsonify({'error': '图片内容为空'}), 400
        
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': '无法读取图片'}), 400
        
        # 按需创建分析器，无需先点击"开始分析"
        current_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 400
        
        result = current_analyzer.analyze_image(image, analysis_config['think_time'])
        
        if result:
            return jsonify(serialize_result(result, include_images=True))
        else:
            return jsonify({'error': '分析失败，请查看日志'}), 500
            
    except Exception as e:
        logger.error(f"上传图片分析失败: {e}")
        return jsonify({'error': str(e)}), 500

# 批量分析一次最多处理的图片数量
BATCH_MAX_FILES = 10

@app.route('/api/upload_batch', methods=['POST'])
def upload_images_batch():
    """批量上传图片并逐张分析
    
    单张失败不会中断整批，结果按文件逐条返回。
    """
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        files = request.files.getlist('images') or request.files.getlist('image')
        files = [file for file in files if file and file.filename]
        
        if not files:
            return jsonify({'error': '未选择图片'}), 400
        
        if len(files) > BATCH_MAX_FILES:
            return jsonify({'error': f'一次最多分析{BATCH_MAX_FILES}张图片'}), 400
        
        current_analyzer, error = get_analyzer()
        if error:
            return jsonify({'error': error}), 400
        
        results = []
        for file in files:
            item = {'filename': file.filename, 'success': False}
            
            try:
                image_data = file.read()
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR) if image_data else None
                
                if image is None:
                    item['error'] = '无法读取图片'
                else:
                    result = current_analyzer.analyze_image(
                        image, analysis_config['think_time'])
                    
                    if result:
                        item.update({
                            'success': True,
                            'fen': result['fen'],
                            'best_move': result['best_move'],
                            'best_move_cn': result.get('best_move_cn'),
                            'score': make_json_serializable(result['score']),
                            'confidence': safe_float(result['confidence'], 0.0),
                            'detect_time': safe_float(result['detect_time'], 0.0),
                            'occluded_count': result.get('occluded_count', 0)
                        })
                    else:
                        item['error'] = '分析失败（可能未识别到完整棋盘）'
                
            except Exception as e:
                logger.error(f"批量分析 {file.filename} 失败: {e}")
                item['error'] = str(e)
            
            results.append(item)
        
        success_count = sum(1 for item in results if item['success'])
        logger.info(f"批量分析完成: {success_count}/{len(results)} 成功")
        
        return jsonify({
            'total': len(results),
            'success': success_count,
            'failed': len(results) - success_count,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"批量上传分析失败: {e}")
        return jsonify({'error': str(e)}), 500

# SocketIO事件
@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return False  # 拒绝连接
    
    logger.info(f"客户端已连接: {request.sid}")
    emit('status', {'running': running, 'config': analysis_config})

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开"""
    logger.info(f"客户端已断开: {request.sid}")

# 后台线程
def capture_loop():
    """捕获循环"""
    global stream_processor, emulator_capture, screen_capture, last_preview_signature
    
    while running:
        try:
            frame = None
            
            if analysis_config['source_type'] == 'stream':
                if not stream_processor or not stream_processor.is_running():
                    if analysis_config['source_value']:
                        stream_processor = RTMPStreamProcessor(analysis_config['source_value'])
                        stream_processor.start()
                
                if stream_processor and stream_processor.is_running():
                    frame = stream_processor.get_latest_frame()
            
            elif analysis_config['source_type'] == 'emulator':
                if not emulator_capture:
                    # source_value 既可以是模拟器名称，也可以是完整窗口标题
                    emulator_capture = EmulatorCapture(analysis_config['source_value'] or 'MuMu')
                
                frame = emulator_capture.capture()
            
            elif analysis_config['source_type'] == 'screen':
                if not screen_capture:
                    screen_capture = create_screen_capture()
                
                region = parse_region(analysis_config['source_value'])
                if analysis_config['source_value'] and region is None:
                    logger.warning(f"截图区域格式错误: {analysis_config['source_value']}，"
                                   "应为 x,y,width,height，本次改为全屏截图")
                
                frame = screen_capture.capture_window(region=region)
            
            # 如果有新帧，可以通过socket发送给前端预览
            if frame is not None:
                # 帧差分：画面和上一帧几乎一样时不重复编码、推送
                signature = frame_signature(frame)
                changed, score = is_frame_changed(
                    signature, last_preview_signature,
                    analysis_config.get('frame_diff_threshold', 3.0))

                if changed:
                    last_preview_signature = signature

                    # 有推荐走法时，在预览帧上叠加箭头（坐标来自最近一次分析）
                    preview_frame = frame
                    if latest_arrow:
                        annotated = draw_on_original(frame, latest_arrow)
                        if annotated is not None:
                            preview_frame = annotated

                    # 压缩并发送预览
                    small_frame = cv2.resize(preview_frame, (320, 240))
                    _, buffer = cv2.imencode('.jpg', small_frame,
                                             [cv2.IMWRITE_JPEG_QUALITY, 70])
                    img_base64 = base64.b64encode(buffer).decode()

                    socketio.emit('preview', {
                        'image': f"data:image/jpeg;base64,{img_base64}",
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    logger.debug(f"预览画面无变化，跳过推送（差异 {score:.2f}）")
            
            time.sleep(0.5)  # 控制捕获频率
            
        except Exception as e:
            logger.error(f"捕获循环出错: {e}")
            time.sleep(1)

def analysis_loop():
    """分析循环"""
    global latest_result, latest_arrow, last_analyzed_signature, analyzer
    global last_analyzer_error
    
    while running:
        try:
            # 获取最新帧
            frame = None
            
            if analysis_config['source_type'] == 'stream' and stream_processor:
                frame = stream_processor.get_latest_frame()
            elif analysis_config['source_type'] == 'emulator' and emulator_capture:
                frame = emulator_capture.capture()
            elif analysis_config['source_type'] == 'screen' and screen_capture:
                # 区域格式非法时返回 None，按全屏截图
                frame = screen_capture.capture_window(
                    region=parse_region(analysis_config['source_value']))
            
            # 分析帧
            if frame is not None:
                # 设置变更后分析器会被释放，这里按最新配置自动重建，
                # 避免分析静默停止、界面一直停留在旧执子的结果上
                if analyzer is None:
                    analyzer, error = get_analyzer()
                    if error:
                        if error != last_analyzer_error:
                            logger.warning(f"等待分析器重建: {error}")
                            last_analyzer_error = error
                    else:
                        last_analyzer_error = None
                        last_analyzed_signature = None

                if analyzer is not None:
                    threshold = analysis_config.get('frame_diff_threshold', 3.0)
                    signature = frame_signature(frame)
                    changed, score = is_frame_changed(
                        signature, last_analyzed_signature, threshold)

                    if not changed:
                        logger.info(f"画面无变化，跳过（差异 {score:.2f} < 阈值 {threshold:g}）")
                    else:
                        result = analyzer.analyze_image(frame, analysis_config['think_time'])

                        if result:
                            last_analyzed_signature = signature
                            latest_result = result
                            latest_arrow = result.get('arrow')

                            # 只推送文本信息，图像单独走 /api/result
                            socketio.emit('analysis_result', serialize_result(result))
            
            # 等待下一个分析周期
            time.sleep(analysis_config['analysis_interval'])
            
        except Exception as e:
            logger.error(f"分析循环出错: {e}")
            time.sleep(1)

# 初始化
def init_app(config=None, config_file_path=None, port: int = 5000, tunnel=None):
    """初始化应用
    
    Args:
        config: 由 main.py 传入的配置（已合并命令行参数），为空时读配置文件
        config_file_path: 配置文件路径，Web 保存设置时写回该文件
        port: Web 服务监听端口，内网穿透转发到该端口
        tunnel: main.py 启动的内网穿透管理器，用于与 Web 端共享状态
        
    Returns:
        dict: 初始化后的配置
    """
    global analysis_config, config_file, tunnel_manager, web_port
    
    config_file = config_file_path
    analysis_config = normalize_config(config) if config else load_config(config_file_path)
    
    web_port = int(port or 5000)
    if tunnel is not None:
        tunnel_manager = tunnel
    
    project_root = Path(__file__).parent.parent
    
    # 用户信息保存在配置文件同目录的 users.json 中
    user_manager.set_max_users(analysis_config.get('max_users', 5))
    if config_file_path:
        user_manager.users_file = Path(config_file_path).with_name('users.json')
    else:
        user_manager.users_file = project_root / 'config' / 'users.json'
    
    user_manager.load()
    
    # 首次运行（没有用户文件）时创建默认用户
    if not user_manager.users:
        user_manager.add_user('admin', 'admin123')
        user_manager.add_user('guest', 'guest123')
        logger.info("已创建默认用户: admin / admin123, guest / guest123")
    
    # 未配置引擎时，尝试使用 Pikafish 子模块中的默认位置
    if not analysis_config['engine_path']:
        candidate = project_root / 'Pikafish' / 'src' / 'pikafish.exe'
        if candidate.exists():
            analysis_config['engine_path'] = str(candidate)
            logger.info(f"使用默认引擎路径: {candidate}")
        else:
            logger.warning("未找到默认Pikafish引擎，请在设置页配置引擎路径")
    
    # 相对路径的模型文件按项目根目录解析
    for key in ('pose_model_path', 'classifier_model_path'):
        path = Path(analysis_config[key])
        if str(path) and not path.is_absolute() and not path.exists():
            candidate = project_root / path
            if candidate.exists():
                analysis_config[key] = str(candidate)
    
    for problem in check_config(analysis_config):
        logger.warning(f"配置检查: {problem}")
    
    # 子模块未初始化时给出明确提示，而不是偷偷创建空文件
    submodule_root = project_root / 'Chinese_Chess_Recognition'
    if not (submodule_root / 'core' / 'chessboard_detector.py').exists():
        logger.warning("检测器子模块未初始化，棋盘识别将退化为模拟数据，"
                       "请执行: git submodule update --init --recursive")
    
    logger.info("应用初始化完成")
    logger.info(f"用户数量: {len(user_manager.users)}/{user_manager.max_users}"
                f"（用户文件: {user_manager.users_file}）")
    
    return analysis_config

# 启动应用
if __name__ == '__main__':
    init_app()
    
    # 启动Web服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)