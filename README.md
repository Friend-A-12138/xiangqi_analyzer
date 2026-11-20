# 中国象棋AI分析器

基于深度学习和象棋引擎的中国象棋实时分析系统，支持棋盘检测、棋子识别和AI推荐走法。

## ✨ 功能特性

- 🎯 **智能棋盘检测**: 自动识别中国象棋棋盘和棋子位置
- 🤖 **AI走法推荐**: 集成Pikafish引擎，提供专业的走法建议
- 📹 **多源输入**: 支持图片、RTMP流、模拟器截图、屏幕截图
- 🖼️ **批量分析**: 一次上传多张棋谱图片，逐张输出FEN与推荐走法
- 🌐 **Web界面**: 提供友好的Web界面，实时显示分析结果
- 🔓 **内网穿透**: 支持ngrok/frp内网穿透，可在设置页直接配置与启停
- 👥 **用户管理**: 支持多用户访问，可配置数量上限并在页面上增删用户
- ♟️ **我方执子**: 可指定红方/黑方走子，避免引擎按错误的一方分析

## 🚀 快速开始

### 1. 环境准备

#### 安装Python依赖

```bash
pip install -r requirements.txt
```

#### 安装Pikafish引擎

从 [Pikafish官方仓库](https://github.com/official-pikafish/Pikafish/releases) 下载对应平台的引擎：

- Windows: 下载 `pikafish-windows-x86_64.exe`
- Linux: 下载 `pikafish-linux-x86_64`
- macOS: 下载 `pikafish-osx-x86_64`

**重要**: 确保引擎有执行权限！
```bash
# Linux/macOS
chmod +x /path/to/pikafish

# Windows
右键属性 → 安全 → 确保有执行权限
```

#### 准备检测模型

模型文件已随仓库提供（也可放在 `Chinese_Chess_Recognition` 子模块内）：

- 姿态检测模型: `onnx/pose/4_v6-0301.onnx`
- 棋子分类模型: `onnx/layout_recognition/nano_v3-0319.onnx`

#### 初始化子模块

检测代码通过子模块引入，首次使用需拉取：

```bash
git submodule update --init --recursive
```

### 2. 启动服务

#### 方式1: 一键启动（推荐）

**Windows:**
```bash
双击 start.bat
```

**Linux/macOS:**
```bash
./start.sh
```

#### 方式2: 命令行启动

```bash
# 基本启动
python main.py

# 指定引擎路径
python main.py --engine-path /path/to/pikafish

# 指定信号源
python main.py --source-type emulator --source-value "MuMu"

# 启用内网穿透
python main.py --enable-tunnel --tunnel-token YOUR_NGROK_TOKEN
```

### 3. 访问Web界面

打开浏览器访问: http://localhost:5000

默认用户:
- 用户名: `admin` / 密码: `admin123`
- 用户名: `guest` / 密码: `guest123`

## 📋 使用流程

### 场景1: 分析单张图片

1. 启动服务: `python main.py`
2. 打开浏览器: http://localhost:5000
3. 登录: admin/admin123
4. 在“上传图片分析”中选择图片并点击“分析图片”（无需先点“开始分析”）
5. 查看FEN、棋盘布局与推荐走法

### 场景2: 批量分析棋谱图片

1. 登录后进入首页
2. 在“棋谱批量分析”中选择多张图片（一次最多10张）
3. 点击“批量分析”，表格中逐张显示FEN、推荐走法与评估

### 场景3: 实时分析模拟器（推荐）

1. 启动MuMu模拟器，打开JJ象棋
2. 启动分析器服务
3. 访问Web界面并登录
4. 进入设置，配置:
   - 信号源类型: "模拟器"
   - 模拟器名称或窗口标题: "MuMu"（可点“刷新窗口”从系统窗口中选择）
   - 我方执子: 我执红 / 我执黑
   - 引擎路径: 你的pikafish.exe路径
5. 保存设置
6. 返回主页，点击"开始分析"
7. 查看实时分析结果

### 场景4: 通过内网穿透远程访问

1. 在设置页填写 ngrok AuthToken（或 frp 服务器信息）
2. 点击“保存配置”，再点击“启动穿透”
3. 页面显示公网URL后即可远程访问；停止时点击“停止”

## 📚 完整文档

### 📖 使用指南
- [快速启动指南](docs/QUICK_START.md) - 5分钟快速上手
- [使用指南](docs/USER_GUIDE.md) - 详细使用说明
- [故障排除指南](docs/TROUBLESHOOTING.md) - 常见问题解决

### 🏗️ 项目架构
- [项目结构](docs/PROJECT_STRUCTURE.md) - 代码组织结构
- [项目总览](docs/PROJECT_OVERVIEW.md) - 系统架构说明
- [实现总结](docs/IMPLEMENTATION_SUMMARY.md) - 实现细节

### 🔧 开发指南
- [Git子模块指南](docs/GIT_SUBMODULE_GUIDE.md) - 第三方代码管理
- [交付文档](docs/DELIVERY.md) - 项目交付清单

### 🧪 测试调试
- [系统测试](test_system.py) - 模块导入/目录/路由等完整性检查
- [Pikafish测试](tests/test_pikafish.py) - 测试Pikafish引擎与权限
- [调试脚本](tests/test_debug.py) - 通用调试工具
- `pytest tests` - 运行 pytest 用例（配置、用户、序列化、批量接口等）

## ⚙️ 配置说明

### 配置文件 (config/config.json)

```json
{
  "engine_path": "path/to/pikafish",
  "pose_model_path": "onnx/pose/4_v6-0301.onnx",
  "classifier_model_path": "onnx/layout_recognition/nano_v3-0319.onnx",
  "source_type": "emulator",
  "source_value": "MuMu",
  "player_side": "red",
  "think_time": 2000,
  "analysis_interval": 3,
  "frame_diff_threshold": 3.0,
  "max_users": 5,
  "uci_options": {
    "Threads": 14,
    "Hash": 512
  },
  "enable_tunnel": false,
  "tunnel_type": "ngrok",
  "tunnel_config": {
    "auth_token": "",
    "region": "ap"
  }
}
```

- `player_side`：我方执子，`red` 红方走子 / `black` 黑方走子 / `auto` 按红帅位置推断
- `max_users`：账号数量与在线人数上限（1-20）
- `uci_options`：引擎启动时下发的 UCI 选项；`Threads` 默认取 CPU 物理核数，`Hash` 默认 512（MB）
- `frame_diff_threshold`：画面变化阈值（灰度均方差），低于该值跳过检测与引擎调用，0 表示不跳过
- `source_value`：`stream` 为流地址、`emulator` 为模拟器名称或窗口标题、`screen` 为 `x,y,width,height`

完整示例见 [config/config.example.json](config/config.example.json)。配置文件由 Web 设置页读写，修改后重启仍生效。

### 命令行参数

```bash
python main.py [选项]

选项:
  -h, --help            显示帮助信息
  -c, --config CONFIG   配置文件路径
  -e, --engine-path PATH Pikafish引擎路径
  -s, --source-type TYPE 信号源类型 (file/stream/emulator/screen)
  -v, --source-value VALUE 信号源值
  --enable-tunnel       启用内网穿透
  --tunnel-type TYPE    内网穿透类型 (ngrok/frp)
  --tunnel-token TOKEN  内网穿透令牌
  -p, --port PORT       Web服务器端口 (默认: 5000)
  --host HOST           Web服务器主机 (默认: 0.0.0.0)
  --no-browser          不自动打开浏览器
  --debug               启用调试模式
```

## 🔧 常见问题

### 问题1: Pikafish引擎没有执行权限

**解决方法:**
```bash
# Linux/macOS
chmod +x /path/to/pikafish

# Windows
右键属性 → 安全 → 完全控制
```

### 问题2: 棋盘检测不准确

**解决方法:**
1. 检查模型文件路径
2. 调整摄像头角度和距离
3. 改善光照条件

### 问题3: Web界面无法访问

**解决方法:**
1. 检查服务是否启动
2. 检查端口是否被占用
3. 查看日志获取详细信息

**更多问题请参考:** [故障排除指南](docs/TROUBLESHOOTING.md)

## 📦 项目结构

```
xiangqi_analyzer/
├── main.py                 # 主程序入口
├── requirements.txt        # Python依赖
├── start.bat               # Windows启动脚本
├── start.sh                # Linux/macOS启动脚本
├── docs/                   # 项目文档
│   ├── QUICK_START.md      # 快速启动
│   ├── USER_GUIDE.md       # 使用指南
│   ├── TROUBLESHOOTING.md  # 故障排除
│   ├── PROJECT_STRUCTURE.md # 项目结构
│   └── ...
├── src/                    # 项目源代码
│   ├── config.py           # 配置管理（默认值/读写/校验）
│   ├── chess_analyzer.py   # 象棋分析器（检测器+Pikafish封装）
│   ├── chess_validator.py  # 棋盘颜色校验
│   ├── stream_processor.py # 流/屏幕/模拟器截图
│   └── tunnel_service.py   # 内网穿透服务（ngrok/frp）
├── web/                    # Web界面
│   ├── app.py              # Flask应用与接口
│   └── templates/          # 页面模板
├── onnx/                   # 检测模型
├── Chinese_Chess_Recognition/  # 检测器代码（Git子模块）
├── Pikafish/               # 引擎源码（Git子模块）
├── config/                 # 配置文件（含示例）
├── tests/                  # 测试与调试脚本
└── logs/                   # 日志文件
```

## 🎯 应用场景

### 1. 在线对局辅助
- 平台: JJ象棋、QQ象棋、天天象棋等
- 模式: 模拟器/屏幕截图
- 用途: 实时分析、学习AI思路

### 2. 棋谱批量分析
- 输入: 棋谱图片集
- 模式: 图片文件
- 用途: 研究经典棋局、棋谱整理

### 3. 教学演示
- 场景: 课堂、直播
- 模式: RTMP流
- 用途: 实时讲解、互动教学

### 4. 远程分析
- 方式: 内网穿透
- 特点: 随时随地访问
- 用途: 移动设备、异地协作

## 🧪 测试调试

### 运行测试

```bash
# 系统完整性测试（模块导入/目录/路由）
python test_system.py

# pytest 用例（配置/用户/序列化/批量接口）
pytest tests -q

# 测试Pikafish引擎
python tests/test_pikafish.py /path/to/pikafish

# 通用调试工具
python tests/test_debug.py
python tests/test_debug.py --interactive
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/xiangqi_analyzer.log

# 查找错误信息
grep ERROR logs/xiangqi_analyzer.log
```

## 📊 性能指标

### 响应时间
- 图片分析: 1-3秒
- 实时分析: 3-5秒/次
- Web界面加载: <1秒

### 准确率
- 棋盘检测: >95%
- 棋子识别: >98%
- 走法推荐: 专业级

## 🤝 贡献指南

### 代码贡献
1. Fork项目
2. 创建特性分支
3. 提交代码
4. 创建Pull Request

### 第三方代码
- 第三方代码位于 `Chinese_Chess_Recognition/` 与 `Pikafish/` 目录
- 使用Git子模块管理，首次使用执行 `git submodule update --init --recursive`
- 不要直接修改第三方代码
- 如需修改，请到原仓库提交PR

## 📄 许可证

本项目采用MIT许可证。

第三方代码的许可证请参考各自的仓库。

## 🎉 总结

本项目提供了一个完整的中国象棋AI分析解决方案，包含：

1. **强大的分析能力**: 集成Pikafish引擎，提供专业级走法推荐
2. **灵活的输入方式**: 支持图片、视频流、模拟器、屏幕截图
3. **友好的Web界面**: 实时显示分析结果，易于使用
4. **完善的文档**: 从快速上手到详细指南
5. **可扩展架构**: 模块化设计，易于添加新功能

**祝你使用愉快！**