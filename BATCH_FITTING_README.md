# Batch Peak Fitting 功能说明

## 概述
已在 curvefit 模块中添加了批量峰拟合功能的完整UI界面。

## 修改的文件

### 1. `interactive_fitting_gui.py`
- 修改了 `show_batch_info()` 函数
- 从显示简单提示信息改为打开完整的批量拟合对话框

### 2. `batch_fitting_dialog.py` (新建)
完整的批量拟合对话框，包含以下功能：

#### 主要特性：
- **文件夹选择**：浏览并选择包含 .xy 文件的输入文件夹
- **拟合方法选择**：支持 Pseudo-Voigt 和 Voigt 两种拟合方法
- **实时日志**：显示处理进度和详细信息
- **后台处理**：使用 QThread 在后台运行，避免UI冻结
- **结果自动保存**：结果保存在 `fit_output` 子文件夹中

#### UI组件：
1. **输入设置区域**
   - 输入文件夹路径输入框和浏览按钮
   - 拟合方法下拉选择框（Pseudo-Voigt/Voigt）

2. **处理日志区域**
   - 实时显示处理进度
   - 显示找到的文件数量
   - 显示处理成功/失败信息

3. **操作按钮**
   - "Run Batch Fitting" 按钮：开始批量处理
   - "Close" 按钮：关闭对话框

## 使用方法

1. 在 curvefit 模块中点击 "Batch" 按钮
2. 在弹出的对话框中点击 "Browse" 选择包含 .xy 文件的文件夹
3. 选择拟合方法（Pseudo-Voigt 或 Voigt）
4. 点击 "🚀 Run Batch Fitting" 开始处理
5. 查看日志区域了解处理进度
6. 处理完成后，结果将保存在 `{输入文件夹}/fit_output/` 目录下

## 输出文件

批量拟合会生成以下文件：
- `{filename}_fit.png`：每个文件的拟合结果图
- `{filename}_results.csv`：每个文件的拟合参数
- `all_results.csv`：所有文件的汇总结果

## 技术细节

### BatchFittingWorker (QThread)
- 在后台线程运行批量拟合
- 通过信号传递日志信息和完成状态
- 捕获并报告错误

### BatchFittingDialog (QDialog)
- 现代化的UI设计
- 完整的输入验证
- 实时日志显示
- 错误处理和用户提示

## 依赖
- PyQt6
- peak_fitting.py 中的 BatchFitter 类
- 其他标准库（os, sys, traceback）

## 注意事项
- 只处理 .xy 格式的文件
- 需要确保输入文件夹中有有效的 .xy 文件
- 处理过程中请勿关闭对话框
- 处理完成后会显示成功/失败消息
