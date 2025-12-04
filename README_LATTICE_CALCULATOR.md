# 晶格参数计算器 - 使用指南
# Lattice Parameter Calculator - User Guide

## 📖 概述 (Overview)

`batch_cal_volume.py` 已被简化为专注于晶格参数计算的工具。不再包含相变检测和峰分离功能，用户需要提前手动分离好峰位数据。

## ✨ 主要特性 (Key Features)

- ✅ 支持8种晶系 (FCC, BCC, SC, HCP, Tetragonal, Orthorhombic, Monoclinic, Triclinic)
- ✅ 使用最小二乘法精确拟合晶格参数
- ✅ 自动计算晶胞体积和原子体积
- ✅ 结果导出为CSV格式
- ✅ 简洁易用的API
- ✅ 向后兼容现有代码

## 🚀 快速开始 (Quick Start)

### 1. 准备CSV文件

将您的峰位数据保存为CSV格式：

```csv
File,Center
10.0,8.5
10.0,9.2
10.0,12.3

20.0,8.6
20.0,9.3
20.0,12.4
```

**注意**: 
- `File` 列: 压力值 (GPa)
- `Center` 列: 峰位 (2theta, 度)
- 空行分隔不同压力点

### 2. 运行计算

```python
from batch_cal_volume import LatticeParameterCalculator

# 创建计算器实例
calculator = LatticeParameterCalculator(wavelength=0.4133)

# 计算晶格参数
results = calculator.calculate('your_peaks.csv', crystal_system_key='cubic_FCC')

# 结果自动保存为: your_peaks_lattice_results.csv
```

## 📊 支持的晶系 (Supported Crystal Systems)

| 晶系类型 | 键值 | 最小峰数 | 晶格参数 |
|---------|------|---------|---------|
| 面心立方 (FCC) | `cubic_FCC` | 1 | a |
| 体心立方 (BCC) | `cubic_BCC` | 1 | a |
| 简单立方 (SC) | `cubic_SC` | 1 | a |
| 六方密排 (HCP) | `Hexagonal` | 2 | a, c |
| 四方 | `Tetragonal` | 2 | a, c |
| 正交 | `Orthorhombic` | 3 | a, b, c |
| 单斜 | `Monoclinic` | 4 | a, b, c, β |
| 三斜 | `Triclinic` | 6 | a, b, c, α, β, γ |

## 💡 使用示例 (Usage Examples)

### 示例 1: 交互式模式

```python
from batch_cal_volume import LatticeParameterCalculator

calculator = LatticeParameterCalculator(wavelength=0.4133)

# 程序会提示您选择晶系
results = calculator.calculate('peaks.csv')
```

### 示例 2: 指定晶系

```python
from batch_cal_volume import LatticeParameterCalculator

calculator = LatticeParameterCalculator(wavelength=0.4133)

# 直接指定晶系，不需要交互
results = calculator.calculate('peaks.csv', crystal_system_key='Hexagonal')
```

### 示例 3: 多相材料分析

```python
from batch_cal_volume import LatticeParameterCalculator

calculator = LatticeParameterCalculator(wavelength=0.4133)

# 分别计算原始相和新相
original_results = calculator.calculate('original_phase.csv', 'cubic_FCC')
new_results = calculator.calculate('new_phase.csv', 'Hexagonal')
```

### 示例 4: 向后兼容（旧代码）

```python
# 旧代码仍然可以工作
from batch_cal_volume import XRayDiffractionAnalyzer

analyzer = XRayDiffractionAnalyzer(wavelength=0.4133, n_pressure_points=4)
results = analyzer.analyze(
    csv_path='peaks.csv',
    original_system='cubic_FCC',
    auto_mode=True
)
```

## 📈 输出结果 (Output Results)

### 输出文件格式

程序会生成 `*_lattice_results.csv` 文件：

```csv
Pressure (GPa),a,V_cell,V_atomic,num_peaks_used
10.0,4.0500,66.430,16.608,3
20.0,4.0200,64.965,16.241,3
30.0,3.9900,63.522,15.881,3
```

### 结果字典结构

```python
results = {
    10.0: {
        'a': 4.0500,           # 晶格参数 a (Å)
        'V_cell': 66.430,      # 晶胞体积 (Å³)
        'V_atomic': 16.608,    # 原子体积 (Å³/atom)
        'num_peaks_used': 3    # 使用的峰数量
    },
    20.0: { ... },
    # ...
}
```

对于非立方晶系，还会包含额外参数：
- **Hexagonal/Tetragonal**: `a`, `c`, `c/a`
- **Orthorhombic**: `a`, `b`, `c`
- **Monoclinic**: `a`, `b`, `c`, `beta`
- **Triclinic**: `a`, `b`, `c`, `alpha`, `beta`, `gamma`

## ⚙️ API 参考 (API Reference)

### LatticeParameterCalculator 类

#### `__init__(wavelength=0.4133, n_pressure_points=4)`
创建计算器实例

**参数**:
- `wavelength` (float): X射线波长 (Å)，默认 0.4133
- `n_pressure_points` (int): 向后兼容参数，简化版本中不使用

#### `calculate(csv_path, crystal_system_key=None)`
计算晶格参数

**参数**:
- `csv_path` (str): CSV文件路径
- `crystal_system_key` (str, optional): 晶系键值，如不提供则交互式选择

**返回**:
- `dict`: 晶格参数结果字典

#### `read_peak_data(csv_path)`
读取CSV文件中的峰位数据

**参数**:
- `csv_path` (str): CSV文件路径

**返回**:
- `dict`: {压力: [峰位列表]} 字典

#### `fit_lattice_parameters(peak_dataset, crystal_system_key)`
拟合晶格参数

**参数**:
- `peak_dataset` (dict): 峰位数据集
- `crystal_system_key` (str): 晶系键值

**返回**:
- `dict`: 拟合结果

#### `save_results_to_csv(results, filename)`
保存结果到CSV文件

**参数**:
- `results` (dict): 拟合结果
- `filename` (str): 输出文件名

## ⚠️ 重要注意事项 (Important Notes)

### 1. 峰位预处理
- ✅ 必须手动分离不同相的峰位
- ✅ 每个CSV文件只包含一个相的数据
- ✅ 不再自动检测相变点

### 2. 数据质量
- 确保峰位数据准确
- 峰数量应满足晶系的最小要求
- 建议使用多个峰以提高拟合精度

### 3. 晶系选择
- 正确选择晶系至关重要
- 不正确的晶系会导致错误的结果
- 如不确定，可以尝试多个晶系并比较拟合质量

## 🔧 故障排除 (Troubleshooting)

### 问题 1: 导入错误
```python
ImportError: cannot import name 'XRayDiffractionAnalyzer'
```
**解决**: 更新 `batch_cal_volume.py` 到最新版本

### 问题 2: 峰数量不足
```
Warning: Less than X peaks required for crystal system
```
**解决**: 确保CSV文件包含足够的峰位数据

### 问题 3: 拟合失败
```
Fitting failed for pressure X GPa
```
**解决**: 
- 检查峰位数据是否正确
- 尝试不同的晶系
- 增加峰的数量

## 📚 相关文档 (Related Documentation)

1. **MODIFICATION_SUMMARY.md** - 完整修改总结
2. **BATCH_CAL_VOLUME_CHANGES.md** - 详细变更说明
3. **example_lattice_calculation.py** - 完整使用示例

## 🤝 技术支持 (Support)

如有问题或建议，请联系：
- 邮箱: 16961@example.com (替换为实际邮箱)
- GitHub: (添加项目链接)

## 📝 更新日志 (Changelog)

### v2.0 (2025-12-04)
- ✨ 简化为专注于晶格参数计算
- ❌ 移除相变检测功能
- ❌ 移除峰分离功能
- ✅ 添加向后兼容性
- 📚 完善文档

### v1.0 (2025-11-13)
- 🎉 初始版本
- ✨ 相变检测
- ✨ 峰追踪
- ✨ 晶格参数拟合

---

**最后更新**: 2025-12-04  
**版本**: 2.0 (简化版)
