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
from pathlib import Path
from datetime import datetime, timedelta
import logging
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chess_analyzer import XiangqiAnalyzer, analyze_image_file
from src.config import (check_config, default_config, load_config,
                        normalize_config, save_config)
from src.stream_processor import (RTMPStreamProcessor, EmulatorCapture,
                                  create_screen_capture, parse_region)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'xiangqi_analyzer_secret_key_2024'
app.config['SESSION_TYPE'] = 'filesystem'

# 创建SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# 全局变量
analyzer = None
stream_processor = None
emulator_capture = None
screen_capture = None
capture_thread = None
analysis_thread = None
running = False
latest_result = None
analysis_config = default_config()

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
            classifier_model_path=analysis_config.get('classifier_model_path', '')
        )
        logger.info("✅ 分析器已按需初始化")
        return analyzer, None

    except Exception as e:
        logger.error(f"初始化分析器失败: {e}")
        return None, f'初始化分析器失败: {e}'

# 用户管理
class UserManager:
    """用户管理器"""
    
    def __init__(self):
        self.users = {}
        self.active_sessions = {}
        self.max_users = 5  # 最大用户数
    
    def add_user(self, username: str, password: str) -> bool:
        """添加用户"""
        if len(self.users) >= self.max_users:
            return False
        
        if username in self.users:
            return False
        
        self.users[username] = {
            'password': password,  # 实际应用中应该加密存储
            'created_at': datetime.now(),
            'last_login': None
        }
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        """验证用户"""
        if username not in self.users:
            return False
        
        return self.users[username]['password'] == password
    
    def login(self, username: str, session_id: str):
        """用户登录"""
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
        'max_users': user_manager.max_users
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

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    global analyzer
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json(silent=True) or {}
        
        # 校验并合并配置（非法值会被规范化到合法范围）
        updated = normalize_config({**analysis_config, **data})
        warnings = check_config(updated)
        for problem in warnings:
            logger.warning(f"配置检查: {problem}")
        
        analysis_config.update(updated)
        
        # 配置变化后丢弃旧分析器，下次分析时按新配置重建
        analyzer = None
        
        # 写回配置文件，保证重启后配置仍然生效
        if not save_config(analysis_config, config_file):
            return jsonify({'error': '配置保存失败，请检查配置文件权限'}), 500
        
        logger.info(f"配置已更新: {analysis_config}")
        return jsonify({'success': True, 'config': analysis_config, 'warnings': warnings})
        
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_analysis():
    """开始分析"""
    global running, analyzer, capture_thread, analysis_thread
    
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
    global running
    
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    running = False
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
    global stream_processor, emulator_capture, screen_capture
    
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
                # 压缩并发送预览
                small_frame = cv2.resize(frame, (320, 240))
                _, buffer = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                img_base64 = base64.b64encode(buffer).decode()
                
                socketio.emit('preview', {
                    'image': f"data:image/jpeg;base64,{img_base64}",
                    'timestamp': datetime.now().isoformat()
                })
            
            time.sleep(0.5)  # 控制捕获频率
            
        except Exception as e:
            logger.error(f"捕获循环出错: {e}")
            time.sleep(1)

def analysis_loop():
    """分析循环"""
    global latest_result
    
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
            if frame is not None and analyzer:
                result = analyzer.analyze_image(frame, analysis_config['think_time'])
                
                if result:
                    latest_result = result
                    
                    # 只推送文本信息，图像单独走 /api/result
                    socketio.emit('analysis_result', serialize_result(result))
            
            # 等待下一个分析周期
            time.sleep(analysis_config['analysis_interval'])
            
        except Exception as e:
            logger.error(f"分析循环出错: {e}")
            time.sleep(1)

# 初始化
def init_app(config=None, config_file_path=None):
    """初始化应用
    
    Args:
        config: 由 main.py 传入的配置（已合并命令行参数），为空时读配置文件
        config_file_path: 配置文件路径，Web 保存设置时写回该文件
        
    Returns:
        dict: 初始化后的配置
    """
    global analysis_config, config_file
    
    config_file = config_file_path
    analysis_config = normalize_config(config) if config else load_config(config_file_path)
    
    # 添加默认用户
    user_manager.add_user('admin', 'admin123')
    user_manager.add_user('guest', 'guest123')
    
    project_root = Path(__file__).parent.parent
    
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
    logger.info("默认用户:")
    logger.info("  admin / admin123")
    logger.info("  guest / guest123")
    
    return analysis_config

# 启动应用
if __name__ == '__main__':
    init_app()
    
    # 启动Web服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)