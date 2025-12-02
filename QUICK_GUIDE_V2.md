# Mask Module V2 - 快速使用指南

## 🎉 V2 新特性

### ✅ 改进 1: Drawing Tools 移到右侧
- **之前**: 工具在顶部，占用空间
- **现在**: 所有工具在右侧面板，图像区域更大

### ✅ 改进 2: Threshold 双模式 (Dioptas 风格)
- **Below Threshold**: 遮蔽低于阈值的像素 (去噪声)
- **Above Threshold**: 遮蔽高于阈值的像素 (去过曝)

### ✅ 改进 3: 统一的右侧面板
- 工具选择
- 阈值控制
- 遮罩操作
- 实时统计

---

## 📍 界面布局

```
┌───────────────────────────────────────────┐
│ File: [Load Image][Load Mask][Save][Clear]│
├────────────────────────┬──────────────────┤
│                        │ 🎨 Drawing Tools │
│   Image Canvas         │  ○ Circle        │
│   (放大的显示区域)      │  ○ Rectangle     │
│                        │  ○ Polygon       │
│          [Contrast]    │  ○ Point         │
│                        │  ○ Threshold     │
│                        │                  │
│                        │ Action:          │
│                        │  ○ Mask/Unmask   │
│                        │                  │
│                        │ [Threshold 区]   │
│                        │                  │
│                        │ 🔧 Operations    │
│                        │ 📊 Statistics    │
└────────────────────────┴──────────────────┘
```

---

## 🎨 Drawing Tools 使用

### 1. Circle (圆形)
```
1. 右侧选择 "🔵 Circle"
2. 在图像上拖动绘制圆形
3. 自动应用 Mask/Unmask
```

### 2. Rectangle (矩形)
```
1. 右侧选择 "▭ Rectangle"
2. 拖动绘制矩形
3. 自动应用
```

### 3. Polygon (多边形)
```
1. 右侧选择 "⬡ Polygon"
2. 点击定义顶点
3. 右键或按 Enter 完成
```

### 4. Point (点)
```
1. 右侧选择 "⊙ Point"
2. 点击要遮蔽/取消的位置
3. 立即生效
```

### 5. Threshold (阈值) ⭐ 新功能
```
1. 右侧选择 "📊 Threshold"
2. 自动显示阈值控制区
3. 选择模式和输入值
4. 点击 Apply
```

---

## 📊 Threshold 详细使用 (新功能!)

### Below Threshold 模式 - 去除背景噪声

**使用场景**: 图像有低强度背景

```
┌─────────────────────────┐
│ Threshold Mode:         │
│ ◉ Below Threshold       │ ← 选择这个
│ ○ Above Threshold       │
│                         │
│ Threshold Value:        │
│ [      100      ]       │ ← 输入阈值
│ Range: 0 - 65535.0     │
│                         │
│ [ Apply Threshold ]     │ ← 点击应用
└─────────────────────────┘

效果: 所有强度 < 100 的像素被遮蔽
用途: 去除低强度噪声、背景
```

### Above Threshold 模式 - 去除过曝区域

**使用场景**: 图像有过曝的高强度区域

```
┌─────────────────────────┐
│ Threshold Mode:         │
│ ○ Below Threshold       │
│ ◉ Above Threshold       │ ← 选择这个
│                         │
│ Threshold Value:        │
│ [     50000     ]       │ ← 输入阈值
│ Range: 0 - 65535.0     │
│                         │
│ [ Apply Threshold ]     │ ← 点击应用
└─────────────────────────┘

效果: 所有强度 > 50000 的像素被遮蔽
用途: 去除饱和峰、过曝区域
```

---

## 🔧 常用工作流程

### 工作流程 1: 清理衍射图像
```
步骤:
1. Load Image → 加载衍射图
2. 📊 Threshold (Below, 100) → 去除背景噪声
3. 📊 Threshold (Above, 50000) → 去除过曝
4. 🔧 Fill Holes → 填充孔洞
5. ➕ Grow → 略微扩展边缘
6. Save Mask → 保存结果

效果: 干净的遮罩!
```

### 工作流程 2: 手动精细遮罩
```
步骤:
1. Load Image
2. 🔵 Circle → 大致圈出区域
3. ⊙ Point → 细节调整
4. ➖ Shrink → 收缩边缘
5. Save Mask

效果: 精确的手动遮罩
```

### 工作流程 3: 快速阈值遮罩
```
步骤:
1. Load Image
2. 📊 Threshold (Below, 阈值)
3. Save Mask

效果: 一步去除背景
```

---

## 🎯 操作按钮

### Mask Operations

| 按钮 | 功能 | 说明 |
|------|------|------|
| ↕️ Invert | 反转 | 遮罩 ↔ 非遮罩 |
| ➕ Grow | 膨胀 | 扩大遮罩区域 1px |
| ➖ Shrink | 腐蚀 | 缩小遮罩区域 1px |
| 🔧 Fill Holes | 填充 | 填充遮罩中的孔洞 |

### Action 选择

| 选项 | 说明 |
|------|------|
| ✓ Mask | 添加到遮罩 |
| ✗ Unmask | 从遮罩中移除 |

---

## 💡 使用技巧

### 1. 图像导航
- **滚轮**: 缩放图像
- **拖动**: 绘制形状
- **右键**: 完成多边形

### 2. Threshold 技巧
- 先用 Below 去背景
- 再用 Above 去过曝
- 组合使用效果最佳

### 3. 快捷操作
- Circle/Rectangle: 一拖即成
- Point: 快速点击调整
- Polygon: 精细勾画

### 4. 统计查看
- 右侧底部实时显示
- 每次操作后自动更新
- 查看遮罩覆盖率

---

## 📊 Statistics 说明

```
┌─────────────────────────┐
│ 📊 Statistics          │
├─────────────────────────┤
│ Total: 2,048,576 px    │ ← 总像素数
│ Masked: 125,000 px     │ ← 已遮蔽像素
│ Percentage: 6.10%      │ ← 遮蔽百分比
│ Unmasked: 1,923,576    │ ← 未遮蔽像素
└─────────────────────────┘
```

---

## ⚡ 常见问题

### Q1: Threshold 选哪个模式?
**A**: 
- 去背景噪声 → Below Threshold
- 去过曝区域 → Above Threshold
- 都需要 → 分两次应用

### Q2: 如何组合使用?
**A**:
```
Below (100) → 去背景
Above (50000) → 去过曝
Fill Holes → 完善
```

### Q3: 图像区域变大了吗?
**A**: 是的! V2 将工具移到右侧，图像显示区域明显增大

### Q4: 符合 Dioptas 标准吗?
**A**: 完全符合! Below/Above 两种模式与 Dioptas 一致

---

## 🎓 对比 V1 → V2

| 特性 | V1 | V2 |
|------|----|----|
| 工具位置 | 顶部 | **右侧** ✅ |
| Threshold 模式 | 1 种 | **2 种** ✅ |
| 图像区域 | 小 | **大** ✅ |
| 操作流畅度 | 跨区域 | **统一右侧** ✅ |
| 专业度 | 自定义 | **Dioptas 标准** ✅ |

---

## ✅ 快速检查清单

使用前确认:
- ☐ 已加载图像
- ☐ 选择合适的工具
- ☐ 选择 Mask/Unmask
- ☐ (Threshold 时) 选择模式

使用后确认:
- ☐ 查看统计信息
- ☐ 确认遮罩效果
- ☐ 保存遮罩文件

---

## 🚀 开始使用

1. **加载图像**: 点击 "📂 Load Image"
2. **选择工具**: 右侧选择绘图工具
3. **绘制遮罩**: 在图像上操作
4. **调整优化**: 使用 Operations 按钮
5. **保存结果**: 点击 "💾 Save Mask"

**就这么简单! 🎉**

---

**版本**: V2.0  
**状态**: ✅ 完成  
**日期**: 2025-12-02  
**参照**: Dioptas Threshold 实现
