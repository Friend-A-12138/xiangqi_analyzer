"""配置模块单元测试"""
import argparse
import json
import os

from src.config import (check_config, default_config, load_config, merge_cli_args,
                        normalize_config, physical_cpu_count, save_config)


def test_default_config_is_copied():
    """默认配置每次返回新对象，避免被调用方修改"""
    first = default_config()
    second = default_config()
    first['tunnel_config']['region'] = 'us'
    assert second['tunnel_config']['region'] == 'ap'


def test_normalize_clamps_ranges():
    """数值参数被限制在合法范围"""
    config = normalize_config({'think_time': 99999, 'analysis_interval': 0,
                               'max_users': 99})
    assert config['think_time'] == 10000
    assert config['analysis_interval'] == 1
    assert config['max_users'] == 20


def test_normalize_falls_back_on_invalid_enum():
    """非法枚举回退到默认值"""
    config = normalize_config({'source_type': 'camera', 'tunnel_type': 'ngrok2',
                               'player_side': 'blue'})
    assert config['source_type'] == 'file'
    assert config['tunnel_type'] == 'ngrok'
    assert config['player_side'] == 'red'


def test_normalize_deep_merges_tunnel_config():
    """只提交部分隧道字段时不丢失其他默认值"""
    config = normalize_config({'tunnel_config': {'auth_token': 'token'}})
    assert config['tunnel_config'] == {'auth_token': 'token', 'region': 'ap'}


def test_save_and_load_roundtrip(config_file):
    """配置保存后可以原样读回"""
    config = normalize_config({'think_time': 3000, 'source_type': 'screen',
                               'source_value': '10,20,300,200'})
    assert save_config(config, config_file)

    loaded = load_config(config_file)
    assert loaded['think_time'] == 3000
    assert loaded['source_type'] == 'screen'
    assert loaded['source_value'] == '10,20,300,200'


def test_load_missing_file_returns_defaults(tmp_path):
    """配置文件不存在时返回默认配置"""
    missing = tmp_path / 'not_exists.json'
    assert load_config(str(missing))['think_time'] == 2000


def test_merge_cli_args_overrides_only_given_values():
    """命令行参数只覆盖显式指定的项"""
    args = argparse.Namespace(engine_path='C:/pikafish.exe', source_type='emulator',
                              source_value='MuMu', enable_tunnel=True,
                              tunnel_type='frp', tunnel_token='tk')
    config = merge_cli_args({'think_time': 5000}, args)
    assert config['engine_path'] == 'C:/pikafish.exe'
    assert config['source_type'] == 'emulator'
    assert config['think_time'] == 5000
    assert config['tunnel_config']['auth_token'] == 'tk'


def test_check_config_reports_missing_engine():
    """缺少引擎时给出提示但不抛异常"""
    problems = check_config({'engine_path': ''})
    assert any('引擎' in problem for problem in problems)


def test_save_config_writes_utf8_json(config_file):
    """保存的 JSON 不转义中文且带缩进"""
    save_config({'source_value': '模拟器'}, config_file)
    text = json.load(open(config_file, encoding='utf-8'))['source_value']
    assert text == '模拟器'


def test_physical_cpu_count_is_sane():
    """物理核数在 1 到逻辑核数之间"""
    count = physical_cpu_count()
    assert 1 <= count <= max(1, os.cpu_count() or 1)


def test_default_uci_options():
    """默认线程数取物理核数，哈希 512MB"""
    options = default_config()['uci_options']
    assert options['Threads'] == physical_cpu_count()
    assert options['Hash'] == 512


def test_normalize_uci_options_overrides_and_clamps():
    """显式配置的 UCI 选项生效并夹取到合法范围"""
    options = normalize_config({'uci_options': {'Threads': 9999, 'Hash': '256'}})['uci_options']
    assert options['Threads'] == 1024
    assert options['Hash'] == 256

    low = normalize_config({'uci_options': {'Threads': 0}})['uci_options']
    assert low['Threads'] == 1


def test_normalize_uci_options_ignores_unknown_and_bad_shapes():
    """未知选项被忽略，非对象回退默认值"""
    options = normalize_config({'uci_options': {'Threads': 8, 'MultiPV': 3}})['uci_options']
    assert options['Threads'] == 8
    assert 'MultiPV' not in options

    fallback = normalize_config({'uci_options': 'fast'})['uci_options']
    assert fallback['Threads'] == physical_cpu_count()
    assert fallback['Hash'] == 512
