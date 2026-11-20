"""箭头坐标与绘制单元测试"""
import numpy as np

from src.board_render import (ARROW_COLORS, arrow_metrics, board_cell_size,
                              board_point, draw_arrow, draw_on_board,
                              draw_on_original, original_cell_size, to_original)

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


def test_arrow_metrics_scale_with_cell_size():
    """箭头尺寸随格子尺寸等比缩放"""
    small = arrow_metrics(40)
    large = arrow_metrics(80)

    assert small['head_length'] == 20.0        # 0.5 格
    assert large['head_length'] == 40.0
    assert small['thickness'] == 3             # 0.08 格
    assert large['thickness'] == 6
    assert large['head_half_width'] == small['head_half_width'] * 2


def test_arrow_metrics_do_not_depend_on_move_distance():
    """同样的格子尺寸下，箭头参数与走法距离无关"""
    assert arrow_metrics(35) == arrow_metrics(35)
    assert arrow_metrics(35)['head_length'] == 17.5


def test_board_cell_size_matches_corner_spacing():
    """棋盘图格子尺寸由四角间距得出"""
    # 宽 350/8=43.75，高 400/9≈44.44，平均取中
    assert abs(board_cell_size(CORNERS) - (43.75 + 400 / 9) / 2) < 1e-6


def test_original_cell_size_matches_board_when_identical():
    """原图与棋盘图坐标系一致时，格子尺寸相同"""
    cell = original_cell_size(CORNERS, CORNERS, 5, 4)
    assert cell is not None
    assert abs(cell - board_cell_size(CORNERS)) < 1e-3


def _head_width(image, color, tip_y, cell):
    """测量竖直向上箭头在箭头区域的彩色最大宽度"""
    mask = np.all(image == np.array(color, dtype=np.uint8), axis=2)
    head = int(round(cell * 0.5))
    rows = range(int(tip_y), int(tip_y) + head)
    widths = [int(mask[row].sum()) for row in rows]
    return max(widths) if widths else 0


def test_head_size_is_fixed_regardless_of_move_length():
    """短走法与长走法的箭头头部一样大（都按格子比例）"""
    color = (0, 0, 255)
    cell = 20
    image = np.zeros((300, 300, 3), dtype=np.uint8)

    short = draw_arrow(image, [150, 200], [150, 200 - cell], color=color, cell_size=cell)
    long = draw_arrow(image, [150, 280], [150, 280 - 5 * cell], color=color, cell_size=cell)

    short_width = _head_width(short, color, 200 - cell, cell)
    long_width = _head_width(long, color, 280 - 5 * cell, cell)

    assert short_width > 0 and long_width > 0
    assert abs(short_width - long_width) <= 2


def test_head_size_scales_with_cell_not_image_size():
    """大图/小图上头部按格子比例缩放"""
    color = (0, 0, 255)

    small_image = np.zeros((300, 300, 3), dtype=np.uint8)
    large_image = np.zeros((600, 600, 3), dtype=np.uint8)

    small = draw_arrow(small_image, [150, 200], [150, 180], color=color, cell_size=20)
    large = draw_arrow(large_image, [300, 400], [300, 360], color=color, cell_size=40)

    small_width = _head_width(small, color, 180, 20)
    large_width = _head_width(large, color, 360, 40)

    assert large_width == small_width * 2 or abs(large_width - small_width * 2) <= 2


def test_draw_on_board_uses_cell_size_from_arrow():
    """棋盘绘制使用 arrow 中的格子尺寸"""
    image = np.zeros((500, 450, 3), dtype=np.uint8)
    arrow = {'side': 'red',
             'board': {'from': [50, 50], 'to': [50, 450], 'cell': 43.75}}

    drawn = draw_on_board(image, arrow)
    assert drawn is not None
    assert np.count_nonzero(drawn) > 0
