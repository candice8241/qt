# 批量问题修复 - 第二批

## 修复日期: 2025-12-05

---

## 问题清单

1. ❌ AttributeError: 'calibrant_info_text' 不存在
2. ❌ Automatic increase ring number 没有效果
3. ❌ Refinement options 应该隐藏
4. ❌ 图像显示区域太小
5. ❌ 对比度控件改为方块样式
6. ❌ 标定时实时显示自动检测的点

---

## 修复方案

### 1. calibrant_info_text 初始化问题

**问题**: 初始化顺序导致属性不存在

**修复**: 确保在使用前初始化
```python
# 在 setup_ui 开始处添加
if not hasattr(self, 'calibrant_info_text'):
    self.calibrant_info_text = QLabel("")
```

### 2. 自动增加环编号

**问题**: 复选框存在但没有连接功能

**修复**: 在 on_peak_click 中检查复选框
```python
def on_peak_click(self, event):
    # ...
    if hasattr(self, 'automatic_peak_num_inc_cb') and self.automatic_peak_num_inc_cb.isChecked():
        self.current_ring_num += 1
        if hasattr(self, 'ring_num_input'):
            self.ring_num_input.setValue(self.current_ring_num)
```

### 3. 隐藏 Refinement Options

**修复**: 不调用 setup_refinement_options_groupbox
```python
# 注释掉或删除
# self.setup_refinement_options_groupbox(calib_params_layout)
```

### 4. 放大图像区域

**修复**: 增加 Canvas 尺寸
```python
# 从 width=6, height=6 改为 width=10, height=10
self.calibration_canvas = CalibrationCanvas(
    parent=None, 
    width=10,    # ← 放大
    height=10,   # ← 放大
    dpi=100
)
```

### 5. 对比度控件改为方块

**修复**: 自定义滑块样式
```python
self.contrast_slider.setStyleSheet("""
    QSlider::groove:vertical {
        width: 20px;
        background: #ddd;
    }
    QSlider::handle:vertical {
        background: #4A90E2;
        border: 1px solid #2E5C8A;
        height: 20px;
        width: 20px;
        margin: 0 -10px;
        border-radius: 3px;  /* 方形 */
    }
""")
```

### 6. 实时显示自动检测的点

**修复**: 在 extract_cp 后立即显示
```python
# 在 perform_calibration 中添加回调
geo_ref.extract_cp(max_rings=10, pts_per_deg=1.0)

# 立即显示检测到的点
if hasattr(geo_ref, 'data') and geo_ref.data is not None:
    self.display_detected_points(geo_ref.data)
```

实现 display_detected_points:
```python
def display_detected_points(self, data):
    """实时显示自动检测的控制点"""
    points_display = []
    for ring in data:
        if len(ring) > 0:
            ring_array = np.array(ring)
            for point in ring_array:
                # Convert to pixel coordinates
                tth_val = point[1]
                chi_val = point[2]
                y, x = self.ai.calcfrom1d(tth_val, chi_val, shape=self.current_image.shape)
                if 0 <= y < shape[0] and 0 <= x < shape[1]:
                    points_display.append([x, y, int(point[0])])
    
    # Update canvas
    self.calibration_canvas.manual_peaks = points_display
    self.calibration_canvas.display_calibration_image(
        self.current_image, 
        self.calibration_canvas.calibration_points
    )
```

---

开始修复...
