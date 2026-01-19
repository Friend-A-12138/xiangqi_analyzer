"""
RTMP流处理器
支持从RTMP/RTSP等视频流中截取图像
"""

import cv2
import numpy as np
import threading
import queue
import time
import logging
from typing import Optional, Tuple, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class RTMPStreamProcessor:
    """RTMP/RTSP流处理器"""
    
    def __init__(self, stream_url: str, buffer_size: int = 5):
        """
        初始化流处理器
        
        Args:
            stream_url: RTMP/RTSP流地址
            buffer_size: 图像缓冲区大小
        """
        self.stream_url = stream_url
        self.buffer_size = buffer_size
        
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.thread = None
        
        self.fps = 0
        self.frame_count = 0
        self.width = 0
        self.height = 0
        
        logger.info(f"RTMP处理器初始化 - 流地址: {stream_url}")
    
    def start(self) -> bool:
        """启动流处理"""
        try:
            # 打开视频流
            self.cap = cv2.VideoCapture(self.stream_url)
            
            if not self.cap.isOpened():
                logger.error(f"无法打开视频流: {self.stream_url}")
                return False
            
            # 获取视频信息
            self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            if self.fps == 0:
                self.fps = 30  # 默认FPS
            
            logger.info(f"视频流打开成功 - 分辨率: {self.width}x{self.height}, FPS: {self.fps}")
            
            # 启动读取线程
            self.running = True
            self.thread = threading.Thread(target=self._read_frames, daemon=True)
            self.thread.start()
            
            # 等待第一帧
            timeout = 10
            start_time = time.time()
            while self.frame_queue.empty() and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if self.frame_queue.empty():
                logger.error("等待第一帧超时")
                self.stop()
                return False
            
            logger.info("✅ RTMP流处理器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"启动流处理器失败: {e}")
            return False
    
    def _read_frames(self):
        """读取视频帧的线程函数"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("无法读取视频帧，尝试重新连接...")
                    time.sleep(1)
                    self._reconnect()
                    continue
                
                self.frame_count += 1
                
                # 如果队列满了，移除最旧的帧
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                # 添加新帧到队列
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    pass
                
            except Exception as e:
                logger.error(f"读取帧时出错: {e}")
                time.sleep(0.1)
    
    def _reconnect(self):
        """重新连接视频流"""
        try:
            if self.cap:
                self.cap.release()
            
            self.cap = cv2.VideoCapture(self.stream_url)
            
            if self.cap.isOpened():
                logger.info("重新连接成功")
            else:
                logger.error("重新连接失败")
                
        except Exception as e:
            logger.error(f"重新连接出错: {e}")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """获取最新的视频帧"""
        try:
            # 清空旧帧，只保留最新的
            frame = None
            while not self.frame_queue.empty():
                frame = self.frame_queue.get_nowait()
            
            return frame
            
        except queue.Empty:
            return None
    
    def get_frame_at_interval(self, interval_seconds: float) -> Optional[np.ndarray]:
        """
        按固定间隔获取帧
        
        Args:
            interval_seconds: 间隔时间（秒）
            
        Returns:
            视频帧或None
        """
        # 计算需要跳过的帧数
        skip_frames = int(self.fps * interval_seconds)
        
        # 跳过指定数量的帧
        for _ in range(skip_frames):
            if not self.frame_queue.empty():
                self.frame_queue.get_nowait()
        
        return self.get_latest_frame()
    
    def is_running(self) -> bool:
        """检查处理器是否正在运行"""
        return self.running and self.thread is not None and self.thread.is_alive()
    
    def stop(self):
        """停止流处理"""
        logger.info("正在停止RTMP流处理器...")
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.cap:
            self.cap.release()
        
        # 清空队列
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("✅ RTMP流处理器已停止")


class ScreenCapture:
    """屏幕截取处理器"""
    
    def __init__(self):
        """初始化屏幕截取器"""
        self.capture_method = None
        self._detect_capture_method()
    
    def _detect_capture_method(self):
        """检测可用的截图方法"""
        try:
            import pyautogui
            self.capture_method = 'pyautogui'
            logger.info("使用pyautogui进行屏幕截取")
            return
        except ImportError:
            pass
        
        try:
            import mss
            self.capture_method = 'mss'
            logger.info("使用mss进行屏幕截取")
            return
        except ImportError:
            pass
        
        # 使用OpenCV的VideoCapture作为备选
        self.capture_method = 'opencv'
        logger.info("使用OpenCV进行屏幕截取")
    
    def capture_window(self, window_title: str = None, region: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """
        截取指定窗口或区域
        
        Args:
            window_title: 窗口标题（部分匹配）
            region: 截图区域 (x, y, width, height)
            
        Returns:
            截图或None
        """
        try:
            if self.capture_method == 'pyautogui':
                return self._capture_pyautogui(window_title, region)
            elif self.capture_method == 'mss':
                return self._capture_mss(window_title, region)
            else:
                return self._capture_opencv(window_title, region)
                
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    def _capture_pyautogui(self, window_title: str = None, region: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """使用pyautogui截图"""
        import pyautogui
        
        if region:
            # 直接截取指定区域
            screenshot = pyautogui.screenshot(region=region)
        else:
            # 查找窗口并截取
            if window_title:
                windows = pyautogui.getWindowsWithTitle(window_title)
                if windows:
                    window = windows[0]
                    region = (window.left, window.top, window.width, window.height)
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    logger.warning(f"未找到窗口: {window_title}")
                    screenshot = pyautogui.screenshot()
            else:
                screenshot = pyautogui.screenshot()
        
        # 转换为OpenCV格式
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame
    
    def _capture_mss(self, window_title: str = None, region: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """使用mss截图"""
        import mss
        
        with mss.mss() as sct:
            if region:
                monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
            else:
                monitor = sct.monitors[0]  # 主显示器
            
            screenshot = sct.grab(monitor)
            frame = np.array(screenshot)
            
            # 转换为OpenCV格式
            if frame.shape[2] == 4:  # RGBA
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
            else:  # RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
    
    def _capture_opencv(self, window_title: str = None, region: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """使用OpenCV截图（仅支持摄像头）"""
        # 这个方法主要用于测试，实际窗口截图需要其他库支持
        logger.warning("OpenCV方法不支持窗口截图，请安装pyautogui或mss")
        return None
    
    def list_windows(self) -> list:
        """列出所有窗口标题"""
        try:
            if self.capture_method == 'pyautogui':
                import pyautogui
                windows = pyautogui.getAllWindows()
                return [w.title for w in windows if w.title]
            else:
                logger.warning("当前截图方法不支持窗口列表")
                return []
        except Exception as e:
            logger.error(f"获取窗口列表失败: {e}")
            return []


class EmulatorCapture:
    """模拟器截图专用类"""
    
    def __init__(self, emulator_name: str = "MuMu"):
        """
        初始化模拟器截图器
        
        Args:
            emulator_name: 模拟器名称（用于窗口匹配）
        """
        self.emulator_name = emulator_name
        self.screen_capture = ScreenCapture()
        self.window_title = self._find_emulator_window()
        
        if self.window_title:
            logger.info(f"找到模拟器窗口: {self.window_title}")
        else:
            logger.warning(f"未找到{emulator_name}模拟器窗口")
    
    def _find_emulator_window(self) -> str:
        """查找模拟器窗口"""
        windows = self.screen_capture.list_windows()
        
        # 查找包含模拟器名称的窗口
        for window in windows:
            if self.emulator_name.lower() in window.lower():
                return window
        
        # 尝试其他常见模拟器名称
        emulator_keywords = ["雷电", "BlueStacks", "Nox", "LDPlayer", "夜神", "逍遥"]
        for keyword in emulator_keywords:
            for window in windows:
                if keyword.lower() in window.lower():
                    logger.info(f"找到{keyword}模拟器窗口: {window}")
                    return window
        
        return ""
    
    def capture(self, region: Tuple[int, int, int, int] = None) -> Optional[np.ndarray]:
        """
        截取模拟器画面
        
        Args:
            region: 截图区域 (x, y, width, height)
            
        Returns:
            截图或None
        """
        if not self.window_title and not region:
            logger.error("未指定窗口标题或截图区域")
            return None
        
        return self.screen_capture.capture_window(self.window_title, region)
    
    def is_emulator_running(self) -> bool:
        """检查模拟器是否正在运行"""
        return bool(self._find_emulator_window())


# 便捷函数
def create_stream_processor(stream_url: str) -> RTMPStreamProcessor:
    """创建RTMP流处理器"""
    return RTMPStreamProcessor(stream_url)


def create_emulator_capture(emulator_name: str = "MuMu") -> EmulatorCapture:
    """创建模拟器截图器"""
    return EmulatorCapture(emulator_name)


def create_screen_capture() -> ScreenCapture:
    """创建屏幕截图器"""
    return ScreenCapture()