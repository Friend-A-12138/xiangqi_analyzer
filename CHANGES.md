# 项目更新日志

## v2.0.0 (2024-01-19)

### 🏗️ 重大架构调整

#### 1. 项目结构重组
- **将 `core/` 重命名为 `src/`**: 更清晰的项目代码目录
- **新增 `Chinese_Chess_Recognition/` 目录**: 专门存放第三方代码（通过Git子模块管理）
- **新增 `tests/` 目录**: 存放测试和调试脚本
- **新增 `docs_all/` 目录**: 统一存放所有文档

#### 2. 代码引用规范化
- **所有项目内部引用改为 `src.*`**: 避免与第三方代码混淆
- **第三方代码引用改为 `Chinese_Chess_Recognition.*`**: 清晰区分代码来源
- **更新了所有导入路径**: 确保代码能够正确运行

#### 3. Git子模块支持
- **添加Git子模块使用指南**: [docs_all/GIT_SUBMODULE_GUIDE.md](docs_all/GIT_SUBMODULE_GUIDE.md)
- **规划第三方代码管理方案**: 使用Git子模块引用原始仓库
- **保持代码归属清晰**: 尊重原作者的贡献

### 📚 文档改进

#### 1. 文档整合
- **将所有Markdown文档移动到 `docs_all/` 目录**: 避免根目录混乱
- **创建统一的README.md**: 提供清晰的项目概览和快速导航
- **整合重复内容**: 减少文档冗余

#### 2. 新增文档
- **故障排除指南**: [docs_all/TROUBLESHOOTING.md](docs_all/TROUBLESHOOTING.md)
- **Git子模块指南**: [docs_all/GIT_SUBMODULE_GUIDE.md](docs_all/GIT_SUBMODULE_GUIDE.md)
- **项目结构说明**: [docs_all/PROJECT_STRUCTURE.md](docs_all/PROJECT_STRUCTURE.md)

### 🧪 测试调试增强

#### 1. 新增测试脚本
- **test_pikafish.py**: 专门测试Pikafish引擎，包括权限检查
- **test_debug.py**: 通用调试工具，支持交互式调试

#### 2. 测试功能
- **权限检查**: 自动检测和修复引擎执行权限问题
- **路径解析**: 测试各种路径格式
- **引擎执行测试**: 验证引擎是否能正常启动和响应
- **交互式调试**: 提供菜单选择要调试的模块

### 🔧 易用性改进

#### 1. 更好的错误提示
- **权限问题**: 提供明确的解决命令
- **路径问题**: 建议绝对路径和相对路径的使用
- **依赖问题**: 清晰的依赖安装说明

#### 2. 调试工具
- **一键诊断**: 运行测试脚本快速定位问题
- **详细日志**: 启用调试模式获取更多信息
- **性能分析**: 提供性能分析工具

### 📝 代码规范

#### 1. 导入规范
```python
# 标准库
import os
import sys

# 第三方库
import cv2
import numpy as np

# 项目模块
from src.analyzer.chess_analyzer import XiangqiAnalyzer

# 第三方模块
from Chinese_Chess_Recognition.core.chessboard_detector import ChessboardDetector
```

#### 2. 命名规范
- **项目模块**: `src.*`（我们的代码）
- **第三方模块**: `Chinese_Chess_Recognition.*`（他人的代码）
- **测试模块**: `tests.*`（测试代码）

## 🎯 使用指南

### 新用户

1. **查看快速启动指南**: [docs_all/QUICK_START.md](docs_all/QUICK_START.md)
2. **运行系统测试**: `python test_system.py`
3. **启动服务**: `python main.py`

### 现有用户升级

1. **备份配置文件**: `config/config.json`
2. **更新代码**: `git pull`
3. **更新导入路径**: 检查是否有自定义代码使用了旧的 `core.*` 导入
4. **运行测试**: `python test_system.py`
5. **启动服务**: `python main.py`

### 开发者

1. **查看项目结构**: [docs_all/PROJECT_STRUCTURE.md](docs_all/PROJECT_STRUCTURE.md)
2. **了解Git子模块**: [docs_all/GIT_SUBMODULE_GUIDE.md](docs_all/GIT_SUBMODULE_GUIDE.md)
3. **运行调试工具**: `python tests/test_debug.py`

## 🔄 迁移指南

### 从旧版本迁移

#### 配置文件
- 配置文件格式保持不变
- 无需修改现有配置

#### 自定义代码
- 如果使用了 `from core.*` 导入，需要改为 `from src.*`
- 示例:
  ```python
  # 旧代码
  from core.chess_analyzer import XiangqiAnalyzer
  
  # 新代码
  from src.chess_analyzer import XiangqiAnalyzer
  ```

#### 第三方代码
- 现在通过 `Chinese_Chess_Recognition.*` 导入
- 示例:
  ```python
  # 旧代码
  from core.chessboard_detector import ChessboardDetector
  
  # 新代码
  from Chinese_Chess_Recognition.core.chessboard_detector import ChessboardDetector
  ```

## 📋 检查清单

### 升级前
- [ ] 备份配置文件
- [ ] 备份自定义代码
- [ ] 记录当前工作目录

### 升级后
- [ ] 运行系统测试: `python test_system.py`
- [ ] 测试Pikafish引擎: `python tests/test_pikafish.py /path/to/pikafish`
- [ ] 启动服务测试: `python main.py --no-browser`
- [ ] 检查Web界面: http://localhost:5000

## 🎉 总结

本次更新主要解决了以下问题：

1. **代码结构混乱**: 通过 `src/` 和 `Chinese_Chess_Recognition/` 清晰分离代码
2. **文档分散**: 统一整理到 `docs_all/` 目录
3. **调试困难**: 提供专门的测试和调试脚本
4. **第三方代码管理**: 引入Git子模块规范

现在项目更加：
- ✅ 结构清晰
- ✅ 易于维护
- ✅ 方便调试
- ✅ 尊重版权
- ✅ 易于扩展

**欢迎使用新版本！**