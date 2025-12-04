# CrysFML Algorithm Replication Summary

## 目的 (Purpose)

将 `crysfml_eos_module.py` 中的三阶 Birch-Murnaghan 拟合算法 1:1 完全复刻到 `interactive_eos_gui.py` 中，确保 GUI 中的拟合结果与核心算法完全一致。

Replicate the third-order Birch-Murnaghan fitting algorithm from `crysfml_eos_module.py` 1:1 into `interactive_eos_gui.py` to ensure complete consistency between GUI fitting results and the core algorithm.

## 修改内容 (Changes Made)

### 1. 核心算法复刻 (Core Algorithm Replication)

在 `InteractiveEoSGUI` 类中添加了以下静态方法和实例方法，完全复刻自 `crysfml_eos_module.py`:

#### `_birch_murnaghan_3rd_pv()` - 三阶 BM 压力计算
- **源代码**: `crysfml_eos_module.py` lines 176-205
- **功能**: 使用 Eulerian 应变公式计算三阶 Birch-Murnaghan 状态方程的压力
- **关键特性**: 使用 `f` 和 `(1+2f)` 表达式，与 F-f 线性化方法保持一致，避免数值误差

```python
@staticmethod
def _birch_murnaghan_3rd_pv(V: np.ndarray, V0: float, B0: float, B0_prime: float) -> np.ndarray:
    f = 0.5 * ((V0 / V) ** (2 / 3) - 1.0)
    prefactor = 3.0 * B0 * f * (1.0 + 2.0 * f) ** 2.5
    correction = 1.0 + 1.5 * (B0_prime - 4.0) * f
    return prefactor * correction
```

#### `_birch_murnaghan_f_F_transform()` - F-f 应变-应力转换
- **源代码**: `crysfml_eos_module.py` lines 441-470
- **功能**: 将 P-V 数据转换为归一化应变-应力 (f-F) 形式
- **关键特性**: CrysFML 核心方法，线性化 Birch-Murnaghan 方程，实现稳定的 B0' 拟合

```python
@staticmethod
def _birch_murnaghan_f_F_transform(V_data, P_data, V0_estimate):
    # 计算 Eulerian 应变
    x = (V0_estimate / V_data) ** (1.0/3.0)
    f = 0.5 * (x**2 - 1.0)
    
    # 计算归一化应力（避免除零）
    denominator = 3.0 * f * (1.0 + 2.0*f)**(5.0/2.0)
    # ... 小应变处理 ...
```

#### `_fit_birch_murnaghan_3rd_linear()` - 两阶段线性拟合
- **源代码**: `crysfml_eos_module.py` lines 472-708
- **功能**: 使用 F-f 线性化方法进行两阶段拟合
- **关键特性**: 
  - 阶段 1: 迭代优化 V0 和 B0
  - 阶段 2: 线性回归 F vs f 获得稳定的 B0'
  - Tikhonov 正则化防止 B0' 发散
  - 物理约束 (B0': 2.0-8.0)
  - 完整的误差传播

```python
def _fit_birch_murnaghan_3rd_linear(self, V_data, P_data, regularization_strength):
    # 物理边界
    B0_PRIME_MIN = 2.0
    B0_PRIME_MAX = 8.0
    
    # 阶段 1: 迭代优化 V0
    for iteration in range(10):
        f, F = self._birch_murnaghan_f_F_transform(V_data, P_data, V0_current)
        # CrysFML 加权方案
        weights = 1.0 / (f**2 + 0.001)
        # Tikhonov 正则化
        lambda_reg = regularization_strength * np.mean(weights)
        # ... 线性回归求解 ...
    
    # 阶段 2: 最终拟合
    # ... 完整的误差估计和物理约束 ...
```

#### `_smart_initial_guess()` - 智能初始猜测
- **源代码**: `crysfml_eos_module.py` lines 377-439
- **功能**: 基于数据特征的智能初始参数估计
- **关键特性**: 
  - 使用低压数据外推 V0
  - 从压缩率估计 B0
  - 物理约束和合理性检查

### 2. GUI 方法更新 (GUI Methods Updated)

所有使用拟合算法的方法都已更新为优先使用复刻的算法:

#### `update_manual_fit()`
- **修改**: 对 BM3 使用 `_birch_murnaghan_3rd_pv()` 计算压力
- **影响**: 手动参数调整时的实时更新

#### `fit_unlocked()`
- **修改**: 当所有参数都未锁定且为 BM3 时，使用 `_fit_birch_murnaghan_3rd_linear()`
- **影响**: 拟合未锁定参数时的算法选择

#### `fit_multiple_strategies()`
- **修改**: 将复刻的 F-f 线性化方法作为第一策略
- **影响**: 多策略拟合的优先级和成功率

#### `update_plot()`
- **修改**: 对 BM3 使用 `_birch_murnaghan_3rd_pv()` 绘制拟合曲线
- **影响**: 绘图的数值一致性

#### `_format_results_output()`
- **修改**: 对 BM3 使用 `_birch_murnaghan_3rd_pv()` 计算残差
- **影响**: 结果输出的数值一致性

#### `reset_parameters()`
- **修改**: 使用 `_smart_initial_guess()` 获取初始参数
- **影响**: 参数重置的智能化

### 3. 依赖更新 (Dependencies Updated)

添加了必要的类型提示导入:

```python
from typing import Tuple
```

## 算法一致性 (Algorithm Consistency)

### 关键保证 (Key Guarantees)

1. **完全一致的公式**: 所有数学公式与 `crysfml_eos_module.py` 完全一致
2. **相同的数值精度**: 使用相同的浮点运算和数值处理方法
3. **一致的物理约束**: B0' 范围 (2.0-8.0), B0 范围 (20-800 GPa)
4. **相同的正则化方法**: Tikhonov 正则化强度和权重方案
5. **统一的误差传播**: 协方差矩阵和误差估计方法

### 代码对应关系 (Code Correspondence)

| GUI 方法 | 源代码位置 | 功能 |
|---------|-----------|------|
| `_birch_murnaghan_3rd_pv()` | lines 176-205 | BM3 压力计算 |
| `_birch_murnaghan_f_F_transform()` | lines 441-470 | F-f 转换 |
| `_fit_birch_murnaghan_3rd_linear()` | lines 472-708 | 两阶段拟合 |
| `_smart_initial_guess()` | lines 377-439 | 初始猜测 |

## 使用场景 (Use Cases)

### 何时使用复刻算法 (When Replicated Algorithm is Used)

1. **手动参数调整**: 实时更新拟合曲线
2. **自动拟合 (BM3, 无锁定)**: 优先使用 F-f 线性化
3. **多策略拟合**: 作为第一策略尝试
4. **参数重置**: 智能初始猜测

### 何时使用外部 fitter (When External Fitter is Used)

1. **非 BM3 模型**: Murnaghan, Vinet, BM2, BM4 等
2. **有参数锁定**: 需要约束优化
3. **复刻算法失败**: 回退到外部 fitter

## 验证 (Verification)

### 语法检查
```bash
python3 -m py_compile interactive_eos_gui.py
```
✅ 编译成功，无语法错误

### 数值一致性测试建议
1. 使用相同的测试数据分别在 GUI 和模块中拟合
2. 比较参数值 (V0, B0, B0')
3. 比较统计指标 (R², RMSE, χ²)
4. 比较残差分布

## 优势 (Advantages)

1. **完全可控**: GUI 不依赖外部模块的黑盒实现
2. **调试方便**: 可以直接在 GUI 中修改和调试算法
3. **数值一致**: 避免因版本差异导致的结果不一致
4. **性能优化**: 减少函数调用开销
5. **独立性强**: GUI 可以独立验证算法正确性

## 注意事项 (Notes)

1. **维护同步**: 如果 `crysfml_eos_module.py` 算法更新，需要同步更新 GUI 中的复刻代码
2. **测试重要**: 每次修改后需要进行完整的数值测试
3. **文档清晰**: 复刻代码中包含详细注释，标明源代码位置
4. **版本控制**: 记录复刻时的源代码版本和日期

## 未来改进 (Future Improvements)

1. 添加单元测试验证算法一致性
2. 实现其他 EoS 模型的复刻 (如需要)
3. 优化性能（如向量化计算）
4. 添加更多物理约束选项

---

**修改日期**: 2025-12-04  
**修改人**: Claude AI Assistant  
**验证状态**: ✅ 语法正确，待数值测试
