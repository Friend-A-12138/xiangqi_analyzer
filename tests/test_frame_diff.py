"""帧差分单元测试"""
import numpy as np

from src.frame_diff import (DEFAULT_THRESHOLD, SIGNATURE_SIZE,
                            frame_difference, frame_signature, is_frame_changed)


def make_frame(value=0, size=(240, 320)):
    """生成纯色 BGR 画面"""
    frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    frame[:] = value
    return frame


def test_signature_is_small_grayscale():
    """签名是小尺寸 float32 灰度图"""
    signature = frame_signature(make_frame(120))

    assert signature is not None
    assert signature.shape == (SIGNATURE_SIZE[1], SIGNATURE_SIZE[0])
    assert signature.dtype == np.float32


def test_signature_handles_grayscale_and_invalid_input():
    """灰度输入可用，None/空图返回 None"""
    gray = np.zeros((240, 320), dtype=np.uint8)
    assert frame_signature(gray) is not None

    assert frame_signature(None) is None
    assert frame_signature(np.array([])) is None


def test_identical_frames_have_zero_difference():
    """同一帧差异为 0，且视为无变化"""
    frame = make_frame(90)
    signature = frame_signature(frame)

    assert frame_difference(signature, signature) == 0.0

    changed, score = is_frame_changed(signature, signature, DEFAULT_THRESHOLD)
    assert changed is False
    assert score == 0.0


def test_small_noise_below_threshold_is_ignored():
    """轻微噪声低于阈值时视为无变化"""
    base = frame_signature(make_frame(100))

    noisy_frame = make_frame(100)
    noisy_frame[0:5, 0:5] = 101          # 极小变化
    noisy = frame_signature(noisy_frame)

    changed, score = is_frame_changed(noisy, base, 5.0)
    assert changed is False
    assert score < 5.0


def test_large_change_exceeds_threshold():
    """明显变化（如走子）超过阈值"""
    before = frame_signature(make_frame(40))

    after_frame = make_frame(40)
    after_frame[60:180, 80:240] = 220    # 大面积变化
    after = frame_signature(after_frame)

    changed, score = is_frame_changed(after, before, 3.0)
    assert changed is True
    assert score > 3.0


def test_zero_threshold_never_skips():
    """阈值为 0 表示不做跳过"""
    signature = frame_signature(make_frame(50))
    changed, _ = is_frame_changed(signature, signature, 0)
    assert changed is True


def test_missing_or_mismatched_signature_is_treated_as_changed():
    """缺少历史帧或尺寸不一致时按有变化处理，避免漏分析"""
    signature = frame_signature(make_frame(50))

    assert is_frame_changed(signature, None, 3.0)[0] is True
    assert frame_difference(signature, None) is None

    other = frame_signature(make_frame(50, size=(160, 120)), size=(80, 60))
    assert is_frame_changed(other, signature, 3.0)[0] is True
