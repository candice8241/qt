# Mask Module Integration - Quick Reference

## What Changed

### Sidebar Updates
| Before | After | Status |
|--------|-------|--------|
| ⚗️ Powder Int. | ⚗️ Batch Int. | ✅ Renamed |
| 🔄 Radial Int. | (hidden) | ✅ Hidden |
| 🔬 SC | (hidden) | ✅ Hidden |
| (none) | 🎭 Mask | ✅ Added (top position) |

### New Button Order
```
🎭 Mask         ← NEW (1st position)
⚗️ Batch Int.   ← Renamed (2nd position)
🔬 BCDI Cal.
💎 Dioptas
📈 curvefit
📊 eosfit
```

## New Mask Module

### Quick Access
Click **🎭 Mask** in left sidebar

### Key Features
- 📂 **Load Image**: TIF, EDF, H5, HDF5
- 📂 **Load Mask**: NPY, EDF, TIF
- 🎨 **Drawing Tools**: Circle, Rectangle, Polygon, Threshold
- 💾 **Save Mask**: NPY, EDF, TIF
- 🗑️ **Clear All**: Remove all mask regions
- 📊 **Preview**: Interactive canvas with contrast control

### Basic Workflow
```
1. Click "🎭 Mask"
2. Load Image
3. Select Tool
4. Draw on image
5. Apply changes
6. Save mask
```

## Files Modified

| File | Change |
|------|--------|
| `main.py` | Added mask button, hidden SC/Radial buttons, renamed Powder→Batch |
| `mask_module.py` | NEW - Complete mask management module |

## Verification

All code compiles successfully:
```bash
python3 -m py_compile main.py mask_module.py
# Exit code: 0 ✅
```

## Documentation

- `MASK_MODULE_INTEGRATION_SUMMARY.md` - Complete details
- `MASK_INTEGRATION_QUICK_REF.md` - This file

---

**Status**: ✅ Complete | **Date**: Dec 2, 2025
