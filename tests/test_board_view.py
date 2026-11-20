"""棋盘显示方向单元测试"""
import pytest

from src.board_view import (BLACK_BOTTOM, RED_BOTTOM, board_squares,
                            build_board_view, display_index, orientation_for,
                            square_to_index)

START_LAYOUT = [
    'rnbakabnr',
    '.........',
    '.c.....c.',
    'p.p.p.p.p',
    '.........',
    '.........',
    'P.P.P.P.P',
    '.C.....C.',
    '.........',
    'RNBAKABNR',
]


def start_board():
    return [list(row) for row in START_LAYOUT]


def test_orientation_follows_player_side():
    """我方执子决定显示朝向"""
    assert orientation_for('red') == RED_BOTTOM
    assert orientation_for('auto') == RED_BOTTOM
    assert orientation_for('black') == BLACK_BOTTOM


def test_red_bottom_keeps_fen_order():
    """执红时显示顺序与 FEN 顺序一致，红方在下方"""
    info = build_board_view(start_board(), 'red')
    view = info['view']
    squares = info['squares']

    assert info['orientation'] == RED_BOTTOM
    assert view[0][0] == 'r'          # 顶部是黑方底线
    assert view[9][4] == 'K'          # 底部中间是红帅
    assert squares[0][0] == 'a9'      # 左上角是 a9
    assert squares[9][0] == 'a0'      # 左下角是 a0
    assert squares[9][4] == 'e0'


def test_black_bottom_rotates_180_degrees():
    """执黑时黑方在下方，棋盘与坐标一起旋转"""
    info = build_board_view(start_board(), 'black')
    view = info['view']
    squares = info['squares']

    assert info['orientation'] == BLACK_BOTTOM
    assert view[0][8] == 'R'          # 旋转后左上角是红车
    assert view[9][4] == 'k'          # 底部中间是黑将
    assert squares[0][8] == 'a0'      # 旋转后左上角仍是 a0
    assert squares[9][8] == 'a9'      # 底部右侧是 a9
    assert squares[9][0] == 'i9'
    assert squares[9][4] == 'e9'


def test_view_squares_match_fen_board():
    """显示格与坐标一一对应，且与 FEN 顺序棋盘一致"""
    board = start_board()
    for side in ('red', 'black'):
        info = build_board_view(board, side)
        for row in range(10):
            for col in range(9):
                square = info['squares'][row][col]
                display_row, display_col = square_to_index(square, info['orientation'])
                assert (display_row, display_col) == (row, col)
                # UCI 坐标回到 FEN 顺序
                file_index = ord(square[0]) - ord('a')
                rank = int(square[1:])
                assert board[9 - rank][file_index] == info['view'][row][col]


def test_display_index_is_inverse_of_itself():
    """180 度旋转执行两次回到原位"""
    for row in range(10):
        for col in range(9):
            rotated = display_index(row, col, BLACK_BOTTOM)
            assert display_index(rotated[0], rotated[1], BLACK_BOTTOM) == (row, col)


def test_board_squares_cover_all_90_points():
    """坐标表覆盖 10x9 且不重复"""
    squares = board_squares()
    flat = [square for row in squares for square in row]
    assert len(flat) == 90
    assert len(set(flat)) == 90
    assert flat[0] == 'a9'
    assert flat[-1] == 'i0'


def test_invalid_board_shape_raises():
    """尺寸不合法的棋盘直接报错"""
    with pytest.raises(ValueError):
        build_board_view([list('abc')], 'red')
