# 中国象棋AI分析器 - 使用指南

## 📚 目录

1. [安装与启动](#安装与启动)
2. [配置说明](#配置说明)
3. [输入源配置](#输入源配置)
4. [Web 界面使用](#web-界面使用)
5. [中文记谱与箭头](#中文记谱与箭头)
6. [GPU 加速](#gpu-加速)
7. [内网穿透](#内网穿透)
8. [测试与日志](#测试与日志)

## 🚀 安装与启动

```bash
git submodule update --init --recursive
pip install -r requirements.txt
pip install -r requirements-onnxruntime-cpu.txt   # 或 -gpu.txt
python main.py
```

访问 <http://localhost:5000>，默认账号 `admin / admin123`、`guest / guest123`。
Pikafish 引擎与模型的准备见 [QUICK_START.md](QUICK_START.md)。

## ⚙️ 配置说明

配置文件为 `config/config.json`，也可以直接在 Web 设置页修改，保存后写回同一文件。

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `engine_path` | 空 | Pikafish 可执行文件路径 |
| `pose_model_path` | `onnx/pose/4_v6-0301.onnx` | 姿态检测模型 |
| `classifier_model_path` | `onnx/layout_recognition/nano_v3-0319.onnx` | 棋子分类模型 |
| `source_type` | `file` | `file` / `stream` / `emulator` / `screen` |
| `source_value` | 空 | 见「输入源配置」 |
| `player_side` | `red` | 我方执子：`red` / `black` / `auto`，同时决定棋盘显示朝向 |
| `think_time` | 2000 | 引擎思考时间（毫秒） |
| `analysis_interval` | 3 | 实时分析间隔（秒） |
| `frame_diff_threshold` | 3.0 | 画面变化阈值（灰度均方差），低于则跳过；0 不跳过 |
| `max_users` | 5 | 账号数量与在线人数上限（1-20） |
| `uci_options` | `Threads=物理核数, Hash=512` | 引擎启动时下发；`Hash` 单位 MB |
| `onnx_providers` | `["CUDAExecutionProvider","CPUExecutionProvider"]` | 检测模型 provider，不可用时自动回退 CPU |
| `enable_tunnel` | false | 是否启用内网穿透 |
| `tunnel_type` | ngrok | `ngrok` / `frp` |
| `tunnel_config` | `{}` | ngrok：`auth_token`、`region`；frp：`server_addr`、`server_port`、`token`、`subdomain` |

### 命令行参数

```bash
python main.py --engine-path Pikafish/src/pikafish.exe \
               --source-type emulator --source-value "MuMu" \
               --no-browser --port 5000
```

命令行参数的优先级高于配置文件。

## 🎥 输入源配置

| 类型 | `source_value` 示例 | 说明 |
|---|---|---|
| 图片文件 `file` | 空 | 在 Web 页面上传图片 |
| 视频流 `stream` | `rtmp://localhost/live/chess` | OpenCV 打开 RTMP/RTSP 流 |
| 模拟器 `emulator` | `MuMu` 或完整窗口标题 | 设置页可点「刷新窗口」选择 |
| 屏幕 `screen` | `100,100,800,600` | `x,y,width,height`，留空为全屏；支持中文逗号 |

## 🌐 Web 界面使用

- **首页**：开始/停止分析、实时预览、棋盘分析、推荐走法、单图上传、批量分析
- **设置页**：引擎与模型路径、信号源、我方执子、思考时间、分析间隔、画面变化阈值、
  引擎线程数/哈希表、内网穿透、用户管理
- **棋盘分析**：显示 FEN、行列坐标、朝向徽标、棋盘布局与走法箭头；朝向随「我方执子」变化
- **用户管理**：在线人数、添加/删除用户（密码 PBKDF2 哈希存储，保存在 `config/users.json`）

## 📖 中文记谱与箭头

推荐走法会同时显示坐标与中文记谱，例如：

| 坐标 | 中文记谱 | 说明 |
|---|---|---|
| `b0c2` | 马二进三 | 红方马从 b0 到 c2 |
| `b2e2` | 炮二平五 | 红方炮平中 |
| `h9g7` | 马8进7 | 黑方使用阿拉伯数字 |

规则（按《象棋竞赛规则》）：

- 红方用中文数字，黑方用阿拉伯数字；列号沿 `a`–`i` 编号 1–9
- 车/炮/兵/卒/帅/将的进/退跟移动行数，马/相/仕跟目标列
- 同列多个同种棋子：2 个用「前/后」，3 个用「前/中/后」，
  4 个用「前/二/三/后」，5 个用「前/二/三/四/后」
- 「前」= 更靠近对方底线的一枚（红黑各自视角）
- 吃子不额外加「吃」，也不追加「将/绝杀」

箭头：红方红色、黑方蓝色，头部长度 = 0.5 格、线宽 = 0.08 格，与走法长短、图片大小无关。
无法记谱时（例如同列超过 5 个，规则之外）会显示坐标并给出原因。

## ⚡ GPU 加速

默认 CPU；NVIDIA 显卡可按 README 的「GPU 加速（可选）」切换 `onnxruntime-gpu`，
实测单图检测从 0.216s 降到 0.028s。首次推理约 12 秒属于正常预热。

## 🔓 内网穿透

1. 设置页选择 ngrok 或 frp 并填写令牌/服务器信息
2. 点击「保存配置」→「启动穿透」
3. 页面显示公网 URL 后即可远程访问，点击「停止」关闭

需要本机安装 `ngrok` 或 `frpc` 客户端。

## 🧪 测试与日志

```bash
python test_system.py          # 系统完整性
python -m pytest               # 108 个单元/接口用例
python tests/test_pikafish.py <引擎路径>
python tests/test_debug.py --interactive
```

日志位于 `logs/xiangqi_analyzer.log`，实时分析跳过的记录形如
`画面无变化，跳过（差异 0.00 < 阈值 3）`。
