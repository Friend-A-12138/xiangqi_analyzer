"""棋盘箭头绘制

检测器把原图透视变换成 450x500 的棋盘图，并给出棋盘四角在变换图中的坐标。
本模块负责：

- 把棋盘的 (行, 列) 换算成棋盘图像素坐标
- 用单应性矩阵把棋盘坐标投影回原图
- 在图像上绘制带白色描边的箭头

箭头尺寸按“格子尺寸”定比例，而不是按图片尺寸或走法距离：
短走法与长走法、大图与小图的视觉效果保持一致。
"""

import math
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

# 箭头尺寸相对格子尺寸的固定比例
ARROW_HEAD_RATIO = 0.5          # 头部长度 = 0.5 格
ARROW_HEAD_HALF_RATIO = 0.28    # 头部半宽
ARROW_WIDTH_RATIO = 0.08        # 线宽 = 0.08 格
ARROW_OUTLINE_RATIO = 0.04      # 白色描边额外宽度
ARROW_START_DOT_RATIO = 0.12    # 起点圆点半径


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


def board_cell_size(corners: Sequence[Sequence[float]]) -> float:
    """棋盘图上单个格子的平均像素尺寸

    Args:
        corners: 棋盘四角坐标 [左上, 右上, 左下, 右下]

    Returns:
        float: 格子尺寸（像素）
    """
    top_left, top_right, bottom_left = corners[0], corners[1], corners[2]

    width = math.hypot(top_right[0] - top_left[0], top_right[1] - top_left[1]) / (BOARD_COLS - 1)
    height = math.hypot(bottom_left[0] - top_left[0], bottom_left[1] - top_left[1]) / (BOARD_ROWS - 1)
    return max((width + height) / 2.0, 1.0)


def original_cell_size(keypoints: Sequence[Sequence[float]],
                       corners: Sequence[Sequence[float]],
                       row: int, col: int) -> Optional[float]:
    """估算原图上该位置附近的格子尺寸（透视下格子大小会变化）

    Args:
        keypoints: 棋盘四角在原图中的坐标
        corners: 棋盘四角在棋盘图中的坐标
        row: 行
        col: 列

    Returns:
        float: 局部格子尺寸；投影失败时返回 None
    """
    neighbor_row = row - 1 if row >= BOARD_ROWS - 1 else row + 1
    neighbor_col = col - 1 if col >= BOARD_COLS - 1 else col + 1

    board_points = [
        board_point(row, col, corners),
        board_point(row, neighbor_col, corners),
        board_point(neighbor_row, col, corners),
    ]
    projected = to_original(board_points, keypoints, corners)
    if not projected:
        return None

    horizontal = math.hypot(projected[1][0] - projected[0][0],
                            projected[1][1] - projected[0][1])
    vertical = math.hypot(projected[2][0] - projected[0][0],
                          projected[2][1] - projected[0][1])

    size = (horizontal + vertical) / 2.0
    return size if size > 1.0 else None


def arrow_metrics(cell_size: float) -> Dict:
    """按格子尺寸计算箭头各部分的像素尺寸

    Args:
        cell_size: 格子尺寸（像素）

    Returns:
        dict: 头部长度、头部半宽、线宽、描边宽度、起点半径
    """
    cell = max(float(cell_size or 1.0), 1.0)

    return {
        'cell': cell,
        'head_length': max(4.0, cell * ARROW_HEAD_RATIO),
        'head_half_width': max(3.0, cell * ARROW_HEAD_HALF_RATIO),
        'thickness': max(1, int(round(cell * ARROW_WIDTH_RATIO))),
        'outline': max(2, int(round(cell * ARROW_WIDTH_RATIO + cell * ARROW_OUTLINE_RATIO))),
        'start_radius': max(2, int(round(cell * ARROW_START_DOT_RATIO))),
    }


def draw_arrow(image: np.ndarray, start: Sequence[float], end: Sequence[float],
               color=(0, 0, 255), cell_size: float = 40.0) -> np.ndarray:
    """在图像上绘制起点到终点的箭头

    头部大小、线宽都按 cell_size 的固定比例计算，与走法距离和图片尺寸无关。

    Args:
        image: 输入图像（BGR）
        start: 起点坐标
        end: 终点坐标
        color: 箭头颜色（BGR）
        cell_size: 当前图像上的格子尺寸（像素）

    Returns:
        np.ndarray: 绘制后的图像（新对象）
    """
    canvas = image.copy()
    metrics = arrow_metrics(cell_size)

    start_vector = np.array(start, dtype=float)
    end_vector = np.array(end, dtype=float)
    delta = end_vector - start_vector
    distance = float(np.linalg.norm(delta))

    if distance < 1e-6:
        return canvas

    direction = delta / distance

    # 线画到箭头底部，避免线头从箭头尖端露出
    head_length = min(metrics['head_length'], distance * 0.8)
    head_base = end_vector - direction * head_length

    start_point = tuple(int(round(v)) for v in start_vector)
    line_end = tuple(int(round(v)) for v in head_base)

    cv2.line(canvas, start_point, line_end, (255, 255, 255),
             metrics['outline'], lineType=cv2.LINE_AA)
    cv2.line(canvas, start_point, line_end, color,
             metrics['thickness'], lineType=cv2.LINE_AA)

    perpendicular = np.array([-direction[1], direction[0]])
    half_width = metrics['head_half_width']
    triangle = np.int32([
        end_vector,
        head_base + perpendicular * half_width,
        head_base - perpendicular * half_width,
    ])

    cv2.polylines(canvas, [triangle], True, (255, 255, 255),
                  metrics['outline'], lineType=cv2.LINE_AA)
    cv2.fillPoly(canvas, [triangle], color, lineType=cv2.LINE_AA)

    cv2.circle(canvas, start_point, metrics['start_radius'] + 2, (255, 255, 255),
               -1, lineType=cv2.LINE_AA)
    cv2.circle(canvas, start_point, metrics['start_radius'], color,
               -1, lineType=cv2.LINE_AA)

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
    return draw_arrow(board_image, board['from'], board['to'],
                      color=color, cell_size=board.get('cell', 40.0))


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
    return draw_arrow(original_image, original['from'], original['to'],
                      color=color, cell_size=original.get('cell', 40.0))
