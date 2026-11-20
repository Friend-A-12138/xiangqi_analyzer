"""引擎封装单元测试：用假进程验证 UCI 交互与走子方传递"""
import threading

import pytest

import src.chess_analyzer as module
from src.chess_analyzer import PikafishEngine


class FakeStdout:
    """按顺序返回预置输出"""

    def __init__(self):
        self._lines = []
        self._lock = threading.Lock()

    def feed(self, *lines):
        with self._lock:
            self._lines.extend(lines)

    def readline(self):
        with self._lock:
            return self._lines.pop(0) + '\n' if self._lines else ''


class FakeStdin:
    """记录写入内容，并按命令产生引擎输出"""

    def __init__(self, out):
        self.out = out
        self.commands = []

    def write(self, text):
        command = text.strip()
        self.commands.append(command)

        if command == 'uci':
            self.out.feed('id name Fake', 'uciok')
        elif command == 'isready':
            self.out.feed('readyok')
        elif command.startswith('go'):
            self.out.feed('info depth 10 score cp 42 pv h2e2 h9g7', 'bestmove h2e2')

    def flush(self):
        pass


class FakeProcess:
    """最小可用的进程替身"""

    def __init__(self):
        self.stdout = FakeStdout()
        self.stdin = FakeStdin(self.stdout)
        self.returncode = None

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return 0

    def terminate(self):
        self.returncode = 0

    def kill(self):
        self.returncode = 0


@pytest.fixture()
def fake_engine(tmp_path, monkeypatch):
    """用假进程替换 subprocess.Popen，避免依赖真实引擎"""
    engine_path = tmp_path / 'pikafish.exe'
    engine_path.write_bytes(b'fake')

    process = FakeProcess()
    monkeypatch.setattr(module.subprocess, 'Popen',
                        lambda *args, **kwargs: process)

    engine = PikafishEngine(str(engine_path))
    return engine, process


def test_engine_sends_uci_options(tmp_path, monkeypatch):
    """启动后按配置下发 Threads/Hash"""
    engine_path = tmp_path / 'pikafish.exe'
    engine_path.write_bytes(b'fake')

    process = FakeProcess()
    monkeypatch.setattr(module.subprocess, 'Popen',
                        lambda *args, **kwargs: process)

    PikafishEngine(str(engine_path),
                   uci_options={'Threads': 6, 'Hash': 256})

    commands = process.stdin.commands
    assert 'setoption name Threads value 6' in commands
    assert 'setoption name Hash value 256' in commands


def test_engine_skips_options_when_empty(tmp_path, monkeypatch):
    """未配置 UCI 选项时不下发 setoption"""
    engine_path = tmp_path / 'pikafish.exe'
    engine_path.write_bytes(b'fake')

    process = FakeProcess()
    monkeypatch.setattr(module.subprocess, 'Popen',
                        lambda *args, **kwargs: process)

    PikafishEngine(str(engine_path))

    options = [cmd for cmd in process.stdin.commands if cmd.startswith('setoption name Threads')]
    assert options == []


def test_engine_parses_best_move(fake_engine):
    """解析 bestmove 与 cp 评分"""
    engine, _ = fake_engine
    result = engine.get_best_move('rnbakabnr/9/9/9/9/9/9/9/9/RNBAKABNR',
                                  think_time=100, side_to_move='w')

    assert result['best_move'] == 'h2e2'
    assert result['score'] == 0.42
    assert result.get('error') is None


def test_engine_sends_requested_side_to_move(fake_engine):
    """FEN 中的走子方来自调用方参数"""
    engine, process = fake_engine
    engine.get_best_move('rnbakabnr/9/9/9/9/9/9/9/9/RNBAKABNR',
                         think_time=100, side_to_move='b')

    positions = [c for c in process.stdin.commands if c.startswith('position fen')]
    assert positions and positions[-1].endswith('b - - 0 1')


def test_engine_infers_side_when_not_given(fake_engine):
    """未指定走子方时按红帅位置推断"""
    engine, process = fake_engine
    engine.get_best_move('rnbakabnr/9/9/9/9/9/9/9/9/RNBAKABNR', think_time=100)

    positions = [c for c in process.stdin.commands if c.startswith('position fen')]
    assert positions and positions[-1].endswith('w - - 0 1')
