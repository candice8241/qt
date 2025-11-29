# UI Configuration System

## 概述

为了方便自定义界面，我创建了一套完整的UI配置系统。现在您可以轻松修改所有颜色、字体和按钮标签，无需编辑主程序代码。

## 文件说明

### 📄 `ui_config.json` (推荐使用)
**JSON格式配置文件 - 最简单的自定义方式**

```json
{
  "colors": {
    "bg_header": "#9775FA",      // 背景区域标题颜色（紫色）
    "smooth_header": "#228BE6",   // 平滑区域标题颜色（蓝色）
    "results_header": "#FF6B9D"   // 结果区域标题颜色（粉色）
  }
}
```

- 包含所有UI颜色定义（31种颜色）
- 字体设置
- 按钮定义和标签
- 区域高度配置
- 易于编辑，不需要Python知识

### 📄 `ui_config.py`
**Python配置模块 - 高级自定义**

- 完整的颜色调色板
- 字体配置
- 按钮样式定义
- 区域配置
- 辅助函数（自动生成样式表）

### 📖 `UI_CUSTOMIZATION_GUIDE.md`
**详细的自定义指南**

包含：
- 如何修改颜色、字体、按钮文本
- 颜色参考表
- 5个主题模板（暗色、简约、暖色、冷色、粉彩）
- 快速参考
- 故障排除

### 🎯 `example_ui_usage.py`
**使用示例代码**

展示如何：
- 创建带配置样式的按钮
- 创建区域标签
- 加载JSON配置
- 创建输入控件
- 动态更改主题
- 从配置创建所有按钮

## 快速开始

### 1. 修改颜色

编辑 `ui_config.json`：

```json
{
  "colors": {
    "btn_load": "#9B86BD",   // Load File按钮颜色
    "btn_fit": "#E4B4E4",    // Fit Peaks按钮颜色
    "btn_save": "#51CF66"    // Save Results按钮颜色
  }
}
```

### 2. 修改按钮文本

```json
{
  "buttons": {
    "control_panel": [
      {"text": "加载文件", "color": "btn_load"},
      {"text": "拟合峰", "color": "btn_fit"}
    ]
  }
}
```

### 3. 修改字体

```json
{
  "fonts": {
    "family": "Microsoft YaHei",  // 使用微软雅黑
    "sizes": {
      "header": 11,
      "normal": 10
    }
  }
}
```

## 当前配置

### 颜色方案

| 组件 | 颜色 | 说明 |
|------|------|------|
| Background标题 | #9775FA | 紫色 |
| Smoothing标题 | #228BE6 | 蓝色 |
| Fitting Results标题 | #FF6B9D | 粉色 |
| Load File | #9B86BD | 柔和紫色 |
| 导航按钮 (◀▶) | #CBA6F7 | 淡紫色 |
| Fit Peaks | #E4B4E4 | 浅粉色 |
| Reset | #FA9999 | 鲑鱼粉 |
| Save Results | #51CF66 | 绿色 |
| Clear Fit | #FFB366 | 橙色 |
| Undo/Auto Find | #CBA6F7 | 淡紫色 |
| Overlap | #AAAAAA | 灰色 |
| Batch Auto Fit | #74C0FC | 青色 |

### 区域设置

- **Control Panel**: 高度55px, 白色背景
- **Background**: 高度50px, 浅蓝色背景 (#E7F5FF)
- **Smoothing**: 高度50px, 浅紫色背景 (#F3F0FF)
- **Results**: 高度120px, 浅黄色背景 (#FFF9DB)

## 预设主题

### 暖色主题
```json
{
  "bg_header": "#E07A5F",
  "smooth_header": "#F2CC8F",
  "results_header": "#81B29A"
}
```

### 冷色主题
```json
{
  "bg_header": "#5E60CE",
  "smooth_header": "#4EA8DE",
  "results_header": "#56CFE1"
}
```

### 粉彩主题
```json
{
  "bg_header": "#FFB4A2",
  "smooth_header": "#B4D8E7",
  "results_header": "#FFCAD4"
}
```

### 暗色主题
```json
{
  "main_bg": "#1E1E1E",
  "bg_header": "#BB86FC",
  "smooth_header": "#03DAC6",
  "results_header": "#CF6679"
}
```

## 验证配置

运行以下命令检查配置文件是否有效：

```bash
# 验证JSON配置
python3 -c "import json; json.load(open('ui_config.json')); print('✓ JSON配置有效')"

# 验证Python配置模块
python3 -c "import ui_config; print('✓ Python配置模块有效')"
```

## 使用方法

### 方法1：直接编辑JSON (推荐)
1. 打开 `ui_config.json`
2. 修改您想要的颜色或设置
3. 保存文件
4. 重启应用程序

### 方法2：使用Python配置
1. 在代码中导入: `import ui_config as cfg`
2. 使用颜色: `cfg.COLORS['btn_load']`
3. 使用辅助函数: `cfg.get_button_style(...)`

## 配置文件大小

- `ui_config.json`: 3.0KB
- `ui_config.py`: 10KB
- `UI_CUSTOMIZATION_GUIDE.md`: 5.5KB
- `example_ui_usage.py`: 5.4KB

## 支持

详细使用说明请参考：
- `UI_CUSTOMIZATION_GUIDE.md` - 完整的自定义指南
- `example_ui_usage.py` - 代码示例

## 总结

现在您可以：
- ✅ 修改所有颜色而不触碰Python代码
- ✅ 更改字体和字号
- ✅ 自定义按钮标签
- ✅ 调整区域高度
- ✅ 使用预设主题
- ✅ 创建自己的配色方案

所有修改都在配置文件中完成，简单、安全、易于维护！
