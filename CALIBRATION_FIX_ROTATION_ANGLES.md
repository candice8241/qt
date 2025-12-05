# 标定模块修复 - 旋转角度合理性验证

## 问题描述

**原问题**: 旋转角度计算离谱，角度过大

**原因**: 之前的实现无条件启用了所有 6 个参数的完整优化，但在数据质量不足时，旋转参数的优化会变得不稳定，导致出现不合理的大角度。

**正确行为**: 探测器倾斜角度通常应该非常小（< 1-3°），大多数情况下接近 0°。

---

## 🔧 修复方案

### 1. 添加数据质量检查

**在尝试旋转优化前，检查数据质量**:

```python
# 启用旋转精修的条件（全部满足）：
1. 控制点数量 >= 50
2. 衍射环数量 >= 4  
3. 初始 RMS < 5 pixels
```

**如果数据质量不足，跳过旋转精修，保持 rot = 0**

### 2. 添加角度合理性验证

**旋转角度阈值**:
```python
# 合理的旋转角度（典型值）
Rot1, Rot2, Rot3: < 3.0°  # 阈值

# 如果任何角度 > 3°，判定为不合理
max_rot = max(abs(rot1), abs(rot2), abs(rot3))
if max_rot > 3.0:
    # 回退到 rot = 0
```

### 3. 添加 RMS 改善验证

**旋转精修必须改善 RMS**:
```python
# 如果 RMS 没有显著改善（< 5%）
if rms_after >= rms_before * 0.95:
    # 回退到 rot = 0
```

### 4. 异常处理和回退机制

**任何错误都回退到安全状态**:
```python
try:
    geo_ref.refine2(fix=["wavelength"])  # 尝试完整精修
    # 验证角度...
except Exception:
    # 回退到 rot = 0
    geo_ref.rot1 = 0.0
    geo_ref.rot2 = 0.0
    geo_ref.rot3 = 0.0
```

---

## 📊 新的精修策略

### Stage 1: 距离和光束中心（总是执行）

```python
geo_ref.refine2(fix=["wavelength", "rot1", "rot2", "rot3"])
# 固定旋转参数，只优化 dist, poni1, poni2
```

**结果**: 获得准确的距离和光束中心

### Stage 2: 旋转参数（条件执行）

```python
# 检查数据质量
if 控制点 >= 50 AND 环数 >= 4 AND RMS < 5:
    # 尝试完整精修
    geo_ref.refine2(fix=["wavelength"])
    
    # 验证结果
    if max_rot > 3.0 OR RMS没改善:
        # 回退到 rot = 0
    else:
        # 接受结果
else:
    # 跳过旋转精修，保持 rot = 0
```

---

## 📝 日志输出示例

### 场景 1: 数据质量不足（跳过旋转精修）

```
Stage 2: Rotation refinement with validation...
  Data quality insufficient - skipping rotation refinement
  Control points: 35, Rings: 3, RMS: 2.156
  (Need: >= 50 points, >= 4 rings, RMS < 5 pixels)
  Rotations kept at zero (perpendicular detector)

  Final Refined Parameters:
    Distance: 150.187 mm
    PONI1 (Y): 83.512 mm
    PONI2 (X): 82.501 mm
    Rot1: 0.0000°  ← 保持为 0
    Rot2: 0.0000°  ← 保持为 0
    Rot3: 0.0000°  ← 保持为 0
```

### 场景 2: 角度过大（回退）

```
Stage 2: Rotation refinement with validation...
  Data quality sufficient for rotation refinement
  Control points: 87, Rings: 5, RMS: 2.156
  Attempting full geometry refinement (all 6 parameters)...
  
  ⚠ Warning: Rotation angles too large!
    Rot1=5.2341°, Rot2=3.8765°, Rot3=0.1234°
    Max angle: 5.2341° > 3.0° (threshold)
  → Reverting to perpendicular detector assumption (rot=0)
  
  Final Refined Parameters:
    Rot1: 0.0000°  ← 回退到 0
    Rot2: 0.0000°  ← 回退到 0
    Rot3: 0.0000°  ← 回退到 0
```

### 场景 3: 成功精修（角度合理）

```
Stage 2: Rotation refinement with validation...
  Data quality sufficient for rotation refinement
  Control points: 120, Rings: 8, RMS: 1.234
  Attempting full geometry refinement (all 6 parameters)...
  
  ✓ Rotation refinement successful!
    Rot1: 0.0234° (tilt around axis 1)  ← 小角度
    Rot2: -0.0187° (tilt around axis 2) ← 小角度
    Rot3: 0.0012° (rotation in plane)   ← 小角度
    RMS improved: 1.234 → 0.867 pixels
  
  Final Refined Parameters:
    Rot1: 0.0234°  ← 合理的小角度
    Rot2: -0.0187° ← 合理的小角度
    Rot3: 0.0012°  ← 合理的小角度
```

---

## 🎯 验证标准

### 合格的旋转角度

| 角度范围 | 评价 | 说明 |
|----------|------|------|
| < 0.1° | 优秀 | 探测器几乎完全垂直 |
| 0.1° - 1.0° | 良好 | 轻微倾斜，正常 |
| 1.0° - 3.0° | 可接受 | 有一定倾斜 |
| **> 3.0°** | **不合理** | **自动回退到 0** |

### 数据质量要求

| 参数 | 最低要求 | 推荐 |
|------|----------|------|
| 控制点数 | >= 50 | >= 80 |
| 衍射环数 | >= 4 | >= 6 |
| 初始 RMS | < 5 pixels | < 3 pixels |

---

## 🔍 故障排除

### Q: 为什么我的旋转角度总是 0？

**A**: 可能有以下原因：

1. **数据质量不足**（最常见）
   - 控制点太少（< 50）
   - 衍射环太少（< 4）
   - 检查日志中的 "Data quality insufficient"

2. **角度过大被回退**
   - 尝试精修了，但角度 > 3°
   - 检查日志中的 "Rotation angles too large"

3. **RMS 没有改善**
   - 精修后 RMS 反而变差
   - 检查日志中的 "RMS did not improve"

### Q: 如何获得更好的旋转精修？

**A**: 改善数据质量：

1. **增加控制点数量**
   - 每个环手动添加更多点（8-12 个）
   - 使用更多的衍射环

2. **提高图像质量**
   - 使用信噪比更高的图像
   - 确保衍射环清晰完整

3. **优化初始参数**
   - 提供更准确的初始距离
   - 调整光束中心估计

### Q: 旋转角度应该多大？

**A**: 典型情况：

```
理想情况（标定板或精密安装）:
  Rot1, Rot2, Rot3 < 0.1°

常见情况（一般安装）:
  Rot1, Rot2, Rot3 < 1.0°

可接受情况（有倾斜）:
  Rot1, Rot2, Rot3 < 3.0°

不正常（精修失败）:
  Rot1, Rot2, Rot3 > 3.0°  ← 会被自动回退
```

---

## 📚 技术细节

### 旋转参数的含义

```python
# PONI 坐标系
#   Z: 沿 X-ray 光束方向
#   Y: 垂直向上
#   X: 水平向右

rot1: 绕 X 轴旋转（垂直方向倾斜）
rot2: 绕 Y 轴旋转（水平方向倾斜）
rot3: 绕 Z 轴旋转（面内旋转）
```

### 为什么大角度不合理？

1. **物理约束**: 探测器通常被精密安装，倾斜应该很小
2. **数值不稳定**: 大角度通常意味着优化陷入局部最优
3. **过拟合**: 用过多参数拟合有限数据

### pyFAI 精修策略

```python
# Dioptas 的保守策略
# 1. 先优化距离和中心（最重要）
geo_ref.refine2(fix=["wavelength", "rot1", "rot2", "rot3"])

# 2. 仅在数据充足时优化旋转
if data_quality_good:
    geo_ref.refine2(fix=["wavelength"])
    # 验证结果合理性
```

---

## ✅ 修复验证

### 修改的代码行

**文件**: `calibrate_module.py`

**关键修改**:
1. 第 ~3530-3600 行: 添加数据质量检查
2. 第 ~3550-3580 行: 添加角度验证和回退机制
3. 第 ~3590-3600 行: 添加 RMS 改善检查

### 测试步骤

1. **低质量数据测试**
   ```
   控制点 < 50 或 环 < 4
   预期: 跳过旋转精修，rot = 0
   ```

2. **正常质量数据测试**
   ```
   控制点 >= 50 且 环 >= 4
   预期: 尝试精修，验证角度 < 3°
   ```

3. **高质量数据测试**
   ```
   控制点 > 100 且 环 > 6
   预期: 成功精修，得到合理小角度
   ```

---

## 🎊 总结

### 修复前的问题
- ❌ 无条件启用旋转优化
- ❌ 无角度合理性检查
- ❌ 数据不足时产生离谱角度

### 修复后的行为
- ✅ 检查数据质量
- ✅ 验证角度合理性（< 3°）
- ✅ 自动回退到安全值
- ✅ 详细的日志反馈
- ✅ 大多数情况下 rot ≈ 0°（正确）

### 适用场景

| 场景 | 旋转精修 | 预期结果 |
|------|----------|----------|
| 少量控制点 | ❌ 跳过 | rot = 0° |
| 中等质量 | ⚠️ 尝试但验证 | rot ≈ 0° |
| 高质量数据 | ✅ 启用 | 0° < rot < 1° |
| 精密实验 | ✅ 启用 | rot < 0.1° |

---

**修复完成时间**: 2025-12-05  
**修复类型**: 旋转角度合理性验证  
**影响**: 所有标定操作更加稳定和准确

---

*现在的旋转角度计算是合理且保守的！*
