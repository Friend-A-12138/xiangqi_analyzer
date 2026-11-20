"""棋盘显示方向处理

检测器输出的布局固定为 FEN 顺序：第 0 行是黑方底线，第 9 行是红方底线。
Web 端再按“我方执子”决定显示方向：

- 执红：红方在下，显示行序与 FEN 顺序一致
- 执黑：黑方在下，显示时旋转 180 度

本模块同时给出每个显示格对应的 UCI 坐标，棋盘、坐标与走法箭头共用这一套映射，
避免出现“只转图片不转数据”的不一致。
"""

from typing import Dict, List

BOARD_ROWS = 10
BOARD_COLS = 9

# 显示朝向常量
RED_BOTTOM = 'red_bottom'
BLACK_BOTTOM = 'black_bottom'


def orientation_for(player_side: str) -> str:
    """根据我方执子返回显示朝向

    Args:
        player_side: red / black / auto

    Returns:
        str: RED_BOTTOM 或 BLACK_BOTTOM
    """
    return BLACK_BOTTOM if player_side == 'black' else RED_BOTTOM


def board_squares() -> List[List[str]]:
    """返回 FEN 顺序下每个格子的 UCI 坐标

    Returns:
        List[List[str]]: 10x9，第 0 行对应 rank 9
    """
    return [[f"{chr(ord('a') + col)}{9 - row}" for col in range(BOARD_COLS)]
            for row in range(BOARD_ROWS)]


def display_index(row: int, col: int, orientation: str) -> tuple:
    """把 FEN 顺序的格子换算成显示位置

    Args:
        row: FEN 顺序行号（0 = 黑方底线）
        col: 列号（0 = 文件 a）
        orientation: 显示朝向

    Returns:
        tuple: (显示行, 显示列)
    """
    if orientation == BLACK_BOTTOM:
        return BOARD_ROWS - 1 - row, BOARD_COLS - 1 - col
    return row, col


def build_board_view(board: List[List[str]], player_side: str = 'red') -> Dict:
    """按我方执子生成显示用棋盘与坐标

    Args:
        board: 10x9 的棋子短记号（FEN 顺序）
        player_side: red / black / auto

    Returns:
        dict: view（显示顺序棋子）、squares（显示顺序 UCI 坐标）、orientation
    """
    if len(board) != BOARD_ROWS or any(len(row) != BOARD_COLS for row in board):
        raise ValueError(f"棋盘尺寸应为 {BOARD_ROWS}x{BOARD_COLS}")

    orientation = orientation_for(player_side)
    squares = board_squares()

    view = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
    view_squares = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            view_row, view_col = display_index(row, col, orientation)
            view[view_row][view_col] = board[row][col]
            view_squares[view_row][view_col] = squares[row][col]

    return {
        'view': view,
        'squares': view_squares,
        'orientation': orientation
    }


def square_to_index(square: str, orientation: str = RED_BOTTOM) -> tuple:
    """把 UCI 坐标换算成显示位置

    Args:
        square: 形如 b0 的坐标
        orientation: 显示朝向

    Returns:
        tuple: (显示行, 显示列)
    """
    if not square or len(square) < 2:
        raise ValueError(f"非法坐标: {square}")

    file_index = ord(square[0].lower()) - ord('a')
    rank = int(square[1:])
    if not (0 <= file_index < BOARD_COLS) or not (0 <= rank < BOARD_ROWS):
        raise ValueError(f"坐标越界: {square}")

    row = BOARD_ROWS - 1 - rank
    return display_index(row, file_index, orientation)
