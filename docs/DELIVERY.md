# 交付文档

## 📦 交付清单

### 代码

- `main.py`：主程序入口（CLI + Web + 内网穿透）
- `src/`：配置、分析器、检测器包装、显示朝向、箭头、中文记谱、帧差分、ONNX provider、流处理、隧道
- `web/`：Flask 应用与 4 个页面模板
- `tests/`：pytest 用例与调试脚本

### 依赖声明

| 文件 | 用途 |
|---|---|
| `requirements.txt` | 运行时依赖（不含 ONNX Runtime） |
| `requirements-onnxruntime-cpu.txt` | CPU 版 ONNX Runtime（默认） |
| `requirements-onnxruntime-gpu.txt` | GPU 版 ONNX Runtime（可选） |
| `requirements-dev.txt` | 开发依赖（pytest/black/flake8） |

### 配置与脚本

- `config/config.json`：默认运行配置
- `config/config.example.json`：完整示例（含全部配置键）
- `start.bat` / `start.sh`：一键启动
- `test_system.py`：系统完整性测试

### 文档

- `README.md`：项目说明、安装、GPU 加速、配置、常见问题
- `docs/QUICK_START.md`：快速启动
- `docs/USER_GUIDE.md`：使用指南
- `docs/TROUBLESHOOTING.md`：故障排除
- `docs/PROJECT_STRUCTURE.md`：项目结构
- `docs/PROJECT_OVERVIEW.md`：架构总览
- `docs/IMPLEMENTATION_SUMMARY.md`：实现总结
- `docs/DELIVERY.md`：本文件
- `docs/GIT_SUBMODULE_GUIDE.md`：子模块通用指南

## 🚀 部署步骤

```bash
# 1. 代码与子模块
git submodule update --init --recursive

# 2. 依赖（CPU 默认；GPU 见 README）
pip install -r requirements.txt
pip install -r requirements-onnxruntime-cpu.txt

# 3. 引擎（官方 release 2026-09-06，exe 与 pikafish.nnue 同目录）
#    放到 Pikafish/src/ 或在设置页指定路径

# 4. 启动
python main.py
```

访问 <http://localhost:5000>，默认账号 `admin / admin123`。

## ✅ 验收结果（本机实测）

| 项目 | 结果 |
|---|---|
| `python -m pytest` | 108 passed |
| `python test_system.py` | 8/8 |
| 单图端到端（真实检测器 + 真实 Pikafish） | FEN/中文记谱/箭头/图像均正常 |
| GPU 检测 | provider 为 CUDA，0.028s（CPU 0.216s） |
| 帧差分 | 静态帧跳过并记录日志 |
| 批量分析 | 10 张上限、单张失败不影响整批 |
| 内网穿透 | Web 端配置/启停/状态（无客户端时返回可读错误） |

## 🖥️ 环境基线

| 项目 | 版本 |
|---|---|
| OS | Windows |
| Python | 3.11.9 |
| ONNX Runtime CPU / GPU | 1.31.1 / 1.32.0 |
| GPU / 驱动 | RTX 5060 Ti 8GB / 617.42 |
| Pikafish | 2026-09-06 官方 release |
| Chinese_Chess_Recognition | 53201d6 |

## ⚠️ 交付说明与已知问题

- 引擎二进制、`pikafish.nnue`、模型权重大文件不入库（模型已随仓库提供，引擎需自行下载）；
- GPU 版与 CPU 版 ONNX Runtime 不能共存，切换前需卸载；
- GPU 首次推理约 12 秒；
- 遮挡位置按空位处理；不合法局面会被引擎拒绝；
- 用户会话保存在内存，重启后需重新登录；
- 角色权限未分级。
