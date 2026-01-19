# Git子模块使用指南

## 📋 概述

本项目使用Git子模块来引用第三方的棋盘检测器代码。这样做的好处是：

1. **尊重原作者**: 保留原作者的代码仓库和提交历史
2. **易于更新**: 可以方便地更新到第三方代码的最新版本
3. **清晰分离**: 我们的代码和第三方代码完全分离
4. **版本控制**: 可以锁定第三方代码的特定版本

## 🏗️ 项目结构

```
xiangqi_analyzer/
├── src/                       # 我们的代码
│   ├── analyzer/
│   │   └── chess_analyzer.py  # 整合第三方检测器
│   └── ...
├── third_party/               # 第三方代码（Git子模块）
│   └── chess_detector/        # 棋盘检测器
│       ├── core/
│       │   └── chessboard_detector.py
│       └── onnx/              # 模型文件
└── ...
```

## 🚀 初次使用

### 克隆项目（包含子模块）

```bash
# 方法1: 使用 --recursive 参数
git clone --recursive https://github.com/yourusername/xiangqi-analyzer.git

# 方法2: 手动初始化和更新
git clone https://github.com/yourusername/xiangqi-analyzer.git
cd xiangqi-analyzer
git submodule init
git submodule update
```

### 如果子模块目录为空

```bash
# 初始化子模块
git submodule init

# 更新子模块内容
git submodule update
```

## 📦 添加子模块

### 添加新的子模块

```bash
# 添加第三方代码仓作为子模块
git submodule add https://github.com/original-author/chess-detector.git third_party/chess_detector

# 提交更改
git add .gitmodules third_party/chess_detector
git commit -m "Add chess_detector submodule"
git push
```

### .gitmodules 文件

添加子模块后，会在项目根目录生成 `.gitmodules` 文件：

```ini
[submodule "third_party/chess_detector"]
	path = third_party/chess_detector
	url = https://github.com/original-author/chess-detector.git
```

## 🔄 更新子模块

### 更新到最新版本

```bash
# 进入子模块目录
cd third_party/chess_detector

# 拉取最新代码
git checkout main  # 或其他分支
git pull origin main

# 返回项目根目录
cd ../..

# 查看子模块状态
git submodule status

# 提交子模块更新
git add third_party/chess_detector
git commit -m "Update chess_detector submodule to latest version"
git push
```

### 更新到特定版本

```bash
# 进入子模块目录
cd third_party/chess_detector

# 查看提交历史
git log --oneline

# 切换到特定提交
git checkout abc123  # 提交哈希

# 或者切换到特定标签
git checkout v1.0.0  # 标签名

# 返回项目根目录
cd ../..

# 提交子模块更新
git add third_party/chess_detector
git commit -m "Update chess_detector to version v1.0.0"
git push
```

## 📊 查看子模块状态

### 检查子模块状态

```bash
# 查看所有子模块的状态
git submodule status

# 输出示例:
# +abc123 third_party/chess_detector (v1.0.0)
# -def456 third_party/other_lib (heads/main)

# 含义:
# + 表示子模块有新的提交
# - 表示子模块未初始化
# 没有符号表示子模块是最新的
```

### 查看子模块的提交记录

```bash
# 在项目根目录查看
git log --submodule

# 或者在子模块目录查看
cd third_party/chess_detector
git log --oneline
```

## 🛠️ 修复子模块问题

### 子模块目录为空

```bash
# 初始化并更新子模块
git submodule init
git submodule update

# 或者使用一条命令
git submodule update --init
```

### 子模块指向错误的提交

```bash
# 重置子模块到正确的提交
git submodule update --force

# 或者手动进入子模块目录切换
cd third_party/chess_detector
git checkout main
git pull origin main
```

### 子模块冲突

```bash
# 如果你在子模块中做了修改，想要放弃
git submodule foreach --recursive git reset --hard

# 或者
git submodule foreach --recursive git clean -fd
```

## 🗑️ 移除子模块

### 完全移除子模块

```bash
# 1. 删除子模块条目
git submodule deinit third_party/chess_detector

# 2. 删除子模块目录
git rm third_party/chess_detector

# 3. 删除 .gitmodules 中的条目
# 编辑 .gitmodules 文件，删除对应条目

# 4. 删除 .git/modules 中的缓存
rm -rf .git/modules/third_party/chess_detector

# 5. 提交更改
git add .gitmodules
git commit -m "Remove chess_detector submodule"
git push
```

## 📝 开发工作流

### 日常开发

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/xiangqi-analyzer.git
cd xiangqi-analyzer

# 2. 初始化子模块
git submodule init
git submodule update

# 3. 开始开发...
# 编辑 src/ 目录下的代码

# 4. 提交我们的代码
git add src/
git commit -m "Add new feature"
git push

# 5. 更新子模块（可选）
cd third_party/chess_detector
git pull origin main
cd ../..
git add third_party/chess_detector
git commit -m "Update chess_detector submodule"
git push
```

### 注意事项

1. **不要直接修改子模块代码**
   - 如果需要修改第三方代码，应该在原仓库提交PR
   - 然后在项目中更新子模块

2. **提交时要分开**
   - 我们的代码提交: `git add src/`
   - 子模块更新: `git add third_party/chess_detector`

3. **清晰的提交信息**
   - 更新子模块时注明版本: "Update chess_detector to v1.0.0"
   - 我们的功能: "Add user authentication"

## 🔍 常见问题

### Q: 子模块目录为什么是空的？

A: 克隆项目后需要初始化和更新子模块：
```bash
git submodule init
git submodule update
```

### Q: 如何查看子模块的当前版本？

A: 
```bash
git submodule status
# 或者
cd third_party/chess_detector
git log --oneline -1
```

### Q: 如何更新子模块到最新版本？

A:
```bash
cd third_party/chess_detector
git checkout main
git pull origin main
cd ../..
git add third_party/chess_detector
git commit -m "Update chess_detector"
```

### Q: 子模块和子树(subtree)有什么区别？

A:
- **子模块**: 独立的Git仓库，主项目只保存引用
- **子树**: 第三方代码直接合并到主项目中

对于我们的场景，子模块更合适，因为：
1. 保持第三方仓库的独立性
2. 更容易更新到特定版本
3. 更清晰的代码归属

### Q: 如何在CI/CD中处理子模块？

A: 在CI/CD配置中添加：
```yaml
# GitHub Actions
- uses: actions/checkout@v2
  with:
    submodules: recursive

# GitLab CI
git submodule update --init --recursive
```

## 📋 检查清单

### 使用子模块前
- [x] 已安装Git 2.13+
- [x] 已配置Git用户信息
- [x] 有权限访问子模块仓库

### 添加子模块时
- [x] 确认子模块URL正确
- [x] 确认子模块路径正确
- [x] 提交.gitmodules文件

### 更新子模块时
- [x] 测试子模块功能正常
- [x] 更新文档说明
- [x] 提交子模块引用

### 克隆项目时
- [x] 使用--recursive参数
- [x] 或手动init和update
- [x] 检查子模块是否完整

## 🎉 总结

使用Git子模块的好处：

1. **代码清晰**: 知道哪些是第三方代码
2. **易于维护**: 可以独立更新第三方代码
3. **尊重版权**: 保留原作者的提交历史
4. **版本控制**: 可以锁定特定版本
5. **协作友好**: 团队成员可以轻松获取完整的代码

记住的关键命令：
```bash
git submodule add <url> <path>    # 添加子模块
git submodule init                # 初始化子模块
git submodule update               # 更新子模块
git submodule update --remote      # 更新到远程最新版本
```