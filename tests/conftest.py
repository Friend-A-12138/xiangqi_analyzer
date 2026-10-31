"""pytest 共享配置：把仓库根目录加入导入路径"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def config_file(tmp_path):
    """返回一个临时配置文件路径"""
    return str(tmp_path / 'config.json')
