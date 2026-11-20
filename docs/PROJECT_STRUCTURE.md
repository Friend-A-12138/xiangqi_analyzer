# 项目结构说明

## 📂 目录结构

```text
xiangqi_analyzer/
├── main.py                       # 主程序入口：解析参数、启动 Web 与内网穿透
├── test_system.py                # 系统完整性测试（导入/目录/路由）
├── pytest.ini                    # pytest 配置（排除脚本式调试工具）
├── requirements.txt              # 运行时依赖（不含 ONNX Runtime）
├── requirements-dev.txt          # 开发依赖（pytest/black/flake8）
├── requirements-onnxruntime-cpu.txt
├── requirements-onnxruntime-gpu.txt
├── start.bat / start.sh          # 一键启动脚本
│
├── src/                          # 项目源码
│   ├── config.py                 # 配置默认值、加载、校验、保存、命令行合并
│   ├── chess_analyzer.py         # 检测器与 Pikafish 引擎封装、分析流程
│   ├── chess_validator.py        # 棋盘颜色校验（启发式，默认关闭硬翻转）
│   ├── board_view.py             # 显示朝向与 UCI 坐标映射
│   ├── board_render.py           # 箭头坐标计算与绘制（含单应性投影）
│   ├── xiangqi_notation.py       # 中文记谱
│   ├── frame_diff.py             # 帧差分签名与阈值判断
│   ├── onnx_runtime.py           # ONNX provider 选择、DLL 预加载、会话注入
│   ├── stream_processor.py       # RTMP/屏幕/模拟器截图
│   └── tunnel_service.py         # ngrok/frp 内网穿透
│
├── web/
│   ├── app.py                    # Flask 应用、REST API、SocketIO、用户管理
│   └── templates/                # base/login/index/settings
│
├── onnx/                         # 检测模型
│   ├── pose/4_v6-0301.onnx
│   └── layout_recognition/nano_v3-0319.onnx
│
├── Chinese_Chess_Recognition/    # 检测器代码（Git 子模块，勿直接修改）
├── Pikafish/                     # 引擎源码（Git 子模块；可放官方 release 二进制）
├── config/                       # config.json / config.example.json / users.json
├── tests/                        # pytest 用例 + 调试脚本
└── logs/                         # 运行日志
```

## 🧩 模块职责

| 模块 | 职责 |
|---|---|
| `src/config.py` | 默认配置、`normalize_config` 校验、读写 `config/config.json`、CLI 合并 |
| `src/chess_analyzer.py` | `PikafishEngine`（UCI 交互、Threads/Hash 下发、崩溃重启）、`ChessboardDetector`（子模块包装、provider 注入、朝向统一）、`XiangqiAnalyzer`（分析主流程） |
| `src/board_view.py` | FEN 顺序 ↔ 显示顺序（执黑旋转 180°），输出 `view/squares_view/orientation` |
| `src/board_render.py` | 棋盘行列 → 像素坐标、单应性投影回原图、按格子比例绘制箭头 |
| `src/xiangqi_notation.py` | 坐标走法 → 中文记谱（红中/黑阿、进退平、同列多子） |
| `src/frame_diff.py` | 160×120 灰度签名 + 均方差，判断画面是否变化 |
| `src/onnx_runtime.py` | 选择可用 provider、`preload_dlls()`、包装 `InferenceSession` 注入 providers |
| `web/app.py` | 路由、上传/批量、实时循环、用户管理、隧道控制、结果序列化 |

## 🔄 数据流

```text
图片/视频帧
  → ChessboardDetector.detect（透视变换 + 棋子分类，ONNX provider 由 onnx_runtime 决定）
  → 统一成 FEN 顺序 → _board_to_fen
  → XiangqiAnalyzer（中文记谱、箭头坐标）
  → PikafishEngine（UCI 搜索，Threads/Hash 已在启动时设置）
  → analyze_image 结果：
      fen / board / view / squares_view / orientation /
      best_move / best_move_cn / arrow / detect_time / confidence
  → web/app.py serialize_result → JSON / WebSocket
```

实时分析链路额外有两处优化：

1. 帧差分：`frame_diff_threshold` 以下跳过检测与引擎；
2. 服务端在预览帧上叠加箭头，前端棋盘用 SVG 叠加（坐标取自 `squares_view`）。

## 🧱 第三方代码规则

- `Chinese_Chess_Recognition/`、`Pikafish/` 均为 Git 子模块，**不要直接修改**；
- 项目通过 `src/onnx_runtime.py`、`sys.path` 注入等方式在主仓侧适配子模块；
- 引擎二进制与 `pikafish.nnue` 不入库；
- 子模块更新后先跑 `python -m pytest` 与 `python test_system.py`。

## 🧪 测试结构

```text
tests/
├── conftest.py              # 路径初始化、临时配置 fixture
├── test_config.py           # 配置默认值/校验/保存/CLI 合并/UCI/ONNX provider
├── test_users.py            # 用户哈希、持久化、上限、删除
├── test_analyzer_utils.py   # 序列化、FEN 朝向、遮挡处理、走子方
├── test_board_view.py       # 显示朝向与坐标自洽
├── test_board_render.py     # 箭头几何、尺寸比例、绘制
├── test_xiangqi_notation.py # 中文记谱（含同列 3/4/5 子）
├── test_engine.py           # UCI 交互与 setoption（假进程）
├── test_onnx_runtime.py     # provider 选择/回退/注入/预加载
├── test_frame_diff.py       # 帧签名与阈值
├── test_web_api.py          # 登录、上传、批量、配置、用户、页面钩子
├── test_pikafish.py         # 脚本式引擎检查工具
└── test_debug.py            # 脚本式调试工具
```
