# Mask Module Integration Summary

## Changes Made

### 1. Main Window Sidebar Updates ✅

**Modified: `main.py`**

#### Buttons Visibility Changes:
- ✅ **Hidden**: "🔬 SC" button (Single Crystal)
- ✅ **Hidden**: "🔄 Radial Int." button (Radial Integration)
- ✅ **Renamed**: "⚗️ Powder Int." → "⚗️ Batch Int."
- ✅ **Added**: "🎭 Mask" button (placed above Batch Int.)

#### New Sidebar Order:
```
┌─────────────────┐
│  🎭 Mask        │ ← NEW (at top)
│  ⚗️ Batch Int.  │ ← Renamed from "Powder Int."
│  🔬 BCDI Cal.   │
│  💎 Dioptas     │
│  📈 curvefit    │
│  📊 eosfit      │
└─────────────────┘
```

### 2. Created Mask Module ✅

**New File: `mask_module.py`**

Designed with h5_preview_dialog style, featuring:

#### Features:
- **File Control**
  - Load diffraction images (TIF, EDF, H5, HDF5)
  - Load existing mask files (NPY, EDF, TIF)
  - Auto-initialize mask from image dimensions

- **Drawing Tools**
  - Tool selector: Select, Circle, Rectangle, Polygon, Threshold
  - Action selector: Mask Pixels / Unmask Pixels
  - Apply button to execute drawing

- **Interactive Preview**
  - Matplotlib canvas for image display
  - Log-scale display with adjustable contrast
  - Vertical contrast slider (Dioptas style)
  - Mouse position tracking
  - Mask overlay (red transparent overlay)
  - Mouse click events for drawing (placeholder)

- **Actions**
  - 💾 Save Mask (NPY, EDF, TIF formats)
  - 🗑️ Clear All (clear all mask regions)

#### UI Style:
- Similar to h5_preview_dialog.py layout
- Color-themed group boxes
- Compact control panels
- Large preview canvas with side slider
- Professional button styling

### 3. Integration Details

#### Module Initialization:
```python
# In main.py __init__:
self.mask_module = None

# Module frames dictionary:
self.module_frames = {
    "mask": None,      # NEW
    "powder": None,
    # ... other modules
}
```

#### Button Management:
```python
# Sidebar buttons:
self.mask_btn = self.create_sidebar_button(
    "🎭 Mask", 
    lambda: self.switch_tab("mask"), 
    is_active=False
)

# Hidden buttons (commented out):
# self.radial_btn = ...  # Hidden
# self.single_btn = ...   # Hidden
```

#### Module Switching:
```python
def switch_tab(self, tab_name):
    if tab_name == "mask":
        target_frame = self._ensure_frame("mask")
        if self.mask_module is None:
            self.mask_module = MaskModule(target_frame, self)
        # MaskModule sets up UI in __init__
```

#### Prebuilding:
```python
def prebuild_modules(self):
    # Prebuild mask module in background
    mask_frame = self._ensure_frame("mask")
    if self.mask_module is None:
        self.mask_module = MaskModule(mask_frame, self)
    mask_frame.hide()
```

## User Workflow

### Creating a Mask:

```
1. Click "🎭 Mask" in sidebar
   ↓
2. Click "📂 Load Image"
   - Select diffraction image
   - Image displays in preview
   ↓
3. Select drawing tool
   - Choose: Circle, Rectangle, Polygon, etc.
   - Choose action: Mask/Unmask pixels
   ↓
4. Draw on image (click to add shapes)
   ↓
5. Click "✓ Apply" to apply changes
   ↓
6. Click "💾 Save Mask" to save
```

### Loading Existing Mask:

```
1. Click "🎭 Mask"
   ↓
2. Click "📂 Load Mask"
   - Select existing mask file
   ↓
3. Optionally load image to view overlay
   ↓
4. Edit mask with drawing tools
   ↓
5. Save updated mask
```

## UI Comparison

### Before:
```
┌─────────────────┐
│  ⚗️ Powder Int. │
│  🔄 Radial Int. │
│  🔬 SC          │
│  🔬 BCDI Cal.   │
│  💎 Dioptas     │
│  📈 curvefit    │
│  📊 eosfit      │
└─────────────────┘
```

### After:
```
┌─────────────────┐
│  🎭 Mask        │ ← NEW
│  ⚗️ Batch Int.  │ ← RENAMED
│  🔬 BCDI Cal.   │
│  💎 Dioptas     │
│  📈 curvefit    │
│  📊 eosfit      │
└─────────────────┘
(SC and Radial Int hidden)
```

## Mask Module Layout

```
┌────────────────────────────────────────────────────────┐
│  🎭 Mask Creation & Management                         │
│  Create, edit, and manage detector masks               │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ File Control                                      │ │
│  │ [📂 Load Image] | [📂 Load Mask]                  │ │
│  │ File info: sample.h5 | Shape: (2048, 2048)       │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Drawing Tools                                     │ │
│  │ Tool: [Select▼] | Action: [Mask Pixels▼] [✓Apply]│ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Mask Preview (Click to draw)                     │ │
│  │ Position: (512, 512) | Mask: mask.npy            │ │
│  │                                                   │ │
│  │  ┌────────────────────────────────┐  ┌───┐      │ │
│  │  │                                 │  │Hi │      │ │
│  │  │                                 │  │gh │      │ │
│  │  │                                 │  ├───┤      │ │
│  │  │     Image with Mask Overlay    │  │███│      │ │
│  │  │                                 │  │███│      │ │
│  │  │                                 │  │███│      │ │
│  │  │                                 │  ├───┤      │ │
│  │  │                                 │  │Low│      │ │
│  │  └────────────────────────────────┘  │50%│      │ │
│  │                                       └───┘      │ │
│  └──────────────────────────────────────────────────┘ │
│                                                         │
│                   [💾 Save Mask]  [🗑️ Clear All]      │
└────────────────────────────────────────────────────────┘
```

## Technical Details

### Supported Image Formats:
- **Input**: TIF, TIFF, EDF, H5, HDF5
- **Mask Output**: NPY (NumPy), EDF, TIF

### Image Loading:
- H5/HDF5: Uses h5py, tries common dataset paths
- EDF/TIF: Uses fabio library
- Fallback: PIL/Pillow

### Mask Representation:
- Boolean NumPy array
- True = masked pixel (excluded from integration)
- False = unmasked pixel (included in integration)

### Display Features:
- Log-scale display: `log10(image + 1)`
- Contrast adjustment: 1-100% (percentile-based)
- Red overlay for masked regions (alpha=0.3)
- Grid overlay for pixel reference

### Drawing Tools (Placeholder):
- **Select**: No drawing, pan/zoom only
- **Circle**: Draw circular mask regions
- **Rectangle**: Draw rectangular mask regions
- **Polygon**: Draw polygonal mask regions
- **Threshold**: Mask pixels above/below threshold

*Note: Drawing functionality is stubbed out for now, ready for implementation*

## Code Files Modified

1. **main.py** (Modified)
   - Added mask button to sidebar
   - Hidden SC and Radial Int buttons
   - Renamed Powder Int to Batch Int
   - Added mask module initialization
   - Added mask case to switch_tab
   - Added mask to prebuild_modules

2. **mask_module.py** (New)
   - Complete mask creation/management module
   - Similar UI style to h5_preview_dialog
   - Interactive preview with contrast control
   - File loading and saving
   - Drawing tools framework

## Testing Checklist

- [x] Code compiles without errors
- [x] Mask button appears in sidebar
- [x] Mask button positioned above Batch Int
- [x] SC and Radial Int buttons hidden
- [x] Powder Int renamed to Batch Int
- [ ] Mask module opens when clicked
- [ ] Image loading works
- [ ] Mask loading works
- [ ] Mask saving works
- [ ] Contrast slider updates display
- [ ] Mouse tracking works
- [ ] Clear All works

## Future Enhancements

- [ ] Implement circle drawing tool
- [ ] Implement rectangle drawing tool
- [ ] Implement polygon drawing tool
- [ ] Implement threshold masking
- [ ] Add undo/redo functionality
- [ ] Add mask statistics (% masked pixels)
- [ ] Add mask validation
- [ ] Add mask templates (beamstop, hot pixels)
- [ ] Export mask to various formats
- [ ] Batch mask application to multiple images

---

**Implementation Date**: December 2, 2025
**Status**: ✅ Complete - Core functionality ready, drawing tools pending
**Version**: 1.0
