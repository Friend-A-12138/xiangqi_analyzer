# 项目结构说明

## 📂 目录结构

```
xiangqi_analyzer/              # 项目根目录
├── main.py                    # 主程序入口
├── requirements.txt           # Python依赖
├── start.bat                  # Windows启动脚本
├── start.sh                   # Linux/macOS启动脚本
├── test_system.py             # 系统测试脚本
│
├── docs_all/                  # 项目文档
│   ├── README.md              # 项目说明（主文档）
│   ├── QUICK_START.md         # 快速启动指南
│   ├── USER_GUIDE.md          # 详细使用指南
│   ├── PROJECT_OVERVIEW.md    # 项目架构总览
│   ├── IMPLEMENTATION_SUMMARY.md # 实现总结
│   ├── DELIVERY.md            # 交付文档
│   └── PROJECT_STRUCTURE.md   # 本文件
│
├── src/                       # 项目源代码（我们的代码）
│   ├── __init__.py
│   ├── analyzer/              # 分析器模块
│   │   ├── __init__.py
│   │   ├── chess_analyzer.py  # 象棋分析器（整合第三方检测器）
│   │   └── pikafish_engine.py # Pikafish引擎封装
│   ├── processors/            # 处理器模块
│   │   ├── __init__.py
│   │   ├── stream_processor.py # 流处理器
│   │   └── screen_capture.py  # 屏幕截图
│   ├── tunnel/                # 内网穿透
│   │   ├── __init__.py
│   │   └── tunnel_service.py  # 内网穿透服务
│   └── web/                   # Web界面
│       ├── __init__.py
│       ├── app.py             # Flask应用
│       └── templates/         # HTML模板
│           ├── base.html
│           ├── login.html
│           ├── index.html
│           └── settings.html
│
├── third_party/               # 第三方代码（Git子模块）
│   ├── chess_detector/        # 棋盘检测器（Git子模块）
│   │   ├── core/              # 第三方core模块
│   │   │   ├── __init__.py
│   │   │   └── chessboard_detector.py
│   │   ├── onnx/
│   │   └── ...
│   └── README.md              # 第三方代码说明
│
├── config/                    # 配置文件
│   ├── config.json            # 主配置文件
│   └── config.example.json    # 配置示例
│
├── tests/                     # 测试文件
│   ├── __init__.py
│   ├── test_system.py         # 系统测试
│   ├── test_pikafish.py       # Pikafish引擎测试
│   ├── test_detector.py       # 检测器测试
│   └── test_debug.py          # 调试脚本
│
└── logs/                      # 日志文件
    └── xiangqi_analyzer.log   # 主日志文件
```

## 🔄 代码引用关系

### 核心引用关系

```
# 项目代码引用第三方代码
src/analyzer/chess_analyzer.py
└── from third_party.chess_detector.core.chessboard_detector import ChessboardDetector

# 项目内部引用
main.py
├── from src.analyzer.chess_analyzer import XiangqiAnalyzer
├── from src.processors.stream_processor import RTMPStreamProcessor
├── from src.tunnel.tunnel_service import TunnelManager
└── from src.web.app import app

# Web应用内部引用
src/web/app.py
├── from src.analyzer.chess_analyzer import XiangqiAnalyzer
└── from src.processors.stream_processor import RTMPStreamProcessor, EmulatorCapture
```

## 📦 模块说明

### 我们的代码 (src/)

#### src/analyzer/ - 分析器模块
- **chess_analyzer.py**: 整合第三方检测器和Pikafish引擎
- **pikafish_engine.py**: Pikafish引擎的封装类

#### src/processors/ - 处理器模块  
- **stream_processor.py**: RTMP流、模拟器、屏幕截图处理
- **screen_capture.py**: 屏幕截图功能

#### src/tunnel/ - 内网穿透
- **tunnel_service.py**: ngrok和frp的封装

#### src/web/ - Web界面
- **app.py**: Flask应用和API
- **templates/**: HTML模板文件

### 第三方代码 (third_party/)

#### third_party/chess_detector/ - 棋盘检测器（Git子模块）
- **core/chessboard_detector.py**: 原始的棋盘检测代码
- **onnx/**: 模型文件
- 这是通过Git子模块引用的外部仓库

## 🚀 使用Git子模块

### 添加子模块

```bash
# 添加第三方代码仓作为子模块
git submodule add https://github.com/original-author/chess-detector.git third_party/chess_detector

# 初始化子模块
git submodule init

# 更新子模块
git submodule update
```

### 克隆包含子模块的项目

```bash
# 克隆项目
git clone https://github.com/yourusername/xiangqi-analyzer.git

# 初始化并更新子模块
git submodule init
git submodule update

# 或者一步到位
git clone --recursive https://github.com/yourusername/xiangqi-analyzer.git
```

### 更新子模块

```bash
# 进入子模块目录
cd third_party/chess_detector

# 拉取最新代码
git pull origin main

# 返回项目根目录
cd ../..

# 提交子模块更新
git add third_party/chess_detector
git commit -m "Update chess_detector submodule"
```

## 📝 代码规范

### 导入规范

```python
# 标准库导入
import os
import sys

# 第三方库导入
import cv2
import numpy as np

# 本地模块导入（绝对导入）
from src.analyzer.chess_analyzer import XiangqiAnalyzer
from third_party.chess_detector.core.chessboard_detector import ChessboardDetector

# 避免使用相对导入
# ❌ from ..analyzer import XiangqiAnalyzer
# ✅ from src.analyzer import XiangqiAnalyzer
```

### 命名规范

- **项目模块**: `src.*`（我们的代码）
- **第三方模块**: `third_party.*`（他人的代码）
- **测试模块**: `tests.*`（测试代码）

## 🔧 开发指南

### 添加新功能

1. **在我们的代码中添加功能**
   ```bash
   # 在src/目录下添加新模块
   touch src/new_module.py
   ```

2. **引用第三方代码**
   ```python
   # 从third_party目录导入
   from third_party.some_lib import SomeClass
   ```

3. **添加Git子模块**（如果需要新的第三方库）
   ```bash
   git submodule add https://github.com/some-author/some-lib.git third_party/some_lib
   ```

### 调试指南

1. **使用测试脚本**
   ```bash
   python tests/test_debug.py
   ```

2. **查看日志**
   ```bash
   tail -f logs/xiangqi_analyzer.log
   ```

3. **启用调试模式**
   ```bash
   python main.py --debug
   ```

## 🎯 重要提示

### 代码归属

- **`src/` 目录下的代码**: 是我们自己编写的
- **`third_party/` 目录下的代码**: 是通过Git子模块引用的第三方代码
- **不要直接修改 `third_party/` 下的代码**，应该去原仓库提交PR

### 依赖关系

- **我们的代码** 依赖于 **第三方代码**
- **第三方代码** 不依赖于我们的代码
- 保持这种单向依赖关系，避免循环依赖

### 更新策略

- 定期更新Git子模块以获取第三方代码的最新版本
- 在更新前测试兼容性
- 记录第三方代码的版本号

## 📋 检查清单

### 项目结构检查
- [x] 所有目录都已创建
- [x] 所有文件都在正确位置
- [x] Git子模块已正确配置
- [x] 导入路径已更新

### 代码检查
- [x] 没有循环导入
- [x] 使用绝对导入
- [x] 代码符合PEP8规范
- [x] 有完整的文档字符串

### 文档检查
- [x] README.md已更新
- [x] 所有文档已移动到docs_all/
- [x] 文档引用正确的路径
- [x] 包含Git子模块使用说明

### 测试检查
- [x] 测试脚本已创建
- [x] 测试覆盖主要功能
- [x] 测试脚本可以独立运行
- [x] 包含调试指南

## 🎉 总结

通过这种项目结构：

1. **清晰分离**: 我们的代码和第三方代码完全分离
2. **易于维护**: 每个模块职责明确
3. **方便调试**: 有专门的测试和调试工具
4. **尊重版权**: 使用Git子模块引用第三方代码
5. **易于扩展**: 模块化设计，易于添加新功能

**记住**: 
- `src/` 是我们的代码
- `third_party/` 是别人的代码（通过Git子模块）
- `tests/` 是测试代码
- `docs_all/` 是文档