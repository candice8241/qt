# batch_cal_volume.py 修改说明 (Modification Summary)

## 概述 (Overview)
已将 `batch_cal_volume.py` 简化为专注于晶格参数计算的工具，移除了相变检测和峰分离功能。

## 主要变更 (Major Changes)

### 1. 类重命名 (Class Renamed)
- **旧类名**: `XRayDiffractionAnalyzer`
- **新类名**: `LatticeParameterCalculator`
- **向后兼容**: 保留了别名 `XRayDiffractionAnalyzer = LatticeParameterCalculator`

### 2. 移除的功能 (Removed Features)
- ❌ 相变检测 (`find_phase_transition_point`)
- ❌ 新峰追踪 (`collect_tracked_new_peaks`)
- ❌ 原始峰数据集构建 (`build_original_peak_dataset`)
- ❌ 峰数据集导出 (`_export_peaks_to_csv`)
- ❌ 复杂的分析工作流

### 3. 保留的核心功能 (Retained Core Features)
- ✅ CSV文件读取 (`read_peak_data`)
- ✅ 8种晶系支持 (FCC, BCC, SC, HCP, Tetragonal, Orthorhombic, Monoclinic, Triclinic)
- ✅ 最小二乘法拟合 (`fit_lattice_parameters_*`)
- ✅ 晶胞参数计算
- ✅ 晶胞体积和原子体积计算
- ✅ 结果导出为CSV (`save_results_to_csv`)

### 4. 新增方法 (New Methods)
- **`calculate(csv_path, crystal_system_key=None)`**: 简化的主方法
  - 读取CSV
  - 选择晶系
  - 计算晶格参数
  - 保存结果

### 5. 向后兼容方法 (Backward Compatibility)
- **`analyze(csv_path, original_system, new_system, auto_mode)`**: 
  - 为兼容现有代码保留
  - 内部调用简化的 `calculate()` 方法
  - 打印提示信息说明使用简化版本

## 使用方法 (Usage)

### 方式1: 简化接口 (Simplified Interface)
```python
from batch_cal_volume import LatticeParameterCalculator

# 创建计算器
calculator = LatticeParameterCalculator(wavelength=0.4133)

# 交互式 - 会提示选择晶系
results = calculator.calculate('peaks.csv')

# 或直接指定晶系
results = calculator.calculate('peaks.csv', crystal_system_key='cubic_FCC')
```

### 方式2: 旧接口（向后兼容）(Legacy Interface - Backward Compatible)
```python
from batch_cal_volume import XRayDiffractionAnalyzer

# 旧代码仍然可以工作
analyzer = XRayDiffractionAnalyzer(wavelength=0.4133, n_pressure_points=4)
results = analyzer.analyze(
    csv_path='peaks.csv',
    original_system='cubic_FCC',
    auto_mode=True
)
```

## CSV 文件格式 (CSV File Format)

```csv
File,Center
10,8.5
10,9.2
10,12.3

20,8.6
20,9.3
20,12.4
```

- **File 列**: 压力值 (GPa)
- **Center 列**: 峰位 (2theta, 度)
- **空行**: 分隔不同压力点

## 输出结果 (Output Results)

输出文件: `*_lattice_results.csv`

包含列:
- `Pressure (GPa)`: 压力
- `a`, `b`, `c`: 晶格参数 (Å)
- `c/a`: 轴比（非立方晶系）
- `V_cell`: 晶胞体积 (Å³)
- `V_atomic`: 原子体积 (Å³/atom)
- `num_peaks_used`: 使用的峰数量

## 支持的晶系 (Supported Crystal Systems)

| 晶系 | 键值 | 最小峰数 | 参数 |
|------|------|----------|------|
| FCC | `cubic_FCC` | 1 | a |
| BCC | `cubic_BCC` | 1 | a |
| SC | `cubic_SC` | 1 | a |
| HCP | `Hexagonal` | 2 | a, c |
| Tetragonal | `Tetragonal` | 2 | a, c |
| Orthorhombic | `Orthorhombic` | 3 | a, b, c |
| Monoclinic | `Monoclinic` | 4 | a, b, c, β |
| Triclinic | `Triclinic` | 6 | a, b, c, α, β, γ |

## 兼容性说明 (Compatibility Notes)

现有代码（如 `powder_module.py` 和 `batch_appearance.py`）通过以下方式保持兼容：
1. 别名 `XRayDiffractionAnalyzer` 指向新类 `LatticeParameterCalculator`
2. `__init__` 接受 `n_pressure_points` 参数（即使不使用）
3. `analyze()` 方法调用简化的 `calculate()` 方法

## 注意事项 (Important Notes)

⚠️ **使用前请手动分离峰位**
- 此简化版本不再自动检测相变或分离新旧峰
- 用户需要提前准备好已分离的峰位CSV文件
- 每个CSV文件应包含单一相的峰位数据

✅ **推荐工作流程**
1. 使用其他工具或手动识别相变点
2. 分别准备原始相和新相的峰位CSV文件
3. 对每个文件运行 `calculate()` 方法
4. 获得各自的晶格参数结果
