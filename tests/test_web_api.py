"""Web 接口测试：使用假分析器，不依赖真实模型与引擎"""
import io
import json

import cv2
import numpy as np
import pytest

import web.app as webapp


class FakeAnalyzer:
    """返回固定分析结果的分析器替身"""

    def quit(self):
        """模拟关闭引擎"""

    def analyze_image(self, image, think_time=2000):
        layout = [list('4k4')] + [list('.........') for _ in range(8)] + [list('4K4')]
        view = [['点'] * 9 for _ in range(10)]
        squares = [[f"{chr(ord('a') + col)}{9 - row}" for col in range(9)]
                   for row in range(10)]
        return {
            'timestamp': '2026-01-01T00:00:00',
            'fen': '4k4/9/9/9/9/9/9/9/9/4K4',
            'layout_pgn': layout,
            'board': layout,
            'layout_2d': [['点'] * 9 for _ in range(10)],
            'view': view,
            'squares_view': squares,
            'orientation': 'red_bottom',
            'scores': [[0.9] * 9 for _ in range(10)],
            'detect_time': 0.2,
            'time_info': '推理用时: 0.20s',
            'occluded_count': 0,
            'best_move': 'h2e2',
            'best_move_cn': '炮八平五',
            'move_note': {'ok': True, 'text': '炮八平五', 'error': None},
            'arrow': {'from_square': 'h2', 'to_square': 'e2', 'side': 'red',
                      'board': {'from': [50, 250], 'to': [225, 250],
                                'size': [450, 500]},
                      'original': {'from': [10, 10], 'to': [30, 30],
                                   'size': [40, 40]}},
            'score': 0.5,
            'original_with_keypoints': image,
            'transformed_board': image,
            'confidence': 0.9,
        }


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """初始化应用并返回已登录的测试客户端"""
    config_path = str(tmp_path / 'config.json')

    webapp.user_manager.users.clear()
    webapp.user_manager.active_sessions.clear()
    webapp.init_app({'engine_path': 'C:/fake/pikafish.exe'},
                    config_file_path=config_path)

    monkeypatch.setattr(webapp, 'get_analyzer', lambda: (FakeAnalyzer(), None))

    test_client = webapp.app.test_client()
    test_client.post('/login', data={'username': 'admin', 'password': 'admin123'})
    return test_client, config_path


def make_image_bytes():
    """生成一张能通过 imdecode 的图片"""
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode('.png', image)
    assert ok
    return buffer.tobytes()


def test_status_requires_login():
    """/api/status 未登录返回 401"""
    webapp.user_manager.active_sessions.clear()
    response = webapp.app.test_client().get('/api/status')
    assert response.status_code == 401


def test_status_contains_tunnel_section(client):
    """登录后状态包含隧道信息"""
    test_client, _ = client
    body = test_client.get('/api/status').get_json()

    assert body['max_users'] >= 1
    assert 'tunnel' in body
    assert body['tunnel']['enabled'] is False


def test_upload_returns_serialized_result(client):
    """上传图片返回可序列化结果与图片 data URI"""
    test_client, _ = client
    response = test_client.post(
        '/api/upload',
        data={'image': (io.BytesIO(make_image_bytes()), 'board.png')},
        content_type='multipart/form-data')

    body = response.get_json()
    assert response.status_code == 200
    assert body['fen'] == '4k4/9/9/9/9/9/9/9/9/4K4'
    assert body['best_move'] == 'h2e2'
    assert body['best_move_cn'] == '炮八平五'
    assert body['orientation'] == 'red_bottom'
    assert body['squares_view'][9][4] == 'e0'
    assert body['view'][9][4] == '点'
    assert body['arrow']['from_square'] == 'h2'
    assert body['arrow']['to_square'] == 'e2'
    assert isinstance(body['detect_time'], float)
    assert body['transformed_board'].startswith('data:image/jpeg;base64,')


def test_settings_page_contains_board_and_arrow_hooks(client):
    """首页包含按朝向渲染的棋盘与箭头绘制逻辑"""
    test_client, _ = client
    page = test_client.get('/').data.decode('utf-8')

    assert 'board-arrow-layer' in page
    assert 'drawBoardArrow' in page
    assert 'squares_view' in page
    assert '显示朝向' in page


def test_settings_page_contains_uci_options(client):
    """设置页包含引擎线程数与哈希表配置"""
    test_client, _ = client
    page = test_client.get('/settings').data.decode('utf-8')

    assert 'uci-threads' in page
    assert 'uci-hash' in page
    assert 'frame-diff-threshold' in page


def test_config_update_persists_frame_diff_threshold(client):
    """画面变化阈值可保存"""
    test_client, config_path = client
    response = test_client.post('/api/config', json={'frame_diff_threshold': 7.5})

    assert response.status_code == 200
    saved = json.loads(open(config_path, encoding='utf-8').read())
    assert saved['frame_diff_threshold'] == 7.5


def test_config_update_persists_uci_options(client):
    """设置页提交的 UCI 选项被保存"""
    test_client, config_path = client
    response = test_client.post('/api/config', json={
        'uci_options': {'Threads': 4, 'Hash': 1024}
    })

    assert response.status_code == 200
    saved = json.loads(open(config_path, encoding='utf-8').read())
    assert saved['uci_options'] == {'Threads': 4, 'Hash': 1024}


def test_get_analyzer_passes_uci_options(tmp_path, monkeypatch):
    """按需创建分析器时把 UCI 选项传下去"""
    engine_file = tmp_path / 'pikafish.exe'
    engine_file.write_bytes(b'fake')
    captured = {}

    class DummyAnalyzer:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(webapp, 'XiangqiAnalyzer', DummyAnalyzer)
    webapp.init_app({'engine_path': str(engine_file),
                     'uci_options': {'Threads': 3, 'Hash': 128},
                     'onnx_providers': ['CPUExecutionProvider']},
                    config_file_path=str(tmp_path / 'config.json'))
    webapp.analyzer = None

    analyzer, error = webapp.get_analyzer()
    assert error is None
    assert isinstance(analyzer, DummyAnalyzer)
    assert captured['uci_options'] == {'Threads': 3, 'Hash': 128}
    assert captured['onnx_providers'] == ['CPUExecutionProvider']
    webapp.analyzer = None


def test_upload_batch_returns_notation(client):
    """批量结果包含中文记谱字段"""
    test_client, _ = client
    response = test_client.post(
        '/api/upload_batch',
        data={'images': [(io.BytesIO(make_image_bytes()), 'one.png')]},
        content_type='multipart/form-data')

    item = response.get_json()['results'][0]
    assert item['success']
    assert item['best_move_cn'] == '炮八平五'


def test_upload_batch_continues_after_bad_file(client):
    """批量分析中单张坏文件不影响其他图片"""
    test_client, _ = client
    data = {
        'images': [
            (io.BytesIO(make_image_bytes()), 'good.png'),
            (io.BytesIO(b'broken'), 'bad.png'),
        ]
    }
    response = test_client.post('/api/upload_batch', data=data,
                                content_type='multipart/form-data')
    body = response.get_json()

    assert response.status_code == 200
    assert body['total'] == 2
    assert body['success'] == 1
    assert body['failed'] == 1
    assert any(item.get('error') for item in body['results'])


def test_upload_batch_rejects_too_many_files(client):
    """超过上限时直接拒绝"""
    test_client, _ = client
    files = [(io.BytesIO(make_image_bytes()), f'{i}.png') for i in range(11)]

    response = test_client.post('/api/upload_batch', data={'images': files},
                                content_type='multipart/form-data')
    assert response.status_code == 400


def test_config_update_is_persisted(client):
    """设置页提交的配置写入文件并生效"""
    test_client, config_path = client
    response = test_client.post('/api/config', json={'player_side': 'black',
                                                     'think_time': 3500})
    body = response.get_json()

    assert response.status_code == 200 and body['success']
    saved = json.loads(open(config_path, encoding='utf-8').read())
    assert saved['player_side'] == 'black'
    assert saved['think_time'] == 3500


def test_users_api_create_and_delete(client):
    """用户接口可新增与删除，且不返回密码"""
    test_client, _ = client

    created = test_client.post('/api/users',
                               json={'username': 'tester', 'password': 'tester123'})
    assert created.status_code == 200

    users = test_client.get('/api/users').get_json()['users']
    assert 'tester' in [user['username'] for user in users]
    assert all('password' not in user for user in users)

    deleted = test_client.delete('/api/users/tester')
    assert deleted.status_code == 200
    assert 'tester' not in [user['username'] for user in deleted.get_json()['users']]


def test_cannot_delete_current_user(client):
    """不能删除当前登录用户"""
    test_client, _ = client
    response = test_client.delete('/api/users/admin')
    assert response.status_code == 400


def test_settings_page_renders_new_sections(client):
    """设置页包含我方执子与内网穿透配置"""
    test_client, _ = client
    page = test_client.get('/settings').data.decode('utf-8')

    assert 'player-side' in page
    assert 'tunnel-type' in page
    assert '启动穿透' in page


def test_config_change_resets_analyzer_and_frame_state(client):
    """修改配置后释放旧分析器、清空帧签名与箭头（下一次会按新执子重算）"""
    test_client, _ = client

    webapp.analyzer = FakeAnalyzer()
    webapp.last_analyzed_signature = 'stale-signature'
    webapp.latest_arrow = {'from_square': 'h2'}

    response = test_client.post('/api/config', json={'player_side': 'black'})

    assert response.status_code == 200
    assert webapp.analysis_config['player_side'] == 'black'
    assert webapp.analyzer is None
    assert webapp.last_analyzed_signature is None
    assert webapp.latest_arrow is None


class FakeCapture:
    """固定返回同一帧的采集器替身"""

    def __init__(self, frame):
        self.frame = frame

    def capture_window(self, region=None):
        return self.frame


class _LoopStop(Exception):
    """用于跳出分析循环"""


def test_analysis_loop_rebuilds_analyzer_and_reanalyzes(client, monkeypatch):
    """分析器被配置变更清空后，循环会按新配置重建并重新分析（即使画面没变）"""
    test_client, _ = client
    image = np.zeros((240, 320, 3), dtype=np.uint8)

    class LoopAnalyzer(FakeAnalyzer):
        def __init__(self):
            self.calls = 0

        def analyze_image(self, frame, think_time=2000):
            self.calls += 1
            return super().analyze_image(frame, think_time)

    created = []

    def fake_get_analyzer():
        analyzer = LoopAnalyzer()
        created.append(analyzer)
        return analyzer, None

    monkeypatch.setattr(webapp, 'get_analyzer', fake_get_analyzer)
    monkeypatch.setattr(webapp, 'screen_capture', FakeCapture(image))
    webapp.analysis_config['source_type'] = 'screen'
    webapp.analysis_config['source_value'] = ''
    webapp.analysis_config['think_time'] = 100
    webapp.analysis_config['analysis_interval'] = 1
    webapp.analysis_config['frame_diff_threshold'] = 3.0

    webapp.analyzer = None
    webapp.last_analyzed_signature = None
    webapp.last_analyzer_error = None
    webapp.running = True

    events = []
    monkeypatch.setattr(webapp.socketio, 'emit',
                        lambda name, payload=None: events.append(name))

    def stop_sleep(seconds):
        raise _LoopStop()

    monkeypatch.setattr(webapp.time, 'sleep', stop_sleep)

    with pytest.raises(_LoopStop):
        webapp.analysis_loop()

    webapp.running = False

    assert created, '分析器应被自动重建'
    assert created[0].calls == 1
    assert 'analysis_result' in events
