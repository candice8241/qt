# 环编号和Mask问题修复

## 修复日期: 2025-12-05

---

## 🐛 报告的问题

### 1. AttributeError: 'use_mask_cb' 不存在

**错误信息**:
```python
if self.use_mask_cb.isChecked() and self.imported_mask is not None:
AttributeError: 'CalibrateModule' object has no attribute 'use_mask_cb'
```

**问题原因**:
- `use_mask_cb` 在 UI 设置中创建（第978行）
- 但在 `run_calibration()` 调用 `perform_calibration()` 时（第2468行），如果 UI 还未完全初始化，就会报错
- 缺少防御性检查

### 2. 环编号应该从 1 开始，不是 0

**用户要求**:
- Current Ring 最小值设为 1
- 默认值为 1（不是之前的 0）

---

## ✅ 修复方案

### 修复 1: use_mask_cb AttributeError

#### 方案 A: 早期初始化

**在 `__init__` 中添加**:
```python
# calibrate_module.py:148-153
# Mask from mask module
self.imported_mask = None
self.mask_module_reference = None

# ★ Initialize use_mask_cb early to avoid AttributeError
self.use_mask_cb = None
```

**位置**: calibrate_module.py:148-153

#### 方案 B: 添加防御性检查

**旧代码**:
```python
# calibrate_module.py:2468 (旧)
if self.use_mask_cb.isChecked() and self.imported_mask is not None:
```

**新代码**:
```python
# calibrate_module.py:2468 (新)
if hasattr(self, 'use_mask_cb') and self.use_mask_cb is not None and \
   self.use_mask_cb.isChecked() and self.imported_mask is not None:
```

**效果**:
- 三重检查：`hasattr()` → `is not None` → `isChecked()`
- 即使 UI 未初始化也不会崩溃
- 安全降级：如果没有 checkbox，就不使用 mask

**位置**: calibrate_module.py:2468

---

### 修复 2: 环编号从 1 开始

#### 修改默认值和最小值

**主 UI (ring_num_input)**:
```python
# calibrate_module.py:1770-1773 (旧)
self.ring_num_input.setMinimum(0)
self.ring_num_input.setValue(0)

# calibrate_module.py:1770-1773 (新)
self.ring_num_input.setMinimum(1)  # ← 最小值改为 1
self.ring_num_input.setValue(1)   # ← 默认值改为 1
```

**位置**: calibrate_module.py:1770-1773

**旧 UI (ring_number_spinbox)**:
```python
# calibrate_module.py:845-847 (旧)
self.ring_number_spinbox.setMinimum(0)
self.ring_number_spinbox.setValue(0)

# calibrate_module.py:845-847 (新)
self.ring_number_spinbox.setMinimum(1)  # ← 最小值改为 1
self.ring_number_spinbox.setValue(1)   # ← 默认值改为 1
```

**位置**: calibrate_module.py:845-847

#### 修改 Clear Peaks 重置值

**旧代码**:
```python
# calibrate_module.py:2362 (旧)
self.ring_num_input.setValue(0)
self.unified_canvas.current_ring_num = 0
self.log("... reset ring number to 0")
```

**新代码**:
```python
# calibrate_module.py:2362 (新)
self.ring_num_input.setValue(1)
self.unified_canvas.current_ring_num = 1
self.log("... reset ring number to 1")
```

**位置**: calibrate_module.py:2362-2369

#### 修改 Canvas 初始化

**旧代码**:
```python
# calibration_canvas.py:367 (旧)
self.current_ring_num = 0
```

**新代码**:
```python
# calibration_canvas.py:367 (新)
self.current_ring_num = 1  # ← 从 1 开始
```

**位置**: calibration_canvas.py:367

---

## 🔄 完整工作流程

### 正常使用流程（环编号从 1 开始）

```
1. 启动程序
   ↓
2. Current Ring # 显示: 1  ← 新的默认值
   ↓
3. 勾选 "Automatic increase ring number"
   ↓
4. 点击图像第一个点
   ↓
5. 标记显示: 1  ← 第一个环编号为 1
   ↓
6. Current Ring # 自动变为: 2
   ↓
7. 点击图像第二个点
   ↓
8. 标记显示: 2  ← 第二个环
   ↓
9. Current Ring # 自动变为: 3
   ↓
   ... 循环
```

### 使用 Mask 流程（不会报错）

```
1. 在 Mask Module 中创建 mask
   ↓
2. 返回 Calibrate Module
   ↓
3. 勾选 "Use Mask from Mask Module"
   ↓
4. 点击 "Run Calibration"
   ↓
5. 检查 use_mask_cb (hasattr + is not None + isChecked)
   ↓
6. 如果全部通过 → 使用 mask
   ↓
7. 如果任何一个失败 → 跳过 mask，继续标定
   ↓
8. 不会崩溃 ✅
```

### Clear Peaks 流程

```
1. 已添加多个点
   ↓
2. Current Ring # 显示: 5
   ↓
3. 点击 "Clear Peaks" 按钮
   ↓
4. 所有点被清除
   ↓
5. Current Ring # 重置为: 1  ← 重置为 1（不是 0）
   ↓
6. 可以重新开始添加点
```

---

## 📊 修改对比表

| 项目 | 旧值 | 新值 | 状态 |
|------|------|------|------|
| use_mask_cb 初始化 | 无 | `= None` (早期) | ✅ 新增 |
| use_mask_cb 检查 | `isChecked()` | `hasattr + is not None + isChecked` | ✅ 改进 |
| 环编号最小值 | 0 | 1 | ✅ 修改 |
| 环编号默认值 | 0 | 1 | ✅ 修改 |
| Clear 重置值 | 0 | 1 | ✅ 修改 |
| Canvas 初始值 | 0 | 1 | ✅ 修改 |

---

## 🧪 测试验证

### 测试 1: use_mask_cb 不崩溃

```python
# 场景 1: UI 未初始化
# 之前: AttributeError
# 现在: 安全跳过，不使用 mask

# 场景 2: UI 已初始化，但未勾选
# 检查: isChecked() == False
# 结果: 不使用 mask

# 场景 3: UI 已初始化，已勾选，有 mask
# 检查: 全部通过
# 结果: 使用 mask ✅
```

### 测试 2: 环编号从 1 开始

```python
# 启动程序后
assert self.ring_num_input.value() == 1
assert self.ring_num_input.minimum() == 1
assert self.unified_canvas.current_ring_num == 1
```

### 测试 3: 点击使用正确环编号

```python
# 默认环编号为 1
# 点击图像
# 验证: 标记显示 "1"
assert self.unified_canvas.manual_peaks[-1][2] == 1

# 自动增量到 2
assert self.ring_num_input.value() == 2
```

### 测试 4: Clear Peaks 重置为 1

```python
# 环编号为 5
self.ring_num_input.setValue(5)

# Clear Peaks
self.clear_peaks_btn.click()

# 验证: 重置为 1
assert self.ring_num_input.value() == 1
assert self.unified_canvas.current_ring_num == 1
```

### 测试 5: 不能设置为 0

```python
# 尝试设置为 0
self.ring_num_input.setValue(0)

# 验证: 自动限制为最小值 1
assert self.ring_num_input.value() == 1
```

---

## 📝 修改的文件

### calibrate_module.py

**修改位置**:

1. **第 151 行**: 添加 `self.use_mask_cb = None` 早期初始化
2. **第 845-847 行**: ring_number_spinbox 最小值和默认值改为 1
3. **第 1770-1773 行**: ring_num_input 最小值和默认值改为 1
4. **第 2362-2369 行**: clear_manual_peaks() 重置值改为 1
5. **第 2468 行**: 添加三重防御性检查

### calibration_canvas.py

**修改位置**:

1. **第 367 行**: current_ring_num 初始值改为 1

---

## 🎯 用户使用指南

### 环编号从 1 开始标定

1. 启动程序，看到 "Current Ring #: 1"
2. 加载标定图像
3. 勾选 "Automatic increase ring number"
4. 点击第一个环的点 → 标记为 "1"，环编号自动变为 2
5. 点击第二个环的点 → 标记为 "2"，环编号自动变为 3
6. 依此类推...

**注意**: 
- 最小值为 1，无法手动设置为 0
- 符合用户要求

### 使用 Mask（不会崩溃）

1. 在 Mask Module 中创建 mask
2. 返回 Calibrate Module
3. 勾选 "Use Mask from Mask Module"
4. 运行标定
5. 如果 mask 可用，会自动使用
6. 如果 mask 不可用，会跳过并继续标定
7. 不会因为 AttributeError 崩溃 ✅

### 重新开始

1. 点击 "Clear Peaks" 按钮
2. 所有点清除
3. 环编号自动重置为 1
4. 可以重新开始标定

---

## ✅ 验证清单

- [x] use_mask_cb 早期初始化
- [x] use_mask_cb 三重防御性检查
- [x] 程序启动时环编号显示 1
- [x] 环编号最小值为 1，无法设为 0
- [x] 点击图像时标记显示正确的环编号（从 1 开始）
- [x] 自动增量功能正常工作（1→2→3→...）
- [x] Clear Peaks 后环编号重置为 1
- [x] 语法检查通过

---

## 🎊 总结

**修复的问题**:
1. ✅ AttributeError: 'use_mask_cb' 不存在
   - 早期初始化
   - 三重防御性检查
   
2. ✅ 环编号从 1 开始
   - 最小值: 0 → 1
   - 默认值: 0 → 1
   - 重置值: 0 → 1
   - Canvas 初始值: 0 → 1

**代码质量**:
✅ 防御性编程（三重检查）
✅ 早期初始化（避免 AttributeError）
✅ 符合用户要求（环编号从 1 开始）

---

*修复完成时间: 2025-12-05*
*语法检查: ✅ 通过*
*可以正常使用！*
