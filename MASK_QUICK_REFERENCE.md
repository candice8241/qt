# Mask Module - Quick Reference

## 🎯 Quick Start

1. **Load Image**: Click `📂 Load Image` → Select diffraction data
2. **Choose Tool**: Select tool from dropdown (Circle, Rectangle, Polygon, etc.)
3. **Select Action**: Choose ⚪ Mask or ⚪ Unmask
4. **Draw**: Interact with the image canvas
5. **Save**: Click `💾 Save Mask` when done

## 🛠️ Drawing Tools

| Tool | How to Use | Icon |
|------|------------|------|
| **Select** | Pan/zoom without drawing | - |
| **Circle** | Click + drag to draw circle | ⭕ |
| **Rectangle** | Click + drag to draw rectangle | ▭ |
| **Polygon** | Click points → Right-click or Enter to finish | ⬡ |
| **Point** | Click to mask/unmask small region (5px radius) | • |
| **Threshold** | Click → Enter value → Mask pixels above threshold | 📊 |

## 🎨 Actions

| Action | Effect | When to Use |
|--------|--------|-------------|
| **Mask** | Add to mask (pixels will be ignored) | Block bad pixels, beamstop, edges |
| **Unmask** | Remove from mask (pixels will be used) | Restore good regions |

## ⚙️ Operations

| Button | Effect | Use Case |
|--------|--------|----------|
| **↕️ Invert** | Flip mask (masked ↔ unmasked) | Quick mask reversal |
| **➕ Grow** | Expand mask by 1 pixel | Ensure full coverage |
| **➖ Shrink** | Contract mask by 1 pixel | Remove edge artifacts |
| **🔧 Fill Holes** | Fill gaps inside masked regions | Clean up mask |

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Enter** | Finish polygon |
| **Escape** | Cancel polygon |

## 🖱️ Mouse Controls

| Action | Effect |
|--------|--------|
| **Left Click** | Start drawing / Add point |
| **Left Drag** | Draw shape (Circle/Rectangle) |
| **Right Click** | Finish polygon |
| **Scroll** | Zoom (if toolbar enabled) |

## 💾 File Operations

### Load Image
```
Formats: .h5, .hdf5, .tif, .tiff, .edf, .cbf, .png, .jpg
Path: Any accessible file
```

### Load Mask
```
Format: .npy (NumPy binary)
Must match image dimensions
```

### Save Mask
```
Format: .npy (NumPy binary)
Saves as boolean array (True = masked)
```

## 📐 Typical Workflow

### Basic Masking
```
1. Load diffraction image
2. Select Circle tool → Mask
3. Draw circle over beamstop
4. Select Threshold tool → Mask
5. Click → Enter value for hot pixels
6. Save mask
```

### Refine Existing Mask
```
1. Load image
2. Load existing mask
3. Select Circle tool → Unmask
4. Remove over-masked regions
5. Click Grow to expand coverage
6. Save updated mask
```

### Create Complex Mask
```
1. Load image
2. Use Polygon tool for irregular regions
3. Use Circle for round features
4. Use Threshold for intensity-based masking
5. Use Fill Holes to clean up
6. Save mask
```

## ⚠️ Common Issues

### Drawing not working?
- ✓ Check that image is loaded
- ✓ Verify tool is selected (not "Select")
- ✓ Click on image area (not outside)

### Polygon won't finish?
- ✓ Need at least 3 points
- ✓ Right-click or press Enter
- ✓ Press Escape to cancel

### Operations not working?
- ✓ Install scipy: `pip install scipy`
- ✓ Check that mask exists

### Can't see mask overlay?
- ✓ Mask exists but may be empty
- ✓ Try drawing something first
- ✓ Red overlay = masked pixels

## 💡 Pro Tips

1. **Contrast**: Adjust slider to see faint features
2. **Combine tools**: Use multiple tools for complex masks
3. **Start with threshold**: Quick way to mask hot pixels
4. **Grow after polygon**: Ensures full coverage at edges
5. **Save versions**: Save mask at different stages
6. **Use unmask**: Easier to unmask than redraw sometimes

## 🔄 Undo Workaround

No built-in undo yet. Workarounds:
- Save mask before major changes
- Use `🗑️ Clear All` to start over
- Load previous saved mask

## 📊 Visual Indicators

| Color | Meaning |
|-------|---------|
| **Red overlay** | Masked pixels (will be ignored) |
| **Yellow dashed** | Shape being drawn |
| **Yellow dots** | Polygon vertices |
| **Green text** | Successful operation |

## 🎯 Integration

Mask can be used in:
- **Powder Integration** (`batch_integration.py`)
- **Radial Integration** (if supported)
- **Any pyFAI-based analysis**

Mask is passed to pyFAI as boolean array where `True` = masked pixel.

---

**Quick Help**: Hover over buttons for tooltips (if implemented)
**Full Documentation**: See `MASK_INTERACTIVE_UPDATE.md`
