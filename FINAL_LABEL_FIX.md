# 堆叠图标签最终修正 / Final Stacked Plot Label Fix

## 日期 / Date: 2025-12-02 (最终版)

---

## ✅ 最终正确的实现 / Final Correct Implementation

### 问题追溯 / Issue History

**用户反馈：** 压力数值点仍然和曲线对不上

**根本原因：** 参考了错误的版本，应该使用 commit a548628 的实现

**Commit a548628:** "Fix label positioning to middle of curve"

---

## 🎯 正确的算法 / Correct Algorithm

### 标签应该在曲线的实际中点 / Label at Actual Middle of Curve

```python
# 计算曲线数据的最小值和最大值
min_intensity = np.min(data[:, 1])
max_intensity = np.max(data[:, 1])

# Y位置 = offset + 数据范围的中点
y_pos = y_offset + (min_intensity + max_intensity) / 2.0

# 垂直对齐方式：center（标签中心在该位置）
verticalalignment='center'
```

### 为什么这是正确的 / Why This Is Correct

**曲线绘制时：**
```python
plt.plot(data[:, 0], data[:, 1] + y_offset, ...)
```

**曲线的实际Y范围：**
```
Y_min = y_offset + min(data[:, 1])
Y_max = y_offset + max(data[:, 1])
Y_middle = y_offset + (min + max) / 2.0  ← 这是曲线的中点！
```

**标签位置：**
```
y_pos = Y_middle = y_offset + (min + max) / 2.0
```

**结果：** 标签精确地在曲线数据范围的中间！

---

## 📊 视觉示意 / Visual Illustration

```
Intensity
    ↑
    │         ╱╲              
    │        ╱  ╲        ← max (y_offset + max_intensity)
    │       ╱    ╲
    │      │      │
    │  →  │Label │      ← 中点 (y_offset + (min+max)/2)
    │      │here │
    │     ╱        ╲
    │    ╱__________╲   ← min (y_offset + min_intensity)
    │━━━━━━━━━━━━━━━━  ← 基线 (y_offset)
    │
    └──────────────────→ 2θ
```

---

## 🔧 最终修改的代码 / Final Modified Code

### 完整实现 / Complete Implementation

**radial_module.py & batch_integration.py (共4处):**

```python
# 绘制曲线
plt.plot(data[:, 0], data[:, 1] + y_offset,
        color=color, linewidth=1.2, label=label)

# 计算标签位置 - 曲线实际数据范围的中点
x_pos = data[0, 0] + (data[-1, 0] - data[0, 0]) * 0.02
min_intensity = np.min(data[:, 1])
max_intensity = np.max(data[:, 1])
y_pos = y_offset + (min_intensity + max_intensity) / 2.0

# 绘制标签 - 无背景框，粗体彩色
plt.text(x_pos, y_pos, label,
        fontsize=10, 
        verticalalignment='center',  # 标签中心在y_pos
        color=color,                   # 使用曲线颜色
        fontweight='bold')             # 粗体
```

---

## 📝 关键参数说明 / Key Parameters Explained

### 1. Y位置计算 / Y Position Calculation

```python
y_pos = y_offset + (min_intensity + max_intensity) / 2.0
```

**组成部分 / Components:**
- `y_offset`: 当前曲线的基线偏移（offset * index）
- `min_intensity`: 数据的最小值
- `max_intensity`: 数据的最大值
- `(min + max) / 2.0`: 数据范围的中点

**示例 / Example:**
```python
# 曲线1
y_offset = 0
min = 100, max = 5000
y_pos = 0 + (100 + 5000) / 2 = 2550

# 曲线2
y_offset = 6000
min = 100, max = 4500
y_pos = 6000 + (100 + 4500) / 2 = 8300

# 曲线3
y_offset = 12000
min = 100, max = 4800
y_pos = 12000 + (100 + 4800) / 2 = 14450
```

### 2. 垂直对齐 / Vertical Alignment

```python
verticalalignment='center'
```

**含义 / Meaning:**
- 标签的**中心**对齐到 y_pos
- 标签向上下两侧延伸
- 正好在曲线中间

**对比其他方式：**
```
'top':    标签顶部在y_pos，向下延伸
'center': 标签中心在y_pos，上下延伸  ← 我们使用这个
'bottom': 标签底部在y_pos，向上延伸
```

### 3. 其他样式参数 / Other Style Parameters

```python
fontsize=10              # 字体大小（比原来的9pt略大）
color=color              # 使用曲线颜色（视觉统一）
fontweight='bold'        # 粗体（增强可读性）
# 无 bbox 参数           # 无背景框（简洁清爽）
```

---

## 🔄 随Offset的对齐 / Alignment with Offset

### 关键：y_pos包含y_offset项 / Key: y_pos Contains y_offset

```python
y_pos = y_offset + (min + max) / 2.0
```

**当offset变化时：**

```
Offset = 1000:
曲线1: y_offset=0,    y_pos = 0 + 2550 = 2550
曲线2: y_offset=1000, y_pos = 1000 + 2300 = 3300
曲线3: y_offset=2000, y_pos = 2000 + 2450 = 4450

Offset = 1500:
曲线1: y_offset=0,    y_pos = 0 + 2550 = 2550
曲线2: y_offset=1500, y_pos = 1500 + 2300 = 3800
曲线3: y_offset=3000, y_pos = 3000 + 2450 = 5450
```

**结果：** 标签自动随曲线移动，始终在曲线中点！

---

## ✨ 最终效果总结 / Final Effect Summary

### 保留的优化 / Kept Optimizations

✅ **无背景框** - 移除了bbox参数
✅ **粗体字** - fontweight='bold'
✅ **曲线颜色** - color=color
✅ **字体10pt** - 比原来的9pt略大

### 修正的关键点 / Corrected Key Points

✅ **Y位置** - 使用 `(min + max) / 2` 而不是 `max * 0.3`
✅ **对齐方式** - 使用 `center` 而不是 `bottom`
✅ **参考版本** - 使用 commit a548628 的实现

---

## 🧮 数学验证 / Mathematical Verification

### 假设数据 / Sample Data

**曲线数据范围：**
```python
data[:, 1] = [100, 500, 2000, 5000, 3000, 800, 200]
min = 100
max = 5000
中点 = (100 + 5000) / 2 = 2550
```

**堆叠偏移：**
```python
曲线1: y_offset = 0
曲线2: y_offset = 6000
曲线3: y_offset = 12000
```

**标签位置：**
```python
标签1: y_pos = 0 + 2550 = 2550
标签2: y_pos = 6000 + 2550 = 8550
标签3: y_pos = 12000 + 2550 = 14550
```

**曲线范围：**
```python
曲线1: [0+100, 0+5000] = [100, 5000]       → 标签在2550 ✓
曲线2: [6000+100, 6000+5000] = [6100, 11000] → 标签在8550 ✓
曲线3: [12000+100, 12000+5000] = [12100, 17000] → 标签在14550 ✓
```

**结论：** 标签精确地在每条曲线的中间！

---

## 📚 Git历史参考 / Git History Reference

### 关键Commits / Key Commits

1. **a548628** - "Fix label positioning to middle of curve"
   - 这是正确的实现
   - 使用曲线中点算法

2. **4c4e7ec^** - 原始tkinter版本
   - 使用 `y_offset + max * 0.3`
   - 不是最终正确版本

3. **4578720** - 尝试使用基线+30%
   - 不正确，已废弃

4. **本次修改** - 最终修正
   - 回到 a548628 的中点算法
   - 保留无背景框优化

---

## 🎉 修改完成 / Modification Complete

### 修改的文件 / Modified Files

**2个文件，4个方法：**
1. `radial_module.py`
   - `_create_single_pressure_stacked_plot()` ✅
   - `_create_all_pressure_stacked_plot()` ✅

2. `batch_integration.py`
   - `_create_single_pressure_stacked_plot()` ✅
   - `_create_all_pressure_stacked_plot()` ✅

### 代码统计 / Code Statistics

**每处修改：**
```python
# 增加3行（min/max计算）
min_intensity = np.min(data[:, 1])
max_intensity = np.max(data[:, 1])
y_pos = y_offset + (min_intensity + max_intensity) / 2.0

# 修改1行（对齐方式）
verticalalignment='center'  # 原来是'bottom'

# 保持不变
color=color, fontweight='bold'  # 无背景框
```

---

## ✅ 最终验证 / Final Verification

### 预期效果 / Expected Effect

**标签位置：**
- ✅ 在曲线数据范围的中点
- ✅ 随offset变化自动调整
- ✅ 视觉上与曲线对齐

**标签样式：**
- ✅ 无背景框，简洁
- ✅ 粗体彩色文字，清晰
- ✅ 字体10pt，易读

**用户体验：**
- ✅ 压力数值与曲线精确对齐
- ✅ 不遮挡数据峰
- ✅ 视觉效果专业

---

## 📞 技术支持 / Technical Support

### 参考文档 / Reference Documents

1. **本文档** - FINAL_LABEL_FIX.md
2. **Git Commit** - a548628 "Fix label positioning to middle of curve"
3. **代码文件** - radial_module.py, batch_integration.py

### 关键代码位置 / Key Code Locations

- radial_module.py: 约第1650行, 第1740行
- batch_integration.py: 约第570行, 第680行

---

**版本 / Version:** 1.4.0 (最终版)  
**日期 / Date:** 2025-12-02  
**状态 / Status:** ✅ 最终修正完成  
**参考 / Reference:** Commit a548628

---

**🎯 标签现在精确对齐到曲线中点！**  
**Labels Now Precisely Aligned to Curve Middle!**

**这是最终正确的实现！/ This Is the Final Correct Implementation!**
