# Quick Reference Guide

## What Was Done

✅ **Integrated bin_config_dialog.py with powder_module.py**
✅ **Converted all Chinese comments to English**
✅ **All files compile successfully**

## Integration Features

### 1. H5 Preview Dialog (Sector Selection)
- **Button**: 🔍 H5 Preview & Select Region
- **Purpose**: Visually select azimuthal sector for integration
- **Output**: Single integration with selected sector

### 2. Bin Configuration Dialog (Azimuthal Binning)  
- **Button**: ⚙️ Configure Bins
- **Purpose**: Configure multiple azimuthal bins
- **Output**: Multiple integrations (one per bin)

## How to Use

### Use H5 Preview (Sector Mode)
```
1. Click "🔍 H5 Preview & Select Region"
2. Load H5 file
3. Set azimuth range (e.g., 0° - 90°)
4. Click "Draw" to visualize
5. Click "✓ Use for Integration"
6. Run Integration
```

### Use Bin Configuration (Bin Mode)
```
1. Click "⚙️ Configure Bins"
2. Quick Generate: Set 0-360°, 36 bins, click "Generate"
   OR Manual Add: Enter custom bins
3. Click "OK"
4. Run Integration
```

## Integration Modes Priority

1. **Bin Mode** (if bins configured) → Multiple output files
2. **Sector Mode** (if sector selected) → Single output file with sector
3. **Full Mode** (default) → Single output file full ring

## Output File Naming

- **Full/Sector**: `filename.xy`
- **Bin Mode**: `filename_Bin001.xy`, `filename_Bin002.xy`, ...

## Files Modified

- ✅ `bin_config_dialog.py` - Comments → English
- ✅ `powder_module.py` - Added bin config, comments → English
- ✅ `batch_integration.py` - Added bin mode support
- ✅ `h5_preview_dialog.py` - Already in English

## Key Functions

### powder_module.py
- `open_h5_preview()` - Opens H5 preview dialog
- `open_bin_config()` - Opens bin configuration dialog
- `run_integration()` - Handles all integration modes

### batch_integration.py
- `integrate_single(..., bins=None)` - Integrates with optional bins
- `run_batch_integration(..., bins=None)` - Main entry point

### bin_config_dialog.py
- `quick_generate()` - Auto-generate evenly-spaced bins
- `manual_add()` - Add custom bin
- `get_bins()` - Returns bin list

## Example Outputs

### Example: 3 files, 36 bins
```
Input:
  sample001.h5
  sample002.h5
  sample003.h5

Output (108 files):
  sample001_Bin001.xy ... sample001_Bin036.xy
  sample002_Bin001.xy ... sample002_Bin036.xy
  sample003_Bin001.xy ... sample003_Bin036.xy
```

## Testing

All files compile successfully:
```bash
python3 -m py_compile *.py
# Exit code: 0 ✅
```

## Documentation

- `INTEGRATION_SUMMARY.md` - Complete overview
- `H5_PREVIEW_INTEGRATION_SUMMARY.md` - H5 preview details
- `BIN_CONFIG_INTEGRATION_SUMMARY.md` - Bin config details
- `INTERACTION_FLOW.md` - H5 preview workflow
- `BIN_CONFIG_FLOW.md` - Bin config workflow
- `QUICK_REFERENCE.md` - This file

---

**Status**: ✅ Complete | **Date**: Dec 2, 2025 | **Version**: 1.0
