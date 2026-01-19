# 快速启动指南

## 🎯 5分钟快速上手

### Windows用户

1. **双击启动**
   ```
   双击 start.bat
   ```

2. **打开浏览器**
   ```
   访问: http://localhost:5000
   ```

3. **登录**
   ```
   用户名: admin
   密码: admin123
   ```

4. **开始使用**
   - 上传图片分析，或
   - 配置模拟器实时分析

### Linux/macOS用户

1. **启动服务**
   ```bash
   ./start.sh
   ```

2. **打开浏览器**
   ```
   访问: http://localhost:5000
   ```

3. **登录**
   ```
   用户名: admin
   密码: admin123
   ```

## 📋 准备工作清单

### 必需项

- [ ] Python 3.7+
- [ ] Pikafish引擎
- [ ] 检测模型文件

### 可选项

- [ ] ngrok账号（用于内网穿透）
- [ ] MuMu模拟器（用于实时分析）

## 🚀 三种使用方式

### 方式1: 图片分析（最简单）

适合：快速测试、棋谱分析

步骤：
1. 启动服务
2. 登录Web界面
3. 上传图片
4. 查看结果

### 方式2: 模拟器分析（推荐）

适合：在线对局、实时分析

步骤：
1. 启动MuMu模拟器
2. 打开JJ象棋
3. 启动分析器服务
4. 在设置中选择"模拟器"
5. 开始分析
6. 查看推荐走法

### 方式3: RTMP流分析（高级）

适合：直播、教学演示

步骤：
1. 配置RTMP推流
2. 在设置中选择"RTMP流"
3. 输入流地址
4. 开始推流和分析

## ⚡ 常用命令

```bash
# 基本启动
python main.py

# 指定引擎路径
python main.py --engine-path C:/pikafish/pikafish.exe

# 模拟器模式
python main.py --source-type emulator --source-value "MuMu"

# 启用内网穿透
python main.py --enable-tunnel --tunnel-token YOUR_TOKEN

# 自定义端口
python main.py --port 8080

# 查看所有选项
python main.py --help
```

## 🔧 配置示例

### 分析JJ象棋

```json
{
  "engine_path": "C:/pikafish/pikafish.exe",
  "source_type": "emulator",
  "source_value": "MuMu",
  "think_time": 2000,
  "analysis_interval": 3
}
```

### RTMP流分析

```json
{
  "engine_path": "/usr/local/bin/pikafish",
  "source_type": "stream",
  "source_value": "rtmp://localhost/live/chess",
  "think_time": 3000,
  "analysis_interval": 5
}
```

### 屏幕截图分析

```json
{
  "engine_path": "/Applications/pikafish.app/Contents/MacOS/pikafish",
  "source_type": "screen",
  "source_value": "100,100,800,600",
  "think_time": 2000,
  "analysis_interval": 3
}
```

## 📱 移动端访问

### 内网穿透（推荐）

1. 注册ngrok账号
2. 获取AuthToken
3. 在设置中配置令牌
4. 启用内网穿透
5. 使用公网URL访问

### 局域网访问

1. 确保手机和电脑在同一WiFi
2. 查看电脑IP地址
3. 访问: http://电脑IP:5000

## 🎮 实战技巧

### 提高准确率

1. **调整摄像头**
   - 距离: 50-100cm
   - 角度: 垂直或略微倾斜
   - 光线: 充足且均匀

2. **优化设置**
   - 思考时间: 2000-3000ms
   - 分析间隔: 3-5秒

3. **选择合适模式**
   - 静态棋盘: 图片模式
   - 在线对局: 模拟器模式
   - 直播演示: RTMP流模式

### 快速响应

1. **减少思考时间**
   - 设置为1000-1500ms
   - 牺牲部分准确性

2. **增大分析间隔**
   - 设置为5-10秒
   - 降低CPU占用

## 🛠️ 故障速查

### 服务无法启动

```bash
# 检查Python版本
python --version

# 检查依赖
pip install -r requirements.txt

# 查看日志
cat logs/xiangqi_analyzer.log
```

### 引擎无法启动

```bash
# 检查引擎文件
ls -la /path/to/pikafish

# 检查权限
chmod +x /path/to/pikafish

# 测试引擎
/path/to/pikafish
```

### 检测不准确

1. 检查模型文件是否存在
2. 调整摄像头角度和距离
3. 改善光照条件
4. 增加思考时间

## 📊 性能参考

### 推荐配置

- **CPU**: i5/Ryzen 5 以上
- **内存**: 8GB+
- **网络**: 稳定宽带

### 响应时间

- 图片分析: 1-3秒
- 实时分析: 3-5秒/次
- 首次启动: 5-10秒

## 📞 获取帮助

### 查看日志

```bash
# 实时查看
 tail -f logs/xiangqi_analyzer.log

# 查看最新错误
grep ERROR logs/xiangqi_analyzer.log | tail
```

### 常见问题

查看: `docs/USER_GUIDE.md#故障排除`

### 提交Issue

在GitHub上提交Issue，包含:
- 错误描述
- 日志文件
- 配置文件
- 系统信息

---

**祝你玩得开心！**