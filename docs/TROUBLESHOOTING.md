# 故障排除指南

## 🚨 快速诊断

### 运行诊断工具

```bash
# 测试Pikafish引擎
python tests/test_pikafish.py /path/to/pikafish

# 运行完整系统测试
python tests/test_debug.py

# 交互式调试
python tests/test_debug.py --interactive
```

## 🔍 常见问题

### 1. Pikafish引擎问题

#### 问题1.1: 没有执行权限

**错误信息:**
```
PermissionError: [Errno 13] Permission denied
```

**解决方法:**

**Linux/macOS:**
```bash
chmod +x /path/to/pikafish

# 验证权限
ls -la /path/to/pikafish
# 应该显示: -rwxr-xr-x
```

**Windows:**
1. 右键点击 `pikafish.exe`
2. 选择"属性"
3. 切换到"安全"选项卡
4. 点击"编辑"按钮
5. 选择你的用户
6. 勾选"完全控制"
7. 点击"应用"

**使用管理员权限运行:**
```bash
# Windows
右键点击命令提示符 → 以管理员身份运行

# Linux/macOS
sudo python main.py
```

#### 问题1.2: 找不到引擎文件

**错误信息:**
```
FileNotFoundError: 找不到Pikafish引擎: /path/to/pikafish
```

**解决方法:**

1. **检查文件是否存在**
   ```bash
   ls -la /path/to/pikafish
   ```

2. **使用绝对路径**
   ```python
   # 在配置文件中
   "engine_path": "/home/user/pikafish/pikafish"
   ```

3. **检查文件完整性**
   ```bash
   # 文件应该大于1KB
   du -h /path/to/pikafish
   
   # 检查是否可执行
   file /path/to/pikafish
   ```

4. **重新下载引擎**
   - 从 [Pikafish官方仓库](https://github.com/official-pikafish/Pikafish/releases) 下载
   - 确保下载对应平台的版本

#### 问题1.3: 引擎启动失败

**错误信息:**
```
RuntimeError: 引擎启动失败
```

**解决方法:**

1. **检查引擎版本**
   ```bash
   # 测试引擎是否能独立运行
   ./pikafish
   
   # 应该看到UCI协议输出
   ```

2. **检查依赖库**
   ```bash
   # Linux
   ldd /path/to/pikafish
   
   # macOS
   otool -L /path/to/pikafish
   ```

3. **查看详细错误**
   ```bash
   # 运行测试脚本获取详细信息
   python tests/test_pikafish.py /path/to/pikafish
   ```

### 2. 棋盘检测问题

#### 问题2.1: 找不到检测器模块

**错误信息:**
```
ImportError: cannot import name 'ChessboardDetector'
```

**解决方法:**

1. **检查第三方代码仓**
   ```bash
   # 确保子模块已初始化
   git submodule init
   git submodule update
   
   # 检查目录是否存在
   ls -la third_party/chess_detector/
   ```

2. **检查导入路径**
   ```python
   # 正确的导入方式
   from third_party.chess_detector.core.chessboard_detector import ChessboardDetector
   ```

3. **添加子模块（如果还没有）**
   ```bash
   git submodule add https://github.com/original-author/chess-detector.git third_party/chess_detector
   ```

#### 问题2.2: 模型文件不存在

**错误信息:**
```
FileNotFoundError: 找不到模型文件: onnx/pose/4_v6-0301.onnx
```

**解决方法:**

1. **检查模型文件路径**
   ```bash
   ls -la onnx/pose/
   ls -la onnx/layout_recognition/
   ```

2. **从第三方仓库获取模型**
   ```bash
   # 确保子模块已更新
   cd third_party/chess_detector
   git pull origin main
   cd ../..
   
   # 复制模型文件（如果需要）
   cp third_party/chess_detector/onnx/* onnx/
   ```

3. **修改模型路径配置**
   ```json
   {
     "pose_model_path": "third_party/chess_detector/onnx/pose/4_v6-0301.onnx",
     "classifier_model_path": "third_party/chess_detector/onnx/layout_recognition/nano_v3-0319.onnx"
   }
   ```

#### 问题2.3: 检测不准确

**问题描述:**
- 棋子识别错误
- 位置不准确
- 置信度低

**解决方法:**

1. **调整图像质量**
   - 确保棋盘清晰可见
   - 调整摄像头角度和距离
   - 改善光照条件

2. **调整检测参数**
   ```python
   # 增加思考时间
   "think_time": 3000,
   
   # 调整检测阈值（如果有）
   DETECTOR_IS_INVERTED = True  # 或 False
   ```

3. **使用测试脚本验证**
   ```bash
   python tests/test_debug.py
   ```

### 3. Web界面问题

#### 问题3.1: 无法访问Web界面

**问题描述:**
- 浏览器无法打开 http://localhost:5000
- 页面加载失败

**解决方法:**

1. **检查服务是否启动**
   ```bash
   # 查看进程
   ps aux | grep python
   
   # 查看端口占用
   netstat -tlnp | grep 5000
   ```

2. **检查防火墙设置**
   ```bash
   # Linux
   sudo ufw status
   sudo ufw allow 5000
   
   # Windows
   控制面板 → Windows防火墙 → 允许应用通过防火墙
   ```

3. **更换端口**
   ```bash
   python main.py --port 8080
   ```

4. **查看日志**
   ```bash
   tail -f logs/xiangqi_analyzer.log
   ```

#### 问题3.2: 登录失败

**问题描述:**
- 无法登录系统
- 提示用户名或密码错误

**解决方法:**

1. **检查用户配置**
   ```python
   # 在 web/app.py 中查看默认用户
   # 默认用户: admin/admin123, guest/guest123
   ```

2. **重置用户**
   ```python
   # 在 web/app.py 中添加用户
   user_manager.add_user('newuser', 'newpass')
   ```

3. **禁用认证（开发环境）**
   ```python
   # 临时注释掉登录检查
   # if not user_manager.is_logged_in(session_id):
   #     return redirect(url_for('login'))
   ```

#### 问题3.3: WebSocket连接失败

**问题描述:**
- 实时更新不工作
- 浏览器控制台显示WebSocket错误

**解决方法:**

1. **检查浏览器兼容性**
   - 使用Chrome、Firefox、Edge等现代浏览器
   - 确保浏览器支持WebSocket

2. **检查网络**
   - 清除浏览器缓存
   - 禁用浏览器插件
   - 检查代理设置

3. **查看日志**
   ```bash
   tail -f logs/xiangqi_analyzer.log | grep -i websocket
   ```

### 4. 流处理问题

#### 问题4.1: RTMP流连接失败

**问题描述:**
- 无法连接到RTMP流
- 画面不显示

**解决方法:**

1. **检查流地址**
   ```bash
   # 确保流地址格式正确
   rtmp://localhost/live/stream
   ```

2. **测试流是否可用**
   ```bash
   # 使用ffplay测试
   ffplay rtmp://localhost/live/stream
   ```

3. **检查网络连接**
   ```bash
   ping localhost
   telnet localhost 1935
   ```

4. **查看流处理器日志**
   ```python
   # 在 src/stream_processor.py 中启用详细日志
   logger.setLevel(logging.DEBUG)
   ```

#### 问题4.2: 模拟器截图失败

**问题描述:**
- 找不到模拟器窗口
- 截图为空

**解决方法:**

1. **检查模拟器是否运行**
   ```bash
   # Linux/macOS
   ps aux | grep -i mumu
   
   # Windows
   tasklist | findstr /i mumu
   ```

2. **检查窗口标题**
   ```python
   # 在 src/stream_processor.py 中添加调试代码
   windows = screen_capture.list_windows()
   for w in windows:
       print(w)
   ```

3. **使用屏幕截图模式**
   ```json
   {
     "source_type": "screen",
     "source_value": "100,100,800,600"
   }
   ```

### 5. 内网穿透问题

#### 问题5.1: ngrok连接失败

**问题描述:**
- 无法获取公网URL
- 连接超时

**解决方法:**

1. **检查ngrok安装**
   ```bash
   ngrok version
   ```

2. **检查认证令牌**
   ```bash
   ngrok authtoken YOUR_TOKEN
   ```

3. **更换区域**
   ```bash
   # 在 tunnel_service.py 中修改区域
   region = 'us'  # 或 'eu', 'ap', 'au', 'sa', 'jp', 'in'
   ```

4. **查看ngrok日志**
   ```bash
   ngrok http 5000 --log=stdout
   ```

#### 问题5.2: frp连接失败

**问题描述:**
- 无法连接到frp服务器
- 认证失败

**解决方法:**

1. **检查服务器地址和端口**
   ```json
   {
     "server_addr": "your-server.com",
     "server_port": 7000
   }
   ```

2. **检查访问令牌**
   ```json
   {
     "token": "your-secret-token"
   }
   ```

3. **测试服务器连接**
   ```bash
   telnet your-server.com 7000
   ```

## 🔧 高级调试技巧

### 1. 启用详细日志

```python
# 在 main.py 中设置日志级别为DEBUG
logging.basicConfig(level=logging.DEBUG)

# 或者在命令行中
python main.py --debug
```

### 2. 使用调试器

```bash
# 使用pdb调试
python -m pdb main.py

# 使用ipdb调试（更友好）
pip install ipdb
python -m ipdb main.py
```

### 3. 添加断点

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或者使用ipdb
import ipdb; ipdb.set_trace()
```

### 4. 性能分析

```bash
# 使用cProfile分析性能
python -m cProfile -o profile.out main.py
python -c "import pstats; pstats.Stats('profile.out').sort_stats('cumulative').print_stats(10)"
```

### 5. 内存分析

```bash
# 使用memory_profiler
pip install memory_profiler
python -m memory_profiler main.py
```

## 📋 调试清单

### 问题排查步骤

1. **查看错误信息**
   - 仔细阅读错误消息
   - 查看日志文件
   - 运行测试脚本

2. **检查基础环境**
   - Python版本
   - 依赖包是否安装
   - 文件路径是否正确

3. **检查配置文件**
   - 配置文件格式是否正确
   - 路径是否正确
   - 参数是否合理

4. **检查权限**
   - 文件执行权限
   - 目录读写权限
   - 网络访问权限

5. **检查网络连接**
   - 端口是否开放
   - 防火墙设置
   - 代理配置

6. **查看系统资源**
   - CPU使用率
   - 内存占用
   - 磁盘空间

### 提交Issue前

- [ ] 已查看日志文件
- [ ] 已运行测试脚本
- [ ] 已搜索已知问题
- [ ] 已尝试基本解决方法
- [ ] 已提供环境信息（OS, Python版本, 错误日志）

## 📞 获取帮助

### 自助资源

1. **查看日志**
   ```bash
   tail -f logs/xiangqi_analyzer.log
   ```

2. **运行测试**
   ```bash
   python tests/test_system.py
   python tests/test_pikafish.py /path/to/pikafish
   python tests/test_debug.py
   ```

3. **查看文档**
   - README.md
   - USER_GUIDE.md
   - TROUBLESHOOTING.md（本文件）

### 提交Issue

在提交Issue前，请提供以下信息：

1. **环境信息**
   - 操作系统及版本
   - Python版本
   - 相关依赖版本

2. **错误信息**
   - 完整的错误消息
   - 日志文件内容
   - 复现步骤

3. **已尝试的解决方法**
   - 已尝试的解决步骤
   - 测试结果

## 🎉 总结

遇到问题时：

1. **不要慌** - 大部分问题都有解决方法
2. **看日志** - 日志通常会告诉你问题所在
3. **查文档** - 本文档包含大多数常见问题
4. **做测试** - 使用测试脚本快速定位问题
5. **提Issue** - 如果解决不了，提交详细的Issue

记住：
- 详细的信息有助于快速解决问题
- 日志是调试的最好朋友
- 测试脚本可以节省大量时间