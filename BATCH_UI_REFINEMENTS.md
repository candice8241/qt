# Batch Module UI Refinements

## Changes Made

### 1. ✅ Removed Internal Panel Borders

**Header Panel** (title + load button):
- **Before**: 1px solid border (#CE93D8)
- **After**: No border (border: none)
- **Style**: Clean, minimal look

**File List Panel** (left sidebar):
- **Before**: 2px solid border (#CCCCCC)
- **After**: No border (border: none)
- **Panel type**: Changed from StyledPanel to NoFrame
- **Title**: Simplified from "📄 File List" (bold) to "File List" (normal)

### 2. ✅ Thinner Outer Purple Border

**Border Specifications**:
- **Before**: 5px thick
- **After**: 2px thin
- **Color**: #7E57C2 (purple) - unchanged
- **Style**: Solid line
- **Radius**: 6px (reduced from 10px)
- **Method**: Manual painting with QPainter

**Code**:
```python
pen = QPen(QColor("#7E57C2"), 2)  # 2px thin
painter.drawRoundedRect(
    rect.adjusted(1, 1, -2, -1),  # Optimized for right visibility
    6, 6  # Smaller radius
)
```

### 3. ✅ Right Border Visibility

**Adjustments Made**:

#### In batch_fitting_dialog.py:
```python
# Layout margins (left, top, right, bottom)
main_layout.setContentsMargins(3, 3, 10, 3)
#                              ↑      ↑
#                          Left:3px  Right:10px

# Border rectangle adjustment
rect.adjusted(1, 1, -2, -1)
#                    ↑
#                Less inset on right = more visible
```

#### In main.py:
```python
# Batch frame right margin
batch_frame.layout().setContentsMargins(0, 0, 20, 0)
#                                           ↑
#                                       20px right space
```

**Total right space**: 10px (widget) + 20px (frame) = **30px clearance**

### 4. ✅ Content Shifted Left

**Margin Adjustments**:

| Element | Before | After | Change |
|---------|--------|-------|--------|
| Widget left margin | 8px | 3px | -5px (shift left) |
| Widget right margin | 8px | 10px | +2px (for border) |
| Content padding | 12px | 8px | -4px (more compact) |
| Header padding | 8px | 5px | -3px (reduced) |
| File list padding | 10px | 8px | -2px (reduced) |

**Result**: Content shifts ~5-7px to the left

---

## Visual Comparison

### Before
```
┌─────────────────────────────────────┐
║ ╔═══════════════════════════════╗ ║ ← 5px thick border
║ ║ ┌────────────────────────────┐║ ║
║ ║ │ 📊 Batch Peak Fitting      │║ ║ ← Border on header
║ ║ └────────────────────────────┘║ ║
║ ║ ┌──┬────────────────────────┐ ║ ║
║ ║ │FL│                        │ ║ ║ ← Border on file list
║ ║ │  │                        │ ║ ║
║ ║ └──┴────────────────────────┘ ║ ║
║ ╚═══════════════════════════════╝ ║ ← Right border not visible
└─────────────────────────────────────┘
```

### After
```
┌───────────────────────────────────┐
│ ┌─────────────────────────────┐  │ ← 2px thin border
│ │ Batch Peak Fitting          │  │ ← No border
│ │ ┌──┬──────────────────────┐ │  │
│ │ │FL│                      │ │  │ ← No border
│ │ │  │                      │ │  │
│ │ └──┴──────────────────────┘ │  │
│ └─────────────────────────────┘  │ ← Right border visible!
└───────────────────────────────────┘
        ↑ Content shifted left
```

---

## Measurements

### Border Clearance

```
Screen Edge
│
│← 20px (batch_frame right margin)
│   │
│   │← 10px (widget right margin)
│   │   │
│   │   │← 2px (border width)
│   │   │ │
│   │   │ │  Widget Content
│   │   │ │  │
└───┴───┴─┴──┴───────
    30px total clearance
```

### Content Shift

```
Before:                    After:
│← 8px                     │← 3px
│   │                      │   │
│   │ Content             │   │ Content
│   │                      │   │
│   │← 12px padding       │   │← 8px padding
```

**Net shift**: 8px - 3px = 5px to the left

---

## Layout Structure

```
BatchFittingDialog (QWidget)
│
├─ paintEvent() draws 2px purple border
│
├─ main_layout (margins: 3, 3, 10, 3)
   │
   └─ container (QWidget, white background)
      │
      └─ layout (margins: 8, 8, 8, 8)
         │
         ├─ header (no border)
         │  ├─ title "Batch Peak Fitting"
         │  └─ load button
         │
         └─ splitter
            ├─ left_panel (no border)
            │  ├─ title "File List"
            │  ├─ file_list_widget
            │  └─ progress_label
            │
            └─ right_panel
               ├─ control_bar (blue border - kept)
               ├─ plot_canvas
               └─ navigation_bar (yellow border - kept)
```

---

## Border Summary

| Element | Border Status | Color | Purpose |
|---------|---------------|-------|---------|
| **Main Widget** | ✅ Visible (2px) | Purple | Module boundary |
| **Header** | ❌ Removed | - | Cleaner look |
| **File List** | ❌ Removed | - | Minimal design |
| **Control Bar** | ✅ Kept (2px) | Blue | Section separation |
| **Navigation Bar** | ✅ Kept (2px) | Yellow | Section separation |

---

## Testing Checklist

### Visual Verification

- [ ] **Main border**: 2px purple line visible on all sides
- [ ] **Right border**: Clearly visible (not cut off)
- [ ] **Header**: No border around title area
- [ ] **File list**: No border around file list panel
- [ ] **Control bar**: Blue border still visible
- [ ] **Navigation bar**: Yellow border still visible

### Layout Verification

- [ ] Content shifted left (compared to before)
- [ ] Right side has visible clearance
- [ ] Border is thin (not thick like before)
- [ ] No overlapping elements
- [ ] Professional, clean appearance

### Functional Verification

- [ ] All controls accessible
- [ ] No layout overflow
- [ ] Resizing works correctly
- [ ] Border stays visible when resizing

---

## Code Locations

### Files Modified

1. **batch_fitting_dialog.py**
   - Line ~138: `pen = QPen(QColor("#7E57C2"), 2)` - Thin border
   - Line ~143: `rect.adjusted(1, 1, -2, -1)` - Right visibility
   - Line ~160: `setContentsMargins(3, 3, 10, 3)` - Shift left
   - Line ~182: Header `border: none` - Remove border
   - Line ~205: File panel `border: none` - Remove border
   - Line ~212: Title simplified - Less emphasis

2. **main.py**
   - Line ~479: `setContentsMargins(0, 0, 20, 0)` - Right margin
   - Line ~576: `setContentsMargins(0, 0, 20, 0)` - Right margin

---

## Troubleshooting

### If Right Border Still Not Visible

1. **Check window size**
   ```python
   print(f"Widget width: {self.width()}")
   print(f"Frame width: {batch_frame.width()}")
   ```
   Widget width should be ~20-30px less than frame width

2. **Temporary high visibility test**
   ```python
   # In paintEvent():
   pen = QPen(QColor("#FF0000"), 5)  # Thick red
   ```

3. **Check parent widget**
   - Ensure scrollable_widget not clipping
   - Check for overflow: hidden CSS

### If Content Not Shifted Left Enough

Increase the shift:
```python
# In setup_ui():
main_layout.setContentsMargins(0, 3, 10, 3)  # 0px left
```

---

## Summary

**Changes**:
- ✅ Removed header panel border
- ✅ Removed file list panel border
- ✅ Thinned main border (5px → 2px)
- ✅ Ensured right border visibility (30px clearance)
- ✅ Shifted content left (~5px)

**Result**:
- Clean, minimal design
- Thin purple border visible on all sides
- More horizontal space for content
- Professional appearance

---

*Last Updated: December 3, 2024*
*Version: UI Refinements v2.0*
