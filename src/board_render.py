"""棋盘箭头绘制

检测器把原图透视变换成 450x500 的棋盘图，并给出棋盘四角在变换图中的坐标。
本模块负责：

- 把棋盘的 (行, 列) 换算成棋盘图像素坐标
- 用单应性矩阵把棋盘坐标投影回原图
- 在图像上绘制带白色描边的箭头
"""

from typing import Dict, List, Optional, Sequence

import cv2
import numpy as np

BOARD_ROWS = 10
BOARD_COLS = 9

# 红方用红色、黑方用蓝色，均带白色描边以保证在木质棋盘上可见
ARROW_COLORS = {
    'red': (0, 0, 255),
    'black': (255, 128, 0),
}


def board_point(row: int, col: int, corners: Sequence[Sequence[float]]) -> List[float]:
    """把棋盘行列换算成棋盘图上的像素坐标

    Args:
        row: 行（0 = 黑方底线）
        col: 列（0 = 文件 a）
        corners: 棋盘四角在变换图中的坐标 [左上, 右上, 左下, 右下]

    Returns:
        List[float]: [x, y]
    """
    top_left, top_right, bottom_left = corners[0], corners[1], corners[2]

    x = top_left[0] + (top_right[0] - top_left[0]) * col / (BOARD_COLS - 1)
    y = top_left[1] + (bottom_left[1] - top_left[1]) * row / (BOARD_ROWS - 1)
    return [float(x), float(y)]


def to_original(points: List[List[float]],
                keypoints: Sequence[Sequence[float]],
                corners: Sequence[Sequence[float]]) -> Optional[List[List[float]]]:
    """把棋盘图坐标投影回原图坐标

    Args:
        points: 棋盘图上的点
        keypoints: 棋盘四角在原图中的坐标（A0, A8, J0, J8）
        corners: 棋盘四角在棋盘图中的坐标

    Returns:
        List[List[float]]: 原图坐标；矩阵不可逆时返回 None
    """
    try:
        matrix = cv2.getPerspectiveTransform(
            np.float32(keypoints), np.float32(corners))

        # 关键点退化时矩阵可能不可逆，直接放弃绘制而不是产出错误坐标
        if not np.isfinite(matrix).all() or abs(np.linalg.det(matrix)) < 1e-9:
            return None

        inverse = np.linalg.inv(matrix)

        array = np.float32(points).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(array, inverse).reshape(-1, 2)
        return [[float(x), float(y)] for x, y in projected]

    except Exception:
        return None


def draw_arrow(image: np.ndarray, start: Sequence[float], end: Sequence[float],
               color=(0, 0, 255), thickness: int = 3) -> np.ndarray:
    """在图像上绘制起点到终点的箭头

    Args:
        image: 输入图像（BGR）
        start: 起点坐标
        end: 终点坐标
        color: 箭头颜色（BGR）
        thickness: 线宽

    Returns:
        np.ndarray: 绘制后的图像（新对象）
    """
    canvas = image.copy()
    start_point = (int(round(start[0])), int(round(start[1])))
    end_point = (int(round(end[0])), int(round(end[1])))

    # 白色描边 + 彩色箭头，保证在任何底色上都清晰
    cv2.arrowedLine(canvas, start_point, end_point, (255, 255, 255),
                    thickness + 3, tipLength=0.22, line_type=cv2.LINE_AA)
    cv2.arrowedLine(canvas, start_point, end_point, color,
                    thickness, tipLength=0.22, line_type=cv2.LINE_AA)
    cv2.circle(canvas, start_point, thickness + 3, (255, 255, 255), -1, lineType=cv2.LINE_AA)
    cv2.circle(canvas, start_point, thickness, color, -1, lineType=cv2.LINE_AA)

    return canvas


def draw_on_board(board_image: np.ndarray, arrow: Dict) -> Optional[np.ndarray]:
    """在棋盘图上绘制箭头

    Args:
        board_image: 棋盘图（BGR）
        arrow: 分析结果中的 arrow 字段

    Returns:
        np.ndarray: 绘制后的图像；缺少坐标时返回 None
    """
    board = arrow.get('board') if arrow else None
    if board_image is None or not board:
        return None

    color = ARROW_COLORS.get(arrow.get('side'), ARROW_COLORS['red'])
    return draw_arrow(board_image, board['from'], board['to'], color=color)


def draw_on_original(original_image: np.ndarray, arrow: Dict) -> Optional[np.ndarray]:
    """在原图上绘制箭头

    Args:
        original_image: 原图（BGR）
        arrow: 分析结果中的 arrow 字段

    Returns:
        np.ndarray: 绘制后的图像；缺少坐标时返回 None
    """
    original = arrow.get('original') if arrow else None
    if original_image is None or not original:
        return None

    color = ARROW_COLORS.get(arrow.get('side'), ARROW_COLORS['red'])
    return draw_arrow(original_image, original['from'], original['to'], color=color)
