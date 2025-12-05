# Dioptas 标定(Calibration)工作流程

## 概述 (Overview)

Dioptas 是一个用于 X 射线衍射图像处理的强大开源软件，特别擅长探测器标定和积分。本文档详细描述了 Dioptas 中的标定流程及其实现原理。

**GitHub 仓库**: https://github.com/Dioptas/Dioptas

---

## 核心标定步骤 (Core Calibration Steps)

### 1. 图像加载 (Image Loading)
**目的**: 加载标准样品(如 CeO₂, LaB₆)的衍射图像

**Dioptas 实现**:
- 支持多种图像格式: `.tif`, `.mar3450`, `.cbf`, `.edf`, `.img` 等
- 使用 `fabio` 库读取图像
- 在 `CalibrationModel` 中管理图像数据

```python
# 关键代码路径: dioptas/model/CalibrationModel.py
def load_img(self, filename):
    """Load calibration image using fabio"""
    self.img = fabio.open(filename).data
```

**步骤**:
1. 点击 "Load Image" 按钮
2. 选择标定图像文件
3. 图像显示在左侧面板

---

### 2. 探测器参数设置 (Detector Setup)
**目的**: 定义探测器的物理特性

**必需参数**:
- **Pixel Size** (像素尺寸): 单个像素的物理尺寸 (μm)
- **Detector Distance** (探测器距离): 样品到探测器的距离 (mm)
- **Center Position** (中心位置): 直射光束在探测器上的位置 (x, y)
- **Detector Tilt** (探测器倾斜): 旋转角度 (rot1, rot2, rot3)

**Dioptas 实现**:
```python
# 关键类: pyFAI.detectors.Detector
from pyFAI.detectors import Detector

detector = Detector(
    pixel1=pixel_size * 1e-6,  # 转换为米
    pixel2=pixel_size * 1e-6,
    max_shape=image.shape
)
```

---

### 3. 标准物质选择 (Calibrant Selection)
**目的**: 选择已知 d-spacing 的标准物质

**Dioptas 支持的标准物质**:
- **CeO₂** (铈氧化物) - 最常用
- **LaB₆** (六硼化镧)
- **Si** (硅)
- **Al₂O₃** (氧化铝)
- **AgBh** (银behenate)
- **Au**, **Ni**, **NaCl** 等

**实现**:
```python
# 使用 pyFAI 的 Calibrant 类
from pyFAI.calibrant import Calibrant, ALL_CALIBRANTS

calibrant = Calibrant(wavelength=wavelength)
calibrant.load_file("CeO2.D")  # 从 pyFAI 数据库加载
```

**步骤**:
1. 在 "Calibrant" 下拉菜单中选择标准物质
2. 输入 X-ray 波长 (Å) 或能量 (keV)

---

### 4. 控制点选择 (Control Points Selection)

这是 Dioptas 标定的**核心步骤**，有两种方式：

#### 方法 A: 自动峰检测 (Automatic Peak Detection)

**步骤**:
1. 点击 "Auto" 按钮
2. Dioptas 自动检测衍射环
3. 使用图像处理算法找到峰位置

**实现原理**:
```python
# 关键方法: dioptas/model/CalibrationModel.py
def auto_search_peaks(self):
    """
    使用 pyFAI 的 peak-picking 算法:
    - 使用高斯滤波器平滑图像
    - 应用阈值检测潜在峰
    - 计算峰的质心位置
    """
    from pyFAI.peak_picker import PeakPicker
    
    pp = PeakPicker(self.img, mask=self.mask)
    pp.set_wavelength(self.wavelength)
    pp.set_distance(self.distance)
    self.control_points = pp.peaks
```

#### 方法 B: 手动选点 (Manual Point Selection)

**步骤**:
1. 选择 "Manual" 模式
2. 在图像上点击衍射环
3. 为每个点分配环编号 (ring number)

**Dioptas 工作流程**:
```
用户点击 → 记录像素坐标 → 分配到特定环 → 存储控制点
  (x, y)      (row, col)      (ring #)      [(x,y,ring), ...]
```

**关键数据结构**:
```python
# 控制点格式: [[row, col, ring_number], ...]
control_points = [
    [150.5, 200.3, 0],  # Ring 0 的一个点
    [150.8, 300.7, 0],  # Ring 0 的另一个点
    [180.2, 210.5, 1],  # Ring 1 的一个点
    ...
]
```

---

### 5. 几何精修 (Geometry Refinement)

**目的**: 优化探测器几何参数以最小化残差

**Dioptas 使用 pyFAI 的 GeometryRefinement 类**:

```python
from pyFAI.geometryRefinement import GeometryRefinement

# 创建几何精修对象
geo_ref = GeometryRefinement(
    data=control_points,      # 控制点 [[row, col, ring], ...]
    calibrant=calibrant,       # 标准物质对象
    detector=detector,         # 探测器对象
    wavelength=wavelength      # X-ray 波长
)

# 设置初始几何参数
geo_ref.dist = distance       # 距离 (m)
geo_ref.poni1 = center_y      # Y 中心 (m)
geo_ref.poni2 = center_x      # X 中心 (m)
geo_ref.rot1 = 0              # 旋转1 (rad)
geo_ref.rot2 = 0              # 旋转2 (rad)
geo_ref.rot3 = 0              # 旋转3 (rad)

# 执行精修 - 这是核心！
geo_ref.refine2()  # 精修所有参数
```

**精修参数**:
- **dist**: 样品到探测器的距离
- **poni1**: Point of Normal Incidence 的 Y 坐标
- **poni2**: Point of Normal Incidence 的 X 坐标
- **rot1**: 绕 X 轴旋转 (tilt)
- **rot2**: 绕 Y 轴旋转 (tilt)
- **rot3**: 绕 Z 轴旋转 (rotation)

**优化算法**:
- 使用非线性最小二乘法 (scipy.optimize.leastsq)
- 最小化理论环位置与实际控制点之间的差异
- 迭代优化直到收敛

---

### 6. 结果验证 (Result Validation)

**Dioptas 显示**:
- **残差图** (Residuals plot): 显示拟合质量
- **标定环叠加** (Calibration rings overlay): 在图像上显示理论环位置
- **参数表** (Parameters table): 显示所有几何参数

**质量指标**:
```
RMS (均方根误差) < 1 像素 = 优秀
RMS < 2 像素 = 良好
RMS > 3 像素 = 需要重新标定
```

---

### 7. 保存标定结果 (Save Calibration)

**PONI 文件格式** (pyFAI 标准):
```ini
# Detector calibration file
Detector: Detector
Wavelength: 1.0332e-10
Distance: 0.15
Poni1: 0.08347
Poni2: 0.08249
Rot1: 0.0123
Rot2: -0.0045
Rot3: 0.0
```

**保存步骤**:
1. 点击 "Save Calibration" 按钮
2. 选择保存位置和文件名
3. 生成 `.poni` 文件

**Dioptas 实现**:
```python
# 保存标定结果
def save_calibration(self, filename):
    """Save calibration to PONI file"""
    ai = self.create_azimuthal_integrator()
    ai.save(filename)  # 使用 pyFAI 的保存功能
```

---

## Dioptas 标定流程图 (Calibration Flowchart)

```
┌─────────────────────────────────────────────────────────────┐
│  1. 加载标定图像 (Load Calibration Image)                    │
│     - 支持多种格式 (.tif, .cbf, .edf, etc.)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 设置探测器参数 (Set Detector Parameters)                │
│     - 像素尺寸 (Pixel Size)                                  │
│     - 初始距离 (Initial Distance)                            │
│     - 探测器类型 (Detector Type)                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 选择标准物质和波长 (Select Calibrant & Wavelength)       │
│     - CeO₂, LaB₆, Si, etc.                                  │
│     - 输入波长或能量                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 选择控制点 (Select Control Points)                       │
│     ┌────────────────┬────────────────────┐                 │
│     │  自动模式       │    手动模式        │                 │
│     │  (Auto)        │    (Manual)        │                 │
│     │  - 自动峰检测   │    - 用户点击环     │                 │
│     └────────────────┴────────────────────┘                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 几何精修 (Geometry Refinement)                           │
│     - 使用 pyFAI GeometryRefinement                          │
│     - 优化 6 个参数: dist, poni1, poni2, rot1, rot2, rot3   │
│     - 最小化残差                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  6. 验证结果 (Validate Results)                              │
│     - 查看残差图                                              │
│     - 检查 RMS 误差                                           │
│     - 可视化标定环叠加                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  7. 保存标定文件 (Save .poni File)                           │
│     - 生成 pyFAI 格式的 .poni 文件                           │
│     - 用于后续数据积分                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Dioptas GitHub 源码结构 (Source Code Structure)

### 关键文件和模块:

#### 1. **CalibrationModel** (`dioptas/model/CalibrationModel.py`)
核心标定模型，管理标定状态和数据

```python
class CalibrationModel:
    def __init__(self):
        self.img = None
        self.calibrant = None
        self.detector = None
        self.geometry = None
        self.wavelength = None
        
    def load_img(self, filename):
        """加载标定图像"""
        
    def set_calibrant(self, calibrant_name):
        """设置标准物质"""
        
    def create_geometry_refinement(self):
        """创建 GeometryRefinement 对象"""
        
    def calibrate(self):
        """执行标定"""
```

#### 2. **CalibrationController** (`dioptas/controller/CalibrationController.py`)
处理用户交互和 UI 逻辑

```python
class CalibrationController:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.connect_signals()
        
    def connect_signals(self):
        """连接 UI 信号到模型方法"""
        self.view.load_btn.clicked.connect(self.load_image)
        self.view.calibrate_btn.clicked.connect(self.start_calibration)
```

#### 3. **CalibrationWidget** (`dioptas/widgets/CalibrationWidget.py`)
UI 组件定义

```python
class CalibrationWidget(QWidget):
    def __init__(self):
        self.setup_ui()
        
    def setup_ui(self):
        """创建标定界面布局"""
```

#### 4. **PeakPicking** (集成在 pyFAI 中)
处理峰检测和控制点选择

---

## 标定原理 (Calibration Theory)

### PONI 坐标系统

**PONI** = Point of Normal Incidence (法向入射点)

这是 X-ray 光束与探测器平面的**垂直交点**。

```
           X-ray Beam
               ↓
        ━━━━━━━┿━━━━━━━  ← Sample
               │
               │ dist
               │
        ╔══════╪══════╗
        ║      ●      ║  ← Detector
        ║    PONI     ║
        ║  (poni1,    ║
        ║   poni2)    ║
        ╚═════════════╝
```

### 六参数模型 (6-Parameter Model)

1. **dist** (m): PONI 到样品的距离
2. **poni1** (m): PONI 的 Y 坐标（沿慢轴）
3. **poni2** (m): PONI 的 X 坐标（沿快轴）
4. **rot1** (rad): 绕 X 轴旋转 (tilt)
5. **rot2** (rad): 绕 Y 轴旋转 (tilt)
6. **rot3** (rad): 绕 Z 轴旋转 (in-plane rotation)

### 坐标变换

从像素坐标 (i, j) 到散射角 (2θ, χ):

```python
# 简化的变换过程
def pixel_to_2theta(i, j, dist, poni1, poni2, rot1, rot2, rot3):
    """将像素坐标转换为散射角"""
    # 1. 像素 → 米
    y = i * pixel_size - poni1
    x = j * pixel_size - poni2
    
    # 2. 应用旋转矩阵
    coords = apply_rotations(x, y, dist, rot1, rot2, rot3)
    
    # 3. 计算散射角
    two_theta = np.arctan2(coords.r, coords.z)
    chi = np.arctan2(coords.y, coords.x)
    
    return two_theta, chi
```

---

## Dioptas vs pyFAI-calib2

| 特性 | Dioptas | pyFAI-calib2 |
|------|---------|--------------|
| **UI** | 现代化 Qt 界面 | 基础 matplotlib GUI |
| **实时预览** | ✅ 是 | ❌ 否 |
| **集成分析** | ✅ 标定 + 积分 + 掩码 | ❌ 仅标定 |
| **易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **手动调整** | ✅ 交互式 | ⚠️ 有限 |
| **核心引擎** | pyFAI | pyFAI |

---

## 实际使用建议 (Best Practices)

### 1. 标定图像质量
- ✅ **使用完整的衍射环** (至少 3-5 个环)
- ✅ **良好的信噪比** (清晰的峰)
- ✅ **避免饱和** (过曝像素)
- ❌ 避免部分遮挡的图像

### 2. 控制点选择
- **自动模式**: 适合高质量图像
- **手动模式**: 适合低质量或复杂图像
- **推荐**: 每个环至少 8-12 个点

### 3. 初始参数
- 尽可能准确地设置初始距离
- 大致估计中心位置
- 旋转角度通常接近 0

### 4. 验证标定
- 检查残差分布是否均匀
- RMS 应小于 2 像素
- 在不同的数据集上测试

---

## 常见问题 (Troubleshooting)

### 问题 1: 标定失败或 RMS 很大
**原因**:
- 初始参数不准确
- 控制点选择不当
- 标准物质选择错误

**解决方案**:
1. 重新设置初始距离
2. 使用手动模式重新选择控制点
3. 确认标准物质和波长

### 问题 2: 无法检测到峰
**原因**:
- 图像对比度低
- 阈值设置不当

**解决方案**:
1. 调整图像显示范围
2. 增加峰检测灵敏度
3. 使用手动选点模式

### 问题 3: 标定环不匹配
**原因**:
- 波长输入错误
- 标准物质选择错误

**解决方案**:
1. 确认 X-ray 能量/波长
2. 选择正确的标准物质

---

## 参考资源 (References)

1. **Dioptas GitHub**: https://github.com/Dioptas/Dioptas
2. **Dioptas 文档**: https://dioptas.readthedocs.io
3. **pyFAI 文档**: https://pyfai.readthedocs.io
4. **原始论文**: Prescher, C., & Prakapenka, V. B. (2015). DIOPTAS: a program for reduction of two-dimensional X-ray diffraction data and data exploration. *High Pressure Research*, 35(3), 223-230.

---

## 本项目中的实现

当前工作空间中的 `calibrate_module.py` 实现了类似 Dioptas 的标定功能:

### 主要特性:
- ✅ 图像加载和显示
- ✅ pyFAI 集成
- ✅ 自动和手动控制点选择
- ✅ 几何精修
- ✅ PONI 文件生成
- ✅ 掩码编辑
- ✅ 实时预览

### 关键类:
```python
class CalibrateModule(GUIBase):
    """主标定模块"""
    
    def perform_calibration(self, image, calibrant, distance, 
                          pixel_size, mask, manual_control_points=None):
        """
        执行标定 - 基于 Dioptas 实现
        
        参数:
            image: 标定图像数据
            calibrant: 标准物质对象
            distance: 探测器距离 (m)
            pixel_size: 像素尺寸 (m)
            mask: 掩码数组
            manual_control_points: 手动控制点 [[row, col, ring], ...]
        """
        # 创建探测器
        detector = Detector(pixel1=pixel_size, pixel2=pixel_size, 
                          max_shape=image.shape)
        
        # 创建几何精修对象
        geo_ref = GeometryRefinement(
            data=manual_control_points,
            calibrant=calibrant,
            detector=detector,
            wavelength=calibrant.wavelength
        )
        
        # 设置初始几何
        geo_ref.dist = distance
        
        # 执行精修
        geo_ref.refine2()
        
        # 返回结果
        return geo_ref
```

---

## 总结 (Summary)

**Dioptas 标定流程总结**:

1. **加载图像** → 标定样品的衍射图像
2. **设置参数** → 探测器特性和初始几何
3. **选择标准物质** → CeO₂, LaB₆ 等
4. **选择控制点** → 自动或手动标记衍射环
5. **几何精修** → 使用 pyFAI 优化参数
6. **验证结果** → 检查残差和 RMS
7. **保存标定** → 生成 .poni 文件

**关键技术**:
- pyFAI 作为计算引擎
- 非线性最小二乘优化
- 6 参数几何模型
- 交互式 UI 实现

**应用场景**:
- 同步辐射 X-ray 衍射
- 高压衍射实验
- 粉末衍射分析
- 单晶衍射

---

*文档创建时间: 2025-12-05*
*基于 Dioptas v0.6.x 和 pyFAI 2023.x*
