# Calibration Module Testing Guide

## 测试更新后的 Dioptas 风格标定功能

### 测试目标

验证以下新功能：
1. ✅ 完整几何精修（6 参数优化）
2. ✅ Rot 参数修正
3. ✅ 理论环叠加显示
4. ✅ 实时标定可视化

---

## 快速测试步骤

### 1. 启动应用

```bash
cd /workspace
python3 main.py
```

### 2. 进入标定模块

- 在主界面选择 "Calibration" 标签

### 3. 准备测试数据

**需要**:
- 标定图像（CeO₂, LaB₆ 等标准样品的衍射图像）
- 波长/能量信息
- 探测器参数（像素尺寸）

**测试图像建议**:
- 格式: `.tif`, `.cbf`, `.edf`
- 至少 3-5 个完整的衍射环
- 良好的信噪比

### 4. 执行标定

#### Step 1: 加载图像
```
1. 点击 "Load Image" 按钮
2. 选择标定图像文件
3. 图像应显示在左侧画布
```

#### Step 2: 设置参数
```
1. 标准物质: 选择 "CeO2" 或 "LaB6"
2. 波长: 输入 X-ray 波长（例如：1.033 Å）
3. 距离: 输入初始距离（例如：150 mm）
4. 像素尺寸: 输入像素大小（例如：79 μm）
```

#### Step 3: 选择控制点

**方法 A - 自动检测**:
```
1. 点击 "Auto Peak Detection" 按钮
2. 等待自动峰检测完成
3. 查看日志中的控制点数量
```

**方法 B - 手动选择**:
```
1. 点击 "Manual Peak Selection" 按钮
2. 在图像上点击衍射环
3. 输入环编号（0, 1, 2, ...）
4. 重复直到每个环有 8-12 个点
```

#### Step 4: 运行标定
```
1. 点击 "Run Calibration" 按钮
2. 观察日志输出
3. 等待标定完成
```

### 5. 验证新功能

#### 功能 1: 查看精修日志

**期望看到**:
```
============================================================
Starting Geometry Refinement (Dioptas-style)
============================================================
Number of control points: XX
Number of rings: X

Stage 1: Refining distance and beam center...
  Distance: XXX.XXX mm
  PONI1 (Y): XX.XXX mm
  PONI2 (X): XX.XXX mm
  RMS error: X.XXX pixels

Stage 2: Full geometry refinement (including rotations)...
  Optimizing all 6 parameters: dist, poni1, poni2, rot1, rot2, rot3  ← 关键！

  Refined Parameters:
    Distance: XXX.XXX mm (Δ=X.XXX mm)
    PONI1: XX.XXX mm (Δ=X.XXX mm)
    PONI2: XX.XXX mm (Δ=X.XXX mm)
    Rot1: X.XXXX° (tilt around axis 1)  ← 新功能：修正 rot1
    Rot2: X.XXXX° (tilt around axis 2)  ← 新功能：修正 rot2
    Rot3: X.XXXX° (rotation in plane)   ← 新功能：修正 rot3

  Final RMS error: X.XXX pixels
  Quality: Excellent ✓✓✓  ← 新功能：质量评估
```

**验证点**:
- ✅ 两阶段精修
- ✅ Rot1, Rot2, Rot3 显示非零值
- ✅ 质量评估（Excellent/Good/Acceptable）

#### 功能 2: 查看理论环叠加

**期望看到**:
```
在图像显示区域：
- 背景：原始衍射图像（灰度）
- 白色点：控制点（如果有）
- 红色圆圈：理论环位置 ← 新功能！
```

**验证点**:
- ✅ 红色圆圈应与实际衍射环重合
- ✅ 所有环都应该显示
- ✅ 环的位置应该准确

**质量判断**:
- 优秀：理论环完美重合实际环
- 良好：理论环略有偏差（< 2 pixels）
- 需改进：理论环明显偏离

#### 功能 3: 查看标定结果

**期望看到**:
```
============================================================
CALIBRATION RESULTS (Dioptas-style)
============================================================
Distance: XXX.XXX mm
PONI1 (Y): XX.XXX mm
PONI2 (X): XX.XXX mm
Rot1: X.XXXX°  ← 新功能
Rot2: X.XXXX°  ← 新功能
Rot3: X.XXXX°  ← 新功能
Wavelength: X.XXXX Å
============================================================

✓ Theoretical calibration rings overlaid on image  ← 新功能
  (Red circles show expected ring positions)
```

### 6. 保存标定

```
1. 点击 "Save PONI" 按钮
2. 选择保存位置
3. 生成 .poni 文件
```

**验证 PONI 文件**:
```bash
cat calibration.poni
```

**应包含**:
```ini
# Detector calibration file
Detector: Detector
Wavelength: 1.0332e-10
Distance: 0.15018
Poni1: 0.083512
Poni2: 0.082501
Rot1: 0.000408   ← 非零值！
Rot2: -0.000326  ← 非零值！
Rot3: 2.09e-05   ← 非零值！
```

---

## 高级测试

### 对比测试：Dioptas vs 本实现

#### 1. 在 Dioptas 中标定

```bash
# 启动 Dioptas
dioptas
```

步骤：
1. Load 相同的图像
2. 使用相同的标准物质和波长
3. 选择相同的控制点（或使用 auto）
4. 运行标定
5. 保存 PONI 文件为 `dioptas_result.poni`

#### 2. 在本实现中标定

步骤：
1. 使用相同的图像和参数
2. 运行标定
3. 保存 PONI 文件为 `our_result.poni`

#### 3. 对比结果

```bash
# 查看参数差异
diff dioptas_result.poni our_result.poni
```

**期望**:
- 参数差异 < 0.5%
- Rot 参数数量级相同
- RMS 误差接近

**示例对比**:
```
Parameter    | Dioptas  | Our Result | Diff (%)
-------------|----------|------------|----------
Distance (mm)| 150.187  | 150.189    | 0.001%
PONI1 (mm)   | 83.512   | 83.511     | 0.001%
PONI2 (mm)   | 82.501   | 82.502     | 0.001%
Rot1 (deg)   | 0.0234   | 0.0235     | 0.4%
Rot2 (deg)   | -0.0187  | -0.0186    | 0.5%
Rot3 (deg)   | 0.0012   | 0.0012     | 0.0%
```

---

## 常见问题

### Q1: 理论环不显示

**可能原因**:
- 标定未完成
- AI 对象未设置

**解决方法**:
1. 确保标定成功完成
2. 查看日志是否有 "Theoretical calibration rings overlaid"
3. 检查图像显示区域

### Q2: Rot 参数为零

**可能原因**:
- 数据质量不足
- 控制点太少

**解决方法**:
1. 增加控制点数量（每环 > 8 个）
2. 增加环的数量（> 3 个环）
3. 提高图像质量

### Q3: RMS 误差很大（> 3 pixels）

**可能原因**:
- 控制点选择不准确
- 初始参数偏差太大
- 标准物质选择错误

**解决方法**:
1. 重新选择控制点（使用手动模式）
2. 调整初始距离
3. 确认标准物质和波长

### Q4: 理论环与实际环不重合

**可能原因**:
- 标定失败
- 参数不正确

**解决方法**:
1. 查看 RMS 误差
2. 重新运行标定
3. 检查所有输入参数

---

## 性能测试

### 测试指标

1. **标定速度**
   - 自动峰检测：< 5 秒
   - 几何精修：< 3 秒
   - 总时间：< 10 秒

2. **精度**
   - RMS 误差：< 1 pixel（优秀）
   - Rot 参数：通常 < 0.1°
   - 与 Dioptas 差异：< 0.5%

3. **可视化**
   - 理论环绘制：< 1 秒
   - 实时更新：立即显示

---

## 测试清单

### 基本功能
- [ ] 图像加载成功
- [ ] 参数设置正确
- [ ] 控制点选择工作
- [ ] 标定运行完成
- [ ] PONI 文件保存成功

### 新功能（Dioptas 风格）
- [ ] 两阶段精修日志
- [ ] Rot1, Rot2, Rot3 非零
- [ ] 质量评估显示
- [ ] 理论环叠加显示
- [ ] 理论环与实际环重合

### 高级测试
- [ ] 与 Dioptas 结果对比
- [ ] 多个图像测试
- [ ] 不同标准物质测试
- [ ] 边界情况测试

---

## 成功标准

### 必须满足（Must Have）
1. ✅ 标定成功完成
2. ✅ 生成有效 PONI 文件
3. ✅ Rot 参数非零（如有倾斜）
4. ✅ RMS < 3 pixels

### 应该满足（Should Have）
1. ✅ 理论环清晰显示
2. ✅ RMS < 1 pixel
3. ✅ 与 Dioptas 结果一致（< 1% 差异）

### 最好满足（Nice to Have）
1. ✅ 标定速度 < 10 秒
2. ✅ 所有环完美重合
3. ✅ 详细的进度反馈

---

## 报告模板

### 测试报告

**测试日期**: ___________
**测试人员**: ___________
**测试图像**: ___________

#### 测试结果

**基本信息**:
- 图像尺寸: _________
- 标准物质: _________
- 波长: _________
- 控制点数: _________

**标定结果**:
- Distance: _________ mm
- PONI1: _________ mm
- PONI2: _________ mm
- Rot1: _________°
- Rot2: _________°
- Rot3: _________°
- RMS: _________ pixels
- 质量评估: _________

**新功能验证**:
- [ ] 完整精修（6 参数）: _________
- [ ] Rot 修正启用: _________
- [ ] 理论环显示: _________
- [ ] 与 Dioptas 对比: _________%

**问题和建议**:
_______________________________________________
_______________________________________________

**总体评价**: ☐ 通过 ☐ 需改进 ☐ 失败

---

*测试指南版本: 1.0*
*创建日期: 2025-12-05*
