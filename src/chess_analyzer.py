"""
中国象棋AI分析核心模块
整合棋盘检测和Pikafish引擎分析
"""

import cv2
import numpy as np
import subprocess
import os
import re
import sys
from pathlib import Path
from typing import Tuple, List, Optional, Dict
import time
import logging
from datetime import datetime
from .chess_validator import ChessboardValidator, CATEGORY_MAP, CATEGORY_MAP_REVERSE
from .board_view import build_board_view
from .board_render import board_point, to_original
from .xiangqi_notation import move_to_chinese, square_to_rowcol

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent
core_package_path = project_root / "Chinese_Chess_Recognition"

# 将 Chinese_Chess_Recognition 添加到 sys.path，使其内部的绝对导入能工作
if str(core_package_path) not in sys.path:
    sys.path.insert(0, str(core_package_path))


def parse_time_info(time_info) -> float:
    """把检测器返回的耗时描述解析为秒数

    Args:
        time_info: 检测器返回的耗时，可能是数字或"推理用时: 0.45s"这类字符串

    Returns:
        float: 耗时秒数，无法解析时返回 0.0
    """
    if isinstance(time_info, (int, float)):
        return float(time_info)

    match = re.search(r'(\d+(?:\.\d+)?)', str(time_info or ''))
    return float(match.group(1)) if match else 0.0

# 现在可以安全导入
try:
    from core.chessboard_detector import ChessboardDetector as OriginalDetector
    from core.helper_4_kpt import extract_chessboard
    CORE_AVAILABLE = True
except Exception as e:
    CORE_AVAILABLE = False
    logger.error(f"导入失败: {e}")
    logger.exception("详细堆栈信息:")


class PikafishEngine:
    """Pikafish引擎封装类，支持UCI协议交互"""

    def __init__(self, engine_path: str, timeout: int = 10):
        """
        初始化引擎

        Args:
            engine_path: pikafish.exe的完整路径
            timeout: 引擎响应超时时间（秒）
        """
        self.engine_path = Path(engine_path)
        if not self.engine_path.exists():
            raise FileNotFoundError(f"找不到Pikafish引擎: {engine_path}")

        self.timeout = timeout
        self.process = None
        self.crash_count = 0  # 新增：追踪连续崩溃次数
        self._start_engine()

    def _start_engine(self, retry_count: int = 0):
        """
        启动引擎进程，带重试机制

        Args:
            retry_count: 当前重试次数
        """
        # 如果进程已存在，先清理
        if self.process and self.process.poll() is None:
            self.process.terminate()
            time.sleep(0.5)

        try:
            # Windows下需要设置creationflags
            creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

            self.process = subprocess.Popen(
                [str(self.engine_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=creation_flags
            )

            # 初始化UCI
            self._send_command("uci")
            self._wait_for_response("uciok")

            # 设置中国象棋变体
            self._send_command("setoption name UCI_Variant value xiangqi")

            # 重置崩溃计数
            self.crash_count = 0
            logger.info("✅ Pikafish引擎启动成功")

        except Exception as e:
            if retry_count < 3:
                logger.error(f"引擎启动失败 (重试 {retry_count + 1}/3): {e}")
                time.sleep(1)
                self._start_engine(retry_count + 1)
            else:
                raise RuntimeError(f"引擎启动失败: {e}")

    def _ensure_engine_alive(self):
        """确保引擎存活，否则自动重启"""
        if self.process is None or self.process.poll() is not None:
            logger.warning("检测到引擎进程异常，尝试自动重启...")
            try:
                self._start_engine()
            except Exception as e:
                logger.error(f"自动重启失败: {e}")
                raise RuntimeError("引擎无法恢复")

    def _send_command(self, command: str):
        """发送命令到引擎，增加崩溃检测"""
        # 先确保引擎存活
        self._ensure_engine_alive()

        if self.process and self.process.poll() is None:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        else:
            # 引擎已死，标记崩溃
            self.crash_count += 1
            raise RuntimeError("引擎进程已终止")

    def _wait_for_response(self, target: str = None, max_time: float = None) -> List[str]:
        """
        等待引擎响应，增加崩溃检测和计数

        Args:
            target: 等待特定响应字符串
            max_time: 最大等待时间

        Returns:
            响应行列表
        """
        if max_time is None:
            max_time = self.timeout

        start_time = time.time()
        responses = []

        while time.time() - start_time < max_time:
            # 检查进程是否存活
            if self.process.poll() is not None:
                self.crash_count += 1  # 检测到崩溃，计数+1
                raise RuntimeError("引擎进程意外终止")

            line = self.process.stdout.readline().strip()
            if line:
                responses.append(line)
                if target and target in line:
                    # 成功返回，重置崩溃计数
                    self.crash_count = 0
                    return responses

        raise TimeoutError(f"引擎响应超时（{max_time}秒）")

    def get_best_move(self, fen: str, think_time: int = 8000, depth: int = None,
                      side_to_move: str = None) -> dict:
        """
        获取最佳走法，增加健壮性处理

        Args:
            fen: FEN格式棋盘字符串（不含轮到哪方，需要手动添加）
            think_time: 思考时间（毫秒）
            depth: 搜索深度（可选，如果设置则覆盖think_time）
            side_to_move: 走子方 ('w'红 / 'b'黑)，为 None 时自动推断

        Returns:
            dict: 包含best_move, score, pv等信息
        """
        try:
            # 调用前确保引擎存活
            self._ensure_engine_alive()

            # 降级策略：如果连续崩溃超过2次，限制搜索强度
            if self.crash_count > 2:
                logger.warning(f"引擎不稳定（崩溃{self.crash_count}次），启用降级模式")
                if depth is None:
                    depth = 12  # 限制搜索深度
                think_time = min(think_time, 10000)  # 限制最大思考时间

            # 清除之前的搜索状态
            self._send_command("isready")
            self._wait_for_response("readyok")

            engine_turn = side_to_move if side_to_move in ('w', 'b') \
                else self._infer_side_to_move(fen)
            logger.info(f"引擎按{'红' if engine_turn == 'w' else '黑'}方走子分析")

            full_fen = f"{fen} {engine_turn} - - 0 1"
            self._send_command(f"position fen {full_fen}")

            # 开始搜索
            if depth:
                go_command = f"go depth {depth}"
            else:
                go_command = f"go movetime {think_time}"

            self._send_command(go_command)

            # 接收输出，增加超时缓冲
            wait_time = (think_time / 1000) + 15  # 原时间 + 15秒缓冲
            responses = self._wait_for_response("bestmove", max_time=wait_time)

            # 解析最佳走法
            best_move = None
            score = None
            pv_line = []

            for line in responses:
                if line.startswith("info") and "score" in line:
                    parts = line.split()
                    if "cp" in parts:
                        score_idx = parts.index("cp") + 1
                        score = int(parts[score_idx]) / 100
                    elif "mate" in parts:
                        score_idx = parts.index("mate") + 1
                        score = f"MateIn{parts[score_idx]}"

                if line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        best_move = parts[1]
                        if best_move in ["(none)", "NULL"]:
                            best_move = None

            return {
                "best_move": best_move,
                "score": score,
                "pv": pv_line,
                "fen": fen,
                "responses": responses
            }

        except RuntimeError as e:
            if "引擎进程意外终止" in str(e):
                # 标记进程已死，下次调用时会自动重启
                self.process = None
                logger.error(f"引擎分析中崩溃，累计{self.crash_count}次")
                return {
                    "best_move": None,
                    "score": None,
                    "pv": [],
                    "fen": fen,
                    "error": "engine_crashed"
                }
            raise

        except TimeoutError as e:
            logger.warning(f"引擎分析超时: {e}")
            return {
                "best_move": None,
                "score": None,
                "pv": [],
                "fen": fen,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"引擎分析出错: {e}")
            return {
                "best_move": None,
                "score": None,
                "pv": [],
                "fen": fen,
                "error": str(e)
            }

    def _infer_side_to_move(self, fen: str) -> str:
        """在调用方未指定走子方时，按红帅位置推断

        Args:
            fen: FEN 棋盘字符串

        Returns:
            str: 'w' 或 'b'
        """
        rows = fen.split('/')
        red_at_top = any('K' in row for row in rows[:5])
        logger.warning("未指定走子方，按红帅位置推断为"
                       f"{'黑' if red_at_top else '红'}方走子")
        return 'b' if red_at_top else 'w'

    def quit(self):
        """安全关闭引擎"""
        if self.process and self.process.poll() is None:
            try:
                self._send_command("quit")
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            finally:
                self.process = None


class ChessboardDetector:
    """棋盘检测器包装类"""
    
    def __init__(self, pose_model_path: str, full_classifier_model_path: str):
        """
        初始化检测器
        
        Args:
            pose_model_path: 姿态检测模型路径
            full_classifier_model_path: 棋子分类模型路径
        """
        try:
            if not CORE_AVAILABLE:
                raise RuntimeError("无法初始化：Chinese_Chess_Recognition 模块不可用")

            self.detector = OriginalDetector(
                pose_model_path=pose_model_path,
                full_classifier_model_path=full_classifier_model_path
            )

            # 初始化校验器
            self.validator = ChessboardValidator()
            # 颜色启发式修正误判较多，默认关闭，仅保留开关供调试
            self.enable_red_flip = False

            logger.info("✅ 棋盘检测器初始化完成")
            
        except (ImportError, RuntimeError) as e:
            logger.warning(f"无法导入原始检测器: {e}")
            logger.warning("使用模拟检测器（仅用于链路验证，识别结果不可信）")
            self.detector = None
            self.validator = None
            self.enable_red_flip = False

    def detect(self, image: np.ndarray) -> Optional[Dict]:
        """
        检测棋盘

        Args:
            image: 输入图像，BGR 格式（与 OpenCV 读取、截图保持一致）

        Returns:
            检测结果字典，其中的图像字段同样是 BGR 格式
        """
        if self.detector is None:
            # 返回模拟数据用于测试
            return self._generate_mock_result(image)
        
        try:
            # 原始检测器按 RGB 训练，这里统一转换，否则红黑棋子颜色会颠倒
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            start_time = time.time()

            keypoints = None
            board_corners = None

            try:
                # 拆开调用以便保留棋盘四角，箭头才能映射回原图
                keypoints, keypoint_scores = self.detector.pred_keypoints(
                    cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
                original_rgb = self.detector.pose.draw_pred(
                    img=image_rgb.copy(), keypoints=keypoints, scores=keypoint_scores)
                transformed_board, cell_labels_str, scores, board_corners = \
                    self._warp_and_classify(image_rgb, keypoints)
                time_info = f"推理用时: {time.time() - start_time:.2f}s"

            except Exception as exc:
                logger.warning(f"关键点提取失败，回退到默认检测流程: {exc}")
                result = self.detector.pred_detect_board_and_classifier(image_rgb)
                if not result or result[0] is None:
                    logger.warning("检测器未返回有效结果，可能图片中没有完整棋盘")
                    return None
                original_rgb, transformed_board, cell_labels_str, scores, time_info = result

            # 检测器输出为 RGB，转回 BGR 供颜色校验和前端显示
            original_bgr = cv2.cvtColor(original_rgb, cv2.COLOR_RGB2BGR)
            transformed_bgr = cv2.cvtColor(transformed_board, cv2.COLOR_RGB2BGR)

            # 1. 解析为二维完整名称
            layout_2d_short = [list(row) for row in cell_labels_str.strip().split('\n')]
            layout_2d_full = [[CATEGORY_MAP_REVERSE.get(p, '点') for p in row]
                              for row in layout_2d_short]

            # 2. 调用校验器（只检测，不修改）
            validation_report = self.validator.validate_per_cell_red(
                transformed_bgr, layout_2d_full, scores
            )

            # 3. 如果开关打开，执行硬翻转
            # import pdb; pdb.set_trace()
            corrected_layout = layout_2d_full
            corrected_scores = scores
            flip_records = validation_report['recommend_flip']

            if self.enable_red_flip and flip_records:
                # 执行翻转
                corrected_layout = [row[:] for row in layout_2d_full]  # 深拷贝
                corrected_scores = [row.copy() for row in scores]

                for flip in flip_records:
                    i, j = flip['pos']
                    corrected_layout[i][j] = flip['to']
                    corrected_scores[i][j] = scores[i][j] * 0.6  # 降低置信度

                logger.info(f"🔄 已硬翻转{len(flip_records)}个棋子")

                # 转回 short 格式
                layout_2d_short = [[CATEGORY_MAP.get(p, '.') for p in row]
                                   for row in corrected_layout]
                cell_labels_str = '\n'.join([''.join(row) for row in layout_2d_short])
                scores = corrected_scores

            return {
                'original_with_keypoints': original_bgr,
                'transformed_board': transformed_bgr,
                'cell_labels_str': cell_labels_str,
                'scores': scores,
                'detect_time': parse_time_info(time_info),
                'time_info': str(time_info),
                'occluded_count': cell_labels_str.count('x'),
                'validation_report': validation_report if self.validator else None,
                'keypoints': None if keypoints is None else np.asarray(keypoints, dtype=float).tolist(),
                'board_corners': None if board_corners is None else np.asarray(board_corners, dtype=float).tolist()
            }
            
        except Exception as e:
            logger.error(f"检测失败: {e}")
            return None

    def _warp_and_classify(self, image_rgb: np.ndarray, keypoints: np.ndarray):
        """棋盘透视变换并做棋子分类

        Args:
            image_rgb: RGB 原图
            keypoints: 棋盘四角的关键点（A0, A8, J0, J8）

        Returns:
            tuple: (棋盘图, 布局字符串, 置信度, 棋盘图四角坐标)
        """
        transformed_image, _transformed_keypoints, board_corners = \
            extract_chessboard(img=image_rgb, keypoints=keypoints)

        _, _, scores, layout_str = self.detector.full_classifier.pred(
            transformed_image, is_rgb=True)

        return transformed_image, layout_str, scores, board_corners
    
    def _generate_mock_result(self, image: np.ndarray) -> Dict:
        """生成模拟检测结果用于测试"""
        logger.info("使用模拟检测器")
        
        # 生成模拟的棋盘布局
        mock_layout = [
            list("rnbakabnr"),
            list("........."),
            list(".c.....c."),
            list("p.p.p.p.p"),
            list("........."),
            list("........."),
            list("P.P.P.P.P"),
            list(".C.....C."),
            list("........."),
            list("RNBAKABNR")
        ]
        
        cell_labels_str = "\n".join(["".join(row) for row in mock_layout])
        scores = [0.95] * 90  # 模拟置信度
        time_info = 0.1  # 模拟检测时间
        
        # 返回原始图像作为占位符
        return {
            'original_with_keypoints': image,
            'transformed_board': image,
            'cell_labels_str': cell_labels_str,
            'scores': scores,
            'detect_time': time_info,
            'time_info': str(time_info),
            'occluded_count': 0,
            'validation_report': None,
            'keypoints': None,
            'board_corners': None
        }


class XiangqiAnalyzer:
    """中国象棋分析器主类"""
    
    def __init__(self, engine_path: str, pose_model_path: str, classifier_model_path: str, 
                 detector_inverted: bool = None, player_side: str = None):
        """
        初始化分析器
        
        Args:
            engine_path: Pikafish引擎路径
            pose_model_path: 姿态检测模型路径
            classifier_model_path: 棋子分类模型路径
            detector_inverted: 已废弃，仅保留兼容；棋盘朝向改为按红帅位置自动判断
            player_side: 我方执子 (red/black/auto)，为 None 时按红方处理
        """
        self.engine_path = engine_path
        self.detector_inverted = detector_inverted
        self.player_side = player_side if player_side in ('red', 'black', 'auto') else 'red'
        
        # 初始化检测器
        self.detector = ChessboardDetector(pose_model_path, classifier_model_path)
        
        # 初始化引擎（延迟初始化，需要时再启动）
        self.engine = None
        
        logger.info("✅ 象棋分析器初始化完成")
    
    def _ensure_engine_started(self):
        """确保引擎已启动"""
        if self.engine is None:
            self.engine = PikafishEngine(self.engine_path)
    
    def analyze_image(self, image: np.ndarray, think_time: int = 2000) -> Optional[Dict]:
        """
        分析单张图片
        
        Args:
            image: 输入图像
            think_time: 引擎思考时间（毫秒）
            
        Returns:
            分析结果字典
        """
        try:
            # 检测棋盘
            logger.info("🔍 正在检测棋盘...")
            detect_result = self.detector.detect(image)
            
            if detect_result is None:
                logger.error("棋盘检测失败")
                return None

            # 解析布局
            pgn_rows = detect_result['cell_labels_str'].strip().split('\n')
            layout_pgn = [list(row.strip()) for row in pgn_rows]

            # 统一成 FEN 顺序（第0行黑方底线），再按我方执子生成显示方向
            board = self._layout_to_board(layout_pgn)
            fen = self._board_to_fen(board)
            board_view = build_board_view(board, self.player_side)
            
            # 启动引擎并分析
            self._ensure_engine_started()
            logger.info(f"🤖 引擎分析中（{think_time}ms）...")
            
            analysis = self.engine.get_best_move(
                fen, think_time=think_time, side_to_move=self._side_to_move())
            
            if analysis.get("error"):
                logger.error(f"引擎分析失败: {analysis['error']}")
                return None

            # 坐标走法翻译为中文记谱（拿不准的情况返回原因，不猜测）
            best_move = analysis['best_move']
            notation = None
            if best_move:
                side = {'w': 'red', 'b': 'black'}.get(self._side_to_move())
                notation = move_to_chinese(board, best_move, side=side)
                if notation['ok']:
                    logger.info(f"📖 中文记谱: {notation['text']}")
                else:
                    logger.warning(f"中文记谱失败: {notation['error']}")

            # 箭头坐标：棋盘图坐标 + 原图坐标（实时预览叠加用）
            arrow = self._build_arrow(best_move, detect_result, board)
            
            # 组装最终结果
            final_result = {
                'timestamp': datetime.now().isoformat(),
                'fen': fen,
                'layout_pgn': layout_pgn,
                'board': board,
                'layout_2d': [[CATEGORY_MAP_REVERSE.get(cell, cell) for cell in row]
                              for row in board],
                'view': [[CATEGORY_MAP_REVERSE.get(cell, cell) for cell in row]
                         for row in board_view['view']],
                'squares_view': board_view['squares'],
                'orientation': board_view['orientation'],
                'scores': detect_result['scores'],
                'detect_time': detect_result.get('detect_time', 0.0),
                'time_info': detect_result.get('time_info', ''),
                'occluded_count': detect_result.get('occluded_count', 0),
                'player_side': self.player_side,
                'best_move': best_move,
                'best_move_cn': notation['text'] if notation and notation['ok'] else None,
                'move_note': notation,
                'arrow': arrow,
                'keypoints': detect_result.get('keypoints'),
                'board_corners': detect_result.get('board_corners'),
                'score': analysis['score'],
                'original_with_keypoints': detect_result['original_with_keypoints'],
                'transformed_board': detect_result['transformed_board'],
                'confidence': np.mean(detect_result['scores'])
            }
            
            logger.info(f"✅ 分析完成 - 最佳走法: {final_result['best_move']}")
            return final_result
            
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return None
    
    def _build_arrow(self, move: Optional[str], detect_result: Dict,
                     board: List[List[str]]) -> Optional[Dict]:
        """计算走法箭头在棋盘图与原图中的坐标

        Args:
            move: UCI 走法
            detect_result: 检测结果（含 keypoints / board_corners）
            board: FEN 顺序的棋盘，用于判断走子方

        Returns:
            dict: 箭头坐标；缺少关键点或坐标越界时返回 None
        """
        if not move or len(move) < 4:
            return None

        keypoints = detect_result.get('keypoints')
        corners = detect_result.get('board_corners')
        if not keypoints or corners is None:
            return None

        try:
            from_row, from_col = square_to_rowcol(move[:2])
            to_row, to_col = square_to_rowcol(move[2:4])

            start = board_point(from_row, from_col, corners)
            end = board_point(to_row, to_col, corners)

            piece = board[from_row][from_col]
            side = 'red' if piece.isupper() else ('black' if piece.islower() else 'red')

            board_image = detect_result.get('transformed_board')
            board_size = list(board_image.shape[1::-1]) if board_image is not None else [0, 0]

            arrow = {
                'from_square': move[:2],
                'to_square': move[2:4],
                'side': side,
                'board': {'from': start, 'to': end, 'size': board_size},
                'original': None
            }

            original = to_original([start, end], keypoints, corners)
            original_image = detect_result.get('original_with_keypoints')
            if original and original_image is not None:
                height, width = original_image.shape[:2]
                arrow['original'] = {
                    'from': original[0],
                    'to': original[1],
                    'size': [width, height]
                }

            return arrow

        except Exception as e:
            logger.warning(f"箭头坐标计算失败: {e}")
            return None

    def _side_to_move(self) -> Optional[str]:
        """根据我方执子返回 FEN 中的走子方
        
        Returns:
            str: 'w' 表示红方走，'b' 表示黑方走，None 表示交给引擎按局面推断
        """
        if self.player_side == 'red':
            return 'w'
        if self.player_side == 'black':
            return 'b'
        return None
    
    def _layout_to_board(self, layout_pgn: List[List[str]]) -> List[List[str]]:
        """把检测器布局统一成 FEN 顺序（第0行黑方底线）

        Args:
            layout_pgn: 检测器输出的 10x9 布局

        Returns:
            List[List[str]]: FEN 顺序的棋盘（红帅在下方）
        """
        red_at_bottom = any('K' in row for row in layout_pgn[-2:])

        if red_at_bottom:
            return [list(row) for row in layout_pgn]

        logger.info("检测到红帅在上方，按180度旋转后生成FEN")
        return [row[::-1] for row in layout_pgn[::-1]]

    def _board_to_fen(self, board: List[List[str]]) -> str:
        """把 FEN 顺序的棋盘转换为 FEN 字符串

        被遮挡的 'x' 单元格无法识别，按空位处理（引擎不接受 'x'）。

        Args:
            board: FEN 顺序的 10x9 棋盘

        Returns:
            str: FEN 字符串
        """
        occluded = sum(row.count('x') for row in board)
        if occluded:
            logger.warning(f"有{occluded}个位置被遮挡（x），FEN中按空位处理")

        fen_rows = []
        for row in board:
            empty_count = 0
            fen_row = ""
            for cell in row:
                if cell in ('.', 'x'):
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    fen_row += cell
            if empty_count > 0:
                fen_row += str(empty_count)
            fen_rows.append(fen_row)

        return "/".join(fen_rows)

    def _board_layout_to_fen(self, layout_pgn: List[List[str]]) -> str:
        """将10x9的PGN布局转换为FEN格式字符串

        朝向按红帅位置自动判断：检测器输出通常红方在下方；若红帅出现在前两行，
        说明视角相反，此时旋转180度（红黑身份不变）后生成 FEN。
        被遮挡的 'x' 单元格无法识别，按空位处理（引擎不接受 'x'）。

        Args:
            layout_pgn: 检测器输出的布局

        Returns:
            str: FEN 字符串
        """
        return self._board_to_fen(self._layout_to_board(layout_pgn))
    
    def format_analysis_result(self, result: Dict) -> str:
        """格式化分析结果为可读文本"""
        if not result:
            return "分析失败"
        
        output = []
        output.append("=" * 60)
        output.append("中国象棋AI分析结果")
        output.append("=" * 60)
        
        output.append(f"\n⏱️  检测用时: {result['detect_time']:.3f}s")
        output.append(f"📊 平均置信度: {result['confidence']:.3f}")
        output.append(f"🏁 FEN位置: {result['fen']}")
        
        view = result.get('view') or result['layout_2d']
        squares = result.get('squares_view') or []
        if result.get('orientation') == 'black_bottom':
            output.append("\n棋盘布局（我执黑，黑方在下）:")
        else:
            output.append("\n棋盘布局（我执红，红方在下）:")
        output.append("-" * 40)

        for i, row in enumerate(view):
            rank = squares[i][0][1:] if squares else ''
            row_str = " ".join([f"{cell:>3}" for cell in row])
            output.append(f"{rank:>2}: {row_str}")
            if i == 4:
                output.append("    " + "-" * 27)
        
        output.append("\n" + "=" * 60)
        output.append("推荐走法")
        output.append("=" * 60)
        
        if result['best_move']:
            move = result['best_move']
            from_pos = move[0:2]
            to_pos = move[2:4]
            
            output.append(f"🎯 最佳走法: {move}  ({from_pos} -> {to_pos})")

            if result.get('best_move_cn'):
                output.append(f"📖 中文记谱: {result['best_move_cn']}")
            elif result.get('move_note') and result['move_note'].get('error'):
                output.append(f"📖 中文记谱: 暂无法生成（{result['move_note']['error']}）")
            
            if result['score']:
                if isinstance(result['score'], str) and result['score'].startswith('MateIn'):
                    output.append(f"🏆 评估: 能在{result['score'][6:]}步内将死")
                else:
                    score = result['score']
                    if score > 0:
                        output.append(f"📈 评估: 红方优势 +{score:.2f}")
                    elif score < 0:
                        output.append(f"📉 评估: 黑方优势 {score:.2f}")
                    else:
                        output.append("⚖️  评估: 双方均势")
        else:
            output.append("❌ 无法计算推荐走法")
        
        output.append("=" * 60)
        
        return "\n".join(output)
    
    def quit(self):
        """释放资源"""
        if self.engine:
            self.engine.quit()
            self.engine = None
        logger.info("分析器已关闭")


# 便捷函数
def create_analyzer(engine_path: str, pose_model_path: str, classifier_model_path: str) -> XiangqiAnalyzer:
    """创建分析器实例的便捷函数"""
    return XiangqiAnalyzer(engine_path, pose_model_path, classifier_model_path)


def analyze_image_file(image_path: str, analyzer: XiangqiAnalyzer, think_time: int = 2000) -> Optional[Dict]:
    """分析图片文件的便捷函数"""
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"无法读取图片: {image_path}")
        return None
    
    return analyzer.analyze_image(image, think_time)