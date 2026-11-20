"""ONNX Runtime provider 配置测试"""
import pytest

import src.chess_analyzer as chess_analyzer
import src.onnx_runtime as onnx_runtime


@pytest.fixture(autouse=True)
def reset_runtime():
    """每个用例前后恢复全局状态，避免互相影响"""
    onnx_runtime._reset_state(restore=True)
    yield
    onnx_runtime._reset_state(restore=True)


def test_normalize_providers_variants():
    """字符串/列表/非法值都能规范化"""
    assert onnx_runtime.normalize_providers('CPUExecutionProvider') == ['CPUExecutionProvider']
    assert onnx_runtime.normalize_providers(
        ['CUDAExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']) == \
        ['CUDAExecutionProvider', 'CPUExecutionProvider']
    assert onnx_runtime.normalize_providers(None) == onnx_runtime.DEFAULT_PROVIDERS
    assert onnx_runtime.normalize_providers(123) == onnx_runtime.DEFAULT_PROVIDERS
    assert onnx_runtime.normalize_providers([]) == onnx_runtime.DEFAULT_PROVIDERS


def test_select_providers_filters_and_appends_cpu():
    """只保留可用 provider，并保证 CPU 兜底在最后"""
    selected = onnx_runtime.select_providers(
        ['CUDAExecutionProvider', 'CPUExecutionProvider'],
        available=['CPUExecutionProvider'])

    assert selected == ['CPUExecutionProvider']

    selected = onnx_runtime.select_providers(
        ['TensorrtExecutionProvider', 'CUDAExecutionProvider'],
        available=['CUDAExecutionProvider', 'CPUExecutionProvider'])

    assert selected == ['CUDAExecutionProvider', 'CPUExecutionProvider']


def test_configure_gpu_available_preloads(monkeypatch):
    """CUDA 可用时选中 CUDA 并执行 preload_dlls"""
    preloaded = []
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CUDAExecutionProvider', 'CPUExecutionProvider'])
    monkeypatch.setattr(onnx_runtime.ort, 'preload_dlls', lambda: preloaded.append(True))

    info = onnx_runtime.configure_onnx_runtime(
        ['CUDAExecutionProvider', 'CPUExecutionProvider'])

    assert info['effective'] == ['CUDAExecutionProvider', 'CPUExecutionProvider']
    assert info['preloaded'] is True
    assert preloaded == [True]
    assert onnx_runtime.current_providers() == info['effective']


def test_configure_gpu_unavailable_falls_back(monkeypatch):
    """CUDA 不可用时回退 CPU，且不做无意义的 DLL 预加载"""
    preloaded = []
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CPUExecutionProvider'])
    monkeypatch.setattr(onnx_runtime.ort, 'preload_dlls', lambda: preloaded.append(True))

    info = onnx_runtime.configure_onnx_runtime(
        ['CUDAExecutionProvider', 'CPUExecutionProvider'])

    assert info['effective'] == ['CPUExecutionProvider']
    assert info['preloaded'] is False
    assert preloaded == []


def test_preload_failure_is_tolerated(monkeypatch):
    """preload_dlls 抛异常时不影响后续回退"""
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CUDAExecutionProvider', 'CPUExecutionProvider'])

    def boom():
        raise OSError('missing nvidia dll')

    monkeypatch.setattr(onnx_runtime.ort, 'preload_dlls', boom)

    info = onnx_runtime.configure_onnx_runtime(
        ['CUDAExecutionProvider', 'CPUExecutionProvider'])

    assert info['preloaded'] is False
    assert info['effective'][0] == 'CUDAExecutionProvider'


def test_patched_session_injects_providers(monkeypatch):
    """子模块未显式传 providers 时自动补上配置值"""
    recorded = {}

    def fake_session(*args, **kwargs):
        recorded['args'] = args
        recorded['kwargs'] = kwargs
        return 'session'

    monkeypatch.setattr(onnx_runtime.ort, 'InferenceSession', fake_session)
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CPUExecutionProvider'])

    onnx_runtime.configure_onnx_runtime(['CPUExecutionProvider'])
    onnx_runtime.ort.InferenceSession('model.onnx')

    assert recorded['kwargs']['providers'] == ['CPUExecutionProvider']


def test_patched_session_keeps_explicit_providers(monkeypatch):
    """调用方显式传入 providers 时不被覆盖"""
    recorded = {}

    def fake_session(*args, **kwargs):
        recorded['args'] = args
        recorded['kwargs'] = kwargs
        return 'session'

    monkeypatch.setattr(onnx_runtime.ort, 'InferenceSession', fake_session)
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CPUExecutionProvider'])

    onnx_runtime.configure_onnx_runtime(['CPUExecutionProvider'])
    onnx_runtime.ort.InferenceSession('model.onnx', None, ['CUDAExecutionProvider'])

    assert recorded['args'][2] == ['CUDAExecutionProvider']
    assert 'providers' not in recorded['kwargs']


def test_detector_retries_with_cpu_when_gpu_session_fails(monkeypatch):
    """GPU 会话创建失败时自动回退 CPU 并重试"""
    calls = {'count': 0}

    class FakeSession:
        def get_providers(self):
            return ['CPUExecutionProvider']

    class FakeModel:
        def __init__(self, **kwargs):
            self.session = FakeSession()

    class FailingDetector:
        def __init__(self, **kwargs):
            calls['count'] += 1
            if calls['count'] == 1:
                raise RuntimeError('CUDA init failed')
            self.pose = FakeModel()
            self.full_classifier = FakeModel()

    monkeypatch.setattr(chess_analyzer, 'OriginalDetector', FailingDetector)
    monkeypatch.setattr(chess_analyzer, 'CORE_AVAILABLE', True)
    monkeypatch.setattr(onnx_runtime.ort, 'get_available_providers',
                        lambda: ['CUDAExecutionProvider', 'CPUExecutionProvider'])
    monkeypatch.setattr(onnx_runtime.ort, 'preload_dlls', lambda: None)

    detector = chess_analyzer.ChessboardDetector(
        'pose.onnx', 'classifier.onnx',
        onnx_providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])

    assert calls['count'] == 2
    assert detector.detector is not None
    assert detector.provider_info['effective'] == ['CPUExecutionProvider']
