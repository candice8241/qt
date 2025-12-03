# Batch Module Quick Reference Guide

## 🎯 New Features at a Glance

### 1. Configurable Peak Grouping
**Overlap FWHM× Parameter** (Default: 1.5)
- Controls when peaks are grouped together for simultaneous fitting
- Lower values (1.0-1.5): Group only closely overlapping peaks
- Higher values (2.0-5.0): Group peaks with larger separations
- **When to adjust**:
  - Narrow, closely spaced peaks → use 1.0-1.5
  - Broad, overlapping peaks → use 2.0-5.0

### 2. Configurable Fitting Window
**Fit Window× Parameter** (Default: 3.0)
- Controls the data window size used for fitting each peak
- Smaller values (2.0-2.5): Fit only near peak center
- Larger values (3.0-4.0): Include more baseline data
- **When to adjust**:
  - Sharp, narrow peaks → use 2.0-2.5
  - Broad peaks or noisy data → use 3.0-4.0

### 3. Enhanced UI with Visual Borders
- **Purple border**: Main module boundary
- **Light purple**: Header section (title + load folder)
- **Blue border**: Control panel (all fitting controls)
- **Yellow border**: Navigation bar (file navigation + save)

## 📐 Parameter Examples

### Example 1: Well-Separated Narrow Peaks
```
Overlap FWHM× = 1.0   (don't group isolated peaks)
Fit Window×   = 2.5   (narrow window for sharp peaks)
```

### Example 2: Closely Overlapping Peaks
```
Overlap FWHM× = 2.0   (group nearby peaks)
Fit Window×   = 3.0   (standard window)
```

### Example 3: Broad Diffuse Peaks
```
Overlap FWHM× = 1.5   (standard grouping)
Fit Window×   = 4.0   (wider window for broad peaks)
```

### Example 4: Complex Multi-Peak Regions
```
Overlap FWHM× = 3.0   (aggressive grouping)
Fit Window×   = 3.5   (larger window for stability)
```

## 🎨 UI Layout (Row 1 of Control Bar)

```
┌────────────────────────────────────────────────────────────────────────┐
│ Mode: [🔴 Peak] [🔵 Background]  │  Fit Method: [Pseudo-Voigt ▼]      │
│                                   │                                     │
│ Overlap FWHM×: [1.5]  │  Fit Window×: [3.0]                           │
└────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start Workflow

1. **Load Data**
   - Click "📁 Load Folder"
   - Select folder with .xy files

2. **Adjust Parameters** (if needed)
   - Set Overlap FWHM× based on peak spacing
   - Set Fit Window× based on peak width

3. **Add Peaks & Background**
   - Switch mode: P (peak) or B (background)
   - Left-click to add
   - Right-click to remove
   - Or use "🔍 Auto Detect"

4. **Fit**
   - Space: Fit current file
   - Enter: Auto-fit all files
   - Arrows: Navigate between files

5. **Save**
   - Click "💾 Save All Results"

## 🔍 Troubleshooting

### Poor Fit Quality (Low R²)
**Symptoms**: R² < 0.92, warning message appears

**Solutions**:
1. Increase Fit Window× (try 3.5 or 4.0)
2. Add more background points
3. Adjust Overlap FWHM× if peaks are grouped incorrectly
4. Manually adjust peak positions

### Peaks Not Grouping Correctly
**Symptoms**: Should-be-grouped peaks fitted separately

**Solutions**:
1. Increase Overlap FWHM× (try 2.0 or higher)
2. Check peak detection - ensure all peaks are marked
3. Verify FWHM estimation is reasonable

### Fitting Takes Too Long
**Symptoms**: Slow fitting, especially for multi-peak groups

**Solutions**:
1. Decrease Overlap FWHM× to avoid unnecessary grouping
2. Decrease Fit Window× to reduce data points
3. Remove unnecessary background points

## 📊 Algorithm Comparison

### Old Algorithm (Fixed Parameters)
```python
overlap_mult = 1.5      # Hard-coded
fit_window_mult = 3.0   # Hard-coded
```

### New Algorithm (Configurable)
```python
overlap_mult = self.overlap_threshold      # User adjustable
fit_window_mult = self.fitting_window_multiplier  # User adjustable
```

## 💡 Tips & Best Practices

### For Best Results
1. **Start with defaults** (Overlap FWHM× = 1.5, Fit Window× = 3.0)
2. **Adjust based on data**:
   - High noise → increase Fit Window×
   - Complex overlaps → increase Overlap FWHM×
   - Sharp peaks → decrease Fit Window×
3. **Test on first file** before auto-fitting all files
4. **Use overlap mode** to compare multiple patterns

### Parameter Selection Guide

| Peak Characteristic | Overlap FWHM× | Fit Window× |
|---------------------|---------------|-------------|
| Narrow & Isolated   | 1.0 - 1.2     | 2.0 - 2.5   |
| Standard XRD        | 1.5 - 2.0     | 3.0         |
| Broad & Overlapping | 2.0 - 3.0     | 3.5 - 4.0   |
| Complex Multi-peak  | 2.5 - 5.0     | 3.5 - 4.5   |

## 🎨 Visual Elements

### Border Color Scheme
- **Purple (#7E57C2)**: Main module border - indicates batch module boundary
- **Light Purple (#CE93D8)**: Header section - file loading area
- **Blue (#90CAF9)**: Control panel - fitting parameters and actions
- **Yellow (#FFD54F)**: Navigation bar - file browsing and saving

### Why Borders?
- **Visual Clarity**: Easy to identify different functional areas
- **Professional Look**: Clean, modern interface
- **User Guidance**: Color-coded sections guide workflow
- **Boundary Definition**: Clear separation from other modules

## 📝 Keyboard Shortcuts

All previous shortcuts remain active:
- **Enter**: Start auto-fitting
- **Space**: Fit current file
- **Arrow Keys**: Navigate files
- **A**: Auto-detect peaks
- **C**: Clear all
- **P**: Peak mode
- **B**: Background mode
- **R**: Reset zoom
- **O**: Toggle overlap

## 🔄 Accessing Batch Module

### Primary Method (Recommended)
```
Main Application → 📊 Batch (sidebar)
```

### Alternative Method
```
python batch_module.py
```

**Note**: Curvefit module is now hidden. Use the dedicated Batch button instead.

---

## Summary

The updated batch module provides:
✅ Flexible peak grouping control
✅ Adjustable fitting windows
✅ Professional bordered interface
✅ Consistent with auto_fitting_module
✅ User-friendly parameter adjustment
✅ Real-time parameter updates

For detailed technical information, see `BATCH_MODULE_UPDATES.md`.
