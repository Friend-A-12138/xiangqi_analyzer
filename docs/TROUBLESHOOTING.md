# 故障排除指南

## 🚨 快速诊断

```bash
python test_system.py                     # 模块/目录/路由自检
python -m pytest                          # 108 个用例
python tests/test_pikafish.py <引擎路径>   # 引擎专项检查
python tests/test_debug.py                # 通用调试工具
```

日志：`logs/xiangqi_analyzer.log`。

## 📦 依赖问题

### 问题1: `ModuleNotFoundError: No module named 'pandas'`

检测器子模块 `Chinese_Chess_Recognition/core/chessboard_detector.py` 使用 pandas，
已包含在 `requirements.txt` 中：

```bash
pip install -r requirements.txt
```

### 问题2: `No module named 'onnxruntime'`

ONNX Runtime 已从基础依赖中拆出，需要单独安装：

```bash
pip install -r requirements-onnxruntime-cpu.txt    # CPU
# 或
pip install -r requirements-onnxruntime-gpu.txt    # GPU
```

### 问题3: 装 GPU 版后 `import onnxruntime` 报 DLL/模块错误

CPU 版与 GPU 版共用 `onnxruntime` 模块，不能共存：

```bash
pip uninstall -y onnxruntime onnxruntime-gpu
pip install -r requirements-onnxruntime-gpu.txt
```

并确认 CUDA 13 运行库已安装（README「GPU 加速（可选）」有已验证的版本组合）。

## ⚙️ 引擎问题

### 问题4: 找不到引擎 / 引擎启动失败

- 确认 `engine_path` 指向真实可执行文件；
- 确认 `pikafish.nnue` 与可执行文件在同一目录（官方 release 压缩包内同时提供）；
- Linux/macOS 需要 `chmod +x`；
- Windows 右键 → 属性 → 安全 → 完全控制。

官方 release 验证版本：**2026-09-06**。

### 问题5: 引擎输出 `No such option: UCI_Variant`

Pikafish 是纯象棋引擎，没有该选项。程序仍会发送以兼容其他引擎，该提示无害，可以忽略。

### 问题6: 引擎分析返回 `engine_crashed`

常见原因是局面本身不合法（例如“将帅可被吃”），Pikafish 2026 会直接拒绝并退出：

```text
info string CRITICAL ERROR: ... Reason: Unsupported position. King can be captured.
```

多见于摆拍图或识别错误（遮挡、颜色误判）。可换一张清晰的真实对局图验证。

## 🎯 检测问题

### 问题7: 日志提示“使用模拟检测器”

`Chinese_Chess_Recognition` 子模块未初始化，或导入失败：

```bash
git submodule update --init --recursive
```

验证基准提交为 `53201d6`。

### 问题8: 模型加载失败

确认以下文件存在：

- `onnx/pose/4_v6-0301.onnx`
- `onnx/layout_recognition/nano_v3-0319.onnx`

子模块内也带一份 `onnx/`，可在设置页把路径指过去。

### 问题9: 结果里有 `x`（遮挡）

被手/棋子遮挡的交叉点无法识别，FEN 中按空位处理，结果字段 `occluded_count` 会给出数量。
遮挡越多，FEN 与推荐走法越不可靠。

### 问题10: 棋盘朝向反了

设置页「我方执子」决定显示朝向：执红红方在下，执黑黑方在下。
`auto` 时按红帅位置推断。FEN 与箭头坐标会随显示朝向一起换算。

## ⚡ GPU 问题

### 问题11: `get_available_providers()` 有 CUDA，但会话只用 CPU

这正是 `preload_dlls()` 的用途。程序已在创建会话前自动调用；手工验证：

```bash
python -c "import onnxruntime as ort; ort.preload_dlls(); s=ort.InferenceSession('onnx/pose/4_v6-0301.onnx', providers=['CUDAExecutionProvider','CPUExecutionProvider']); print(s.get_providers())"
```

### 问题12: 启动日志显示回退 CPU

日志会打印原因，例如：

```text
请求 providers: ['CUDAExecutionProvider', 'CPUExecutionProvider'] -> 实际使用: ['CPUExecutionProvider']
以下 provider 不可用，已回退: ['CUDAExecutionProvider']
```

依次检查：显卡驱动、`onnxruntime-gpu` 版本与 CUDA 版本是否匹配、`onnx_providers` 配置。

### 问题13: GPU 第一次分析特别慢

首次推理需要编译 CUDA kernel、分配显存，本机实测约 **11.9 秒**，之后约 0.03 秒。
启动后先分析一张图预热即可。

## 🌐 Web 问题

### 问题14: 无法访问页面

- 确认服务已启动，端口未被占用（`python main.py --port 8080`）；
- 防火墙放行；`--host 0.0.0.0` 时用本机 IP 访问。

### 问题15: 实时分析一直“画面无变化，跳过”

说明画面确实没有变化，或阈值过高：

- 检查信号源是否在更新；
- 设置页调低「画面变化阈值」，或设为 0 关闭跳过。

### 问题16: 没有箭头

箭头依赖引擎给出的最佳走法。以下情况不会画箭头：

- 引擎分析失败（局面不合法、引擎未配置）；
- 画面中未识别到完整棋盘；
- 走法坐标越界（识别错误）。

## 🔓 内网穿透问题

- ngrok：确认已安装 `ngrok` 并配置 AuthToken；
- frp：确认已安装 `frpc` 并填写服务器地址；
- 免费版 ngrok 有并发/时长限制，失败时查看日志中的客户端输出。

## 📖 记谱问题

- 同列 4-5 个兵/卒使用「前/二/三/后」「前/二/三/四/后」；
- 超过 5 个同列同种棋子属于规则外，程序会显示坐标并附原因，不猜测；
- 吃子不加「吃」、不追加「将/绝杀」，与《象棋竞赛规则》一致。
