"""箭头坐标与绘制单元测试"""
import numpy as np

from src.board_render import (ARROW_COLORS, board_point, draw_arrow,
                              draw_on_board, draw_on_original, to_original)

# 检测器输出的棋盘四角（450x500 棋盘图，padding=50）
CORNERS = [[50, 50], [400, 50], [50, 450], [400, 450]]


def test_board_point_corners():
    """四角行列换算结果与角点一致"""
    assert board_point(0, 0, CORNERS) == [50.0, 50.0]
    assert board_point(0, 8, CORNERS) == [400.0, 50.0]
    assert board_point(9, 0, CORNERS) == [50.0, 450.0]
    assert board_point(9, 8, CORNERS) == [400.0, 450.0]


def test_board_point_center_is_symmetric():
    """中心点位于棋盘中央"""
    x, y = board_point(4.5, 4, CORNERS)
    assert abs(x - 225.0) < 1e-6
    assert abs(y - 250.0) < 1e-6


def test_to_original_identity_when_same_corners():
    """原图四角与棋盘四角一致时投影不变"""
    points = [[50, 50], [225, 250]]
    projected = to_original(points, CORNERS, CORNERS)
    assert projected is not None
    assert abs(projected[0][0] - 50) < 1e-4
    assert abs(projected[1][1] - 250) < 1e-4


def test_to_original_scales_with_keypoints():
    """原图坐标是棋盘坐标的两倍时，投影结果翻倍"""
    keypoints = [[x * 2, y * 2] for x, y in CORNERS]
    projected = to_original([[225, 250]], keypoints, CORNERS)
    assert projected is not None
    assert abs(projected[0][0] - 450) < 1e-3
    assert abs(projected[0][1] - 500) < 1e-3


def test_to_original_returns_none_for_degenerate_matrix():
    """退化关键点无法求逆时返回 None 而不抛异常"""
    degenerate = [[0, 0], [0, 0], [0, 0], [0, 0]]
    assert to_original([[10, 10]], degenerate, CORNERS) is None


def test_draw_arrow_does_not_mutate_input():
    """绘制返回新图，原图不变"""
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    drawn = draw_arrow(image, [10, 50], [90, 50])

    assert drawn.shape == image.shape
    assert np.count_nonzero(drawn) > 0
    assert np.count_nonzero(image) == 0


def test_draw_arrow_uses_requested_color():
    """箭头颜色按走子方传入"""
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    drawn = draw_arrow(image, [10, 50], [90, 50], color=ARROW_COLORS['black'])

    blue = drawn[:, :, 0] > 200
    assert blue.any()


def test_draw_on_board_requires_coordinates():
    """缺少坐标时返回 None"""
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    assert draw_on_board(image, None) is None
    assert draw_on_board(image, {'board': None}) is None


def test_draw_on_original_draws_when_coordinates_exist():
    """有原图坐标时能画出箭头"""
    image = np.zeros((120, 120, 3), dtype=np.uint8)
    arrow = {'side': 'black',
             'original': {'from': [10, 10], 'to': [100, 100]}}

    drawn = draw_on_original(image, arrow)
    assert drawn is not None
    assert np.count_nonzero(drawn) > 0
