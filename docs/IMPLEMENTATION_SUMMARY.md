# 实现总结

## ✅ 已实现功能

### 1. 检测与推理

| 功能 | 文件 | 说明 |
|---|---|---|
| 棋盘检测/棋子分类 | `src/chess_analyzer.py` + CCR 子模块 | BGR→RGB、透视校正、10×9 分类 |
| GPU 加速与回退 | `src/onnx_runtime.py` | provider 可配、`preload_dlls()`、会话注入、失败回退 CPU |
| FEN 生成 | `src/chess_analyzer.py` | 统一成红方在下；遮挡 `x` 按空位并在结果中计数 |
| 颜色校验 | `src/chess_validator.py` | 启发式，默认关闭硬翻转（实测误判较多） |

### 2. 展示与记谱

| 功能 | 文件 | 说明 |
|---|---|---|
| 显示朝向 | `src/board_view.py` | 执红红在下 / 执黑黑在下，坐标与 FEN 自洽 |
| 中文记谱 | `src/xiangqi_notation.py` | 红方中文数字、黑方阿拉伯；同列 2/3/4/5 子规则 |
| 走法箭头 | `src/board_render.py` | 头长 0.5 格、线宽 0.08 格；单应性投影回原图 |
| 前端渲染 | `web/templates/*` | 棋盘网格 + 行列坐标 + SVG 箭头；推荐区显示中文记谱 |

### 3. 引擎与实时

| 功能 | 文件 | 说明 |
|---|---|---|
| UCI 封装 | `src/chess_analyzer.py` | 启动下发 `Threads/Hash`、崩溃自动重启 |
| 走子方 | 配置 `player_side` | 传给引擎，不再按红帅位置猜测 |
| 帧差分 | `src/frame_diff.py` | 160×120 灰度签名 + MSE 阈值，跳过无变化画面 |
| 实时推送 | `web/app.py` | SocketIO 推送结果，预览帧服务端叠加箭头 |

### 4. Web 与运维

| 功能 | 说明 |
|---|---|
| 用户管理 | PBKDF2 哈希、`config/users.json` 持久化、数量上限、在线统计 |
| 批量分析 | 一次最多 10 张，单张失败不中断 |
| 内网穿透 | ngrok/frp，Web 端配置与启停，状态展示 |
| 配置中心 | `config/config.json` 读写、校验、命令行覆盖 |

## ⚙️ 配置项一览

| 键 | 默认值 | 备注 |
|---|---|---|
| `player_side` | `red` | red/black/auto |
| `think_time` | 2000 | 500-10000 |
| `analysis_interval` | 3 | 1-60 |
| `frame_diff_threshold` | 3.0 | 0 表示不跳过 |
| `max_users` | 5 | 1-20 |
| `uci_options` | Threads=物理核数，Hash=512 | 启动时下发 |
| `onnx_providers` | CUDA→CPU | 不可用自动回退 |
| `source_type/source_value` | file/空 | 见使用指南 |
| `enable_tunnel/tunnel_*` | 关闭/ngrok | 可选 |

## 🧪 验证结果

| 项目 | 结果 |
|---|---|
| `python -m pytest` | **108 passed** |
| `python test_system.py` | **8/8** |
| GPU provider 实测 | 会话 provider 为 `['CUDAExecutionProvider','CPUExecutionProvider']` |
| GPU 加速 | CPU 0.216s → GPU 0.028s（约 7.8×），首次推理 11.9s |
| 帧差分 | 静态帧跳过、变化帧分析（循环级验证） |
| 中文记谱 | 红/黑、进退平、同列 2/3/4/5 子均有用例 |

## ⚠️ 已知限制

- 遮挡（`x`）按空位处理，会改变局面，`occluded_count` 仅作提示；
- 不合法局面（如“将帅可被吃”）会被 Pikafish 2026 拒绝，分析返回失败；
- 颜色启发式（`enable_red_flip`）默认关闭；
- GPU 首次推理约 12 秒，实时模式第一帧会慢；
- 同列超过 5 个同种棋子属于规则外，记谱返回原因而非猜测；
- 会话保存在内存，重启后需重新登录（账号本身持久化）；
- 角色权限未分级，所有登录用户权限相同。
