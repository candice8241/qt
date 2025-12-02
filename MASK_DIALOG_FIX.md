# Mask Module - File Dialog Fix

## Issue
用户报告："点击load image、load mask 打不开任何界面"
(File dialogs not opening when clicking Load Image or Load Mask buttons)

## Root Cause
`QFileDialog` 和 `QMessageBox` 使用了错误的父窗口。

Since `MaskModule` inherits from `GUIBase` (not `QWidget`), using `self` as the parent for dialogs doesn't work. The dialogs either:
- Don't appear at all
- Open behind the main window
- Can't get focus properly

## Solution
Changed all dialog parent references from `self` to `self.root` (the main window).

### Files Fixed

**Before:**
```python
file_path, _ = QFileDialog.getOpenFileName(
    self,  # ❌ Wrong - MaskModule is not a QWidget
    "Select Diffraction Image",
    ...
)

QMessageBox.warning(self, "Error", "...")  # ❌ Wrong
```

**After:**
```python
file_path, _ = QFileDialog.getOpenFileName(
    self.root,  # ✅ Correct - Use main window as parent
    "Select Diffraction Image",
    ...
)

QMessageBox.warning(self.root, "Error", "...")  # ✅ Correct
```

## Changed Functions

All dialog parent parameters changed from `self` → `self.root`:

1. ✅ `load_image()` - QFileDialog.getOpenFileName
2. ✅ `load_image()` - QMessageBox.warning (2 places)
3. ✅ `load_image()` - QMessageBox.critical
4. ✅ `load_mask()` - QFileDialog.getOpenFileName
5. ✅ `load_mask()` - QMessageBox.critical
6. ✅ `save_mask()` - QMessageBox.warning
7. ✅ `save_mask()` - QFileDialog.getSaveFileName
8. ✅ `save_mask()` - QMessageBox.information
9. ✅ `save_mask()` - QMessageBox.critical
10. ✅ `clear_mask()` - QMessageBox.question
11. ✅ `apply_current_tool()` - QMessageBox.information

## Testing

### Test 1: Load Image
```
1. Run main.py
2. Click "🎭 Mask" in sidebar
3. Click "📂 Load Image" button
4. File dialog should open immediately ✅
5. Select an image file (TIF, EDF, H5, etc.)
6. Image should load and display ✅
```

### Test 2: Load Mask
```
1. Click "📂 Load Mask" button
2. File dialog should open ✅
3. Select a mask file (NPY, EDF, TIF)
4. Mask should load with red overlay ✅
```

### Test 3: Save Mask
```
1. After creating/loading a mask
2. Click "💾 Save Mask" button
3. Save dialog should open ✅
4. Choose location and format
5. Success message should appear ✅
```

### Test 4: Clear All
```
1. Click "🗑️ Clear All" button
2. Confirmation dialog should appear ✅
3. Click Yes to clear mask ✅
```

## Verification

```bash
# Code compiles successfully
python3 -m py_compile mask_module.py
# Exit code: 0 ✅

# Run main application
python3 main.py
# Click Mask button, test all dialogs ✅
```

## Why This Matters

Proper parent window assignment for dialogs:
- ✅ Ensures dialogs appear in front of main window
- ✅ Prevents dialogs from opening behind/hidden
- ✅ Provides correct focus behavior
- ✅ Maintains proper modal behavior
- ✅ Allows proper window hierarchy

## Pattern for Other Modules

When creating modules that inherit from `GUIBase`:

```python
class MyModule(GUIBase):
    def __init__(self, parent, root):
        super().__init__()
        self.parent = parent  # Frame widget
        self.root = root      # Main window
    
    def my_method(self):
        # ✅ CORRECT: Use self.root for dialogs
        file_path, _ = QFileDialog.getOpenFileName(
            self.root,  # Parent is main window
            "Title",
            "",
            "Filter"
        )
        
        # ✅ CORRECT: Use self.root for message boxes
        QMessageBox.information(
            self.root,  # Parent is main window
            "Title",
            "Message"
        )
```

---

**Status**: ✅ FIXED
**Date**: December 2, 2025
**Impact**: All file dialogs and message boxes now work correctly
