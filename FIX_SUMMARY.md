# 修复说明 / Fix Summary

## 问题描述 / Issue Description

**中文：**
在使用"浏览"按钮选择H5文件时，积分功能只处理选中的单个H5文件，而不是遍历整个文件夹中的所有H5文件。

**English:**
When using the "Browse" button to select an H5 file, the integration feature only processes the selected single H5 file instead of traversing all H5 files in the folder.

## 修复方案 / Solution

### 修改的文件 / Modified Files:
1. `radial_module.py` - Azimuthal Integration Module
2. `powder_module.py` - Powder XRD Module

### 修改内容 / Changes Made:

在 `browse_file()` 方法中添加了智能检测逻辑：
- 当用户通过"浏览"按钮选择一个H5文件时
- 程序会自动提取该文件所在的目录
- 将输入模式设置为该目录下所有H5文件的递归搜索模式（`directory/**/*.h5`）
- 在日志中显示提示信息，告知用户将处理整个目录

Added intelligent detection logic in the `browse_file()` method:
- When a user selects an H5 file through the "Browse" button
- The program automatically extracts the directory containing that file
- Sets the input pattern to recursively search for all H5 files in that directory (`directory/**/*.h5`)
- Shows log messages informing the user that all files in the directory will be processed

### 代码变更 / Code Changes:

**修改前 / Before:**
```python
def browse_file(self, entry):
    """Browse for a file"""
    filename, _ = QFileDialog.getOpenFileName(...)
    if filename:
        entry.setText(filename)  # 只设置单个文件
```

**修改后 / After:**
```python
def browse_file(self, entry):
    """Browse for a file"""
    filename, _ = QFileDialog.getOpenFileName(...)
    if filename:
        # 如果是H5文件，自动设置为处理整个目录
        if filename.lower().endswith('.h5'):
            directory = os.path.dirname(filename)
            pattern = os.path.join(directory, '**', '*.h5')
            entry.setText(pattern)
            self.log(f"Selected h5 file: {os.path.basename(filename)}")
            self.log(f"Will process all h5 files in: {directory}")
        else:
            entry.setText(filename)
```

## 使用方法 / Usage

### 方式1：使用浏览按钮 / Method 1: Using Browse Button
1. 点击"Input .h5 File"旁的"浏览"按钮
2. 在文件选择对话框中选择目录中的任意一个H5文件
3. 程序会自动设置为处理该目录下的所有H5文件（递归搜索）
4. 日志区域会显示：
   - "Selected h5 file: [文件名]"
   - "Will process all h5 files in: [目录路径]"

1. Click the "Browse" button next to "Input .h5 File"
2. Select any H5 file in the directory from the file selection dialog
3. The program will automatically set it to process all H5 files in that directory (recursive search)
4. The log area will show:
   - "Selected h5 file: [filename]"
   - "Will process all h5 files in: [directory path]"

### 方式2：手动输入模式 / Method 2: Manual Input Pattern
您仍然可以手动输入以下模式：
- 目录路径: `/path/to/folder`
- 通配符模式: `/path/to/folder/*.h5`
- 递归模式: `/path/to/folder/**/*.h5`

You can still manually input these patterns:
- Directory path: `/path/to/folder`
- Wildcard pattern: `/path/to/folder/*.h5`
- Recursive pattern: `/path/to/folder/**/*.h5`

## 兼容性 / Compatibility

✅ 向后兼容 / Backward compatible
- 原有的手动输入功能保持不变
- 非H5文件的浏览行为不受影响
- 现有的批处理逻辑完全兼容

✅ Backward compatible
- Existing manual input functionality remains unchanged
- Browsing behavior for non-H5 files is unaffected
- Existing batch processing logic is fully compatible

## 测试建议 / Testing Recommendations

1. **基础测试 / Basic Test:**
   - 在包含多个H5文件的目录中选择一个文件
   - 验证所有文件都被处理

2. **递归测试 / Recursive Test:**
   - 在包含子目录的目录中选择一个H5文件
   - 验证子目录中的H5文件也被处理

3. **兼容性测试 / Compatibility Test:**
   - 手动输入目录路径
   - 手动输入通配符模式
   - 验证两种方式都能正常工作

## 技术细节 / Technical Details

### 文件搜索机制 / File Search Mechanism

程序使用多级回退搜索机制（在 `_do_integration()` 方法中）:

The program uses a multi-level fallback search mechanism (in the `_do_integration()` method):

1. **Method 1**: 直接使用glob与recursive=True / Direct glob with recursive=True
2. **Method 2**: 如果是目录，使用 `directory/**/*.h5`
3. **Method 3**: 如果包含 `*.h5` 但没有 `**`，转换为递归模式
4. **Method 4**: 清理路径后重试
5. **Method 5**: 尝试父目录

这确保了在各种输入情况下都能找到文件。

This ensures files can be found in various input scenarios.

## 注意事项 / Notes

⚠️ **重要 / Important:**
- 递归搜索会包含所有子目录中的H5文件
- 对于大型目录结构，搜索可能需要一些时间
- 请确保目录中的所有H5文件都是您想要处理的

⚠️ **Important:**
- Recursive search includes H5 files in all subdirectories
- For large directory structures, searching may take some time
- Ensure all H5 files in the directory are ones you want to process

## 版本信息 / Version Info

- 修复日期 / Fix Date: 2025-12-02
- 影响模块 / Affected Modules: 
  - Radial Integration Module (radial_module.py)
  - Powder XRD Module (powder_module.py)
- 状态 / Status: ✅ 已完成测试 / Completed Testing
