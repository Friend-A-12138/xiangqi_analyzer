"""
配置管理模块
统一管理 config/config.json、命令行参数和 Web 界面的配置项
"""

import copy
import ctypes
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 项目根目录（src 的上一级）
project_root = Path(__file__).parent.parent


def physical_cpu_count() -> int:
    """返回 CPU 物理核数

    Windows 下通过 GetLogicalProcessorInformationEx 统计物理核，
    其他平台或调用失败时退回逻辑核数。

    Returns:
        int: 物理核数，至少为 1
    """
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            length = ctypes.c_uint32(0)

            # RelationProcessorCore = 0
            if kernel32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(length)) == 0 \
                    and length.value > 0:
                buffer = ctypes.create_string_buffer(length.value)
                if kernel32.GetLogicalProcessorInformationEx(
                        0, buffer, ctypes.byref(length)) != 0:
                    count = 0
                    offset = 0
                    while offset + 8 <= length.value:
                        relationship = ctypes.c_uint.from_buffer(buffer, offset).value
                        size = ctypes.c_uint.from_buffer(buffer, offset + 4).value
                        if size <= 0:
                            break
                        if relationship == 0:
                            count += 1
                        offset += size

                    if count > 0:
                        return count
        except Exception as e:
            logger.debug(f"获取物理核数失败，改用逻辑核数: {e}")

    return max(1, os.cpu_count() or 1)


# UCI 选项默认值：线程数取物理核数，哈希表 512MB
DEFAULT_UCI_OPTIONS = {
    'Threads': physical_cpu_count(),
    'Hash': 512,
}

# UCI 选项取值范围（与 Pikafish 的 UCI 声明一致）
UCI_OPTION_LIMITS = {
    'Threads': (1, 1024),
    'Hash': (1, 33554432),
}

# 默认配置
DEFAULT_CONFIG = {
    'engine_path': '',
    'pose_model_path': 'onnx/pose/4_v6-0301.onnx',
    'classifier_model_path': 'onnx/layout_recognition/nano_v3-0319.onnx',
    'source_type': 'file',
    'source_value': '',
    'player_side': 'red',
    'think_time': 2000,
    'analysis_interval': 3,
    'frame_diff_threshold': 3.0,
    'onnx_providers': ['CUDAExecutionProvider', 'CPUExecutionProvider'],
    'max_users': 5,
    'uci_options': DEFAULT_UCI_OPTIONS,
    'enable_tunnel': False,
    'tunnel_type': 'ngrok',
    'tunnel_config': {
        'auth_token': '',
        'region': 'ap'
    }
}

# 支持的信号源类型与内网穿透类型
SOURCE_TYPES = ('file', 'stream', 'emulator', 'screen')
TUNNEL_TYPES = ('ngrok', 'frp')

# 我方执子：red 红方走子 / black 黑方走子 / auto 自动判断
PLAYER_SIDES = ('red', 'black', 'auto')

# 参数取值范围（与 Web 设置页滑块保持一致）
THINK_TIME_RANGE = (500, 10000)
ANALYSIS_INTERVAL_RANGE = (1, 60)
MAX_USERS_RANGE = (1, 20)

# 画面变化阈值（灰度均方差），0 表示不做跳过
FRAME_DIFF_RANGE = (0.0, 10000.0)


def config_path() -> Path:
    """返回默认配置文件路径"""
    return project_root / 'config' / 'config.json'


def default_config() -> Dict[str, Any]:
    """返回默认配置的深拷贝"""
    return copy.deepcopy(DEFAULT_CONFIG)


def _merge(base: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
    """把已加载的配置合并到基础配置中，未知键会被忽略

    Args:
        base: 基础配置（会被就地修改）
        loaded: 从文件或命令行得到的配置

    Returns:
        Dict: 合并后的配置
    """
    for key, value in loaded.items():
        if key not in base:
            logger.warning(f"忽略未知配置项: {key}")
            continue

        if isinstance(base[key], dict) and isinstance(value, dict):
            _merge(base[key], value)
        else:
            base[key] = value

    return base


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件，缺失的配置项使用默认值

    Args:
        config_file: 配置文件路径，默认使用 config/config.json

    Returns:
        Dict: 完整配置
    """
    config = default_config()
    path = Path(config_file) if config_file else config_path()

    if not path.exists():
        logger.warning(f"配置文件不存在，使用默认配置: {path}")
        return config

    try:
        with open(path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            logger.error(f"配置文件格式错误（应为JSON对象）: {path}")
            return config

        _merge(config, loaded)
        logger.info(f"配置文件已加载: {path}")

    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")

    return normalize_config(config)


def save_config(config: Dict[str, Any], config_file: Optional[str] = None) -> bool:
    """保存配置到文件

    Args:
        config: 配置字典
        config_file: 配置文件路径，默认使用 config/config.json

    Returns:
        bool: 是否保存成功
    """
    path = Path(config_file) if config_file else config_path()

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(normalize_config(config), f, indent=2, ensure_ascii=False)

        logger.info(f"配置文件已保存: {path}")
        return True

    except Exception as e:
        logger.error(f"保存配置文件失败: {e}")
        return False


def normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """校验并规范化配置，非法值回退到默认值或取值范围

    Args:
        config: 原始配置

    Returns:
        Dict: 规范化后的配置（新字典）
    """
    result = default_config()
    _merge(result, config if isinstance(config, dict) else {})

    # 路径统一为字符串
    for key in ('engine_path', 'pose_model_path', 'classifier_model_path', 'source_value'):
        value = result.get(key)
        result[key] = '' if value is None else str(value).strip()

    # 信号源与穿透类型
    if result['source_type'] not in SOURCE_TYPES:
        logger.warning(f"不支持的信号源类型: {result['source_type']}，回退为 file")
        result['source_type'] = 'file'

    if result['tunnel_type'] not in TUNNEL_TYPES:
        logger.warning(f"不支持的内网穿透类型: {result['tunnel_type']}，回退为 ngrok")
        result['tunnel_type'] = 'ngrok'

    # 我方执子
    if result['player_side'] not in PLAYER_SIDES:
        logger.warning(f"不支持的我方执子: {result['player_side']}，回退为 red")
        result['player_side'] = 'red'

    # 数值参数
    result['think_time'] = _clamp_int(
        result['think_time'], THINK_TIME_RANGE, DEFAULT_CONFIG['think_time'])
    result['analysis_interval'] = _clamp_int(
        result['analysis_interval'], ANALYSIS_INTERVAL_RANGE,
        DEFAULT_CONFIG['analysis_interval'])
    result['max_users'] = _clamp_int(
        result['max_users'], MAX_USERS_RANGE, DEFAULT_CONFIG['max_users'])
    result['frame_diff_threshold'] = _clamp_float(
        result['frame_diff_threshold'], FRAME_DIFF_RANGE,
        DEFAULT_CONFIG['frame_diff_threshold'])

    # 引擎 UCI 选项（Threads/Hash），未知选项忽略
    result['uci_options'] = _normalize_uci_options(result.get('uci_options'))

    # ONNX Runtime provider（默认 CUDA -> CPU，运行时按可用性回退）
    result['onnx_providers'] = _normalize_providers(result.get('onnx_providers'))

    # 布尔参数（兼容 "true"/1 这类来自JSON或表单的值）
    result['enable_tunnel'] = _to_bool(result['enable_tunnel'])

    return result


def _normalize_uci_options(value: Any) -> Dict[str, int]:
    """校验引擎 UCI 选项，缺失项用默认值补齐

    Args:
        value: 形如 {"Threads": 8, "Hash": 512} 的字典

    Returns:
        Dict[str, int]: 只包含 Threads/Hash 的合法取值
    """
    options = dict(DEFAULT_UCI_OPTIONS)

    if value is None:
        return options

    if not isinstance(value, dict):
        logger.warning(f"uci_options 应为对象，已回退默认值: {value}")
        return options

    for key, raw in value.items():
        if key not in UCI_OPTION_LIMITS:
            logger.warning(f"忽略未知的引擎选项: {key}")
            continue

        low, high = UCI_OPTION_LIMITS[key]
        options[key] = _clamp_int(raw, (low, high), options[key])

    return options


def _normalize_providers(value: Any) -> List[str]:
    """校验 ONNX Runtime provider 列表

    Args:
        value: 字符串或字符串列表

    Returns:
        List[str]: 去重后的 provider 名称，空值回退默认
    """
    defaults = list(DEFAULT_CONFIG['onnx_providers'])

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple)):
        logger.warning(f"onnx_providers 应为数组，已回退默认值: {value}")
        return defaults

    providers = []
    for item in value:
        name = str(item).strip()
        if name and name not in providers:
            providers.append(name)

    return providers or defaults


def _clamp_int(value: Any, value_range: tuple, default: int) -> int:
    """把值转换为整数并限制在范围内"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default

    low, high = value_range
    return max(low, min(high, number))


def _clamp_float(value: Any, value_range: tuple, default: float) -> float:
    """把值转换为浮点数并限制在范围内"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default

    low, high = value_range
    return max(low, min(high, number))


def _to_bool(value: Any) -> bool:
    """把各种形式的值转换为布尔值"""
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


def merge_cli_args(config: Dict[str, Any], args) -> Dict[str, Any]:
    """把命令行参数合并进配置，未指定的参数保持原值

    Args:
        config: 配置文件得到的配置
        args: argparse 解析结果

    Returns:
        Dict: 合并后的配置（新字典）
    """
    result = normalize_config(config)

    if getattr(args, 'engine_path', None):
        result['engine_path'] = args.engine_path

    if getattr(args, 'source_type', None):
        result['source_type'] = args.source_type

    if getattr(args, 'source_value', None):
        result['source_value'] = args.source_value

    if getattr(args, 'enable_tunnel', False):
        result['enable_tunnel'] = True

    if getattr(args, 'tunnel_type', None):
        result['tunnel_type'] = args.tunnel_type

    if getattr(args, 'tunnel_token', None):
        result['tunnel_config']['auth_token'] = args.tunnel_token

    return normalize_config(result)


def check_config(config: Dict[str, Any]) -> List[str]:
    """检查配置是否完整，返回问题列表（只提示，不阻止启动）

    Args:
        config: 配置字典

    Returns:
        List[str]: 问题描述列表
    """
    problems = []

    engine_path = config.get('engine_path')
    if not engine_path:
        problems.append("未配置Pikafish引擎路径，AI分析不可用")
    elif not Path(engine_path).exists():
        problems.append(f"Pikafish引擎不存在: {engine_path}")

    for key, name in (('pose_model_path', '姿态检测模型'),
                      ('classifier_model_path', '棋子分类模型')):
        path = config.get(key)
        if path and not Path(path).exists():
            problems.append(f"{name}不存在: {path}")

    if config.get('source_type') in ('stream', 'emulator', 'screen') \
            and not config.get('source_value'):
        problems.append("已选择实时信号源，但未填写信号源值")

    return problems


# 便捷函数
def create_default_config_file(config_file: Optional[str] = None) -> str:
    """创建默认配置文件

    Args:
        config_file: 配置文件路径，默认使用 config/config.json

    Returns:
        str: 创建的文件路径
    """
    path = Path(config_file) if config_file else config_path()
    save_config(default_config(), str(path))
    return str(path)
