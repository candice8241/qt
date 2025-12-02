# Bin Configuration Integration with Powder Module

## Overview

This implementation integrates `bin_config_dialog.py` with `powder_module.py`, allowing users to configure azimuthal binning for diffraction data integration. The system supports both quick bin generation and manual bin configuration.

## Features

### 1. Bin Configuration Dialog
- **Quick Generate**: Automatically generate evenly-spaced bins
  - Set start angle, end angle, and number of bins
  - Example: 0° to 360° divided into 36 bins (10° each)
- **Manual Add**: Add custom bins with specific ranges
  - Name each bin (e.g., "Bin001", "Sector_A")
  - Define start and end angles
- **Bin Management**: 
  - View all bins in a table
  - Delete individual bins
  - Clear all bins
- **Interactive Table**: Shows bin name, start angle, end angle, and delete button

### 2. Powder Module Integration
- Added "⚙️ Configure Bins" button in Integration Settings
- Displays bin configuration status
- Shows number of bins and sample ranges
- Integrates with existing sector integration feature

### 3. Batch Integration Support
- Each H5 file is integrated multiple times (once per bin)
- Output files are named with bin identifier: `{filename}_{binname}.{format}`
- Example: `sample_Bin001.xy`, `sample_Bin002.xy`, etc.
- Supports all output formats: .xy, .dat, .chi, .fxye, .svg, .png

## Workflow

```
1. Open Powder Module
   ↓
2. Click "⚙️ Configure Bins"
   ↓
3. In Bin Configuration Dialog:
   - Quick Generate: Set 0° to 360°, 36 bins
   OR
   - Manual Add: Add custom bins
   - Click OK to confirm
   ↓
4. Return to Powder Module
   - See "✓ N bins configured" message
   ↓
5. Set other integration parameters
   ↓
6. Click "Run Integration"
   ↓
7. System integrates each bin separately
   - Creates output files for each bin
   - Files named: filename_BinName.format
```

## Code Changes

### 1. bin_config_dialog.py
**Updated:**
- Converted all Chinese comments to English
- Dialog for configuring azimuthal bins
- Quick generation and manual addition modes
- Returns list of bins: `[{'name': str, 'start': float, 'end': float}, ...]`

**Key Methods:**
- `quick_generate()`: Generate evenly-spaced bins
- `manual_add()`: Add single custom bin
- `get_bins()`: Return configured bins list

### 2. powder_module.py
**Added:**
- Import `BinConfigDialog`
- `bin_config` variable to store bin configuration
- "⚙️ Configure Bins" button in UI
- Bin info label to display configuration
- `open_bin_config()` method to launch dialog and store results
- Pass bin configuration to integration script

**Updated:**
- Converted all Chinese comments to English
- `run_integration()` method to handle bin mode
- `_create_integration_script()` to pass bins parameter
- Priority: Bins > Sector > Full integration

### 3. batch_integration.py
**Updated:**
- `integrate_single()` method to support bins parameter
  - Loops through bins if provided
  - Sets azimuth_range for each bin
  - Saves output with bin name suffix
- `batch_integrate()` method to accept bins parameter
- `run_batch_integration()` function to accept bins parameter
- Prints bin mode information when enabled

## Integration Modes

The system now supports three integration modes with priority:

### Mode 1: Full Integration (Default)
- No sector or bin configuration
- Integrates entire diffraction ring
- Output: `{filename}.{format}`

### Mode 2: Sector Integration
- Single azimuthal sector selected via H5 Preview
- Integrates only specified angular range
- Output: `{filename}.{format}`
- Example: 0° to 90° sector

### Mode 3: Bin Mode (Highest Priority)
- Multiple azimuthal bins configured
- Integrates each bin separately
- Output: `{filename}_{binname}.{format}`
- Example: 36 bins of 10° each

**Priority:** Bin Mode > Sector Mode > Full Integration

## Usage Examples

### Example 1: Quick Generate 36 Bins
```
1. Click "⚙️ Configure Bins"
2. In dialog:
   Start: 0
   End: 360
   Bins: 36
   Click "Generate"
3. Click "OK"
4. Result: 36 bins (Bin001 to Bin036), 10° each
```

### Example 2: Custom Bins for Specific Analysis
```
1. Click "⚙️ Configure Bins"
2. Manual add:
   - Name: "Peak_A", Start: 45, End: 55
   - Name: "Peak_B", Start: 135, End: 145
   - Name: "Background", Start: 90, End: 100
3. Click "OK"
4. Result: 3 custom bins for specific regions
```

### Example 3: Combined with H5 files
```
Input: 10 H5 files, 36 bins configured
Output: 10 × 36 = 360 integrated files
  - file1_Bin001.xy, file1_Bin002.xy, ..., file1_Bin036.xy
  - file2_Bin001.xy, file2_Bin002.xy, ..., file2_Bin036.xy
  - ...
  - file10_Bin001.xy, ..., file10_Bin036.xy
```

## Technical Details

### Azimuthal Binning
- Each bin defines an angular sector
- pyFAI's `integrate1d` is called with `azimuth_range` parameter
- Angles converted from degrees to radians internally
- Integration performed sequentially for each bin

### File Naming Convention
```
Format: {basename}_{binname}.{extension}

Examples:
- Single integration: sample_001.xy
- Bin mode: sample_001_Bin001.xy
                sample_001_Bin002.xy
                ...
```

### Performance Considerations
- Bin mode multiplies processing time by number of bins
- 10 files × 36 bins = 360 integrations
- Progress bar shows per-file progress
- Each bin integration is independent

### Data Structure
```python
bins = [
    {
        'name': 'Bin001',
        'start': 0.0,    # degrees
        'end': 10.0      # degrees
    },
    {
        'name': 'Bin002',
        'start': 10.0,
        'end': 20.0
    },
    # ... more bins
]
```

## UI Changes

### Integration Settings Panel

**Before:**
```
┌─────────────────────────────────────┐
│ PONI File:        [...] [Browse]   │
│ Mask File:        [...] [Browse]   │
│ Input Pattern:    [...] [Browse]   │
│ Output Directory: [...] [Browse]   │
│ Dataset Path:     [...] [Browse]   │
│                                     │
│ Sector Integration (Optional):     │
│ [🔍 H5 Preview & Select Region]    │
│ No sector selected                  │
│                                     │
│        [Run Integration]            │
└─────────────────────────────────────┘
```

**After:**
```
┌─────────────────────────────────────┐
│ PONI File:        [...] [Browse]   │
│ Mask File:        [...] [Browse]   │
│ Input Pattern:    [...] [Browse]   │
│ Output Directory: [...] [Browse]   │
│ Dataset Path:     [...] [Browse]   │
│                                     │
│ Sector Integration (Optional):     │
│ [🔍 H5 Preview & Select Region]    │
│ No sector selected                  │
│                                     │
│ Azimuthal Binning (Optional):      │ ◄── NEW
│ [⚙️ Configure Bins]                 │ ◄── NEW
│ ✓ 36 bins configured                │ ◄── NEW
│                                     │
│        [Run Integration]            │
└─────────────────────────────────────┘
```

## Comments Translation

All files now use English comments:
- ✅ `bin_config_dialog.py` - All comments in English
- ✅ `powder_module.py` - All comments in English  
- ✅ `h5_preview_dialog.py` - Already in English
- ✅ `batch_integration.py` - Updated with English comments

## Testing Recommendations

1. **Test Quick Generate**
   - Generate 36 bins (0° to 360°)
   - Verify 36 output files per H5 file
   - Check angular ranges in files

2. **Test Manual Add**
   - Add 3-5 custom bins
   - Verify correct angular ranges
   - Check bin naming in output files

3. **Test Priority**
   - Configure both bins and sector
   - Verify bins take priority
   - Clear bins, verify sector works
   - Clear both, verify full integration works

4. **Test Edge Cases**
   - Empty bin list (should show error)
   - Single bin covering full range (0° to 360°)
   - Overlapping bins (should work independently)
   - Many bins (100+) for performance

5. **Test Output**
   - Verify file naming: `{basename}_{binname}.{format}`
   - Check all output formats work with bins
   - Verify data integrity in each bin file

## Future Enhancements

- [ ] Add bin visualization on H5 preview dialog
- [ ] Support bin configuration import/export (JSON/CSV)
- [ ] Add preset bin configurations (e.g., "36 bins", "72 bins")
- [ ] Support radial binning in addition to azimuthal
- [ ] Add bin overlap detection and warnings
- [ ] Create stacked plots per bin group
- [ ] Add bin color coding in output plots

---

**Implementation Date**: 2025-12-02
**Author**: AI Assistant with Cursor
**Version**: 1.0
