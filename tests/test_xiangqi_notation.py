"""中文记谱单元测试"""
from src.xiangqi_notation import (file_number, move_to_chinese, number_text,
                                  square_to_rowcol)


def empty_board():
    return [['.'] * 9 for _ in range(10)]


def board_with(*pieces):
    """按 (行, 列, 棋子) 构造棋盘"""
    board = empty_board()
    for row, col, piece in pieces:
        board[row][col] = piece
    return board


def test_square_to_rowcol():
    """UCI 坐标换算：rank 0 在红方底线（行9）"""
    assert square_to_rowcol('a0') == (9, 0)
    assert square_to_rowcol('e0') == (9, 4)
    assert square_to_rowcol('a9') == (0, 0)
    assert square_to_rowcol('i9') == (0, 8)


def test_file_number_is_one_based_from_left():
    """列号沿 a-i 从 1 开始"""
    assert file_number(0) == 1
    assert file_number(8) == 9


def test_number_text_by_side():
    """红方中文数字，黑方阿拉伯数字"""
    assert number_text(3, True) == '三'
    assert number_text(3, False) == '3'


def test_red_cannon_to_center():
    """红炮二平五（经典开局）"""
    board = board_with((7, 1, 'C'))
    result = move_to_chinese(board, 'b2e2')
    assert result['ok'] and result['text'] == '炮二平五'


def test_black_knight_uses_arabic_numbers():
    """黑方走法使用阿拉伯数字：马8进7"""
    board = board_with((0, 7, 'n'))
    result = move_to_chinese(board, 'h9g7')
    assert result['ok'] and result['text'] == '马8进7'


def test_red_knight_advance():
    """马二进三：起点 b0、终点 c2"""
    board = board_with((9, 1, 'N'))
    result = move_to_chinese(board, 'b0c2')
    assert result['ok'] and result['text'] == '马二进三'


def test_red_pawn_advance():
    """兵七进一：起点 g3"""
    board = board_with((6, 6, 'P'))
    result = move_to_chinese(board, 'g3g4')
    assert result['ok'] and result['text'] == '兵七进一'


def test_red_rook_flat_move():
    """车一平二：横向移动跟目标列"""
    board = board_with((9, 0, 'R'))
    result = move_to_chinese(board, 'a0b0')
    assert result['ok'] and result['text'] == '车一平二'


def test_black_rook_flat_move():
    """黑车1平2"""
    board = board_with((0, 0, 'r'))
    result = move_to_chinese(board, 'a9b9')
    assert result['ok'] and result['text'] == '车1平2'


def test_red_advisor_uses_target_file():
    """仕四进五：相/仕/马 的进/退跟目标列"""
    board = board_with((9, 3, 'A'))
    result = move_to_chinese(board, 'd0e1')
    assert result['ok'] and result['text'] == '仕四进五'


def test_two_rooks_same_file_front_and_back():
    """同列双子用前/后区分"""
    board = board_with((9, 4, 'R'), (7, 4, 'R'))

    front = move_to_chinese(board, 'e2e3')
    back = move_to_chinese(board, 'e0e1')

    assert front['ok'] and front['text'] == '前车进一'
    assert back['ok'] and back['text'] == '后车进一'


def test_black_two_pawns_same_file_front_and_back():
    """黑方同列双子同样用前/后，数字用阿拉伯"""
    board = board_with((3, 4, 'p'), (5, 4, 'p'))

    front = move_to_chinese(board, 'e4e3')   # 行5 -> 行6，黑方前进；行5 更靠前
    back = move_to_chinese(board, 'e6e5')    # 行3 -> 行4，黑方前进；行3 更靠后

    assert front['ok'] and front['text'] == '前卒进1'
    assert back['ok'] and back['text'] == '后卒进1'


def test_retreat_notation():
    """红方后退"""
    board = board_with((7, 1, 'C'))
    result = move_to_chinese(board, 'b2b1')
    assert result['ok'] and result['text'] == '炮二退一'


def test_three_same_file_pieces_is_ambiguous():
    """同列三个同种棋子时明确返回不支持，而不是猜"""
    board = board_with((4, 4, 'P'), (5, 4, 'P'), (6, 4, 'P'))
    result = move_to_chinese(board, 'e5e6')
    assert not result['ok']
    assert '前/中/后' in result['error']


def test_empty_origin_is_reported():
    """起点没有棋子"""
    board = empty_board()
    result = move_to_chinese(board, 'b0c2')
    assert not result['ok']
    assert '没有棋子' in result['error']


def test_side_mismatch_is_reported():
    """走子方与棋子颜色不一致"""
    board = board_with((7, 1, 'C'))
    result = move_to_chinese(board, 'b2e2', side='black')
    assert not result['ok']
    assert '不一致' in result['error']
