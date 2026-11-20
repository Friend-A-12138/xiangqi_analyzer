# 中国象棋AI分析器

基于深度学习和象棋引擎的中国象棋实时分析系统，支持棋盘检测、棋子识别、AI推荐走法与中文记谱。

## ✨ 功能特性

- 🎯 **智能棋盘检测**: 自动识别中国象棋棋盘和棋子位置
- 🤖 **AI走法推荐**: 集成 Pikafish 引擎，提供专业的走法建议
- 📖 **中文记谱**: 坐标走法自动翻译为「马二进三」「炮二平五」等标准记谱
- ➡️ **走法箭头**: 在棋盘与实时预览上叠加起点到终点的箭头
- 📹 **多源输入**: 支持图片、RTMP 流、模拟器截图、屏幕截图
- 🖼️ **批量分析**: 一次上传多张棋谱图片，逐张输出 FEN 与推荐走法
- 🌐 **Web 界面**: 实时显示分析结果，棋盘朝向跟随「我方执子」
- ⚡ **GPU 加速（可选）**: 检测模型可切换到 CUDA，实测约 7.8 倍加速
- 🔓 **内网穿透**: 支持 ngrok/frp，可在设置页直接配置与启停
- 👥 **用户管理**: 多用户访问，可配置数量上限并在页面上增删用户
- ♟️ **我方执子**: 指定红方/黑方走子，避免引擎按错误一方分析

## 💻 环境要求

- **Python 3.11**：本项目在 **Python 3.11.9 / Windows** 上完成验证（其他 3.11.x 版本通常可用）
- **Pikafish 引擎**：使用官方 release 二进制（见下文），或自行编译
- **检测模型**：仓库已内置 `onnx/pose/4_v6-0301.onnx` 与 `onnx/layout_recognition/nano_v3-0319.onnx`
- **检测器子模块**：`Chinese_Chess_Recognition`，验证版本为提交 `53201d6`
- **GPU（可选）**：NVIDIA 显卡 + CUDA 运行库，见「GPU 加速（可选）」

## 🚀 快速开始

### 1. 获取代码与子模块

```bash
git clone <本仓库地址>
cd xiangqi_analyzer
git submodule update --init --recursive
```

检测器代码位于 `Chinese_Chess_Recognition` 子模块，必须先初始化，否则只能使用模拟检测器。

> 验证基准：`Chinese_Chess_Recognition` 提交 `53201d6`。仓库中的子模块指针由维护者更新，若你拉取到别的提交，请以该版本为参照。

### 2. 安装 Python 依赖

```bash
# 1) 运行时依赖（不包含 ONNX Runtime）
pip install -r requirements.txt

# 2) ONNX Runtime：按硬件二选一
pip install -r requirements-onnxruntime-cpu.txt   # 默认：CPU 推理
# pip install -r requirements-onnxruntime-gpu.txt # 可选：NVIDIA GPU
```

> 基础依赖故意不含 ONNX Runtime：CPU 版与 GPU 版共用 `onnxruntime` 模块，混装会互相覆盖。重装 `requirements.txt` 不会动已安装的 GPU 版。

开发/测试还需要：

```bash
pip install -r requirements-dev.txt   # 包含运行时依赖 + pytest/black/flake8
```

### 3. 准备 Pikafish 引擎

从 [Pikafish 官方 Releases](https://github.com/official-pikafish/Pikafish/releases) 下载最新发布包。本项目验证的是 **Pikafish 2026-09-06**，包内包含：

- `Pikafish-Windows-x86-64-universal.exe`（Windows 可执行文件）
- `pikafish.nnue`（神经网络权重，必需）

Windows 下可用系统自带的 `tar` 解压（已验证）：

```bash
tar -xf Pikafish.2026-09-06.7z -C Pikafish/src
```

Linux/macOS 请使用 `7z`/`p7zip` 解压。随后把可执行文件与 `pikafish.nnue` 放在同一目录，常见做法：

```text
Pikafish/src/pikafish.exe      # 与 pikafish.nnue 同目录
Pikafish/src/pikafish.nnue
```

- 也可以在设置页/配置文件中指定任意路径（`engine_path`）。
- **引擎二进制与 nnue 不入库**，请勿提交到仓库。
- Linux/macOS 需要执行权限：`chmod +x /path/to/pikafish`。

### 4. 启动服务

```bash
python main.py
# 或指定引擎/信号源
python main.py --engine-path Pikafish/src/pikafish.exe --source-type screen
```

也可以使用 `start.bat`（Windows）或 `start.sh`（Linux/macOS）。启动后访问 <http://localhost:5000>，默认账号：

- `admin` / `admin123`
- `guest` / `guest123`

## ⚡ GPU 加速（可选）

检测模型基于 ONNX Runtime。默认安装 CPU 版；NVIDIA 显卡可切换 GPU 版，实测单图检测约 **7.8 倍**加速。

### 前提

- NVIDIA 显卡（本机验证：RTX 5060 Ti 8GB）
- 显卡驱动正常（本机验证：617.42）
- CUDA 13 的 pip 运行库（本机验证版本见下）

### 安装（CUDA 13，已验证）

```bash
# 1) 先卸载 CPU 版，避免两个包共用 onnxruntime 模块
pip uninstall -y onnxruntime onnxruntime-gpu

# 2) 安装 GPU 版
pip install -r requirements-onnxruntime-gpu.txt

# 3) 安装 CUDA 13 运行库（本机已验证的组合，单行命令）
pip install nvidia-cuda-runtime==13.5.37 nvidia-cublas==13.10.0.20 nvidia-cudnn-cu13==9.28.1.4 nvidia-cufft==12.5.0.14 nvidia-curand==10.4.5.25 nvidia-cuda-nvrtc==13.5.37 nvidia-nvjitlink==13.5.37
```

> `onnxruntime-gpu` 自身只依赖 `numpy/flatbuffers/protobuf/packaging`，**不会自动安装 CUDA 运行库**；上面的 nvidia 包是单独安装的。
> CUDA 12 环境：本机未验证。请按 [ONNX Runtime 官方兼容表](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) 选择匹配 CUDA 12 的 `onnxruntime-gpu` 版本，再执行上面前两步。

### 验证

```bash
python -c "import onnxruntime as ort; print(ort.__version__, ort.get_available_providers())"
```

输出中应包含 `CUDAExecutionProvider`。启动服务后日志会打印真实生效的 provider，例如：

```text
onnxruntime 1.32.0 可用 providers: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
请求 providers: ['CUDAExecutionProvider', 'CPUExecutionProvider'] -> 实际使用: ['CUDAExecutionProvider', 'CPUExecutionProvider']
pose 模型实际 provider: ['CUDAExecutionProvider', 'CPUExecutionProvider']
classifier 模型实际 provider: ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

### 配置

```json
"onnx_providers": ["CUDAExecutionProvider", "CPUExecutionProvider"]
```

- 默认值即上面的顺序：优先 CUDA，不可用时自动回退 CPU。
- 只想要 CPU：改为 `["CPUExecutionProvider"]`。
- CUDA 不可用或会话创建失败时，程序会记录警告并自动用 CPU 重建，不会中断分析。
- Windows 上 pip 安装的 CUDA DLL 不在 PATH，程序在创建会话前会自动调用 `onnxruntime.preload_dlls()`；这也是不调用时 `get_providers()` 只剩 CPU 的原因。

### 实测收益

测试条件：示例图 `examples/demo002.png`（476×448），预热 3 次后取 5 次中位数。

| provider | 内部 detect_time | 端到端耗时（检测部分） |
|---|---|---|
| CPU | 0.25 s | **0.216 s** |
| GPU (CUDA) | 0.03 s | **0.028 s** |
| GPU 首次推理 | — | **11.9 s**（首次包含 CUDA kernel 编译与显存分配） |

### 首次预热说明

GPU 第一次推理会明显变慢（本机约 12 秒），之后稳定在 0.03 秒左右。建议：

- 启动服务后先上传/分析一张图，再开始实时分析；
- 实时模式下第一帧分析会慢，属于正常现象。

### 共存冲突的坑

- `onnxruntime`（CPU）与 `onnxruntime-gpu` 安装的是**同一个 Python 包路径**，同时存在会导致 `import onnxruntime` 行为不确定或 DLL 冲突。
- 切换方向前务必先 `pip uninstall -y onnxruntime onnxruntime-gpu`，再安装目标版本。
- 不要用 `pip install -r requirements.txt --upgrade` 之后又单独装 GPU 版：基础依赖里没有 ONNX Runtime，重复安装基础依赖是安全的；但手动 `pip install onnxruntime` 会覆盖 GPU 版。

## 📋 使用流程

### 场景1: 分析单张图片

1. 启动服务并登录
2. 在「上传图片分析」中选择图片，点击「分析图片」（无需先点「开始分析」）
3. 查看 FEN、棋盘布局、**中文记谱**、推荐走法与**箭头**

### 场景2: 批量分析棋谱图片

1. 首页「棋谱批量分析」选择多张图片（一次最多 10 张）
2. 点击「批量分析」，表格逐张显示 FEN、坐标走法、**中文记谱**、评估与耗时

### 场景3: 实时分析模拟器

1. 启动模拟器与对局
2. 设置页配置：信号源「模拟器」、模拟器名称或窗口标题（可点「刷新窗口」选择）、我方执子、引擎路径
3. 保存后返回首页，点击「开始分析」
4. 实时预览上会叠加走法箭头；画面无变化时会自动跳过检测（日志：`画面无变化，跳过`）

### 场景4: 通过内网穿透远程访问

1. 设置页填写 ngrok AuthToken（或 frp 服务器信息）
2. 保存配置 → 启动穿透 → 页面显示公网 URL

## ⚙️ 配置说明

### 配置文件 (config/config.json)

```json
{
  "engine_path": "Pikafish/src/pikafish.exe",
  "pose_model_path": "onnx/pose/4_v6-0301.onnx",
  "classifier_model_path": "onnx/layout_recognition/nano_v3-0319.onnx",
  "source_type": "file",
  "source_value": "",
  "player_side": "red",
  "think_time": 2000,
  "analysis_interval": 3,
  "frame_diff_threshold": 3.0,
  "max_users": 5,
  "uci_options": {
    "Threads": 14,
    "Hash": 512
  },
  "onnx_providers": ["CUDAExecutionProvider", "CPUExecutionProvider"],
  "enable_tunnel": false,
  "tunnel_type": "ngrok",
  "tunnel_config": {
    "auth_token": "",
    "region": "ap"
  }
}
```

| 配置项 | 默认 | 说明 |
|---|---|---|
| `engine_path` | 空 | Pikafish 可执行文件路径 |
| `source_type` / `source_value` | `file` / 空 | `file`、`stream`（流地址）、`emulator`（名称或窗口标题）、`screen`（`x,y,w,h`） |
| `player_side` | `red` | 我方执子：`red` 红方走子 / `black` 黑方走子 / `auto` 按红帅位置推断；棋盘朝向随其变化 |
| `think_time` | 2000 | 引擎思考时间（毫秒） |
| `analysis_interval` | 3 | 实时分析间隔（秒） |
| `frame_diff_threshold` | 3.0 | 画面变化阈值（灰度均方差）；低于该值跳过检测与引擎；`0` 表示不跳过 |
| `max_users` | 5 | 账号数量与在线人数上限（1-20） |
| `uci_options` | 物理核数 / 512 | 引擎启动时下发：`Threads` 默认取 CPU 物理核数，`Hash` 单位 MB |
| `onnx_providers` | CUDA→CPU | ONNX Runtime provider，不可用时自动回退 CPU |
| `enable_tunnel` / `tunnel_type` / `tunnel_config` | 关闭 / ngrok | 内网穿透配置 |

完整示例见 [config/config.example.json](config/config.example.json)。配置文件由 Web 设置页读写，修改后重启或保存设置即生效。

### 命令行参数

```bash
python main.py [选项]

  -c, --config CONFIG       配置文件路径
  -e, --engine-path PATH    Pikafish 引擎路径
  -s, --source-type TYPE    file/stream/emulator/screen
  -v, --source-value VALUE  信号源值
  --enable-tunnel           启用内网穿透
  --tunnel-type TYPE        ngrok/frp
  --tunnel-token TOKEN      内网穿透令牌
  -p, --port PORT           Web 端口（默认 5000）
  --host HOST               Web 主机（默认 0.0.0.0）
  --no-browser              不自动打开浏览器
  --debug                   调试模式
```

## 🔧 常见问题

### 问题1: 引擎无法启动或没有执行权限

```bash
# Linux/macOS
chmod +x /path/to/pikafish
# Windows：右键属性 → 安全 → 完全控制
```

确认 `pikafish.nnue` 与可执行文件在同一目录。

### 问题2: 棋盘检测不准确

1. 确认已执行 `git submodule update --init --recursive`
2. 检查模型文件路径
3. 调整拍摄角度、距离与光照

### 问题3: Web 界面无法访问

检查服务是否启动、端口是否被占用、防火墙是否放行。

### 问题4: GPU 明明是好的，`get_providers()` 却只有 CPU

- 先按「GPU 加速」章节确认 `get_available_providers()` 包含 CUDA；
- 确认 `onnx_providers` 配置包含 `CUDAExecutionProvider`；
- Windows 下需要 `preload_dlls()`（程序已自动调用）；手动测试时可这样验证：
  ```bash
  python -c "import onnxruntime as ort; ort.preload_dlls(); s=ort.InferenceSession('onnx/pose/4_v6-0301.onnx', providers=['CUDAExecutionProvider','CPUExecutionProvider']); print(s.get_providers())"
  ```

### 问题5: 装完 GPU 版之后推理报 DLL/模块错误

多为 CPU 版与 GPU 版混装，按下面顺序重装：

```bash
pip uninstall -y onnxruntime onnxruntime-gpu
pip install -r requirements-onnxruntime-gpu.txt
```

## 📦 项目结构

```text
xiangqi_analyzer/
├── main.py                     # 主程序入口（CLI + Web 启动）
├── requirements.txt            # 运行时依赖（不含 ONNX Runtime）
├── requirements-dev.txt        # 开发依赖
├── requirements-onnxruntime-cpu.txt / -gpu.txt
├── pytest.ini
├── test_system.py              # 系统完整性测试
├── start.bat / start.sh
├── docs/                       # 文档（以本目录为准）
├── src/
│   ├── config.py               # 配置加载/校验/保存
│   ├── chess_analyzer.py       # 检测器与引擎封装
│   ├── chess_validator.py      # 棋盘颜色校验
│   ├── board_view.py           # 显示朝向与坐标映射
│   ├── board_render.py         # 箭头坐标与绘制
│   ├── xiangqi_notation.py     # 中文记谱
│   ├── frame_diff.py           # 帧差分（跳过无变化画面）
│   ├── onnx_runtime.py         # ONNX provider 选择与注入
│   ├── stream_processor.py     # 流/屏幕/模拟器截图
│   └── tunnel_service.py       # 内网穿透
├── web/
│   ├── app.py                  # Flask 应用与接口
│   └── templates/              # 页面模板
├── onnx/                       # 检测模型
├── Chinese_Chess_Recognition/  # 检测器代码（Git 子模块）
├── Pikafish/                   # 引擎源码（Git 子模块，可放 release 二进制）
├── config/                     # 配置（含示例）
├── tests/                      # pytest 用例与调试脚本
└── logs/                       # 运行日志
```

## 🎯 应用场景

1. **在线对局辅助**：模拟器/屏幕截图模式，实时查看推荐走法
2. **棋谱批量分析**：一次上传多张棋谱图片，整理 FEN 与推荐
3. **教学演示**：RTMP 流 + Web 界面，实时讲解
4. **远程分析**：内网穿透，随时随地访问

## 🧪 测试与调试

```bash
# 系统完整性测试（模块导入/目录/路由）
python test_system.py

# pytest 用例（配置/用户/序列化/记谱/箭头/队形/接口等，108 个）
python -m pytest

# Pikafish 引擎测试
python tests/test_pikafish.py /path/to/pikafish

# 通用调试工具
python tests/test_debug.py
python tests/test_debug.py --interactive
```

日志：`logs/xiangqi_analyzer.log`。

## 📊 性能指标

### 延迟（本机实测）

| 项目 | 实测 |
|---|---|
| 单图检测（CPU） | 0.216 s |
| 单图检测（GPU / RTX 5060 Ti） | 0.028 s |
| GPU 首次推理 | 11.9 s（含 CUDA kernel 编译） |
| 引擎分析 | 由 `think_time` 控制（默认 2 s） |
| 完整单图分析 | 检测耗时 + 引擎思考时间 |
| Web 页面加载 | 未单独复测（本地 Flask 开发服务器） |

### 准确率

- 棋盘检测 >95%、棋子识别 >98%、走法推荐专业级：**历史宣称，未在本环境复测**。

## ✅ 已验证环境

| 项目 | 版本/说明 |
|---|---|
| 操作系统 | Windows（本机验证） |
| Python | 3.11.9 |
| ONNX Runtime（CPU） | 1.31.1 |
| ONNX Runtime（GPU） | 1.32.0 + CUDA 13 pip 运行库（nvidia-cuda-runtime 13.5.37 等） |
| 显卡 / 驱动 | RTX 5060 Ti 8GB / 617.42 |
| OpenCV / NumPy | 5.0.0 / 2.4.6（CPU 环境）；5.1.0 / 2.4.6（GPU 环境） |
| Pikafish | 2026-09-06 官方 release（含 pikafish.nnue） |
| Chinese_Chess_Recognition | 提交 53201d6 |

## 🤝 贡献指南

1. Fork 项目并创建特性分支
2. 提交前运行 `python -m pytest` 与 `python test_system.py`
3. 第三方代码（`Chinese_Chess_Recognition/`、`Pikafish/`）不要直接修改，请到上游仓库提交 PR

## 📄 许可证

本项目采用 MIT 许可证；第三方代码的许可证请参考各自仓库。
