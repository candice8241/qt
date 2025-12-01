# CrysFML EoSFit 源码说明

## 关于当前实现

项目中的 `crysfml_eos_module.py` 是基于 **CrysFML (Crystallographic Fortran Modules Library)** 的 `cfml_eos` 模块的 **Python 重新实现**。

### 源码信息

- **作者**: candicewang928@gmail.com
- **创建日期**: 2025-11-23
- **实现语言**: Python (NumPy, SciPy)
- **原始参考**: CrysFML Fortran Library 的 cfml_eos 模块

## CrysFML 原始源码位置

### GitLab 仓库

CrysFML 的官方 GitLab 仓库地址：

```
https://gitlab.com/CrysFML/CrysFML2008
```

或者新版本：

```
https://github.com/jrcrespoh/CrysFML2008
```

### EoS 模块位置

在 CrysFML 中，EoS 相关代码位于：

```
CrysFML2008/Src/CFML_EoS_Mod.f90
```

这个 Fortran 模块包含：
- `CFML_EoS_Mod`: 主 EoS 模块
- 多种 EoS 模型实现
- P-V-T 关系计算
- EoS 参数拟合程序

## 理论基础

当前的 Python 实现基于以下文献：

### 主要参考文献

**Angel, R.J., Alvaro, M., and Gonzalez-Platas, J. (2014)**
- 标题: "EosFit7c and a Fortran module (library) for equation of state calculations"
- 期刊: Zeitschrift für Kristallographie - Crystalline Materials, 229(5), 405-419
- DOI: 10.1515/zkri-2013-1711

这篇论文详细描述了：
1. F-f 线性化方法
2. 稳定的 B₀' 拟合算法
3. 多种 EoS 模型的实现
4. 误差分析和统计方法

### 其他参考

- **ASE (Atomic Simulation Environment)** EoS 实现
- **pwtools** EoS 实现

## 当前 Python 实现的功能

### 已实现的 EoS 模型

1. **Birch-Murnaghan**
   - 2nd order (2参数: V₀, B₀)
   - 3rd order (3参数: V₀, B₀, B₀')
   - 4th order (4参数: V₀, B₀, B₀', B₀'')

2. **Murnaghan** (经典经验 EoS)

3. **Vinet** (通用 EoS，适用于极端压缩)

4. **Natural Strain** (3阶自然应变 EoS)

5. **Tait** (可逆形式 EoS)

### 核心方法

#### 1. F-f 线性化 (CrysFML 关键方法)

```python
def _birch_murnaghan_f_F_transform(V_data, P_data, V0_estimate):
    """
    将 P-V 数据转换为归一化应变-应力 (f-F) 形式
    
    f = 归一化应变 = [(V0/V)^(2/3) - 1] / 2
    F = 归一化应力 = P / [3f(1+2f)^(5/2)]
    
    对于 BM3: F = B0 [1 + (B0'-4)f]  --> 在 f 中线性！
    """
```

这是 CrysFML 的核心创新，通过线性化防止 B₀' 参数发散。

#### 2. 加权最小二乘拟合

```python
weights = 1.0 / (f**2 + epsilon)  # 强调低应变数据
```

#### 3. Tikhonov 正则化

```python
lambda_reg = regularization_strength * np.mean(weights)
ATA_reg = ATA + lambda_reg * R  # 软约束 B₀' 接近 4.0
```

### 与 CrysFML Fortran 代码的对应关系

| CrysFML Fortran | Python 实现 | 说明 |
|-----------------|-------------|------|
| `EOS_Type` | `EoSType` (Enum) | EoS 类型枚举 |
| `EOS_Parameters_Type` | `EoSParameters` (dataclass) | 参数数据结构 |
| `Get_Props_EoS` | `calculate_pressure()` | 计算 P(V) |
| `EoS_Fit` | `fit()` | 拟合 EoS 参数 |
| `K_Cal` | 内嵌在 `fit()` 中 | 体积模量计算 |
| `Vol_EoS` | 未实现 | V(P) 反向计算 |

## 如何获取原始 CrysFML 代码

### 方法 1: 从 GitLab 克隆

```bash
# 克隆 CrysFML2008 仓库
git clone https://gitlab.com/CrysFML/CrysFML2008.git

# 或从 GitHub 镜像
git clone https://github.com/jrcrespoh/CrysFML2008.git

# EoS 模块位于
cd CrysFML2008/Src
ls -la CFML_EoS_Mod.f90
```

### 方法 2: 直接下载

访问 GitLab 页面直接下载特定文件：
```
https://gitlab.com/CrysFML/CrysFML2008/-/blob/master/Src/CFML_EoS_Mod.f90
```

### 方法 3: 使用 EosFit7-GUI

EosFit7-GUI 是配套的图形界面程序：

```bash
# 下载 EosFit7-GUI
# 网址: https://www.cryst.ehu.es/cryst/get_software.html
```

## CrysFML EoS 模块的特点

### 1. Fortran 性能优势

- 高性能数值计算
- 经过充分测试和验证
- 被广泛引用（>500 次引用）

### 2. 完整功能

- P-V-T 关系（温度相关）
- 热 EoS 模型
- 更多 EoS 类型（如 APL, Kumar 等）
- 批量拟合工具

### 3. 与 FullProf Suite 集成

CrysFML 是 FullProf Suite 的一部分，可以：
- 结合结构精修
- 相变分析
- 多相 EoS 拟合

## Python 实现的优势

### 1. 易于集成

- 纯 Python，无需编译
- 使用 NumPy/SciPy 生态
- 易于与 PyQt6 GUI 集成

### 2. 交互式分析

- Jupyter Notebook 支持
- 实时参数调整
- 灵活的可视化

### 3. 可扩展性

- 易于添加新的 EoS 模型
- 可以结合机器学习方法
- 与其他 Python 工具集成

## 验证和测试

### 测试数据集

可以使用 CrysFML 论文中的测试数据验证实现：

```python
# MgO 测试数据 (来自 Angel et al. 2014)
V_data = np.array([74.68, 74.22, 73.48, 72.90, 72.28, 71.65])  # Å³
P_data = np.array([0.0, 2.01, 5.03, 7.49, 10.10, 12.84])  # GPa

# 期望结果 (BM3):
# V₀ = 74.698(6) Å³
# B₀ = 160.2(8) GPa
# B₀' = 4.0(1)
```

### 结果比较

运行测试比较 Python 实现与文献值：

```bash
python3 crysfml_eos_module.py
```

## 建议

### 如果需要 Fortran 版本

1. **学术研究**: 使用原始 CrysFML Fortran 代码，便于引用
2. **高性能计算**: Fortran 版本更快，适合大规模数据
3. **与 FullProf 集成**: 使用 CrysFML 原生集成

### 如果使用 Python 版本

1. **快速原型**: Python 实现更灵活
2. **交互式分析**: 适合探索性数据分析
3. **GUI 应用**: 与 PyQt6 无缝集成

## 引用信息

如果在研究中使用，请引用：

```bibtex
@article{angel2014eosfit7c,
  title={EosFit7c and a Fortran module (library) for equation of state calculations},
  author={Angel, Ross J and Alvaro, Matteo and Gonzalez-Platas, Javier},
  journal={Zeitschrift f{\"u}r Kristallographie-Crystalline Materials},
  volume={229},
  number={5},
  pages={405--419},
  year={2014},
  publisher={De Gruyter}
}
```

## 相关资源

### 官方网站

- CrysFML: https://www.ill.eu/sites/crystallography/crysfml/
- EosFit: https://www.rossangel.net/text_eosfit.htm
- FullProf Suite: https://www.ill.eu/sites/fullprof/

### 文档

- CrysFML 用户手册: 包含在发行版中
- EosFit7-GUI 手册: 详细的使用说明

### 相关软件

- **EosFit7-GUI**: 独立的 GUI 程序
- **PVT-Plot**: P-V-T 数据可视化
- **FullProf**: 结构精修套件

## 总结

当前项目使用的是基于 CrysFML 方法的 **Python 重新实现**，它：

✅ 实现了核心的 F-f 线性化算法  
✅ 支持主要的 EoS 模型  
✅ 提供交互式 GUI  
✅ 完全开源，易于修改  

❌ 不是原始 CrysFML Fortran 代码  
❌ 缺少一些高级功能（如 P-V-T）  
❌ 性能略低于 Fortran 版本  

如需原始 CrysFML Fortran 代码，请从 GitLab 下载完整的 CrysFML 库。
