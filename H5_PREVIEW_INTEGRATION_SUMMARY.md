# H5 Preview Dialog Integration with Powder Module

## 概述 (Overview)

本次实现将 `h5_preview_dialog.py` 集成到 `powder_module.py` 中，允许用户在 H5 预览对话框中选择扇形区域，然后在积分时使用该区域进行扇区积分。

This implementation integrates `h5_preview_dialog.py` into `powder_module.py`, allowing users to select a sector region in the H5 preview dialog and use it for sector integration.

## 功能流程 (Workflow)

### 1. 打开 H5 预览对话框 (Open H5 Preview Dialog)
- 在 Powder Module 的 Integration Settings 部分，新增了一个"🔍 H5 Preview & Select Region"按钮
- 点击按钮后，会打开 H5 预览对话框
- 如果已经选择了 H5 文件作为输入，对话框会自动加载第一个 H5 文件

### 2. 选择扇形区域 (Select Sector Region)
在 H5 预览对话框中：
- 用户可以加载 H5 衍射图像
- 使用控制面板设置扇形参数：
  - **Azimuthal Range (方位角范围)**: 起始角度 - 结束角度 (度)
  - **Radial Range (径向范围)**: 最小半径 - 最大半径 (像素)
- 点击 "🎯 Draw" 按钮可视化选择的扇形区域
- 点击 "✓ Use for Integration" 按钮确认选择并返回到 Powder Module

### 3. 执行扇区积分 (Perform Sector Integration)
- 选择扇形区域后，Powder Module 会显示所选参数
- 运行积分时，batch_integration 会使用扇形参数进行积分
- pyFAI 的 `integrate1d` 方法会仅在指定的方位角范围内积分

## 代码修改 (Code Changes)

### 1. h5_preview_dialog.py
**新增功能：**
- 添加了 "Use for Integration" 按钮
- 添加了 `use_for_integration()` 方法来验证并返回选择
- 添加了 `get_sector_parameters()` 方法返回扇形参数字典

**返回的参数：**
```python
{
    'h5_file': str,        # H5 文件路径
    'azim_start': float,   # 起始方位角 (度)
    'azim_end': float,     # 结束方位角 (度)
    'rad_min': float,      # 最小半径 (像素)
    'rad_max': float,      # 最大半径 (像素，0 = 自动)
    'center_x': int,       # 中心点 X 坐标
    'center_y': int        # 中心点 Y 坐标
}
```

### 2. powder_module.py
**新增功能：**
- 导入 `H5PreviewDialog`
- 添加 `sector_params` 变量存储扇形参数
- 在 Integration Settings 中添加：
  - "🔍 H5 Preview & Select Region" 按钮
  - 扇形参数信息标签
- 添加 `open_h5_preview()` 方法：
  - 打开 H5 预览对话框
  - 接收并存储扇形参数
  - 更新界面显示
  - 自动填充输入文件路径
- 修改 `run_integration()` 方法：
  - 检查是否有扇形参数
  - 将方位角从度转换为弧度（pyFAI 要求）
  - 传递扇形参数给积分脚本
- 修改 `_create_integration_script()` 方法：
  - 接受 `sector_kwargs` 参数
  - 将扇形参数传递给 `run_batch_integration`

### 3. batch_integration.py
**新增功能：**
- 修改 `run_batch_integration()` 函数签名，添加 `sector_kwargs` 参数
- 将 `sector_kwargs` 合并到 `integration_kwargs` 中
- 参数会传递给 pyFAI 的 `integrate1d` 方法

**pyFAI 扇区积分参数：**
```python
integration_kwargs = {
    'azimuth_range': (azim_start_rad, azim_end_rad),  # 方位角范围（弧度）
    # ... 其他参数
}
```

## 使用示例 (Usage Example)

### 基本工作流程：
1. 打开 Powder XRD 模块
2. 点击 "🔍 H5 Preview & Select Region" 按钮
3. 在 H5 预览对话框中：
   - 加载 H5 文件（如果未自动加载）
   - 设置方位角范围，例如：0° - 90°
   - 设置径向范围，例如：100 - 0 (auto)
   - 点击 "Draw" 查看扇形区域
   - 点击 "✓ Use for Integration" 确认
4. 返回 Powder Module，查看扇形参数显示
5. 设置其他积分参数（PONI、mask、输出目录等）
6. 点击 "Run Integration" 执行扇区积分

### 扇区积分说明：
- **全积分（默认）**: 不选择扇形区域，直接运行积分
- **扇区积分**: 选择扇形区域后，仅对指定方位角范围进行积分
- **应用场景**: 
  - 研究各向异性样品
  - 分析特定方向的衍射峰
  - 排除某些方向的噪声或异常信号

## 技术细节 (Technical Details)

### 方位角定义：
- 0° = 正右方向（+X 轴）
- 逆时针旋转为正方向
- 范围：0° - 360°

### 坐标系统：
- 原点：图像中心（自动计算）
- X 轴：水平向右
- Y 轴：垂直向上

### pyFAI 集成参数：
```python
# 方位角范围（弧度）
azimuth_range = (azim_start * π/180, azim_end * π/180)

# 传递给 integrate1d
result = ai.integrate1d(
    data,
    npt=npt,
    mask=mask,
    unit=unit,
    azimuth_range=azimuth_range,  # 扇形积分关键参数
    **other_kwargs
)
```

## 注意事项 (Notes)

1. **可选功能**: 扇区积分是可选的，不选择扇形区域时执行全积分
2. **角度转换**: 界面使用度（°），内部转换为弧度传递给 pyFAI
3. **径向范围**: 目前未实现径向范围限制，仅实现方位角扇区积分
4. **多文件处理**: 扇形参数应用于所有批处理的 H5 文件
5. **参数持久化**: 扇形参数在当前会话中保持，直到重新选择或关闭程序

## 未来改进 (Future Improvements)

- [ ] 添加径向范围（radial_range）积分支持
- [ ] 支持多个扇形区域同时积分
- [ ] 保存和加载扇形参数配置
- [ ] 在积分结果文件名中标注扇形参数
- [ ] 添加扇形区域的可视化叠加到积分结果图上

## 测试建议 (Testing Recommendations)

1. 测试全积分（无扇形选择）
2. 测试单个扇形区域积分（例如：0-90°）
3. 测试不同方位角范围（例如：45-135°, 180-270°）
4. 测试边界情况（例如：0-360°，应等同于全积分）
5. 验证积分结果文件是否正确生成

---

**实现日期**: 2025-12-02
**作者**: AI Assistant with Cursor
**版本**: 1.0
