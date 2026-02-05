import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

# 棋子映射
CATEGORY_MAP = {
    '.': '.', 'x': 'x',
    '红帅': 'K', '红士': 'A', '红相': 'B', '红马': 'N', '红车': 'R', '红炮': 'C', '红兵': 'P',
    '黑将': 'k', '黑仕': 'a', '黑象': 'b', '黑傌': 'n', '黑車': 'r', '黑砲': 'c', '黑卒': 'p',
}
CATEGORY_MAP_REVERSE = {v: k for k, v in CATEGORY_MAP.items()}

class ChessboardValidator:
    """棋盘校验器：只检测，不修改"""

    def __init__(self):
        """初始化（无开关，纯逻辑）"""
        pass

    def validate_per_cell_red(self, transformed_board, layout_2d, scores):
        hsv = cv2.cvtColor(transformed_board, cv2.COLOR_BGR2HSV)

        # 红色掩码
        lower_red1, upper_red1 = np.array([0, 50, 50]), np.array([10, 255, 255])
        lower_red2, upper_red2 = np.array([160, 50, 50]), np.array([180, 255, 255])
        red_mask = cv2.inRange(hsv, lower_red1, upper_red1) + \
                   cv2.inRange(hsv, lower_red2, upper_red2)

        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

        board_h, board_w = transformed_board.shape[:2]
        cell_h, cell_w = board_h // 10, board_w // 9

        recommend_flip = []

        for i in range(10):
            for j in range(9):
                piece = layout_2d[i][j]
                if piece not in CATEGORY_MAP or piece in ['.', 'x']:
                    continue

                # 提取格子区域
                y1, y2 = i * cell_h, (i + 1) * cell_h
                x1, x2 = j * cell_w, (j + 1) * cell_w
                cell_mask = red_mask[y1:y2, x1:x2]

                # 【补充定义】格子总像素
                total_pixels = cell_h * cell_w

                # 计算中心区域（50%中心）
                margin = 0.25
                cy1, cy2 = int(cell_h * margin), int(cell_h * (1 - margin))
                cx1, cx2 = int(cell_w * margin), int(cell_w * (1 - margin))
                center_mask = cell_mask[cy1:cy2, cx1:cx2]

                center_pixels = (cy2 - cy1) * (cx2 - cx1)
                center_red = cv2.countNonZero(center_mask)
                total_red = cv2.countNonZero(cell_mask)

                center_ratio = center_red / center_pixels
                edge_red = total_red - center_red
                edge_pixels = total_pixels - center_pixels
                edge_ratio = edge_red / edge_pixels if edge_pixels > 0 else 0

                # 调试输出（临时添加，方便你观察）
                if piece.startswith('红') or piece.startswith('黑'):
                    logger.debug(f"[{i},{j}] {piece}: 中心{center_ratio:.1%} 边缘{edge_ratio:.1%}")

                is_home_row = (i >= 8) or (i <= 1)

                if piece.startswith('红'):
                    # 底线需要边缘红色>10%才认为是污染，中场只需>5%
                    edge_threshold = 0.10 if is_home_row else 0.05

                    if center_ratio < 0.02 and edge_ratio > edge_threshold:
                        short = CATEGORY_MAP[piece]
                        target = CATEGORY_MAP_REVERSE[short.lower()]
                        recommend_flip.append({
                            'pos': (i, j), 'from': piece, 'to': target,
                            'reason': f'颜色污染(行{i}):中心{center_ratio:.1%} 边缘{edge_ratio:.1%}'
                        })

                elif piece.startswith('黑'):
                    # 黑子深入敌阵的判断（通常在中场，底线很少出现黑子标成红子的情况）
                    if center_ratio > 0.08:
                        # 如果是底线黑子中心有红，可能是误识别，谨慎处理
                        if is_home_row and scores[i][j] > 0.7:
                            continue  # 高置信度底线黑子不翻转

                        short = CATEGORY_MAP[piece]
                        target = CATEGORY_MAP_REVERSE[short.upper()]
                        recommend_flip.append({
                            'pos': (i, j), 'from': piece, 'to': target,
                            'reason': f'深入敌阵:中心{center_ratio:.1%}'
                        })

        if recommend_flip:
            logger.info(f"🎯 检测到 {len(recommend_flip)} 个颜色不匹配")
            for f in recommend_flip:
                logger.info(f"   [{f['pos']}] {f['from']} -> {f['to']} | {f['reason']}")

        return {
            'recommend_flip': recommend_flip,
            'overall_confidence': 0.8 if recommend_flip else 1.0
        }

    def _create_flip(self, piece, i, j):
        """辅助函数：生成翻转记录，使用查表法处理异体字"""
        short = CATEGORY_MAP[piece]
        if piece.startswith('红'):
            target_short = short.lower()
        else:
            target_short = short.upper()
        target_piece = CATEGORY_MAP_REVERSE[target_short]

        return {
            'pos': (i, j),
            'from': piece,
            'to': target_piece
        }