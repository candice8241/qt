# Auto Fitting Module - Qt6 Integration

## 概述

`auto_fitting_module.py` 是一个Qt6包装模块，用于将原有的`auto_fitting.py`（基于tkinter）集成到Qt6主应用程序中。

## 实现方式

由于原始`auto_fitting.py`文件非常大（2952行代码）且功能复杂，直接将所有tkinter代码转换为Qt6需要大量的工作和调试。因此采用了**包装器(Wrapper)模式**：

### 包装器方案的优势

1. **保持原始功能完整**：`auto_fitting.py`的所有功能保持不变
2. **快速集成**：无需重写大量代码
3. **独立运行**：Auto Fitting工具在独立进程中运行，不影响主程序
4. **易于维护**：原始代码的任何更新都可以直接使用

### 工作原理

1. 主程序通过Qt6模块界面提供启动按钮
2. 点击"Launch Auto Fitting Tool"按钮时，在新进程中启动`auto_fitting.py`
3. Auto Fitting工具以独立窗口形式运行，保留了所有原始功能

## 文件结构

```
/workspace/
├── auto_fitting.py              # 原始tkinter应用（保持不变）
├── auto_fitting_module.py       # Qt6包装模块（新增）
└── main.py                      # 主程序（已更新以集成新模块）
```

## 集成到主程序

在`main.py`中已经完成以下集成：

1. **导入模块**：
   ```python
   from auto_fitting_module import AutoFittingModule
   ```

2. **添加侧边栏按钮**：
   在主界面左侧导航栏添加了"🔍 Auto Fit"按钮

3. **模块初始化**：
   在`prebuild_modules()`方法中预构建模块

4. **标签页切换**：
   在`switch_tab()`方法中添加了auto_fitting的处理逻辑

## 使用方法

1. 启动主程序
2. 在左侧导航栏点击"🔍 Auto Fit"按钮
3. 在显示的模块页面中，点击"Launch Auto Fitting Tool"按钮
4. Auto Fitting工具将在新窗口中打开

## 功能特性

Auto Fitting工具提供以下功能：

- ✅ 自动峰检测和拟合
- ✅ 手动峰选择
- ✅ 背景扣除
- ✅ 批处理
- ✅ 多种拟合曲线（Pseudo-Voigt, Voigt）
- ✅ 结果导出

## 未来改进

如果需要完全的Qt6原生实现，可以考虑：

1. 逐步重写核心GUI类为Qt6版本
2. 保留数据处理类（DataProcessor, PeakClusterer等）不变
3. 将matplotlib backend从tkagg改为qt5agg
4. 替换所有tkinter控件为对应的Qt6控件

这将是一个大型重构项目，需要：
- 转换约2400行GUI代码
- 测试所有功能
- 修复布局和样式问题
- 确保与原有功能的兼容性

## 注意事项

1. 确保`auto_fitting.py`文件在同一目录下
2. Auto Fitting工具依赖tkinter，确保系统已安装
3. 两个程序可以同时运行，互不干扰

## 技术细节

- **包装模块**：`AutoFittingModule(QWidget)`
- **启动方式**：`subprocess.Popen()`
- **进程隔离**：独立Python进程
- **通信方式**：无需进程间通信（独立运行）
