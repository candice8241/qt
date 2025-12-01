# EoSFit Module Integration Guide

## 概述

成功将 CrysFML 的 EoSFit GUI 集成到 Qt 主界面中，实现了一个独立的模块接口。

## 集成内容

### 1. 新增文件

- **`eosfit_module.py`**: EoSFit 模块的封装类
  - 提供模块 UI 界面
  - 包含弹出 EoSFit GUI 窗口的功能
  - 继承自 `GUIBase`，保持与其他模块一致的设计风格

### 2. 修改的文件

- **`main.py`**: 主界面
  - 导入 `EoSFitModule`
  - 在左侧边栏添加 "📐 EoSFit" 按钮
  - 注册 `eosfit` 模块框架
  - 在 `prebuild_modules()` 中预构建 EoSFit 模块
  - 在 `switch_tab()` 中添加 EoSFit 标签页处理

## 功能特性

### EoSFit 模块界面

1. **模块简介**
   - 显示 EoSFit 工具的功能描述
   - 列出支持的 EoS 模型：
     - Birch-Murnaghan 2nd/3rd/4th Order
     - Murnaghan
     - Vinet
     - Natural Strain

2. **主要功能**
   - 点击 "🚀 Open EoSFit GUI" 按钮弹出完整的 EoSFit GUI 窗口
   - 独立的窗口界面，不影响主界面操作
   - 窗口状态管理（避免重复创建）

3. **EoSFit GUI 窗口**
   - 完整的交互式 P-V 数据拟合界面
   - 多种 EoS 模型选择
   - 实时参数调整和可视化
   - 参数锁定功能
   - 质量指标显示（R²、RMSE、χ²）

## 使用方法

### 启动应用

```bash
python3 main.py
```

### 使用 EoSFit 模块

1. 在主界面左侧边栏找到 "📐 EoSFit" 按钮
2. 点击按钮切换到 EoSFit 模块界面
3. 阅读模块介绍和支持的 EoS 模型
4. 点击 "🚀 Open EoSFit GUI" 按钮
5. 在弹出的窗口中：
   - 加载 CSV 数据文件（包含 V_atomic 和 Pressure (GPa) 列）
   - 选择 EoS 模型
   - 调整参数或运行自动拟合
   - 查看拟合结果和质量指标

## 模块架构

```
XRDProcessingGUI (main.py)
├── Powder Int. Module (powder_module.py)
├── Radial Int. Module (radial_module.py)
├── SC Module (single_crystal_module.py)
├── BCDI Cal. Module (bcdi_cal_module.py)
├── Dioptas Module (dioptas_module.py)
├── EoSFit Module (eosfit_module.py) ← 新增
├── curvefit Tool (interactive_fitting_gui.py)
└── eosfit Tool (interactive_eos_gui.py)
```

## 设计特点

1. **模块化封装**
   - `EoSFitModule` 类作为独立模块
   - 与其他模块保持一致的接口设计
   - 继承 `GUIBase` 基类，统一样式

2. **窗口管理**
   - 弹出式独立窗口，不影响主界面
   - 窗口状态检查，避免重复创建
   - 支持窗口激活和前置显示

3. **用户体验**
   - 美观的模块介绍界面
   - 清晰的功能说明
   - 直观的按钮操作
   - 与整体 UI 风格统一

## 技术细节

### EoSFitModule 类

```python
class EoSFitModule(GUIBase):
    def __init__(self, parent, root)
    def setup_ui()
    def open_eosfit_window()
    def cleanup()
```

### 窗口创建流程

1. 检查是否已存在 `eosfit_window`
2. 如果存在且可见，激活现有窗口
3. 如果不存在，创建新的 `QMainWindow`
4. 实例化 `InteractiveEoSGUI` 作为中心部件
5. 显示窗口并前置

### 集成位置

- 侧边栏位置：Dioptas 和 curvefit 之间
- 模块顺序：第 6 个主功能模块
- 工具类型：既是模块又可弹出独立工具窗口

## 与现有功能的关系

### 与 "📊 eosfit" 按钮的区别

主界面中现在有两个 EoSFit 相关的入口：

1. **"📐 EoSFit" (新增模块)**
   - 完整的模块界面，包含介绍和说明
   - 弹出独立窗口
   - 适合新用户了解功能后使用

2. **"📊 eosfit" (原有工具)**
   - 直接在主界面右侧嵌入 EoSFit GUI
   - 快速访问，不弹出新窗口
   - 适合熟悉用户快速使用

两者使用相同的 `InteractiveEoSGUI` 类，但展示方式不同。

## CrysFML EoS 方法

基于 CrysFML 的 EoSFit 模块，使用以下核心方法：

1. **F-f 线性化方法**
   - 将 Birch-Murnaghan 方程转换为线性形式
   - 防止 B₀' 参数发散
   - 提高拟合稳定性

2. **正则化约束**
   - 对 B₀' 施加软约束（默认值 4.0）
   - 用户可调节正则化强度
   - 平衡数据拟合和物理合理性

3. **多策略拟合**
   - 智能初始猜测
   - 多起点优化
   - 选择最佳拟合结果

## 依赖关系

- `PyQt6`: Qt GUI 框架
- `interactive_eos_gui.py`: EoSFit GUI 实现
- `crysfml_eos_module.py`: CrysFML EoS 核心算法
- `gui_base.py`: 基类和样式
- `theme_module.py`: 主题和组件

## 未来改进

1. 支持批量文件处理
2. 添加数据预览功能
3. 支持更多数据格式
4. 结果导出功能增强
5. 参数历史记录

## 注意事项

1. CSV 文件必须包含 `V_atomic` 和 `Pressure (GPa)` 列
2. 弹出窗口大小为 1480x900，建议屏幕分辨率 >= 1920x1080
3. 窗口关闭后数据不会自动保存，请在关闭前导出结果
4. 参数调整时实时更新图形，可能占用较多 CPU 资源

## 故障排除

### 问题：点击按钮没有反应
- 检查控制台是否有错误信息
- 确认 `interactive_eos_gui.py` 和 `crysfml_eos_module.py` 存在

### 问题：窗口显示异常
- 尝试关闭窗口后重新打开
- 检查屏幕分辨率是否足够

### 问题：拟合失败
- 检查数据格式是否正确
- 尝试不同的 EoS 模型
- 调整正则化强度参数

## 贡献者

集成日期：2025-12-01
基于 CrysFML eosfit 模块和 EosFit7-GUI 方法

## 参考文献

- Angel, R.J., Alvaro, M., and Gonzalez-Platas, J. (2014). "EosFit7c and a Fortran module (library) for equation of state calculations". Zeitschrift für Kristallographie - Crystalline Materials, 229(5), 405-419.
- CrysFML: https://gitlab.com/CrysFML
