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
from src.stream_processor import RTMPStreamProcessor, EmulatorCapture, create_screen_capture

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
capture_thread = None
analysis_thread = None
running = False
latest_result = None
analysis_config = {
    'engine_path': '',
    'pose_model_path': '',
    'classifier_model_path': '',
    'source_type': 'file',  # file, stream, emulator, screen
    'source_value': '',
    'think_time': 2000,
    'analysis_interval': 3,  # 秒
    'users': {}  # 用户管理
}

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

@app.route('/api/config', methods=['POST'])
def update_config():
    """更新配置"""
    session_id = session.get('session_id')
    if not session_id or not user_manager.is_logged_in(session_id):
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        
        # 更新配置
        if 'engine_path' in data:
            analysis_config['engine_path'] = data.get('engine_path') or analysis_config['engine_path']
        if 'pose_model_path' in data:
            analysis_config['pose_model_path'] = data.get('pose_model_path') or analysis_config['pose_model_path']
        if 'classifier_model_path' in data:
            analysis_config['classifier_model_path'] = data.get('classifier_model_path') or analysis_config['classifier_model_path']
        if 'source_type' in data:
            analysis_config['source_type'] = data['source_type']
        if 'source_value' in data:
            analysis_config['source_value'] = data['source_value']
        if 'think_time' in data:
            analysis_config['think_time'] = int(data['think_time'])
        if 'analysis_interval' in data:
            analysis_config['analysis_interval'] = int(data['analysis_interval'])
        
        logger.info(f"配置已更新: {analysis_config}")
        return jsonify({'success': True, 'config': analysis_config})
        
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
        # 检查必需配置
        if not analysis_config['engine_path']:
            return jsonify({'error': '请先设置Pikafish引擎路径'}), 400
        
        # 初始化分析器
        analyzer = XiangqiAnalyzer(
            engine_path=analysis_config['engine_path'],
            pose_model_path=analysis_config.get('pose_model_path', ''),
            classifier_model_path=analysis_config.get('classifier_model_path', '')
        )
        
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
        return jsonify(latest_result)
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
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': '无法读取图片'}), 400
        
        # 分析图片
        if not analyzer:
            return jsonify({'error': '分析器未初始化'}), 500
        
        result = analyzer.analyze_image(image, analysis_config['think_time'])

        if result:
            # 第一步：转换所有 numpy 类型
            serializable_result = make_json_serializable(result)

            # 第二步：确保关键字段是数字（修复前端 toFixed 错误）
            serializable_result['detect_time'] = safe_float(serializable_result.get('detect_time'), 0.0)
            serializable_result['confidence'] = safe_float(serializable_result.get('confidence'), 0.0)

            # 第三步：转换图像为 base64（用原始 result 中的数组）
            for img_key in ['original_with_keypoints', 'transformed_board']:
                if img_key in result:
                    _, buffer = cv2.imencode('.jpg', result[img_key])
                    img_base64 = base64.b64encode(buffer).decode()
                    serializable_result[img_key] = f"data:image/jpeg;base64,{img_base64}"

            return jsonify(serializable_result)
        else:
            return jsonify({'error': '分析失败'}), 500
            
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
    global stream_processor, emulator_capture
    
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
                    emulator_capture = EmulatorCapture(analysis_config.get('emulator_name', 'MuMu'))
                
                frame = emulator_capture.capture()
            
            elif analysis_config['source_type'] == 'screen':
                if 'screen_capture' not in globals():
                    global screen_capture
                    screen_capture = create_screen_capture()
                
                region = analysis_config.get('screen_region')
                if region:
                    frame = screen_capture.capture_window(region=region)
                else:
                    frame = screen_capture.capture_window()
            
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
            elif analysis_config['source_type'] == 'screen':
                global screen_capture
                if 'screen_capture' in globals():
                    region = analysis_config.get('screen_region')
                    frame = screen_capture.capture_window(region=region)
            
            # 分析帧
            if frame is not None and analyzer:
                result = analyzer.analyze_image(frame, analysis_config['think_time'])
                
                if result:
                    latest_result = result
                    
                    # 转换为可序列化格式并通过Socket发送
                    serializable_result = result.copy()
                    
                    # 移除图像数据，只发送文本信息
                    serializable_result.pop('original_with_keypoints', None)
                    serializable_result.pop('transformed_board', None)
                    
                    # 转换numpy类型
                    serializable_result['detect_time'] = float(serializable_result['detect_time'])
                    serializable_result['confidence'] = float(serializable_result['confidence'])
                    
                    socketio.emit('analysis_result', serializable_result)
            
            # 等待下一个分析周期
            time.sleep(analysis_config['analysis_interval'])
            
        except Exception as e:
            logger.error(f"分析循环出错: {e}")
            time.sleep(1)

# 初始化
def init_app():
    """初始化应用"""
    global user_manager
    
    # 添加默认用户
    user_manager.add_user('admin', 'admin123')
    user_manager.add_user('guest', 'guest123')

    # ===== 在这里设置真实的默认值 =====
    project_root = Path(__file__).parent.parent

    # 设置默认路径（根据你的实际文件结构）
    analysis_config.update({
        'engine_path': str(project_root / 'Pikafish' / 'src' / 'pikafish.exe'),
        'pose_model_path': str(project_root / 'onnx' / 'pose' / '4_v6-0301.onnx'),
        'classifier_model_path': str(project_root / 'onnx' / 'layout_recognition' / 'nano_v3-0319.onnx'),
    })

    # 验证文件是否存在（可选，但推荐）
    for key, path in analysis_config.items():
        if key.endswith('_path') and path:  # 只检查路径字段
            if not Path(path).exists():
                logger.warning(f"默认路径不存在 {key}: {path}")

    submodule_root = project_root / "Chinese_Chess_Recognition"
    core_init = submodule_root / "core" / "__init__.py"

    # 确保 __init__.py 存在
    if not (submodule_root / "__init__.py").exists():
        (submodule_root / "__init__.py").touch()
        logger.info("✅ 已创建 Chinese_Chess_Recognition/__init__.py")

    if not core_init.exists():
        core_init.touch()
        logger.info("✅ 已创建 Chinese_Chess_Recognition/core/__init__.py")

    logger.info("应用初始化完成")
    logger.info("默认用户:")
    logger.info("  admin / admin123")
    logger.info("  guest / guest123")

# 启动应用
if __name__ == '__main__':
    init_app()
    
    # 启动Web服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)