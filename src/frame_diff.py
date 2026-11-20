"""帧差分工具

用于判断当前画面相对上次分析帧是否发生变化，从而跳过多余的
模型检测与引擎调用。

做法：把画面缩成小尺寸灰度图作为签名，再计算两张签名的均方差（MSE）。
"""

from typing import Optional, Tuple

import cv2
import numpy as np

# 签名图尺寸（越小越快，同时保留足够的画面变化信息）
SIGNATURE_SIZE = (160, 120)

# 默认阈值：均方差低于该值视为“画面无变化”
DEFAULT_THRESHOLD = 3.0


def frame_signature(frame: Optional[np.ndarray],
                    size: Tuple[int, int] = SIGNATURE_SIZE) -> Optional[np.ndarray]:
    """生成画面的紧凑签名（小尺寸灰度图）

    Args:
        frame: BGR 或灰度图像
        size: 签名尺寸 (宽, 高)

    Returns:
        np.ndarray: float32 灰度签名；输入无效时返回 None
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return None

    if frame.ndim == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    elif frame.ndim == 2:
        gray = frame
    else:
        return None

    small = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
    return small.astype(np.float32)


def frame_difference(current: Optional[np.ndarray],
                     previous: Optional[np.ndarray]) -> Optional[float]:
    """计算两帧签名的均方差

    Args:
        current: 当前帧签名
        previous: 上次分析帧签名

    Returns:
        float: 均方差；任一签名缺失或尺寸不一致时返回 None
    """
    if current is None or previous is None:
        return None

    if current.shape != previous.shape:
        return None

    diff = current.astype(np.float32) - previous.astype(np.float32)
    return float(np.mean(diff * diff))


def is_frame_changed(current: Optional[np.ndarray],
                     previous: Optional[np.ndarray],
                     threshold: float = DEFAULT_THRESHOLD) -> Tuple[bool, float]:
    """判断画面是否发生了变化

    Args:
        current: 当前帧签名
        previous: 上次分析帧签名
        threshold: 均方差阈值；<=0 表示不做跳过（总是视为有变化）

    Returns:
        tuple: (是否有变化, 均方差)；无法比较时按“有变化”处理，避免漏分析
    """
    score = frame_difference(current, previous)

    if score is None:
        return True, 0.0

    try:
        limit = float(threshold)
    except (TypeError, ValueError):
        limit = DEFAULT_THRESHOLD

    if limit <= 0:
        return True, score

    return score >= limit, score
