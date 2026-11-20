# 快速启动指南

本文基于 **Python 3.11.9 / Windows** 实测环境编写，命令均可直接执行。

## 1. 准备代码与子模块

```bash
git clone <本仓库地址>
cd xiangqi_analyzer
git submodule update --init --recursive
```

检测器代码在 `Chinese_Chess_Recognition` 子模块中，未初始化时只能使用模拟检测器。
验证基准提交：`53201d6`。

## 2. 安装依赖

```bash
# 运行时依赖（不含 ONNX Runtime）
pip install -r requirements.txt

# ONNX Runtime：按硬件二选一
pip install -r requirements-onnxruntime-cpu.txt   # 默认 CPU
# pip install -r requirements-onnxruntime-gpu.txt # 可选 GPU（见 README「GPU 加速」）

# 开发/测试（可选）
pip install -r requirements-dev.txt
```

## 3. 准备引擎与模型

**Pikafish 引擎**：下载 [官方 release](https://github.com/official-pikafish/Pikafish/releases)（验证版本 **2026-09-06**），解压后把可执行文件与 `pikafish.nnue` 放到同一目录，例如：

```text
Pikafish/src/pikafish.exe
Pikafish/src/pikafish.nnue
```

Windows 可用系统自带 `tar` 解压（已验证）：

```bash
tar -xf Pikafish.2026-09-06.7z -C Pikafish/src
```

引擎与 nnue **不入库**。Linux/macOS 记得 `chmod +x`。

**检测模型**：仓库已内置 `onnx/pose/4_v6-0301.onnx` 与 `onnx/layout_recognition/nano_v3-0319.onnx`。

## 4. 启动

```bash
python main.py
# 指定引擎与信号源
python main.py --engine-path Pikafish/src/pikafish.exe --source-type screen
```

Windows 也可以双击 `start.bat`，Linux/macOS 用 `./start.sh`。

访问 <http://localhost:5000>，默认账号 `admin / admin123`、`guest / guest123`。

## 5. 三种常用场景

### 分析单张图片

1. 登录后进入首页
2. 「上传图片分析」选择图片并点击「分析图片」（无需先点「开始分析」）
3. 查看 FEN、棋盘布局、中文记谱与箭头

### 批量分析棋谱

1. 「棋谱批量分析」选择多张图片（一次最多 10 张）
2. 点击「批量分析」，表格逐行显示 FEN、坐标走法、中文记谱、评估与耗时

### 实时分析（模拟器/屏幕）

1. 启动模拟器或打开对局画面
2. 设置页配置信号源与「我方执子」
3. 保存后返回首页点击「开始分析」
4. 实时预览上会叠加走法箭头；画面无变化时日志显示 `画面无变化，跳过`

## 6. 验证安装

```bash
# 系统完整性
python test_system.py

# 单元测试（108 个）
python -m pytest

# 引擎自检
python tests/test_pikafish.py Pikafish/src/pikafish.exe
```

GPU 环境额外验证：

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```

输出应包含 `CUDAExecutionProvider`（详见 README「GPU 加速（可选）」）。

## 7. 常见问题速查

| 现象 | 处理 |
|---|---|
| 提示使用模拟检测器 | 未初始化 `Chinese_Chess_Recognition` 子模块 |
| 引擎启动失败 | 检查路径、执行权限，确认 `pikafish.nnue` 与可执行文件同目录 |
| GPU 未生效 | 见 README「GPU 加速」；确认 `onnx_providers` 与 `get_available_providers()` |
| 检测结果有 `x` | 棋子被遮挡，FEN 中按空位处理，结果会给出 `occluded_count` |
| 端口被占用 | `python main.py --port 8080` |

更多问题见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。
