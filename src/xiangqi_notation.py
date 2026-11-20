"""中国象棋中文记谱

把 UCI 坐标走法（如 b0c2）转换为中文记谱（如 马八进七）。

规则：
- 行文用“棋子 + 列号 + 进/退/平 + 数字”
- 红方用中文数字（一二三…），黑方用阿拉伯数字（123…）
- 列号沿 FEN/UCI 坐标统一从 a 到 i 编号 1-9（红黑同向；等价于“各自从右手边数起”）
- 车/炮/兵/卒/帅/将的进/退后面跟移动的行数；马/相/仕的进/退后面跟目标列
- 同一列有多个同种棋子时按《象棋竞赛规则》用位置标记代替列号：
  2 个用 前/后，3 个用 前/中/后，4 个用 前/二/三/后，5 个用 前/二/三/四/后；
  前 = 更靠近对方底线的一枚（红黑各自从自己的视角判断）
"""

from typing import Dict, List, Optional

BOARD_ROWS = 10
BOARD_COLS = 9

CHINESE_DIGITS = '一二三四五六七八九'

PIECE_NAMES = {
    'K': '帅', 'A': '仕', 'B': '相', 'N': '马', 'R': '车', 'C': '炮', 'P': '兵',
    'k': '将', 'a': '士', 'b': '象', 'n': '马', 'r': '车', 'c': '炮', 'p': '卒',
}

# 进/退后面跟“目标列”的棋子（其余跟移动行数）
FILE_SUFFIX_PIECES = set('NBAnba')

# 同一列多个同种棋子时的位置标记（按“从前到后”排序，前 = 更靠近对方底线）
SAME_FILE_LABELS = {
    2: ['前', '后'],
    3: ['前', '中', '后'],
    4: ['前', '二', '三', '后'],
    5: ['前', '二', '三', '四', '后'],
}

RED_PIECE_SYMBOLS = set('KABNRCP')
BLACK_PIECE_SYMBOLS = set('kabnrcp')


def square_to_rowcol(square: str) -> tuple:
    """把 UCI 坐标换算成 FEN 顺序的行列

    Args:
        square: 形如 b0 的坐标

    Returns:
        tuple: (行, 列)，第 0 行为黑方底线
    """
    if not square or len(square) < 2:
        raise ValueError(f"非法坐标: {square}")

    file_index = ord(square[0].lower()) - ord('a')
    rank = int(square[1:])

    if not (0 <= file_index < BOARD_COLS) or not (0 <= rank < BOARD_ROWS):
        raise ValueError(f"坐标越界: {square}")

    return BOARD_ROWS - 1 - rank, file_index


def file_number(col: int) -> int:
    """列号（1-9，沿 FEN 坐标从 a 到 i）"""
    return col + 1


def number_text(value: int, is_red: bool) -> str:
    """按红/黑方输出数字"""
    if is_red:
        return CHINESE_DIGITS[value - 1]
    return str(value)


def _piece_name(piece: str) -> str:
    return PIECE_NAMES.get(piece, piece)


def move_to_chinese(board: List[List[str]], move: str,
                    side: Optional[str] = None) -> Dict:
    """把坐标走法翻译为中文记谱

    Args:
        board: FEN 顺序的 10x9 棋盘（大写红、小写黑）
        move: UCI 走法，如 b0c2
        side: 走子方 red/black；为空时按起点棋子颜色判断

    Returns:
        dict: ok/text/side/piece/error 等字段；无法确定时 ok=False 并给出原因
    """
    if not move or len(move) < 4:
        return {'ok': False, 'text': None, 'fallback': move, 'error': f'非法走法: {move}'}

    from_square, to_square = move[:2], move[2:4]

    try:
        from_row, from_col = square_to_rowcol(from_square)
        to_row, to_col = square_to_rowcol(to_square)
    except ValueError as exc:
        return {'ok': False, 'text': None, 'fallback': move, 'error': str(exc)}

    piece = board[from_row][from_col]
    if piece not in PIECE_NAMES:
        return {'ok': False, 'text': None, 'fallback': move,
                'error': f'起点 {from_square} 没有棋子'}

    piece_is_red = piece.isupper()
    if side not in ('red', 'black'):
        side = 'red' if piece_is_red else 'black'
    elif (side == 'red') != piece_is_red:
        return {'ok': False, 'text': None, 'fallback': move,
                'error': f'走子方与棋子颜色不一致: {side} / {piece}'}

    is_red = side == 'red'

    # 同一列上的同种棋子：按《象棋竞赛规则》用 前/后、前/中/后、前/二/三/后 等表示
    same_file_rows = [row for row in range(BOARD_ROWS)
                      if board[row][from_col] == piece]

    # 前 = 更靠近对方底线的一枚：红方取行号最小，黑方取行号最大
    front_first_rows = sorted(same_file_rows, reverse=(side == 'black'))
    labels = SAME_FILE_LABELS.get(len(front_first_rows))

    if labels is None and len(front_first_rows) > 5:
        return {'ok': False, 'text': None, 'fallback': move,
                'error': f'同一列有 {len(front_first_rows)} 个同种棋子，超出规则范围'}

    if labels:
        label = labels[front_first_rows.index(from_row)]
        head = label + _piece_name(piece)
    else:
        head = _piece_name(piece) + number_text(file_number(from_col), is_red)

    if to_row == from_row:
        action = '平'
    elif is_red:
        action = '进' if to_row < from_row else '退'
    else:
        action = '进' if to_row > from_row else '退'

    if action == '平' or piece in FILE_SUFFIX_PIECES:
        suffix = number_text(file_number(to_col), is_red)
    else:
        suffix = number_text(abs(to_row - from_row), is_red)

    return {
        'ok': True,
        'text': f'{head}{action}{suffix}',
        'fallback': move,
        'side': side,
        'piece': _piece_name(piece),
        'action': action,
        'error': None,
    }
