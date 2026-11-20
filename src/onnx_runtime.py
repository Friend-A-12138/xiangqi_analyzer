"""ONNX Runtime provider 配置

检测器位于 Chinese_Chess_Recognition 子模块，内部直接调用
``onnxruntime.InferenceSession(model_path)``，该子模块属于第三方仓库，
不能直接修改。因此在主仓一侧统一注入：

- 按配置选择 provider（默认 CUDA -> CPU），不可用时自动回退
- Windows 下在创建会话前按需 ``preload_dlls()``，让 pip 安装的 CUDA DLL 生效
- 用模块级包装替换 ``onnxruntime.InferenceSession``，未显式传 providers 时自动补上

这样无需改动子模块文件，也能让检测器走 GPU。
"""

import logging
import threading
from typing import Any, Dict, List, Optional

import onnxruntime as ort

logger = logging.getLogger(__name__)

CPU_PROVIDER = 'CPUExecutionProvider'

# 默认 provider 顺序：优先 CUDA，失败时回退 CPU
DEFAULT_PROVIDERS = ['CUDAExecutionProvider', 'CPUExecutionProvider']

_lock = threading.Lock()
_state = {
    'requested': None,
    'effective': None,
    'patched': False,
}
_original_session = None


def normalize_providers(value: Any) -> List[str]:
    """把配置里的 provider 规范化为去重后的字符串列表

    Args:
        value: 字符串、列表或 None

    Returns:
        List[str]: provider 名称列表，无效输入回退默认值
    """
    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple)):
        return list(DEFAULT_PROVIDERS)

    result = []
    for item in value:
        name = str(item).strip()
        if name and name not in result:
            result.append(name)

    return result or list(DEFAULT_PROVIDERS)


def select_providers(requested: List[str],
                     available: Optional[List[str]] = None) -> List[str]:
    """从请求的 provider 中筛选可用项，并保证包含 CPU 兜底

    Args:
        requested: 请求的 provider 列表
        available: 当前环境可用的 provider 列表，默认向 onnxruntime 查询

    Returns:
        List[str]: 实际可用的 provider 列表（CPU 在最后）
    """
    if available is None:
        available = list(ort.get_available_providers())

    selected = [name for name in requested if name in available]

    if CPU_PROVIDER in available and CPU_PROVIDER not in selected:
        selected.append(CPU_PROVIDER)

    return selected or [CPU_PROVIDER]


def preload_cuda_dlls(providers: List[str]) -> bool:
    """在创建会话前预加载 CUDA 相关 DLL

    Windows 上 pip 安装的 nvidia 运行库不在 PATH 中，需要 preload_dlls()
    才能让 CUDAExecutionProvider 真正生效。

    Args:
        providers: 实际将要使用的 provider 列表

    Returns:
        bool: 是否执行了预加载
    """
    if not any(name != CPU_PROVIDER for name in providers):
        return False

    loader = getattr(ort, 'preload_dlls', None)
    if loader is None:
        logger.info(f"当前 onnxruntime {ort.__version__} 不支持 preload_dlls，跳过预加载")
        return False

    try:
        loader()
        logger.info("已执行 onnxruntime.preload_dlls()")
        return True
    except Exception as e:
        logger.warning(f"preload_dlls() 失败，GPU 可能不可用: {e}")
        return False


def _install_patch() -> None:
    """用包装函数替换 onnxruntime.InferenceSession（只安装一次）"""
    global _original_session

    if _state['patched']:
        return

    _original_session = ort.InferenceSession

    def _session_with_providers(*args, **kwargs):
        if 'providers' not in kwargs and len(args) < 3:
            kwargs['providers'] = list(_state['effective'])
        return _original_session(*args, **kwargs)

    ort.InferenceSession = _session_with_providers
    _state['patched'] = True


def configure_onnx_runtime(providers: Any = None) -> Dict[str, Any]:
    """配置全局 onnxruntime provider，并让后续会话自动使用

    Args:
        providers: 配置中的 provider 列表（如 ["CUDAExecutionProvider", "CPUExecutionProvider"]）

    Returns:
        dict: requested / available / effective / preloaded 四项信息
    """
    requested = normalize_providers(providers)
    available = list(ort.get_available_providers())
    effective = select_providers(requested, available)
    preloaded = preload_cuda_dlls(effective)

    with _lock:
        _state['requested'] = requested
        _state['effective'] = effective
        _install_patch()

    logger.info(f"onnxruntime {ort.__version__} 可用 providers: {available}")
    logger.info(f"请求 providers: {requested} -> 实际使用: {effective}")

    if effective != requested:
        missing = [name for name in requested if name not in effective]
        if missing:
            logger.warning(f"以下 provider 不可用，已回退: {missing}")

    return {
        'requested': requested,
        'available': available,
        'effective': effective,
        'preloaded': preloaded,
    }


def current_providers() -> Optional[List[str]]:
    """返回当前生效的 provider 列表（未配置时为 None）"""
    return list(_state['effective']) if _state['effective'] else None


def _reset_state(restore: bool = True) -> None:
    """重置内部状态（仅供测试使用）

    Args:
        restore: 是否恢复原始的 InferenceSession
    """
    global _original_session

    if restore and _state['patched'] and _original_session is not None:
        ort.InferenceSession = _original_session

    _state['requested'] = None
    _state['effective'] = None
    _state['patched'] = False
    _original_session = None
