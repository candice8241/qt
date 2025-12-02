# 堆叠图标签对齐修正 - 简要说明
# Stacked Plot Label Alignment Correction - Brief Summary

## ✅ 问题已修正 / Issue Corrected

根据batch_integration.py的原始tkinter版本，已修正标签对齐算法。

According to the original tkinter version of batch_integration.py, the label alignment algorithm has been corrected.

---

## 🎯 核心修改 / Core Changes

### 修改前（错误）/ Before (Incorrect)
```python
# 标签在曲线数据中点
y_pos = y_offset + (min_intensity + max_intensity) / 2.0
verticalalignment='center'
```

### 修改后（正确）/ After (Correct)
```python
# 标签在基线上方30%最大值处
y_pos = y_offset + np.max(data[:, 1]) * 0.3
verticalalignment='bottom'
```

---

## 📊 视觉效果 / Visual Effect

### 正确的标签位置 / Correct Label Position

```
Intensity
    ↑
    │     ╱╲              
    │    ╱  ╲  ← 曲线峰值 (不被遮挡)
    │   ╱    ╲
    │  ╱      ╲
    │ ╱        ╲
    │╱__________╲
    │ 10.5 GPa      ← 标签在这里 (y_offset + max*0.3)
    │                  标签底部对齐，文字向上
    │━━━━━━━━━━━━━   ← 基线 (y_offset)
    │
    └─────────────────→ 2θ
```

---

## 🔧 修改的文件 / Modified Files

✅ `radial_module.py` (2处)
- `_create_single_pressure_stacked_plot()`
- `_create_all_pressure_stacked_plot()`

✅ `batch_integration.py` (2处)
- `_create_single_pressure_stacked_plot()`
- `_create_all_pressure_stacked_plot()`

---

## 📝 关键变化 / Key Changes

| 参数 | 修改前 | 修改后 |
|------|--------|--------|
| Y位置 | `y_offset + (min+max)/2` | `y_offset + max*0.3` |
| 对齐方式 | `verticalalignment='center'` | `verticalalignment='bottom'` |
| 背景框 | 无 (已移除) | 无 (保持) |
| 字体 | 10pt粗体彩色 | 10pt粗体彩色 (保持) |

---

## ✨ 效果说明 / Effect Description

### 标签位置特点 / Label Position Features

1. **固定比例 / Fixed Ratio:**
   - 标签在基线上方30%最大值的位置
   - 不会遮挡数据峰

2. **随offset调整 / Adjusts with Offset:**
   ```python
   曲线1: y_pos = 0 + max*0.3
   曲线2: y_pos = 1000 + max*0.3
   曲线3: y_pos = 2000 + max*0.3
   ```

3. **视觉对齐 / Visual Alignment:**
   - 标签底部在计算位置
   - 文字向上延伸
   - 不侵入基线以下区域

---

## 🎉 修正完成 / Correction Complete

**状态 / Status:** ✅ 已完成并验证

**效果 / Effect:** 标签现在正确对齐到曲线基线上方，随offset自动调整！

**Result:** Labels now correctly aligned above curve baseline, automatically adjusting with offset!

---

**日期 / Date:** 2025-12-02  
**版本 / Version:** 1.3.0  
**参考 / Reference:** 原始tkinter版本实现
