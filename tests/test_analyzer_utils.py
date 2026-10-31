"""分析结果序列化与 FEN 转换单元测试"""
import numpy as np

from src.chess_analyzer import XiangqiAnalyzer, parse_time_info
from web.app import encode_image, safe_float, serialize_result


def test_parse_time_info_supports_string_and_number():
    """检测器返回的耗时字符串能解析为秒数"""
    assert parse_time_info('推理用时: 0.45s') == 0.45
    assert parse_time_info(0.1) == 0.1
    assert parse_time_info('') == 0.0
    assert parse_time_info(None) == 0.0


def test_safe_float_handles_common_inputs():
    """数值字段容错，保证前端 toFixed 不报错"""
    assert safe_float('推理用时: 0.28s') == 0.28
    assert safe_float(None) == 0.0
    assert safe_float(np.float64(1.5)) == 1.5


def test_serialize_result_converts_numpy():
    """numpy 数组与标量都能转换为 JSON 可序列化类型"""
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    result = {
        'fen': '4k4/9/9/9/9/9/9/9/9/4K4',
        'scores': np.array([[0.9, 0.8]]),
        'confidence': np.float64(0.95),
        'detect_time': np.float64(0.2),
        'best_move': 'h2e2',
        'original_with_keypoints': image,
        'transformed_board': image,
    }

    data = serialize_result(result, include_images=False)
    assert isinstance(data['confidence'], float)
    assert isinstance(data['detect_time'], float)
    assert isinstance(data['scores'], list)
    assert 'original_with_keypoints' not in data

    with_images = serialize_result(result, include_images=True)
    assert with_images['transformed_board'].startswith('data:image/jpeg;base64,')


def test_encode_image_rejects_invalid_input():
    """无效图像返回 None 而不是抛异常"""
    assert encode_image(None) is None
    assert encode_image(np.array([])) is None


def _bare_analyzer(player_side='red'):
    """构造不初始化检测器/引擎的分析器实例，仅用于测试纯逻辑方法"""
    analyzer = object.__new__(XiangqiAnalyzer)
    analyzer.player_side = player_side
    return analyzer


def test_board_layout_to_fen_keeps_red_at_bottom():
    """红帅在下方时布局直接按行输出"""
    layout = [list(row) for row in [
        'rnbakabnr', '.........', '.........', '.........', '.........',
        '.........', '.........', '.........', '.........', 'RNBAKABNR']]
    fen = _bare_analyzer()._board_layout_to_fen(layout)
    assert fen == 'rnbakabnr/9/9/9/9/9/9/9/9/RNBAKABNR'


def test_board_layout_to_fen_handles_inverted_view():
    """红帅在上方时旋转180度并交换红黑"""
    layout = [list(row) for row in [
        'RNBAKABNR', '.........', '.........', '.........', '.........',
        '.........', '.........', '.........', '.........', 'rnbakabnr']]
    fen = _bare_analyzer()._board_layout_to_fen(layout)
    assert fen == 'rnbakabnr/9/9/9/9/9/9/9/9/RNBAKABNR'


def test_board_layout_to_fen_treats_occluded_as_empty():
    """遮挡位置 x 按空位处理，避免生成非法 FEN"""
    layout = [list(row) for row in [
        '4k4', '.........', '.........', '.........', '.........',
        '.........', '.........', '.........', '.........', 'xxxKxxxxx']]
    fen = _bare_analyzer()._board_layout_to_fen(layout)
    assert 'x' not in fen
    assert fen.endswith('3K5')


def test_side_to_move_mapping():
    """我方执子映射到 FEN 的走子方"""
    assert _bare_analyzer('red')._side_to_move() == 'w'
    assert _bare_analyzer('black')._side_to_move() == 'b'
    assert _bare_analyzer('auto')._side_to_move() is None
